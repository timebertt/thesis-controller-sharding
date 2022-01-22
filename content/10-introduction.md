# Motivation

- kubernetes controllers are the "brains of the cluster"
- controllers as such are stateless
- only state they carry is leadership
- leader election: only active/passive HA-setups
- scalability limits: machine size, network bandwidth (-> cost implications)
- no canary rollout: no able to gradually shift leadership

# Background

- Kubernetes background

## Architecture

- etcd
  - only stateful component in cluster
- API servers
  - stateless
  - provide API machinery
  - watch connections
- controllers
  - actual implementation of API logic

## API Machinery

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

# Sharding in Distributed Databases

- background on distributed databases
- look into Cassandra, MongoDB, CockroachDB, Spanner/F1, ...
- consensus vs sharding algorithms?
  - paxos, raft, ...

## Sharding Criteria

- input for sharding algorithms
- object / row ID (primary key)
- arbitrary sharding key
  - natural sharding key in product (e.g. workspace, project, etc.)

## Algorithms

- consistent hashing

# Sharding in Kubernetes Controllers

- transfer ideas from distributed databases
- distributed scheduling?

## Sharding Criteria

- by resource
  - can't be done dynamically / during runtime (or at least that's more difficult)
  - unequal sharding / no control over shard sizes
  - controllers probably need to list/cache resources, that are handled by other controllers -> overhead, scalability benefits questionable
  - doesn't provide HA / multiple instances for controllers
- by namespace
  - one controller per namespace
    - easy to implement via operator/meta-controller
    - dedicated RBAC, ...
    - still caches cluster-scoped resources
    - high overhead, scalability benefits questionable
  - multiple namespaces per controller instance
    - label namespaces with shard id, reconstruct cache/watches on changes to set of responsible namespaces
    - -> restart of controller's necessary?
    - restart of caches/controllers undesirable
      - restarts are costly
      - reduces scalability benefits
- by name
- by arbitrary shard key
  - one shard only holds objects with one shard key value
    - e.g. by seed name, by extension provider type

- mapping from sharding key to shard
  - n to n (e.g. controller per namespace)
  - n to m, with n > m (e.g. controller for multiple namespaces)

## Implementation

- manifesting sharding decisions
  - in objects themselves
  - or in dedicated objects
    - e.g. if sharded by namespace
    - otherwise, watches not restrictable
  - labels
    - selectable on watch connection
    - users can remove labels -> should be deterministic / cached
  - status field
    - needs field selector to be selectable
    - not supported using CRDs
- sharding controller
  - deployment model: goroutine / sidecar / individual deployment?
  - populating sharding keys
- actual controller changes
  - restrict watches with namespace/label/field selectors
  - handover?

## Benefits / Applications

- dynamic scaling up and down
  - e.g. targeted queue wait duration, sharding size, active/idle workers
  - HPA on custom metrics
- canary rollout for controllers
- equally sized controller replicas
  - easier to right-size / scale vertically

# Experiment

## Setup

- describe measurements
  - resource consumption: CPU, memory
  - profiling?
  - network usage
  - both on controller and server side
- how are measurements done
  - cadvisor
  - prometheus
  - grafana
- describe experiment process
  - look into kubernetes performance tests

## Execution

- execute experiment for different approaches

## Evaluation

- compare approaches by test results

# Conclusion

- which approach worked best?
