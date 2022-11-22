# Design {#sec:design}

This chapter presents a design for implementing sharding in Kubernetes controllers to make them horizontally scalable.
The presented design includes well-known approaches for sharding in distributed databases and applies them to the problem space of Kubernetes controllers.
Approaches are chosen to fulfill the requirements listed in [@sec:requirements].
First, the overall architecture of the design is introduced.
After that, different aspects of the design are described in detail.

## Architecture

![Kubernetes controller sharding architecture](../assets/design-overview.pdf)

The design heavily builds upon existing mechanisms of the Kubernetes API and controllers.
It reuses established approaches from distributed databases and maps them to Kubernetes to implement sharding in a "Kubernetes-native" manner.
This is done to leverage as much of the existing controller infrastructure as possible.

Firstly, multiple instances of the controller are deployed with the same configuration.
All instances are equal, though one of them is elected to be the "sharder" using the usual lease-based leader election mechanism.
In addition to running the main controllers, the sharder is also responsible for performing sharding-related tasks.
Most importantly, this includes assigning API objects that should be sharded to individual controller instances.
It persists object assignments by setting the `shard` label on the objects themselves to the ID of the responsible instance.
The sharder components themselves are responsible for all API objects and bootstrapping the sharding mechanism.
Hence, the sharder components are only executed as long as the instance is the current leader as they must not run in multiple instances concurrently.
I.e., there is only a single active sharder at any given time and the sharder components in additional instances are on standby.
The sharder uses a metadata-only watch for all the sharded objects to minimize the resulting resource footprint.

Each controller instance ("shard") maintains an individual lease ("shard lease"), which is used as a heartbeat resource to inform the sharder about the health status of all instances.
The sharder watches the shard leases in addition to the sharded API objects themselves in order to react to state changes, e.g., the addition or removal of shards.
The main controllers in all shards watch and cache only the objects they are responsible for by filtering the watch connection using a label selector on the `shard` label.

## Membership and Failure Detection {#sec:des-membership}

To address requirement \ref{req:membership}, a lease-based membership and failure detection mechanism are used.
The mechanism is heavily inspired by Bigtable but adapted to use Kubernetes `Lease` objects stored via the API server instead of leases stored in Chubby [@bigtable2006].

The sharder performs the usual leader election to ensure that there is only one active sharder at any given time.
Additionally, each shard maintains an individual shard lease.
Like usual leader election, the `Lease` API resource with the same fields and semantics are used for this purpose.
However, shard leases use individual names that are equal to the shard's instance ID.
The instance ID needs to be stable between restarts of the shard, so the hostname is used, i.e., the controller's `Pod` name.
On startup, the shards acquire the respective shard lease using the instance ID as name and holder identity.
As with the usual leader election, the shards periodically renew their leases after a configured duration.
As long as the shard actively holds its lease, it watches and reconciles objects that are assigned to itself.
If the shard fails to renew its lease within a configured period, it needs to stop all sharded controllers immediately and terminate.

The sharder controller watches all shard leases, which allows it to discover all available instances and immediately react to state changes.
As long as a shard holds its lease, the sharder considers it for partitioning.
On shard termination, the shard unsets the lease's holder identity field to release its lease.
This signals a voluntary disruption to the sharder, which immediately removes the instance from the partitioning.
With this, all objects assigned to the terminated shard are moved to other available instances.

Shard failures are detected by checking the leases' `renewTimestamp` field.
If a shard fails to renew its lease within `leaseDurationSeconds`, the lease is considered expired.
To decrease the sensitivity of the system, the sharder waits for another `leaseDurationSeconds` and allows the instance to renew its lease again.
If the shard comes available again by renewing its lease it is considered ready again.
If the shard fails to renew its lease though, the sharder considers the instance unavailable.
However, before it removes the instance from partitioning, it tries to acquire the shard lease once.
This is done to ensure the API server is functioning and the sharder doesn't act on stale lease data.
If the sharder is able to acquire the shard lease, it considers the instance dead, removes it from partitioning, and moves objects to available instances.
Afterward, the sharder doesn't touch the shard lease anymore.
With this, the shard is allowed to acquire its lease once it comes up again after the lease duration set by the sharder has passed.
If this is successful, the instance is considered ready and included in partitioning again.

The sharder garbage collects leases of dead shards after a period of inactivity.
With this, leases of voluntarily terminated instances as well as failed instances get cleaned up eventually.

## Partitioning

To address requirement \ref{req:partitioning}, a variant of consistent hashing is used [@karger1997consistent; @stoica2001chord].
With this, partitioning is done similarly as in Apache Cassandra [@cassandradocs] and Amazon Dynamo [@dynamo2007] but adapted to use Kubernetes API object metadata as input.
Consistent hashing is chosen because it minimizes movement on the addition and removal of instances.
Also, it provides a simple and deterministic algorithm for determining the responsible shard solely based on the set of available instances.
Therefore, no state of the partitioning algorithm must be stored apart from the instance states available through the membership mechanism ([@sec:des-membership]).
The sharder can simply reconstruct the hash ring based on this information after a restart or leader transition without risking inconsistency or unstable assignments.
In order to provide a balanced distribution even with a small number of instances, every instance ID is mapped to a preconfigured number of tokens on the hash ring (virtual nodes) [@stoica2001chord].

