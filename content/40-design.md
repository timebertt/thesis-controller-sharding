# Design

## Architecture

\todo[inline]{insert drawing}

- sharder
  - metadata-only watch
- instances with ID
  - filtered watch/cache

## Membership

- similar to BigTable
- sharder controller performs usual leader election
- individual leases per instance
  - name = instance ID
- sharder watches leases
- as long as instance holds its lease
  - sharder considers it ready and assigns objects to it
  - instance watches and controls objects labelled with its ID
- on termination
  - instance deletes its lease
  - sharder moves assigned objects
- on failure
  - instance fails to renew its lease within deadline
  - instance needs to stop reconciling objects, terminates as with usual leader election
  - sharder tries to acquire instance lease once (to ensure API server availability)
  - if successful, instance is considered dead sharder moves assigned objects
  - instance is free to re-acquire lease once it comes up again
  - if successful, instance is considered ready again

## Partitioning

- similar to Cassandra, Dynamo
- sharding algorithm:
  - consistent hashing for stable assignments and simple (deterministic) logic
  - virtual nodes for balanced distribution in small clusters
    - number of virtual nodes per instance is specified by label on lease
  - \todo[inline]{make this more specific}
- partition key:
  - default: by (namespaced) name
  - customizable: by arbitrary shard key?
    - challenge: controller doesn't only watch controlled object, but also owned objects and dependents
- sharder watches objects (metadata-only) and assigns them to instances by adding labels

## Coordination / Object Assignment

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
- labels must not be mutated by user -> can be prevented via validating webhook

## Preventing Concurrency

- when moving objects
  - watches might lag behind
  - sharder can't know if instances already observed the movement
  - instances need to acknowledge movement and stop working on object accordingly
  - protocol/flow
    - on desire to move object: sharder adds "drain" label, indicating that the object should be moved
    - when controller observes the drain label, it must remove it as well as the shard label, marking the object as unassigned
    - once sharder observes that object is unassigned, it can be reassigned
    - if controller doesn't remove the drain label within a given timeout, it is force moved by sharder
  - makes sure, that controllers have observed movement
  - facilitates fast movements with ready controllers
- when moving object from running instances (rebalancing during scale-out):
  - objects that should be moved are marked as draining
  - objects are reassigned to new instance
  - controllers must ensure they stop working on moved objects within that period
  - challenge: watches might lag behind
  - alternative: short period of no reconciliation (~15 seconds) between unassigning and reassigning
  - prevent unnecessary movement during rolling updates (necessary?)
    - move all objects belonging to one virtual node in batch, one virtual node at a time
- when moving objects from dead instance (rebalancing after instance failure):
  - challenge: instance could come up again
  - treat similar like running instance
- when moving objects from terminating instance (rebalancing during scale-down, moving during rolling update):
  - instance deletes its own lease
  - objects are reassigned immediately

## Alternatives Considered

- sharding by resource
  - can't be done dynamically / during runtime (or at least that's more difficult)
  - unequal sharding / no control over shard sizes
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
