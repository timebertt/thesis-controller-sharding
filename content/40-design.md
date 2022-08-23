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

## Membership and Failure Detection {#sec:des-membership}

To address [requirement @sec:req-membership], a lease-based membership and failure detection mechanism is used.
The mechanism is heavily inspired by Bigtable [@bigtable2006] but adapted to use Kubernetes `Lease` objects stored in etcd instead of leases stored in Chubby [@chubby2006].

The sharder performs usual leader election to ensure that there is only one active sharder at any given time.
Additionally, each shard maintains an individual shard lease.
Like usual leader election, the `Lease` API resource with the same fields and semantics is used for this purpose.
However, shard leases use individual names that are equal to the shard's instance ID.
The instance ID needs to be stable between restarts of the shard, so the hostname is used, i.e. the controller's Pod name.
On startup, the shards acquire the respective shard lease using the instance ID as name and holder identity.
As with usual leader election, the shards periodically renew their leases after a configured duration.
As long as the shard actively holds its lease, it watches and reconciles objects that are assigned to itself.
If the shard fails to renew its lease within a configured period, it needs to stop all sharded controllers immediately and terminate.

The sharder controller watches all shard leases, which allows it to discover all available instances and immediately react to state changes.
As long as a shard holds its lease, the sharder considers it for partitioning.
On shard termination, the shard unsets the lease's holder identity field to release its lease.
This signals a voluntary disruption to the sharder, which immediately removes the instance from the partitioning.
With this, all objects assigned to the terminated shard are moved to other available instances.

Shard failures are detected by checking the leases' `renewTimestamp` field.
If a shard fails to renew its lease within `leaseDurationSeconds`, the lease is considered expired.
To decrease sensitivity of the system, the sharder waits for another `leaseDurationSeconds` and allows the instance to renew its lease again.
If the shard comes available again by renewing its lease it is considered ready again.
If the shard fails to renew its lease though, the sharder considers the instance unavailable.
However, before it removing the instance from partitioning, it tries to acquire the shard lease once.
This is done to ensure the API server is functioning well and the sharder doesn't act on stale lease data.
If the sharder is able to acquire the shard lease, it considers the instance dead, removes it from partitioning and moves objects to available instances.
Afterwards, the sharder doesn't touch the shard lease anymore.
With this, the shard is allowed to acquire its lease once it comes up again after the lease duration set by the sharder has passed.
If this is successful, the instance is considered ready and considered again for partitioning.

The sharder garbage collects leases of dead shards after 1 minute of inactivity.
With this, leases of voluntarily terminated instances as well as failed instances get cleaned up eventually.

## Partitioning

To address [requirement @sec:req-partitioning], a variant of consistent hashing is used as described in [@karger1997consistent; @stoica2001chord].
With this, partitioning is done similarly as in Apache Cassandra [@cassandradocs] and Amazon Dynamo [@dynamo2007] but adapted to use Kubernetes API object metadata as input.
Consistent hashing is chosen because it minimizes movement on addition and removal of instances.
Also, it provides a simple and deterministic algorithm for determining the responsible shard solely based on the set of available instances.
Therefore, no state of the partitioning algorithm must be stored apart from the instance states available through the membership mechanism ([@sec:des-membership]).
The sharder can simply reconstruct the hash ring based on this information after a restart or leader transition without risking inconsistency or unstable assignments.
In order to provide a balanced distribution even with a small number of instances, every instance ID is mapped to a preconfigured number of tokens on the hash ring -- known as "virtual nodes" [@stoica2001chord].

For determining ownership of a given API object, a partition key is derived from the object's metadata.
By default, it consists of the object's API group, kind, namespace and name.
This partition key is chosen in order to equally distribute objects of different kinds with the same namespace and name across shards.
Additionally, the object's UID is added in order to distinguish between different instances of an API object with the same namespace and name.
As all API objects share these common metadata fields, this approach can be applied to all API resources equally.
Also, it allows the sharder to use lightweight metadata-only watches.
In order to assign owned objects to the same shard as their owners, the owner's partition key can be determined from the owner reference in the owned object's metadata.

## Coordination and Object Assignment

Realizing coordination and object assignment ([requirement @sec:req-coordination]) in Kubernetes controllers is much simpler than in distributed databases.
In contrast to sharding in databases, no request coordination is needed because no client directly communicates with the controller instances.
Because of this, object assignments don't need to be persisted in a dedicated store or storage section like in Bigtable, MongoDB or Spanner [@bigtable2006; @mongodbdocs; @spanner2013].
Furthermore, instances don't need to be aware of assignment information of objects they are not responsible for.
Hence, there is no need to propagate this information throughout the system as it is done in many distributed databases [@dynamo2007; @cassandradocs].

In the presented design, object assignment is done by the sharder controller by labelling API objects with the instance ID of the responsible shard.
For each object kind that should be sharded, one sharder controller is started that uses the mechanisms described above for discovering available instances and determining assignments.
Persisting assignments in the API objects themselves is done in order to make use of existing controller infrastructure for coordination.
By labelling the objects themselves, controllers can simply use a filtered watch to retrieve all API objects that are assigned to them.
For this, a label selector on the `shard` label for the shards' instance ID is added to the controllers' watches.
With this, the controllers' caches and reconciliations are already restricted to the relevant objects and no further coordination between controllers is needed.
Additionally, controllers already rebuild watch connections on failures or after restarts automatically.
This means, object assignment information is automatically rebuilt on failures or restarts without any additional implementation.

The sharder itself is not on the critical path for all reconciliations.
As soon as objects are assigned to an instance, the sharder doesn't need to be available for reconciliations to happen successfully.
Reconciliations of new object might however be delayed by a short period of time on leader transitions.
As there are multiple instances of the sharder controller in stand-by, handover should generally happen quickly.
Also, handover can be sped up by releasing the leader election lease on voluntary step down.

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
