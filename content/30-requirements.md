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

: Resource requirements of a Kubernetes controller {#tbl:scaling-resources}

As controllers can only be scaled by deploying larger instances, this effectively limits their scalability by the available machine sizes and network bandwidth.
Note, that using bigger machines and broader network connections typically has negative impact on cost-efficiency at the top end of the spectrum.
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

To scale Kubernetes controllers horizontally the restriction of having only a single active instance at any given time needs to be lifted.
For this, a concept of sharding for API objects must be introduced which distributes ownership of different objects across multiple instances.
Nevertheless, it must still be prevented that multiple instances own a single API object at the same time or act on it concurrently.

This section defines precise requirements for a sharding mechanism for Kubernetes controllers.
\todo{mention sharding in DBs}
Once these requirements are met, the resources listed in [@tbl:scaling-resources] can be distributed across multiple instances making the implementing controller horizontally scalable.

### Requirement 1: Membership and Failure Detection {#sec:req-membership}
\todo[inline]{fix requirement numbering}

Firstly, the system needs to populate information about the set of controller instances.
In order to distribute object ownership across instances, there must be mechanism for discovering members of the sharded setup.
Additionally, this mechanism needs to provide information on the availability of individual instances.
Instance failures need to be detected in order to remediate them and restore functionality of the system quickly and automatically.

Because Kubernetes controllers are part of a distributed system and deployed in cloud environments (on commodity hardware), the sharding mechanism must expect that instances can fail at any time.
Also, instances can be dynamically added or removed to adapt to growing or decreasing demand.
Furthermore, instances will typically be replaced in quick succession during rolling updates.
For these reasons, it is desirable to handle voluntary disruption specifically (scale-down, rolling updates) to achieve fast rebalancing.

### Requirement 2: Partitioning {#sec:req-partitioning}

Secondly, the sharding mechanism must include a partitioning algorithm for determining ownership of a given object based on information about the set of available controller instances.
Partitioning results need to be transparent and not change any existing API semantics.
Additionally, the partitioning algorithm needs to provide a balanced distribution even with a small number of instances (e.g. less than 5).

As an input for the partitioning algorithm, a partition key is needed.
It needs to be applicable to all available API resources.
Hence, there should be a commonly sensible way to determine the partition key of any given API object.
Furthermore, controllers commonly own and manage objects of different kinds for implementing the logic of a given API resource.
E.g., the `Deployment` controller owns and manages `ReplicaSet` objects.
As controllers watch the owned objects to trigger reconciliation of the owning object on relevant changes to owned objects, the partitioning algorithm must support assigning related objects to the same instance.
For this, all owned objects should map to the same partition key as their owners.
However, there might as well be other relationships between objects their controllers act upon.
Hence, the mapping from object to its partition key needs to be customizable.

### Requirement 3: Coordination and Object Assignment {#sec:req-coordination}

- objects should not be blocked for too long during normal operations, minimize time-intensive movements
- no direct communication to controller instances needed -> no request coordination from client perspective
- instances need to know which objects are assigned to them
- instances and clients don't need to know entire mapping
- watches/caches must be restricted (label selector), otherwise we have gained almost nothing
- instances need to be able to discover assignment information after restart
- no single-point of failure or bottleneck for all reconciliations

### Requirement 4: Preventing Concurrency {#sec:req-concurrency}

- no concurrent / distributed reconciliations for a single object allowed (no concurrent writes / no split-brain scenarios)
- only a single instance is allowed to make mutations to a given object
- strictly consistent view on assignments is not needed
  - however, multiple instance must not feel responsible for a single object simultaneously
- generally, simple sharding, no replication involved: all objects are assigned to a single instance
- concurrency generally prevented as long as assignments do not change
- however, concurrency needs to be prevented when moving objects
- old instance needs to stop working on moved objects before new instance picks up objects

### Requirement 5: Incremental Scale-Out {#sec:req-scale-out}

- linearly increase capacity and throughput with every added instance

Challenges:

- watches might lag behind
