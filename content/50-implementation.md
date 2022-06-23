# Implementation

## Sharding Criteria

- chosen sharding criteria

## Sharding Mechanism

- replica discovery
  - via (headless?) Service?
  - StatefulSet for stable shard identity?
- sharding controller:
  - deployment model: goroutine / sidecar / webhook / individual deployment?
- manifesting sharding decisions
  - in objects themselves
  - or in dedicated objects
    - e.g. if sharded by namespace
    - otherwise, watches not restrictable
  - or in external store
  - labels
    - selectable on watch connection
    - users can remove labels -> should be deterministic / cached
  - status field
    - only possible on custom resources you control
    - needs field selector to be selectable
    - not supported using CRDs
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

## Observability

- metrics for shards: sharding size, sharding latency
- visualization
