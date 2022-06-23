# Background

## Architecture

Kubernetes is an open-source container orchestration system that manages containers on a cluster of machines.
It is a distributed system composed of several components, that can be categorized as control plane components and node components.
The Kubernetes control plane consists of etcd and API server for storing cluster state and a set of controllers for managing the cluster's worker nodes and the workload itself.
Each worker node hosts a cluster agent called kubelet, a container runtime and other system components that are responsible for tasks like networking, monitoring, etc. [@k8sdocs]

![Kubernetes Cluster Architecture [@k8sdocs]](../assets/cluster-architecture.png)

\todo{redraw?}

**etcd** [@etcddocs] is the only stateful component of the Kubernetes cluster architecture.
It is a consistent key-value store, that is used by the API server for storing the entire cluster state.
etcd itself can be run as a set of etcd instances (also called "cluster") for ensuring high availability.
Running multiple instances of etcd doesn't increase performance though, as there will only be one leader accepting write operations.
The only component communicating directly with etcd is the API server, all other components use etcd only indirectly through the API server.

The Kubernetes **API server** exposes a REST API [@fielding2000architectural] -- the Kubernetes API -- as the single point of entry for all cluster operations.
As a stateless component, it can be scaled horizontally in order to increase throughput and availability by load balancing between multiple instances.
The cluster's state is persisted and managed in form of API objects following the "Kubernetes Resource Model" (see [-@sec:resourcemodel]).
The API server allows retrieving and manipulating objects via standard HTTP mechanisms using the respective API endpoints.
It transforms API objects from and to the storage format that is used for persisting them in etcd.
For human users of the API, objects are typically presented in YAML.
The operations on objects and related mechanics that the API server exposes are often referred to as "API machinery" (see [-@sec:apimachinery]).

Kubernetes **controllers** control the actual state of the cluster to match the desired state, that the user or other controllers specified declaratively.
Controllers work on individual API objects retrieved from the API server and implement their actual business logic.
For this purpose, controllers use the API server's mechanics for listening for changes to API objects and update the current state of the objects on the API server.
Typically, there is a single controller for each kind of API object.
Controllers are contained in multiple components of the cluster, most prominently in the Kubernetes controller manager and scheduler.
These components contain most of the controllers for implementing the logic of Kubernetes' core API objects and are essential parts of the control plane.

**kubelet** and **kube-proxy** are node components running on every machine of the cluster.
They instrument the container runtime and networking stack for managing the cluster's workload.
At the core, both components are controllers as well and use the same mechanics as controllers that are part of the control plane.
However, kubelet, kube-proxy and other node components as such are not relevant for this thesis and thus not discussed in more detail.

## Kubernetes Resource Model {#sec:resourcemodel}

Kubernetes is an API-centric system, meaning all users and components interact with the same central API, i.e., there are no internal or hidden APIs.
All resources of the Kubernetes API follow the same patterns, that are described as the Kubernetes Resource Model. [@k8sdesign]

API objects are managed declaratively rather than imperatively.
This means, users declare the desired state of objects via the respective API resources instead of performing iterative actions on them.
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

\todo[inline]{Caption not working}

All API objects contain common metadata (`apiVersion`, `kind`, `metadata`) describing general object information.
`apiVersion` and `kind` fully identify the object's type in a given API group and the version it is described in (`GroupVersionKind`).
The `metadata` section contains the object's identifying `name` along with user-defined key-value pairs as `labels` and `annotations`.
Labels are used for filtering and grouping API objects by certain attributes, while annotations allow adding arbitrary information.
API objects are grouped by user-created namespaces (specified in `metadata.namespace`), if the respective type is namespace-scoped.

Most API objects also contain `spec` and `status` sections.
The `spec` section contains the user-declared desired state of the object, while the `status` section contains the state observed by the responsible controller.

\todo[inline]{OwnerReferences / garbage collection}

## API Machinery {#sec:apimachinery}

The API server offers a discovery API (path `/api` and `/apis`) which allows clients to discover available API groups, resources and versions.
Additionally, this API presents mappings between fully-qualified API kinds -- `GroupVersionKind` -- and their fully-qualified API resources -- `GroupVersionResource`.
This process is also referred to as "REST mapping" and is used by clients to build the API URL corresponding to the API object they want to interact with.
I.e. the API URL of a given object follows this pattern: [@k8sdesign]

`/<prefix>/<group>/<version>/namespaces/<namespace>/<resource>/<name>`

`prefix` is `/apis`, except for resources belonging to the `core` API group, which is signified by a missing group in the `apiVersion` field, in which case `prefix` is `/api`.

Resources can have so-called subresources, which offer specific actions on a given API object.
E.g., the `/status` subresource allows to update the `status` section of an object, which enables segregating authorization policies for users and controllers.
Subresources are available under the API URL of the targeted object, suffixed with the subresource name.

