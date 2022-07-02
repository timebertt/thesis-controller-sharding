# Status Quo

\todo[inline]{Call this chapter Research Question?}

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

- what needs to be done in order to scale controllers horizontally
- what kind of sharding algorithms are needed

Requirements:

- instances can fail at any time (commodity / cloud-native)
- balanced distribution even with small number of instances (2, 3)
- incremental scale-out: increase capacity, throughput with every added instance
- stable partitioning
  - minimize needless movement
  - instances need to be able to discover sharding information after restart
- fast resharding on replica add/remove, e.g. during rolling updates
- watches/caches must be restricted (label selector), otherwise we have gained almost nothing
- no replication allowed
  - hence, also no consensus between replicas needed
  - only one instance is allowed to act on any given object
  - notify controller when object is moved (could be discarded in the light of short reconciliations)
- instance failure detection, objects should not be blocked for too long
- outside master that shards is allowed (like Chubby in BigTable)
  - as long as it does not become single-point of failure
