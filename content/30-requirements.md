# Requirement Analysis

- what needs to be done for making controllers horizontally scalable?

## Current Limitations {#sec:limitations}

- leader election prevents scaling horizontally
- list resources that are most important for controllers / relevant for scaling

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

To scale controllers horizontally, object ownership and resources mentioned in [@sec:limitations] need to be distributed across multiple instances.
For this, the following is needed:

- membership mechanism, failure detection
  - instances can fail at any time (commodity / cloud native)
  - instances are dynamically added and removed (scale-out/in)
  - instances are replaced during rolling updates
  - fast rebalancing when adding or removing instances (voluntarily)
- partitioning
  - sharding algorithm for determining ownership/assignment of a given object based on membership information
  - assignments should be entirely determined by the system, API semantics and client interaction with the system must not change
  - balanced distribution even with small number of instances (2, 3)
  - objects should not be blocked for too long during normal operations, minimize time-intensive movements
  - partition key is needed:
    - should be applicable to all resources -> sensible default
    - desirable/necessary to co-locate different resources on same instance (e.g. Deployments and owned ReplicaSets) -> should be customizable
- coordination / object assignment
  - no direct communication to controller instances needed -> no request coordination from client perspective
  - instances need to know which objects are assigned to them
  - instances and clients don't need to know entire mapping
  - watches/caches must be restricted (label selector), otherwise we have gained almost nothing
  - instances need to be able to discover assignment information after restart
  - no single-point of failure or bottleneck for all reconciliations
- preventing concurrency
  - no concurrent / distributed reconciliations for a single object allowed (no concurrent writes / no split-brain scenarios)
  - only a single instance is allowed to make mutations to a given object
  - strictly consistent view on assignments is not needed
    - however, multiple instance must not feel responsible for a single object simultaneously
  - generally, simple sharding, no replication involved: all objects are assigned to a single instance
  - concurrency generally prevented as long as assignments do not change
  - however, concurrency needs to be prevented when moving objects
  - old instance needs to stop working on moved objects before new instance picks up objects
- incremental scale-out
  - linearly increase capacity and throughput with every added instance

Challenges:

- watches might lag behind

\todo[inline]{enumerate requirements}
