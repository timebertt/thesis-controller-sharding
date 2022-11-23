# Background

## Architecture

Kubernetes is an open-source container orchestration system that manages containers [@soltesz2007container] on a cluster of machines.
It is a distributed system composed of several components, that can be categorized as control plane components and worker node components.
The Kubernetes control plane consists of etcd and API server for storing cluster state and a set of controllers for managing the cluster's worker nodes and the workload itself.
Each worker node hosts a cluster agent called kubelet, a container runtime, and other system components that are responsible for tasks like networking, monitoring, etc. [@k8sdocs]

![Kubernetes cluster architecture [@k8sdocs]](../assets/cluster-architecture.pdf)

**etcd** is the only stateful component of the Kubernetes cluster architecture.
It is a consistent key-value store, that is used by the API server for storing the entire cluster state.
etcd itself can be run as a set of etcd instances (also called "cluster") for ensuring high availability.
Running multiple instances of etcd doesn't increase performance though, as there will only be one leader accepting write operations.
The only component communicating directly with etcd is the API server, all other components use etcd only indirectly through the API server. [@k8sdocs; @etcddocs]

The Kubernetes **API server** exposes a REST API [@fielding2000architectural] – the Kubernetes API – as the single point of entry for all cluster operations.
As a stateless component, it can be scaled horizontally in order to increase throughput and availability by load balancing between multiple instances [@bondi2000characteristics].
The cluster's state is persisted and managed in form of API objects following the "Kubernetes Resource Model" ([@sec:resourcemodel]).
The API server allows retrieving and manipulating objects via standard HTTP mechanisms using the respective API endpoints.
It transforms API objects from and to the storage format that is used for persisting them in etcd.
For human users of the API, objects are typically presented in YAML.
The operations on objects and related mechanics that the API server exposes are often referred to as "API machinery" ([@sec:apimachinery]).

Kubernetes **controllers** control the actual state of the cluster to match the desired state, that the user or other controllers specified declaratively.
Controllers work on individual API objects retrieved from the API server and implement their actual business logic.
For this purpose, controllers use the API server's mechanics for listening for changes to API objects and update the current state of the objects on the API server.
Typically, there is a single controller for each kind of API object.
Controllers are contained in multiple components of the cluster, most prominently in the Kubernetes controller manager and scheduler.
These components contain most of the controllers for implementing the logic of Kubernetes' core API objects and are essential parts of the control plane. [@hausenblas2019programming]

**kubelet** and **kube-proxy** are node components running on every machine of the cluster.
They instrument the container runtime and networking stack for managing the cluster's workload.
At the core, both components are controllers as well and use the same mechanics as controllers that are part of the control plane.
However, kubelet, kube-proxy, and other node components as such are not relevant for this thesis and thus not discussed in more detail.

## Kubernetes Resource Model {#sec:resourcemodel}

Kubernetes is an API-centric system, meaning all users and components interact with the same central API, i.e., there is no internal or hidden API.
All resources of the Kubernetes API follow the same patterns, which are also referred to as the Kubernetes Resource Model. [@k8sdesign]

API objects are managed declaratively rather than imperatively.
This means users declare the desired state of objects via the respective API resources instead of performing iterative actions on them.
Changes to the desired state are accepted instantly without waiting for them to manifest in the system.
Controllers pick up the declared specification asynchronously and update the status of API objects while the actual state gradually converges with the desired state.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: default
  annotations:
    foo: bar
  labels:
    app: nginx
  uid: f4dc8f2d-075d-41b1-a511-0f44671cd5d0
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx
status:
  availableReplicas: 1
  readyReplicas: 1
  replicas: 1
  updatedReplicas: 1
