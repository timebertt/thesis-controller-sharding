# Requirement Analysis

Based on the motivation for this study project and the described background, this chapter first describes what the current limitations in scaling Kubernetes controllers are.
Afterwards, it analyzes what is required to make Kubernetes controllers horizontally scalable.

## Current Scalability Limitations {#sec:limitations}

Kubernetes controllers need to prevent uncoordinated and conflicting actions from different instances on the same API objects.
Therefore, controllers currently use leader election mechanisms to determine a single active instance at any given time.
Even if multiple instances are running at the same time, there will only be a single instance carrying out work -- the current leader.
This means, that a controller's work cannot be distributed across multiple controller instances.
Because of this, capacity and throughput of a controller can only be increased by scaling it vertically, i.e., adding more resources to the instances.
However, one cannot increase capacity or throughput by adding more controller instances.
I.e., as of now, Kubernetes controllers are not horizontally scalable.

In order to understand what is required for scaling Kubernetes controllers horizontally, it's important to note which resource dimensions are relevant for scaling.
Generally speaking, the following resource requirements increase with the controller's capacity and throughput:

+------------------+------------------------------------------------------------+
| resource         | depends on                                                 |
+==================+============================================================+
| compute          | rate and size of API objects encoded, decoded;             |
|                  | rate and CPU consumption of actual reconciliations         |
+------------------+------------------------------------------------------------+
| memory           | number of API objects stored in the controller's caches    |
+------------------+------------------------------------------------------------+
| network transfer | rate and size of API requests and watch events             |
+------------------+------------------------------------------------------------+

: Resource requirements of a Kubernetes controller

As controllers can only be scaled by deploying larger instances, this effectively limits their scalability by the available machine sizes and network bandwidth.
Note, that using bigger machines and broader network connections typically has negative impact on cost-efficiency at the rear end of the spectrum.
Hence, it is desirable to make controllers horizontally scalable and rather distribute multiple instances across smaller machines instead of deploying bigger instances.
\todo[inline]{move this to motivation?}

Additionally, scaling controllers increases the resource footprint of the API server and etcd in the following dimensions as well:

+------------------+------------------------------------------------------------+
| resource         | depends on                                                 |
+==================+============================================================+
| compute          | rate and size of API objects converted, encoded, decoded;  |
|                  | rate and size of watch events dispatched to clients        |
+------------------+------------------------------------------------------------+
| memory           | number of API objects stored in the watch cache            |
+------------------+------------------------------------------------------------+
| network transfer | rate and size of API requests and watch events             |
+------------------+------------------------------------------------------------+
| disk I/O         | rate and size of API objects read from and written to disk |
+------------------+------------------------------------------------------------+

: Resource implications on API server and etcd

However, this study project focuses on scalability of the controller-side only.
Scalability limitations and implications of the control plane is out of scope of this thesis.

## Requirements for Horizontal Scalability

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