For determining ownership of a given API object, a partition key is derived from the object's metadata.
By default, it consists of the object's API group, kind, namespace, and name.
This partition key is chosen in order to equally distribute objects of different kinds with the same namespace and name across shards.
Additionally, the object's UID is added to distinguish between different instances of an API object with the same namespace and name.
As all API objects share these common metadata fields, this approach can be applied to all API resources likewise.
Also, it allows the sharder to use lightweight metadata-only watches.
To assign owned objects to the same shard as their owners, the owner's partition key can be determined from the owner reference in the owned object's metadata.

## Coordination and Object Assignment

Realizing coordination and object assignment (requirement \ref{req:coordination}) in Kubernetes controllers is very simple in comparison to distributed databases.
In contrast to sharding in databases, no request coordination is needed because clients don't communicate directly with the controller instances.
Because of this, object assignments don't need to be persisted in a dedicated store or storage section like in Bigtable, MongoDB, or Spanner [@bigtable2006; @mongodbdocs; @spanner2013].
Furthermore, instances don't need to be aware of assignment information of objects they are not responsible for.
Hence, there is no need to propagate this information throughout the system as it is done in many distributed databases [@dynamo2007; @cassandradocs].

In the presented design, object assignment is done by the sharder controller by labeling API objects with the instance ID of the responsible shard.
For each object kind that should be sharded, one sharder controller is started that uses the mechanisms described above for discovering available instances and determining assignments.
Persisting assignments in the API objects themselves are done to make use of existing controller infrastructure for coordination.
By labeling the objects themselves, controllers can simply use a filtered watch to retrieve all API objects that are assigned to them.
For this, a label selector on the `shard` label for the shards' instance ID is added to the controllers' watches.
With this, the controllers' caches and reconciliations are already restricted to the relevant objects and no further coordination between controllers is needed.
Additionally, controllers already rebuild watch connections on failures or after restarts automatically.
This means object assignment information is automatically rebuilt on failures or restarts without any additional implementation.
Using a filter watch and cache additionally addresses requirement \ref{req:scale-out}, as all relevant resource requirements ([@tbl:scaling-resources]) are distributed across multiple instances.
The system's capacity roughly increases linearly with each added instance.

The sharder itself is not on the critical path for all reconciliations.
As soon as objects are assigned to an instance, the sharder doesn't need to be available for reconciliations to happen successfully.
Reconciliations of new objects might however be delayed by a short period on leader transitions.
As there are multiple instances of the sharder controller on standby, handover generally happens quickly.
Also, handover can be sped up by releasing the leader election lease on voluntary step-down.

## Preventing Concurrency {#sec:des-concurrency}

With the presented design, concurrent writes from different instances to the same API object are already prevented as long as object assignments don't change.
To fulfill requirement \ref{req:concurrency}, concurrent mutating reconciliations must additionally be prevented when moving objects between shards.
In this case, the sharder must ensure that the old instance has stopped working on the given object before another instance picks it up.

The first case that needs to be considered is when moving objects from a ready shard to another shard.
This can be required for rebalancing during scale-out or a rolling update, i.e. when a new instance is added.
As the controller system is asynchronous and pull-/watch-based, the sharder cannot immediately reassign objects.
The watch connection and cache of the old instance might receive the reassignment event later than the new instance, which could lead to concurrent and conflicting reconciliations.
In other words, the sharder can't know if and when an instance has stopped working on an object that is supposed to be moved.
To address this challenge, the old instance needs to acknowledge the reassignment and confirm it has stopped working on the object.
When the sharder needs to move an object from a ready shard to another, it adds a `drain` label indicating that the object should be moved.
As soon as the old shard observes the `drain` label it must remove it from the object as well as the `shard` label, marking the object as unassigned.
When the sharder observes that the object is unassigned it reassigns it to the desired instance as it does for new objects.
Following this protocol, concurrent reconciliations by the old and the new shard are prevented.
Also, it facilitates fast rebalancing with ready and responsive instances.

A second case to consider is when moving objects from a terminating instance to a ready instance.
This can be required for rebalancing during scale-in or a rolling update, i.e. when an existing instance is removed.
In this case, the shard releases its shard lease to signal voluntary termination to the sharder.
As soon as the sharder observes this change to the shard lease it immediately reassigns API objects to another instance.
A `drain` operation is not performed in this case because the instance has already acknowledged that it stopped working on the objects by releasing its shard lease.

The last case that needs to be considered is when moving objects from a dead instance, i.e. for rebalancing after an instance failure.
Once the sharder has detected a shard failure and acquired the shard lease as described in [@sec:des-membership], objects are reassigned immediately without performing a `drain` operation.
If the shard eventually becomes ready again, objects can be assigned to it again once it acquires its lease just like when a new instance is added.
A special case occurs when an instance failure is detected after initiating a `drain` operation.
In this case, the sharder removes the `drain` label by itself when updating the `shard` label to prevent performing the `drain` operation with the shard that the object is supposed to be assigned to.
