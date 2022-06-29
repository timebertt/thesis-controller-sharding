# Design

- transfer ideas from distributed databases
- distributed scheduling?

## Sharding Criteria

- by resource
  - can't be done dynamically / during runtime (or at least that's more difficult)
  - unequal sharding / no control over shard sizes
  - controllers probably need to list/cache resources, that are handled by other controllers -> overhead, scalability benefits questionable
  - doesn't provide HA / multiple instances for controllers
- by namespace
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
- by name
- by arbitrary shard key
  - one shard only holds objects with one shard key value
    - e.g. by seed name, by extension provider type

- mapping from sharding key to shard
  - n to n (e.g. controller per namespace)
  - n to m, with n > m (e.g. controller for multiple namespaces)

- problems
  - controller doesn't only watch controlled object, but also owned objects and dependents
    - restrict watch only possible on namespace basis, but not

## Sharding Mechanism

- replica discovery
  - membership protocol?
  - gossip between replicas?
  - leases?
- sharding algorithm
- sharding controller
  - manifests sharding decisions
  - populating sharding keys