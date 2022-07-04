# Status Quo

\todo[inline]{Call this chapter Research Question or merge with Design?}

## Current Limitations

Because controller work cannot be distributed across multiple instances, capacity and throughput of a controller can only be increased by scaling it vertically, i.e., adding more resources to a single instance.
Generally, the following resources need to be added to scale controllers vertically:

- compute: grows with the number of API objects encoded / decoded and reconciled
- memory: grows with the number of API objects stored in controller caches
- network transfer: grows with the number of API requests and watch events

This effectively limits the scalability of controllers by available machine sizes and network bandwidth.
Additionally, scaling controllers increases the resource footprint of the API server and etcd in the following dimensions as well:

- compute: grows with the number of API objects converted, encoded / decoded and with the number of watch events dispatched to clients
- memory: grows with the number of API objects stored in the watch cache
- network transfer: grows with the number of API requests and watch events
- disk I/O: grows with the number of API objects read from and written to disk

## Requirements

To scale controllers horizontally, the following is needed:

- membership mechanism
  - instances can fail at any time (commodity / cloud native)
  - instances are dynamically added and removed (scale-out/in)
  - instances are replaced during rolling updates
  - fast resharding on voluntary replica add/remove
- partitioning
  - sharding algorithm, movement
  - balanced distribution even with small number of instances (2, 3)
  - objects should not be blocked for too long
    - stable partitioning desirable, minimize needless movements
  - partition key:
    - should be applicable to all resources -> sensible default
    - maybe desirable/necessary to co-locate different resources on same instance (e.g. ) -> customizable
      - discard for this thesis?
- request coordination / assignment
  - no direct communication to controller instances needed -> no request coordination from client perspective
  - instances need to know which objects are assigned to them
  - instances and clients don't need to know entire mapping
  - watches/caches must be restricted (label selector), otherwise we have gained almost nothing
  - instances need to be able to discover assignment information after restart
  - no single-point of failure or bottleneck for all reconciliations
- no replication allowed
  - concurrency must be prevented, only one instance is allowed to act on any given object
  - consistent view on assignments
  - ensure no split-brain scenarios can happen
  - when moving objects, controllers need to stop working on it
- incremental scale-out
  - linearly increase capacity, throughput with every added instance

Challenges:

- watches might lag behind
