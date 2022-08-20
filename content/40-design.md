# Design

This chapter presents a design for implementing sharding in Kubernetes controllers to make them horizontally scalable.
The presented design includes well-known approaches for sharding in distributed databases and applies them to the problem in Kubernetes controllers.
Approaches are chosen to fulfill the requirements in [@sec:requirements].
First, the overall architecture of the design is introduced.
After that, different aspects of the design are described in detail.

## Architecture

![Kubernetes controller sharding architecture](../assets/design-overview.pdf)

The design architecture heavily builds upon existing mechanisms of the Kubernetes API and controllers.
It reuses established approaches from distributed databases and maps them to Kubernetes in a way that sharding is accomplished in a "Kubernetes-native" manner in order to leverage as much of the existing controller infrastructure as possible.

Firstly, multiple instances of a single controller are deployed with the same configuration.
All instances are equal, though they are differentiated by a unique instance ID.
In addition to the usual controllers, a new controller is added to all instances: the sharder.
The sharder is a controller that reconciles API objects of a given kind and assigns them to the individual controller instances.
It persists object assignments by setting the `shard` label on the objects themselves to the ID of the responsible instance.
As the sharder itself is responsible for mutating all API objects of a given kind, it must run under the usual leader election.
I.e., there is only a single active sharder at any given time and additional sharder instances are in stand-by.
The sharder itself watches and caches all API objects of the sharded kind.
However, it uses a metadata-only watch to minimize the resulting resource usage.

Each controller instance ("shard") maintains an individual lease ("shard lease"), which is used as a heartbeat resource to inform the sharder about the health status of all instances.
The sharder watches the shard leases in addition to the sharded API objects themselves in order to react on state changes, e.g., addition or removal of shards.
The sharded controllers watch and cache only the objects they are responsible for by filtering the watch/cache using a label selector on the `shard` label.

## Membership and Failure Detection

To address [requirement @sec:req-membership], a lease-based membership and failure detection mechanism is used.
The mechanism is heavily inspired by Bigtable [@bigtable2006] but adapted to use Kubernetes `Lease` objects stored in etcd instead of leases stored in Chubby [@chubby2006].

The sharder performs usual leader election to ensure that there is only one active sharder at any given time.
Additionally, each shard maintains an individual shard lease.
Like usual leader election, it uses the `Lease` API resource including the same fields and semantics.
However, shard leases use individual names that are equal to the shard's instance ID.
The instance ID needs to be stable between restarts of the shard, so the hostname is used, i.e. the controller's Pod name.
On startup, the shards acquire the respective shard lease using the instance ID as name and holder identity.
As with usual leader election, the shards periodically renew their leases after a configured duration.
As long as the shard actively holds its lease, it watches and reconciles objects that are assigned to itself.
If the shard fails to renew its lease within a configured period, it needs to stop all sharded controllers immediately and terminate.

- sharder watches leases
- as long as instance holds its lease
  - sharder considers it "ready" and assigns objects to it
- on termination
  - instance releases its lease
  - sharder considers instances as "dead", moves assigned objects
  - idea: StatefulSet could be used for stable hostname to minimize movements during rolling updates
- on failure
  - instance fails to renew its lease within `leaseDurationSeconds`
  - sharder considers instance as "expired", waits for another `leaseDurationSeconds`
  - if instance comes up again and renews its lease, sharder considers instance as ready again
  - if instance still doesn't renew lease within timeout, sharder consideres instance as "uncertain" and tries to acquire instance lease once (to ensure API server availability/connectivity) with double `leaseDurationSeconds`
  - if successful, instance is considered "dead", sharder moves assigned objects
  - instance is free to re-acquire lease once it comes up again after lease has expired
  - if successful, instance is considered "ready" again
- sharder cleans up "dead" leases after 1 minute ("orphaned")

## Partitioning

- similar to Cassandra, Dynamo
- sharding algorithm:
  - consistent hashing for stable assignments and simple (deterministic) logic
  - virtual nodes for balanced distribution in small clusters
    - number of virtual nodes per instance is specified by label on lease -> future work
  - every object is assigned to exactly one instance
