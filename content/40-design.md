# Design

## Architecture

\todo[inline]{insert drawing}

- sharder
  - watch objects (metadata-only)
  - watch instances (leases)
  - determines assignments
  - add labels to objects according to instance assignments
- instances
  - instance ID = hostname
  - maintains individual lease
  - filtered watch/cache

## Membership and Failure Detection

- similar to BigTable
- sharder controller performs usual leader election
- individual leases per instance
  - name = holder identity = instance ID
  - name needs to be stable between restarts to allow restarts of instances (can fail at any time)
  - holder identity needs to be stable as well, otherwise restart is similar to instance not able to renew its lease -> minimize movements
- sharder watches leases
- as long as instance holds its lease
  - sharder considers it ready and assigns objects to it
  - instance watches and controls objects labelled with its ID
- on termination
  - instance releases its lease
  - sharder moves assigned objects
- on failure
  - instance fails to renew its lease within `leaseDurationSeconds`
  - instance needs to stop reconciling objects, terminates as with usual leader election
  - sharder considers instance as "unknown", waits for another `leaseDurationSeconds`
  - if instance comes up again and renews its lease, sharder considers instance as ready again
  - if instance still doesn't renew lease within timeout, sharder tries to acquire instance lease once (to ensure API server availability/connectivity) with double `leaseDurationSeconds`
  - if successful, instance is considered dead, sharder moves assigned objects
  - instance is free to re-acquire lease once it comes up again after lease has expired
  - if successful, instance is considered ready again
- cleanup expired / orphaned leases
  - either: sharder cleans up expired leases once `renewTime + 10 * leaseDurationSeconds` has passed
  - or: instances add `Pod` as `ownerReference` to `Lease` -> rely on garbage collection

## Partitioning

- similar to Cassandra, Dynamo
- sharding algorithm:
  - consistent hashing for stable assignments and simple (deterministic) logic
  - virtual nodes for balanced distribution in small clusters
    - number of virtual nodes per instance is specified by label on lease
  - \todo[inline]{make this more specific}
  - every object is assigned to exactly one instance
- partition key:
  - default: by `GroupKind` + namespaced name
    - done in order to distribute objects of different kind with identical names
  - challenge: controller doesn't only watch controlled object, but also controlled objects and dependents
  - owner and owned object need to have identical partition key, so they are assigned to same instance
  - allow mapping from object to other object, that should be used as partition key
    - e.g., map to controlling object (sensible for most controllers)

## Coordination and Object Assignment

- unlike distributed databases
  - no request coordination is needed -> not persisted externally in dedicated store
  - assignment information not needed by all instances -> not propagating via gossip
- sharder ("meta controller") assigns objects to instances
  - adds labels to objects
- instances need to know which objects are assigned to them:
  - labels used for filtered watches
  - makes use of already existing watches in controllers, only need to add label selector
  - once labels are persisted in etcd, no additional coordination is needed -- sharder is not on the critical path for all reconciliations
  - controllers simply rebuild filtered watches after restart
- objects are not assigned when sharder stops working (should recover quickly though)
- challenge: labels must not be mutated by user
  - can be prevented via validating webhook
- challenge: multiple controllers in same instance might work on the same object kind, share the same cache by default
  - neglected for now (?)
  - solution: multiple caches with different selectors?

## Preventing Concurrency

- when moving objects from ready instance (rebalancing during scale-out, movement during rolling update):
  - challenge: system is pull/watch-based (no request routing), watches/caches might lag behind
  - sharder can't know if instances already observed the movement
  - instances need to acknowledge movement and stop working on object accordingly
  - protocol/flow to ensure, that controllers have observed movement
    - on desire to move object: sharder adds "drain" label, indicating that the object should be moved
    - when controller observes the drain label, it must remove it as well as the shard label, marking the object as drained/unassigned
    - once sharder observes that object is drained, it can be reassigned
    - if controller doesn't remove the drain label within a given timeout, it is forcefully moved by sharder
  - facilitates fast movements with ready instances
- when moving objects from terminating instance (rebalancing during scale-down, moving during rolling update):
  - instance releases its own lease
  - objects are reassigned immediately
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
