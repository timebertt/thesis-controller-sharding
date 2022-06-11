# Background

- Kubernetes background

## Architecture

- etcd
  - stores entire cluster state
  - only stateful component in cluster
- API servers
  - provides API for all cluster operations, single point of entry
  - stateless
  - provide API machinery
  - watch connections
  - label selectors
- controllers
  - actual implementation of API logic
- kubelet, etc.
  - are controllers as well, but irrelevant for this topic

## API Machinery

- Kubernetes Resource Model
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