API objects can be requested and manipulated in different API versions, which also describe the maturity level of the API.
However, the API server stores all objects only once in a designated API version.
If a client retrieves or updates objects in a version that is different from their storage version, the API server converts them back and forth.
Different API versions can thus be considered as different representations of the same API object, which allows Kubernetes to guarantee backwards-compatibility of the API.
This is particularly important in the distributed architecture of Kubernetes and allows evolving and upgrading components independently.

Requests to API resources have different types -- so-called verbs -- that are identified by the used HTTP verb, path and query parameters.
`get` requests use HTTP `GET` and a full API URL for retrieving a single object.
`list` requests are `get` requests but omit the name for retrieving all objects of a given kind in the cluster.
`list` requests can be restricted to a namespace if the resource is namespace-scoped.
`list` requests including the query parameter `watch=true` are called `watch` requests, which stream change events for a given kind of objects.
These verbs are non-mutating, the mutating verbs are: `create`, `update`, `patch`, `delete` and `deletecollection` [@k8sdocs]. 
Mutating requests are not relevant for this thesis, thus they are not discussed in further detail.

Every Kubernetes object carries a `metadata.resourceVersion` field, which uniquely identifies the object's internal version as stored in etcd.
All mutating operations change the `resourceVersion` field, allowing clients to detect when an object was changed.
Currently, the field is backed by the revision that etcd stores as metadata for all keys and returns on all requests.
Resource versions are represented as strings and must be treated as opaque by clients, i.e., they may only be checked for equality.
In Kubernetes, the resource version is used for implementing optimistic concurrency control and efficient detection of changes (i.e., watches).

\todo[inline]{generation?}

For optimistic concurrency control, clients typically pass the resource version when updating or patching objects as part of a read-modify-write loop.
With this, the API server checks the given resource version against the resource version of the current object in the store.
If the values don't match, a concurrent update has been successfully written and the request is denied with `409 Conflict`.
This is an important mechanism in Kubernetes that prevents controllers and other clients from performing uncoordinated and conflicting changes to API objects [@k8scommunity].

Watch requests are an important factor for the scalability of Kubernetes.
Watches are long-lived requests sending notifications for changes to API objects, that clients care about.
Typically, clients make an initial `list` request for the collection of objects they are interested in and start listening for changes since the retrieved version.
For this, clients pass the resource version from the retrieved list as a query parameter in the watch request.
Starting from the specified resource version, the API server sends notifications in form of JSON documents affecting the watched objects with type `ADDED`, `MODIFIED` or `DELETED`.
The watch mechanism internally relies on etcd's `Watch` service [@etcddocs].
However, the API server only opens a single watch to etcd per resource type and dispatches events to all watches registered by clients.
This is done to reduce the request load on etcd and save encoding/decoding effort.
Additionally, the API server keeps a history of watch events in memory -- the "watch cache" -- allowing clients to lag behind and to catch up with changes since an older resource version [@k8sdocs].

Label selectors are frequently used in Kubernetes to select a group of objects of the same kind based on common attributes stored in form of labels.
Clients can supply them via the `labelSelector` query parameter on `list` and `watch` requests (as well as `deletecollection`).
This instructs the API server to return a filtered list of objects that match the given selector, which saves encoding/decoding effort as well as network transfer.
However, it's important to note that the API server itself issues unfiltered requests to etcd and filters the results in memory before sending the result list back to clients.
This means, the given label selector is matched on each list item or watch event individually. 

Field selectors are similar to labels selectors but filter by matching individual fields of objects rather than labels, e.g. `Pod.spec.nodeName`.
However, field selectors cannot be used for selecting arbitrary object fields.
Instead, they can only be used with specific fields for which the API server supports field selectors.
For `list` request, field selectors behave similar to label selectors, meaning they are processed for each list item before returning the filtered result to clients.
Under certain circumstances, field selectors can however decrease processing effort on the API server side for `watch` requests via index lookups.

## API Extensions

\todo[inline]{check if relevant}

- CustomResourceDefinition
- Webhooks
- API aggregation?
- operator pattern: custom resource + controller

## Controllers

Kubernetes controllers are composed of the following building blocks: cache, event handlers, workqueue and worker routines.
Most of them are implemented in libraries, mainly client-go, the official Kubernetes API client for the go programming language.
Theoretically, controllers can be implemented in any arbitrary programming language.
However, most controllers use go in order to benefit from the matured and performance-optimized libraries that the official Kubernetes controllers are based on themselves. [@samplecontroller]

![Building Blocks of a Controller [@samplecontroller]](../assets/controller-components.jpeg)

A controller's **cache** is responsible for watching the controller's object type on the API server, inform the controller about changes to them and make the objects available to the controller in memory in form of an indexed store.
It therefore starts a reflector that lists and watches a given object type as described in section [-@sec:apimachinery].
The reflector emits corresponding delta events and adds them to a queue.
An informer then reads these events from the queue and updates changed objects in the store accordingly for later retrieval by the controller.
The store (indexer) is a flat key-value store with additional indices for increasing performance of namespaced lookups or lookups with field selectors, that the controller frequently uses.
In addition to saving objects in the store, the informer also distributes notifications to all event handlers registered by the controller.
Note, that the store is not a write-trough cache, meaning controllers might read an old version of the object they modified from the cache, until the watch connection received the respective change event.

