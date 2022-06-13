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

\todo[inline]{OwnerReferences / garbage collection?}

## API Machinery {#sec:apimachinery}

The API server offers a discovery API (path `/api` and `/apis`) which allows clients to discover available API groups, resources and versions.
Additionally, this API presents mappings between fully-qualified API kinds -- `GroupVersionKind` -- and their fully-qualified API resources -- `GroupVersionResource`.
This process is also referred to as "REST mapping" and is used by clients to build the API URL corresponding to the API object they want to interact with.
I.e. the API URL of a single object is structured like this: [@k8sdesign]

`/<prefix>/<group>/<version>/namespaces/<namespace>/<resource>/<name>`

`prefix` is `/apis`, expect for resources belonging to the `core` API group, which is signified by a missing group in the `apiVersion` field, in which case `prefix` is `/api`.

API objects can be requested and manipulated in different API versions, which also describe the maturity level of the API.
However, the API server stores all objects only once in a predefined API version.
If a client retrieves or updates objects in a version that is different from their storage version, the API server converts them back and forth.
Different API versions can thus be considered as different representations of the same API object, which allows guaranteeing backwards-compatibility of the API.
This is particularly important in the distributed architecture of Kubernetes and allows to evolve and upgrade components independently.

- request types
- subresources?
- resource version, concurrency control
- watches
  - shared watch cache on API server to reduce load on etcd
  - watch history to allow latency of clients
- field selectors, label selectors
  - unfiltered requests to etcd, filtered by API server
- extension points:
  - custom resources
  - webhooks
  - API aggregation?

## Controllers

- basic building blocks of controllers:
  - informers, watches, event handlers
  - caches
  - queues
  - concurrent workers
- actual and desired state of world
- edge-triggered, level-driven
- leader election
- implications on resources
  - CPU: encoding, decoding, conversion, actual work
  - memory: caches
  - network: watch connections, API requests
  - on API server side: watch cache, watch connections, etc.
- operator pattern: custom resource + controller
