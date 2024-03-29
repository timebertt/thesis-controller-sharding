# Requirement Analysis {#sec:requirement-analysis}

Based on the motivation for this study project and the described background, this chapter first describes the current limitations in scaling Kubernetes controllers.
Afterward, it analyzes what is required to make Kubernetes controllers horizontally scalable.

## Current Scalability Limitations {#sec:limitations}

Kubernetes controllers need to prevent uncoordinated and conflicting actions from different instances on the same API objects.
Therefore, controllers currently use leader election mechanisms to determine a single active instance at any given time.
Even if multiple instances are running at the same time, only a single instance carries out the actual work – the current leader.
This means, that a controller's work cannot be distributed across multiple controller instances.
In the context of this thesis, such a setup is referred to as a "singleton controller" setup.

The most important scalability dimensions of a Kubernetes controller are capacity and throughput.
The capacity of a controller shall be defined as the total number and size of API objects existing in the cluster simultaneously that are watched by the controller.
Increasing a controller's capacity is mainly reflected in increased cache size.
When reaching the upper limit of the controller's capacity, it might run out of memory and stop working entirely.
This sets hard limits for how many API objects can be managed in a single cluster and might limit the ability to support increased usage of the service that the controller is responsible for.
A controller's throughput shall be defined as the rate of reconciliations it performs and watch events it handles.
If API objects are created, updated, and deleted frequently the controller's throughput needs to be high enough to properly handle all reconciliation requests.
When the rate of reconciliation requests exceeds the controller's maximum throughput, the system will become less responsive as reconciliation requests are queued up and delayed.
This results in a decreased user experience and stability of the system.

Because a controller's work cannot be distributed, its capacity and throughput can only be increased by scaling it vertically, i.e., by adding more resources to the instance.
However, one cannot increase capacity or throughput by adding more controller instances.
I.e., as of now, Kubernetes controllers are not horizontally scalable.
To understand what is required for scaling Kubernetes controllers horizontally, it's important to note which resource dimensions are relevant for scaling.
Generally speaking, the following resource requirements increase with the controller's capacity and throughput:

+-------------------+------------------------------------------------------------+
| resource          | depends on                                                 |
+==================:+============================================================+
| CPU               | rate and size of API objects encoded, decoded              |
|                   | (API requests and watch events), \newline                  |
|                   | rate and CPU consumption of actual reconciliations         |
+-------------------+------------------------------------------------------------+
| memory            | number and size of API objects stored in the controller's  |
|                   | caches                                                     |
+-------------------+------------------------------------------------------------+
| network bandwidth | rate and size of API requests and watch events             |
+-------------------+------------------------------------------------------------+