- partition key:
  - default: by `GroupKind` + namespaced name + uid
    - done in order to distribute objects of different kind with identical names
  - challenge: controller doesn't only watch controlled object, but also controlled objects and dependents
  - owner and owned object need to have identical partition key, so they are assigned to same instance
  - allow mapping from object to other object, that should be used as partition key
    - e.g., map to controlling object (sensible for most controllers)

## Coordination and Object Assignment

- unlike distributed databases
  - no request coordination is needed -> not persisted externally in dedicated store
  - assignment information not needed by all instances -> not propagating via gossip
- sharder assigns objects to instances
  - adds labels to objects
- instances need to know which objects are assigned to them:
  - labels used for filtered watches
  - makes use of already existing watches in controllers, only need to add label selector
  - once labels are persisted in etcd, no additional coordination is needed -- sharder is not on the critical path for all reconciliations
  - controllers simply rebuild filtered watches after restart
- objects are not assigned when sharder stops working (should recover quickly via active-passive HA though)
- challenge: labels must not be mutated by user
  - can be prevented via validating webhook
- challenge: multiple controllers in same instance might work on the same object kind, share the same cache by default
  - neglected for now (?)
  - solution: multiple caches with different selectors?
  - -> future work
- challenge: relation between objects of same kind
  - example: scheduler: pod anti affinity
  - -> future work

## Preventing Concurrency

- concurrency generally prevented as long as assignments do not change
- however, concurrency needs to be prevented when moving objects
- old instance needs to stop working on moved objects before new instance picks up objects

- when moving objects from ready instance (rebalancing during scale-out, movement during rolling update):
  - challenge: system is pull/watch-based (no request routing), watches/caches might lag behind
  - sharder can't know if instances already observed the movement
  - instances need to acknowledge movement and stop working on object accordingly
  - protocol/flow to ensure, that controllers have observed movement
    - on desire to move object: sharder adds "drain" label, indicating that the object should be moved
    - when controller observes the drain label, it must remove it as well as the shard label, marking the object as drained/unassigned
    - once sharder observes that object is drained, it can be reassigned
    - if controller doesn't remove the drain label, sharder removes it forcefully when instance gets unavailable
  - facilitates fast movements with ready instances
- when moving objects from terminating instance (rebalancing during scale-down, moving during rolling update):
  - instance releases its own lease
  - objects are reassigned immediately, sharder skips drain operation
- when moving objects from dead instance (rebalancing after instance failure):
  - after lease expiration (failure detected by sharder), objects are forcefully moved
  - if instance comes up again, objects can be assigned to it again once it renewed its lease
- alternative: consensus/gossip based concurrency control
  - make things more complicated: implementation-wise, more communication involved
  - adds another failure domain: peer-to-peer communication
- alternative: static hash slots (comparable to Redis) instead of consistent hashing with lease per slot
  - high overhead for lease updates
  - doesn't scale, etcd as bottleneck
- alternative: short period of no reconciliation (~15 seconds) between unassigning and reassigning
  - would need to prevent unnecessary movement during rolling updates
  - e.g., move all objects belonging to one virtual node in batch, one virtual node at a time

## Alternatives Considered

- sharding by resource
  - can't be done dynamically / during runtime (or at least that's more difficult)
  - unbalanced distribution / no control over shard sizes
  - controllers probably need to list/cache resources, that are handled by other controllers -> overhead, scalability benefits questionable
  - doesn't provide HA / multiple instances for controllers
- sharding by namespace
  - one controller per namespace
    - easy to implement via operator/meta-controller
    - dedicated RBAC, ...
    - still caches cluster-scoped resources
    - high overhead, scalability benefits questionable
  - multiple namespaces per controller instance
    - label namespaces with shard id, reconstruct cache/watches on changes to set of responsible namespaces
    - -> restart of controller's necessary?
    - restart of caches/controllers undesirable
      - restarts are costly
      - reduces scalability benefits