```

: Example API object {#lst:deployment}

All API objects contain common metadata (`apiVersion`, `kind`, `metadata`) describing general object information.
`apiVersion` and `kind` fully identify the object's type in a given API group and the version it is described in (`GroupVersionKind`).
The `metadata` section contains the object's identifying `name` along with user-defined key-value pairs as `labels` and `annotations`.
Labels are used for filtering and grouping API objects by certain attributes, while annotations allow adding arbitrary information.
API objects are grouped by user-created namespaces (specified in `metadata.namespace`), if the respective type is namespace-scoped.
Additionally, all API objects are assigned a globally unique identifier in `metadata.uid`.
As it changes when an object is deleted and recreated, it can be used to distinguish between different instances of the same kind in the same namespace with the same name over time.

API objects can specify so-called owners in the `metadata.ownerReferences` field.
This is used by controllers for efficiently mapping objects to their owners.
Furthermore, an API object is automatically deleted by the garbage collector controller once all referenced owners are gone.

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-8f458dc5b
  namespace: default
  # ...
  ownerReferences:
  - apiVersion: apps/v1
    blockOwnerDeletion: true
    controller: true
    kind: Deployment
    name: nginx
    uid: f4dc8f2d-075d-41b1-a511-0f44671cd5d0
```

: Example owner reference {#lst:owner-reference}

Most API objects also contain `spec` and `status` sections.
The `spec` section contains the user-declared desired state of the object, while the `status` section contains the state observed by the responsible controller. [@k8sdocs]

## API Machinery {#sec:apimachinery}

The API server offers a discovery API (path `/api` and `/apis`) which allows clients to discover available API groups, resources, and versions.
Additionally, this API presents mappings between fully-qualified API kinds – `GroupVersionKind` – and their fully-qualified API resources – `GroupVersionResource`.
This process is also referred to as "REST mapping" and is used by clients to build the API URL corresponding to the API object they want to interact with.
I.e. the API URL of a given object follows this pattern: [@k8sdesign]

`/<prefix>/<group>/<version>/namespaces/<namespace>/<resource>/<name>`

The path prefix is `/apis`, except for resources belonging to the `core` API group, which is signified by a missing group in the `apiVersion` field, in which case the prefix `/api` is used.

Resources can have so-called subresources, which offer specific actions on a given API object.
E.g., the `/status` subresource allows updating the `status` section of an object, which enables segregating authorization policies for users and controllers.
Subresources are available under the API URL of the targeted object, suffixed with the subresource name.

API objects can be requested and manipulated in different API versions, which also describe the maturity level of the API.
However, the API server stores all objects only once in a designated API version.
If a client retrieves or updates objects in a version that is different from their storage version, the API server converts them back and forth.
Different API versions can thus be considered as different representations of the same API object, which allows Kubernetes to guarantee backward-compatibility of the API.
This is particularly important for the distributed architecture of Kubernetes and allows evolving and upgrading components independently.

Requests to API resources have different types – so-called verbs – that are identified by the used HTTP verb, path, and query parameters.
`get` requests use HTTP `GET` and a full API URL for retrieving a single object.
`list` requests are `get` requests but omit the name for retrieving all objects of a given kind in the cluster.
`list` requests can be restricted to a namespace if the resource is namespace-scoped.
`list` requests including the query parameter `watch=true` are called `watch` requests, which stream change events for a given kind of object.
These verbs are categorized as non-mutating.
The mutating verbs – not described in further detail – are: `create`, `update`, `patch`, `delete`, and `deletecollection`. [@k8sdocs]

Every Kubernetes object carries a `metadata.resourceVersion` field, which uniquely identifies the object's internal version as stored in etcd.
All mutating operations change the `resourceVersion` field, allowing clients to detect when an object was changed.
Currently, the field is backed by the revision that etcd stores as metadata for all keys and returns on all requests [@etcddocs].
Resource versions are represented as strings and must be treated as opaque by clients, i.e., they may only be checked for equality.
In Kubernetes, the resource version is used for implementing optimistic concurrency control and efficient detection of changes (watches).
In addition to the `resourceVersion` field, most API objects carry a `metadata.generation` field.
The `generation` field is set to `1` on creation and increased on every change to the `spec` section and on deletion.
This field is typically used by controllers for filtering out irrelevant change events.
Additionally, controllers typically report the latest observed generation of the API object in `status.observedGeneration` allowing other clients to determine if changes to the desired state have already been picked up by the controller.

For optimistic concurrency control, clients typically pass the resource version when updating or patching objects as part of a read-modify-write loop.
With this, the API server checks the given resource version against the resource version of the current object in the store.
If these values don't match, another concurrent update has been successfully written and the request is denied with `409 Conflict`.
This is an important mechanism in Kubernetes that prevents controllers and other clients from performing uncoordinated and conflicting changes to API objects. [@k8scommunity]

Watch requests are an important factor for the scalability of Kubernetes.
Watches are long-lived requests which stream notifications for changes to API objects, that clients care about.
Typically, clients make an initial `list` request for the collection of objects they are interested in and start listening for changes since the retrieved version.
For this, clients pass the resource version from the retrieved list as a query parameter of the watch request.
Starting from the specified resource version, the API server sends notifications in form of JSON documents affecting the watched objects with one of the types `ADDED`, `MODIFIED`, and `DELETED`.
The watch mechanism internally relies on etcd's `Watch` service [@etcddocs].
However, the API server only opens a single watch connection to etcd per resource type and dispatches events to all watches registered by API clients.
This is done to reduce the request load on etcd and save encoding/decoding effort.
Additionally, the API server keeps a history of watch events in memory – the "watch cache" – allowing clients to lag behind and to catch up with changes since an older resource version [@k8sdocs].

Label selectors are frequently used in Kubernetes to select a group of objects of the same kind based on common attributes stored in form of labels.
Clients can supply them via the `labelSelector` query parameter of `list` and `watch` requests (as well as `deletecollection` requests).
This instructs the API server to return a filtered list of objects that match the given selector, which saves encoding/decoding effort as well as network transfer.
However, it's important to note that the API server itself issues unfiltered requests to etcd and filters the results in memory before sending the result list back to clients.
This means the given label selector is matched on each list item or watch event individually.

Field selectors are similar to label selectors but filter by matching individual fields of objects rather than labels, e.g. `Pod.spec.nodeName`.
However, field selectors cannot be used for selecting arbitrary object fields.
Instead, they can only be used with specific fields for which the API server supports field selectors.
For `list` request, field selectors behave similarly to label selectors, meaning they are processed for each list item before returning the filtered result to clients.
Under certain circumstances, field selectors can however reduce processing effort on the API server side for `watch` requests via index lookups.

## API Extensions {#sec:apiextensions}

The Kubernetes API server features several mechanisms for extending the API and integrating third-party components.
These include most importantly: webhooks and custom resources.
Webhooks can be registered via dedicated API objects and provide means to validate or mutate API requests.
However, webhooks are not discussed in further detail in this thesis.
Custom resources, on the other hand, offer options to augment the set of built-in API resources with additional resources that follow the same API semantics. [@k8sdocs]

There are two ways to register custom resources with the API server: via `APIServices` (often referred to as API aggregation) and `CustomResourceDefinitions` (CRDs).
An `APIService` is a usual API object that configures the API server to delegate API requests for a certain set of `GroupVersions` to another API server (extension API server), that is typically deployed as a dedicated component into the cluster.
This extension API server needs to implement the same semantics as the Kubernetes API server itself so that clients can use the extended resources by the same means as built-in resources.
From a client's perspective, custom resources are available at the same endpoint (via the Kubernetes API server) and follow the same characteristics as described in [@sec:resourcemodel; @sec:apimachinery].
Extension API servers are developed, deployed, and managed independently of the Kubernetes API server and thus feature full flexibility but also require a certain amount of development and operations effort.

In contrast to that, CRDs offer a lightweight mechanism for augmenting the Kubernetes API with custom resources, though with less flexibility.
`CustomResourceDefinitions` are API objects that each register a single custom resource with the API server in a purely declarative manner.
Most importantly, they specify the API group, versions, and kind along with an optional API schema.
As soon as CRDs are created, the Kubernetes API server starts serving endpoints for the specified resources.
Although the API server doesn't know the concrete structure and meaning of the resources, it offers the same characteristics for such API objects.
This includes the same object structure (metadata, spec, and status), the same API request semantics (including watch requests), discovery endpoints, label selectors, and so on. [@k8sdocs; @hausenblas2019programming]

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: websites.webhosting.timebertt.dev
spec:
  group: webhosting.timebertt.dev
  names:
    kind: Website
    listKind: WebsiteList
    plural: websites
    singular: website
  scope: Namespaced
  versions:
  - name: v1alpha1
    served: true
    storage: true
    subresources:
      status: {}
    schema:
      openAPIV3Schema:
        description: Website enables declarative management of hosted websites.
        # ...
```

: Example CustomResourceDefinition {#lst:crd}

By leveraging these mechanisms, the Kubernetes API can be extended to provide declarative management of arbitrary API resources.
However, custom resources as such don't implement any corresponding business logic.
For this, additional controllers can be deployed that implement the logic for realizing the desired state declared by the API objects.
This combination of a custom resource and a custom controller is often referred to as the "operator pattern", where the custom controller is referred to as the "operator".
Operators can be used to codify any kind of operational knowledge for applications and represent a powerful mechanism for running cloud-native workloads on Kubernetes. [@hausenblas2019programming]

## Controllers

Kubernetes controllers are composed of the following building blocks: cache, event handlers, work queue, and worker routines.
Most of them are implemented in libraries, mainly client-go, the official Kubernetes API client for the go programming language.
Theoretically, controllers can be implemented in any arbitrary programming language.
However, most controllers use go to benefit from the matured and performance-optimized libraries that the official Kubernetes controllers are based on as well. [@samplecontroller]

![Building blocks of a controller [@samplecontroller]](../assets/controller-components.jpeg)

A controller's **cache** is responsible for watching the controller's object type on the API server, informing the controller about changes to the objects, and making the objects available to the controller in memory in form of an indexed store.
Therefore, it starts a so-called reflector that lists and watches a given object type as described in [@sec:apimachinery].
The reflector emits corresponding delta events and adds them to a queue.
An informer then reads these events from the queue and updates changed objects in the store accordingly for later retrieval by the controller.
The store (indexer) is a flat key-value store with additional indices for increasing the performance of namespaced lookups or lookups with field selectors, that the controller frequently uses.
In addition to saving objects in the store, the informer also distributes notifications to all event handlers registered by the controller.
Note, that the store is not a write-trough cache, meaning controllers might read an old version of the object they modified from the cache until the watch connection receives the respective change event.

Controllers can use caches for multiple object types if they work with different kinds of objects during reconciliation or listen for changes to related objects.
Therefore, controller caches are typically shared between all controllers of a single binary in order to reduce processing effort and memory consumption (`SharedIndexInformer`).
Caches can also be configured to use filtered list and watch requests (e.g., by namespace or label) to reduce overhead for processing, transferring, and storing objects that controllers are not interested in.

Controllers add **event handlers** to informers for notifications about all important watch events.
Typically, event handlers perform basic filtering for relevant changes based on the changed object to determine whether the controller needs to act on it or not.
This is done to reduce unnecessary reconciliation work.
If work needs to be done on the watched object, event handlers add the object's key (`namespace/name`) to the work queue.
However, event handlers don't always enqueue a key for the changed object itself.
Instead, they might also perform a mapping between watched objects and objects that the controller is responsible for.
For example, the `Job` controller manages `Pods` for carrying out the actual work and adds an `ownerReference` to the owned `Pods`.
When a `Pod` completes its work, the `Job` controller is notified of the status change via a watch event and enqueues the owning `Job` designated in `Pod.metadata.ownerReferences` to update the `Job` object's status accordingly.

A controller's **work queue** centrally keeps track of all keys of objects that the controller needs to perform actions on.
It decouples event handling and actual reconciliation: controllers might only act upon objects once taken from the queue, but never in event handlers.
The work queue also keeps track of all objects that are currently being processed by worker routines.
It ensures, that a given object key is only picked up by a single worker at a time, even if the key is added to the queue multiple times.
It only emits a key again once the processing worker has marked the key as processed.
Furthermore, the work queue implements multiple mechanisms that are important to the controller's stability and scalability.
For example, if work on a given object fails because of some error, the object's key is re-queued, so that it is picked up by a worker again.
The work queue keeps track of retries and applies an exponential backoff strategy and jittering in order to break the periodicity of the system.
Additionally, it applies overall and per-item rate limiting to the key emission rate to protect the controller from load spikes.

Eventually, the controller's actual work is carried out by **worker routines**, also referred to as "control loops".
Note, however, that they are not looping over a single object as often depicted.
Instead, they react to relevant changes as notified by the watch connection and pick a single key from the work queue at a time.
Workers mark the key as being processed, retrieve the full object from the cache and finally carry out the actual business logic of the controller.
If implemented in go, workers run as concurrent goroutines.
The number of concurrent workers reading from the queue and performing work can be raised in order to increase throughput and decrease queue wait time.

Controllers take the desired state of objects, observe the actual state and perform actions to reconcile both.
Generally, controllers need to be level-driven, meaning their actions should be based on observations of the full state independent of any intermediate state changes.
However, controllers are typically edge-triggered for increasing the scalability of the system and reducing unnecessary work and network transfer.
Therefore, they use API server watches instead of long-pulling. [@k8sdocs; @hausenblas2019programming]

## Leader Election {#sec:leader-election}

There might be multiple instances of a single controller binary, e.g., during rolling updates or in HA setups.
To prevent conflicting actions of multiple instances, one instance is elected to be the active one – the leader.
Controllers may only perform reconciliations when the instance is the current leader.
The leader election mechanism follows a simple protocol based on Kubernetes API objects.
For this purpose, dedicated `Lease` objects are used, `Endpoints` and `ConfigMaps` were used historically.
In these objects, a leader election record is persisted ([@lst:lease]), which states the current leader as well as when the lease has been acquired and for how long it is valid.

```yaml
apiVersion: coordination.k8s.io/v1
kind: Lease
metadata:
  creationTimestamp: "2022-06-16T08:54:48Z"
  name: kube-controller-manager
  namespace: kube-system
  resourceVersion: "522"
  uid: 562f1ebe-4da1-4dda-80ce-63b9a50337ab
spec:
  acquireTime: "2022-06-16T08:54:48.860913Z"
  holderIdentity: test-control-plane_2629b027-995b-40fe-991e-7aa3770bb654
  leaseDurationSeconds: 15
  leaseTransitions: 0
  renewTime: "2022-06-16T08:56:17.146876Z"
```

: Example Lease {#lst:lease}

All instances carry a unique identity, composed of pod name and container ID or any other unique identifier for the instance's process.
If there currently is no active leader, all instances try to create or update the respective object to become the leader.
As the API server denies concurrent writes to the same object (optimistic concurrency control, [@sec:apimachinery]), only a single write request can be successful, which determines the elected leader.
Once a given instance has successfully acquired leadership, it regularly renews its leadership by updating `renewTime`.
As long as the active leader renews the lease before `leaseDurationSeconds` expires, it continues to perform reconciliations and other instances need to stay on standby.
If however, the leader fails to renew its lease in time (loss of leadership), it must stop performing any actions and a new leader is elected.
In an HA setup with multiple instances, this mechanism ensures fast failovers in case of losing the active leader.

## Sharding in Distributed Databases {#sec:databases}

This section summarizes important and proven sharding approaches in well-known distributed databases [@abadi2009data; @agrawal2004integrating].
It is structured by mechanisms that are common across different implementations.
[Chapter @sec:design] evaluates which of these mechanisms and approaches can be applied to Kubernetes controllers as well.

First, nodes of distributed database clusters need to discover their peers and derive information about their state, e.g. whether they are ready to host data and serve queries or not.
One common approach for this **membership mechanism** is gossip-based and used for example in Cassandra and CockroachDB [@cassandradocs; @cockroachdbdocs].
In this approach, all nodes of the system are equal and there is no designated leader
or central instance.
Nodes announce themselves to the cluster and discover their peers by communicating with the cluster.
Node information is then propagated to other nodes via ongoing communication between peers, which is called gossip.
Several nodes can be used as seed nodes, which are used to bootstrap the gossip protocol.
If a node failure occurs the other nodes independently detect the failure based on the gossiped information.

Bigtable implements a different approach to discovering membership information, which is based on leases in a central metadata store [@bigtable2006].
Here, individual nodes don't communicate with each other for exchanging membership information but instead announce themselves to the master node by acquiring individual locks in Chubby, a highly-available lock service [@chubby2006].
As long as an instance is alive, it renews its lock lease to signal readiness to the master and serves data to clients.
The lock is deleted on termination to inform the master about the voluntary disruption.
The master watches the servers directory in Chubby and asks instances for the lock status to discover ready instances.
If an instance fails to report a healthy lock, the master tries to acquire the instance's lock to ensure Chubby is reachable.
If this succeeds, the master has successfully detected the instance failure and deletes the corresponding lock in Chubby so that the instance will not serve data again.
Another approach for implementing the membership mechanism includes frequent communication between a master and individual instances for checking their health status as seen in Spanner [@spanner2013].

After discovering available instances, sharded databases need an **algorithm for partitioning data**, i.e., for determining which data is stored by which instance.
For this, each unit of data holds a partition key that is used as input for the sharding algorithm.
Partition keys are typically backed by a physical index and often are part of a primary key structure.
In many database systems, application developers can designate a certain column as the partition key which allows co-locating related data.
If there is a natural sharding key in the applications business model, it can be used for example to place all data belonging to the same workspace, project, or similar structures on the same servers for improved query performance.
While the concept of partition keys is common among distributed databases, there are different approaches for the actual partitioning algorithm that assigns subsets of data to instances. [@agrawal2004integrating]

Bigtable, MongoDB, CockroachDB, and Spanner for example have some form of master instance to control data partitioning using some arbitrary logic.
In these systems, a central instance decides where to place data according to current server utilization, placement constraints, and similar indicators.
The partitioning information is persisted in metadata tables or metadata key ranges respectively that are known to all instances.
This allows all servers to discover where a given data subset is located for querying. [@bigtable2006; @mongodbdocs; @cockroachdbdocs; @spanner2013]

On the other hand, Cassandra and Dynamo use consistent hashing as a partitioning algorithm [@karger1997consistent] – also known as ring hashing.
In consistent hashing, servers and partition keys are both hashed onto an imaginary ring.
Data is assigned to the server with the key that has the smallest hash larger than the hash of the partition key.
When new servers are added to the ring or existing servers are removed from a ring with $n$ servers, only $1/n$ of all entries are moved to another server on average.
This provides near-optimal stability of partitioning in dynamic environments during scale-out/in operations.
A common improvement of consistent hashing is to use so-called virtual nodes for achieving a better distribution of keys in clusters with a small number of members.
For this, each instance is mapped to multiple tokens that are hashed onto the ring. [@stoica2001chord; @dynamo2007; @cassandradocs]

The third important sharding mechanism in distributed databases is the **coordination of client requests** and the **storage of assignments**.
Consistent hashing is deterministic given the partition key and cluster members' statuses.
Hence, there is no need to store data assignments in a central place in Cassandra and Dynamo.
Instead, data locality can be determined by all nodes independently, e.g., based on the gossiped membership information.
In Cassandra and Dynamo, clients can send requests to any cluster node.
The node then takes care of determining the responsible server for the queried data and proxies the request accordingly [@cassandradocs; @dynamo2007].
Similarly, clients can also send requests to any cluster member of a CockroachDB cluster, which looks up and caches data locality from the metadata key range and proxies them to the responsible node accordingly [@cockroachdbdocs].
In contrast to that, Bigtable stores the location of its metadata table in Chubby, which clients need to request to determine data locality.
For each request, clients first locate the requested data from the metadata table or possibly from a cache and then send the request to the responsible server [@bigtable2006].
In MongoDB and Spanner, there are dedicated server instances that don't store data and only respond to requests.
These proxies are responsible for locating data in the cluster and caching that information for further client requests [@mongodbdocs; @spanner2013].
One important aspect of all approaches to request coordination in distributed databases is that there is no single point of failure or bottleneck on the request path, that all client communication goes through.

Last, many sharded database setups also replicate data subsets to provide high availability and durability.
Typically, there is some form of **concurrency control** involved to provide consistency despite concurrent requests to different replicas of the same data subset.
Depending on the database's consistency guarantees, different approaches are applied.
Cassandra and Dynamo use timestamp versioning per data item and resolve conflicts by applying the "last write wins" policy [@cassandradocs; @dynamo2007].
In other database systems, a form of distributed consensus algorithm is leveraged to provide concurrency control.
Examples of this are Paxos as used in Chubby [@chubby2006], raft as used in etcd [@etcddocs], or multi-group derivatives of them as used in Spanner and CockroachDB [@spanner2013; @cockroachdbdocs].