Controllers can use caches for multiple object types if they work with different kinds of objects during reconciliation or listen for changes to related objects.
Therefore, controller caches are typically shared between all controllers of a single binary in order to reduce processing effort and memory consumption (`SharedIndexInformer`).
Caches can also be configured to use filtered list and watch requests (e.g., by namespace or label) in order to reduce overhead for processing and storing objects that controllers are not interested in.

Controllers add **event handlers** to informers in order to be notified for all important watch events.
Typically, event handlers perform basic filtering for relevant changes on the changed object to determine whether the controller needs to act on it or not.
This is done to eliminate unnecessary reconciliation work.
If work needs to be done on the watched object, event handlers add the object's key (`namespace/name`) to the workqueue.
However, event handlers don't always enqueue the changed object itself.
Instead, they might also perform mapping between watched objects and objects that the controller is responsible for.
For example, the `Job` controller manages `Pods` for carrying out the actual work and adds an `ownerReference` to the owned `Pods`.
When a `Pod` completes its work, the `Job` controller is notified of the status change via a watch event and enqueues the owning `Job` designated in `Pod.metadata.ownerReferences`.

A controller's **workqueue** centrally keeps track of all keys of objects that the controller needs to perform actions on.
It decouples event handling and actual reconciliation: controllers might only act upon objects once taken from the queue, but never in event handlers.
The workqueue also keeps track of all objects that are currently being processed by worker routines.
It ensures, that a given object key is only picked up by a single worker at a time, even if the key is added to the queue multiple times.
It only emits a key again once the processing worker has marked the key as processed.
Furthermore, the workqueue implements multiple mechanisms that are important to the controller's stability and scalability.
For example, if work on a given object fails because of some error, the object's key is re-queued, so that it is picked up by a worker again.
The workqueue keeps track of retries and applies an exponential backoff and a jitter in order to break periodicity of the system.
Additionally, it applies overall and per-item rate limiting to the key emission rate to protect the controller from load spikes.

Eventually, the controller's actual work is carried out by **worker routines**, also referred to as "control loops".
Note however, that they are not actually looping over a single object as often depicted.
Instead, they react on relevant changes as notified by the watch connection and pick up a single key from the workqueue at a time.
Workers mark the key as being processed, retrieve the full object from the cache and finally carry out the actual business logic of the controller.
If implemented in go, workers run as concurrent goroutines.
The number of concurrent workers reading from the queue and performing work can be raised in order to increase throughput and decrease wait time.

Controllers take the desired state of objects, observe the actual state and perform actions to converge both.
Generally, controllers need to be level-driven, meaning their actions should be based on observations of the full state independent of any intermediate state changes.
However, controllers are typically edge-triggered for increasing scalability of the system and reducing unnecessary work and network transfer.
Therefore, they use API server watches instead of long-pulling.

There might be multiple instances of a single controller binary, e.g., during rolling updates or in HA-setups.
In order to prevent conflicting actions of multiple instances, one instance is elected to be the active one -- the leader.
Controllers may only perform reconciliations when the instance is the current leader.
The leader election mechanism follows a simple protocol based on Kubernetes API objects.
For this purpose, dedicated `Lease` objects are used, `Endpoints` and `ConfigMaps` were used historically.
In these objects, a leader election record is persisted ([@lst:lease])\todo{not working}, that states the current leader as well as when the lease has been acquired and for how long it is valid.

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

: Example Lease Object {#lst:lease}

All instances carry a unique identity, composed of pod name and container ID or any other unique identifier for the instance's process.
If there currently is no active leader, all instances try to create or update the respective object to specify their identity.
As the API server denies concurrent writes to the same object, only a single write request can be successful, which determines the elected leader.
Once a given instance has successfully acquired leadership, it regularly renews its leadership by updating `renewTime`.
As long as the active leader renews the lease before `leaseDurationSeconds` expires, it continues to perform reconciliations and other instances need to stay in stand-by.
If however, the leader fails to renew its lease in time (loss of leadership), it must stop performing any actions and a new leader is elected.
In an HA-setup with multiple instances, this mechanism ensures a fast fail-over in case of losing the active leader.
However, this effectively prevents scaling controllers horizontally and distributing work across multiple instances.

## Sharding in Distributed Databases

- background on distributed databases
- look into Cassandra, MongoDB, CockroachDB, Spanner/F1, ...
- consensus vs sharding algorithms?
  - paxos, raft, ...
- Sharding Criteria
  - input for sharding algorithms
  - object / row ID (primary key)
  - arbitrary sharding key
  - natural sharding key in product (e.g. workspace, project, etc.)
- Sharding Algorithms
  - consistent hashing