: Resource requirements of a Kubernetes controller {#tbl:scaling-resources}

As controllers can only be scaled by deploying larger instances, this effectively limits their scalability by the available machine sizes and network bandwidth.
Note, that using bigger machines and broader network connections typically harms cost-efficiency at the top end of the spectrum.
Hence, it is desirable to make controllers horizontally scalable and rather distribute multiple instances across smaller machines instead of deploying bigger instances.

Additionally, increasing a controller's capacity and throughput also increases the resource footprint of the API server and etcd as outlined in [@tbl:scaling-resources-server].
However, this study project focuses on the scalability of the controller's side only.
Scalability limitations and implications of the control plane are out of the scope of this thesis.

+-------------------+-----------------------------------------------------------------------+
| resource          | depends on                                                            |
+==================:+=======================================================================+
| CPU               | rate and size of API objects converted, encoded, decoded, \newline    |
|                   | rate and size of watch events dispatched to clients                   |
+-------------------+-----------------------------------------------------------------------+
| memory            | number and size of API objects stored in the watch cache              |
+-------------------+-----------------------------------------------------------------------+
| network bandwidth | rate and size of API requests and watch events                        |
+-------------------+-----------------------------------------------------------------------+
| disk I/O          | rate and size of serialized API objects read from and written to disk |
+-------------------+-----------------------------------------------------------------------+

: Resource implications on API server and etcd {#tbl:scaling-resources-server}

## Requirements for Horizontal Scalability {#sec:requirements}

To scale Kubernetes controllers horizontally, the restriction of having only a single active instance at any given time needs to be lifted.
For this, a concept for sharding API objects must be introduced which distributes ownership of different objects across multiple instances.
Nevertheless, it must still be prevented that multiple instances own a single API object at the same time or act on it concurrently.

This section defines precise requirements for a sharding mechanism for Kubernetes controllers.
The requirements themselves are inspired by the required mechanisms for sharding in distributed databases ([@sec:databases]).
If these requirements are met, the resources listed in [@tbl:scaling-resources] can be distributed across multiple instances which makes the controller horizontally scalable.

\subsection*{\requirement\label{req:membership}Membership and Failure Detection}

Firstly, the system needs to populate information about the set of controller instances.
In order to distribute object ownership across instances, there must be a mechanism for discovering members of the sharded setup.
Additionally, this mechanism needs to provide information on the availability of individual instances.
Instance failures need to be detected for remediating them and restoring the system's functionality quickly and automatically.

Because Kubernetes controllers are part of a distributed system and deployed in cloud environments (on commodity hardware), the sharding mechanism must expect that instances are restarted frequently and can fail at any time.
Also, instances can be dynamically added or removed to adapt to growing or decreasing demand.
Furthermore, instances will typically be replaced in quick succession during rolling updates.
For these reasons, voluntary disruptions should be handled specifically and gracefully (scale-down, rolling updates) to achieve fast rebalancing.

\subsection*{\requirement\label{req:partitioning}Partitioning}

Secondly, the sharding mechanism must include a partitioning algorithm for determining ownership of a given object based on information about the set of available controller instances.
It must map every sharded API object to exactly one instance.
Additionally, the partitioning algorithm needs to provide a balanced distribution even with a small number of instances (e.g., less than 5).

As an input for the partitioning algorithm, a partition key is needed.
It needs to apply to all available API resources.
Hence, there should be a generic function for determining the partition key of a given API object.
Furthermore, controllers commonly own and manage objects of different kinds for implementing the logic of a given API resource.
E.g., the `Deployment` controller owns and manages `ReplicaSet` objects.
As controllers watch the owned objects to trigger reconciliation of the owning object on relevant changes to owned objects, the partitioning algorithm must support assigning related objects to the same instance.
For this, all owned objects should map to the same partition key as their owners.

\subsection*{\requirement\label{req:coordination}Coordination and Object Assignment}

Next, the sharding mechanism must provide some form of coordination between individual controller instances and assign API objects to the instances based on the partitioning results.
As Kubernetes controllers realize the desired state of the system asynchronously, there is no direct communication of intent between the issuing user and the responsible controller.
Hence, there is no need for partition-based coordination of client requests.
Individual controller instances need to know which objects are assigned to them in order to perform the necessary reconciliations.
However, individual instances don't need to be aware of all object assignments.
The object assignment needs to be transparent and must not change any existing API semantics.

As described in [@tbl:scaling-resources], the resource requirements of Kubernetes controllers don't only depend on the actual reconciliations but also depend on the controllers' caches and underlying watch connections.
The sharding mechanism can only make controllers horizontally scalable if the instances' caches and watch connections are filtered to only contain and transport the API objects that are assigned to the respective instances.
Otherwise, the mechanism would replicate the cached data and the corresponding resource requirements, which contradicts the main goals of distributing load between instances.
Another important requirement is that individual instances need to be able to retrieve the object assignment information after restarts.
I.e., object assignments must be stored persistently.

Furthermore, there must not be a single point of failure or bottleneck for reconciliations.
This means, the sharding mechanism must not add additional points of failure on the critical path of API requests and the reconciliations themselves, which would limit the mechanism's scalability again.
During normal operations, reconciliations should not be blocked for a longer period.

\subsection*{\requirement\label{req:concurrency}Preventing Concurrency}

Additionally, even when object ownership is distributed across multiple controller instances, concurrent reconciliations for a single object in different instances are still not allowed.
I.e., the purpose of the current leader election mechanism must not be violated.
Only a single instance is allowed to perform mutations on a given object at any given time.
A strictly consistent view on object assignments is not needed for this though.
The only requirement is, that multiple controller instances must not perform writing actions for a single object concurrently.
In other words, the sharding mechanism must not involve the replication of objects.
All API objects are only assigned to a single controller instance.

\subsection*{\requirement\label{req:scale-out}Incremental Scale-Out}

The final requirement is that the introduced sharding mechanism provides incremental scale-out properties.
This means that the capacity and throughput of the system increase almost linearly with the added resources, i.e. with every added controller instance.
