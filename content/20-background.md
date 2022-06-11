# Background

## Architecture

Kubernetes is an open-source container orchestration system that manages containers on a cluster of machines.
It is a distributed system composed of several components, that can be categorized as control plane components and node components.
The Kubernetes control plane consists of etcd and API server for storing cluster state and a set of controllers for managing the cluster's worker nodes and workload.
Each worker node hosts a cluster agent called kubelet, a container runtime and other system components that are responsible for tasks like networking. [@k8sdocs]

![Kubernetes Cluster Architecture [@k8sdocs]](../assets/cluster-architecture.png)

\todo{redraw?}

**etcd** [@etcddocs] is the only stateful component of the Kubernetes architecture.
It is a consistent key-value store, that is used by API server for storing the entire cluster state.
etcd itself can be run as a set of etcd instances (etcd cluster) for ensuring high availability.
Running multiple instances of etcd doesn't increase performance though, as there will only be one leader accepting write operations.
The only component communicating directly with etcd is the API server, all other components use etcd only indirectly through the API server.

The Kubernetes **API server** exposes a REST API [@fielding2000architectural] -- the Kubernetes API -- as the single point of entry for all cluster operations.
As a stateless component, it can be scaled horizontally in order to increase throughput and availability by load balancing between multiple instances.
The cluster's state is persisted and managed in form of API objects.
The API server allows retrieving and manipulating objects via standard HTTP mechanisms using the respective API endpoints.
It transforms API objects from and to the storage format used for persisting them etcd.
For human users of the API, objects are typically presented in YAML.
The operations on objects and related mechanics that the API server exposes are often referred to as "API machinery" and are discussed in more detail in the next section ([-@sec:apimachinery]).

Kubernetes **controllers** control the actual state of the cluster to match the desired state, that the user or other controllers specified declaratively.
Controllers work on individual API objects retrieved from the API server and implement their actual business logic.
For this purpose, controllers use the API server's mechanics for listening for changes to API objects and update the current state of the objects on the API server.
Typically, there is a single controller for each kind of API object.
Controllers are contained in multiple components of the cluster, most prominently in the Kubernetes controller manager and scheduler.
Controller manager and scheduler contain most of the controllers for implementing the logic of Kubernetes' core API objects and are essential parts of the control plane.

**kubelet** and **kube-proxy** are node components running on every machine of the cluster.
They instrument the container runtime and networking stack for managing the cluster's workload.
At the core, both components are controllers as well and use the same mechanics as controllers that are part of the control plane.
However, kubelet, kube-proxy and other node components as such are not relevant for this thesis and thus not discussed in more detail.

## API Machinery {#sec:apimachinery}

- Kubernetes Resource Model
  - declarative nature
- basic building blocks of API objects
  - Object Metadata, Spec, Status
  - GroupVersionKind / GroupVersionResource
  - Namespaces
  - OwnerReferences / garbage collection?
- Versioning
  - backwards-compatibility?
  - conversion
- REST API, request types, subresources
  - discovery?
- resource version, concurrency control
- watches
- field selectors, label selectors
- extension points: custom resources?

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
