# Implementation

## Architecture

- controller-runtime
- shard lease attached to manager
- sharding configured per controller-watch pair
- ...

## Membership and Failure Detection

- sharded runnables
- stopped when shard lease cannot be renewed
- explain states
- on shard failure, state label update basically triggers an event that the object sharder acts on
- idea: StatefulSet could be used for stable hostname to minimize movements during rolling updates

## Partitioning

- consistent hashing
- ring constructed based on shard leases
- ring cached, reconstructed on lease updates
- 100 tokens per instance (similar to virtual nodes in cassandra), inspired by groupcache

## Coordination and Object Assignment

- reconciler wrapper
  - check shard label, discard object if not assigned to instance
  - remove drain label if present

## Preventing Concurrency


## Challenges

- sharding of owned objects is only eventually consistent
  - could lead to problems?
  - owned object assigned later than owner
  - owner is drained, owned object immediately reassigned

## Benefits / Applications

- dynamic scaling up and down
  - e.g. targeted queue wait duration, sharding size, active/idle workers
  - HPA on custom metrics
- canary rollout for controllers (separate deployment per version, number of virtual nodes)
- equally sized controller replicas
  - easier to right-size / scale vertically

## Observability

- metrics for shards: sharding size, sharding latency
- visualization
