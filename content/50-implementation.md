# Implementation

## Demo Operator

- introduce webhosting-operator [^webhosting-operator]

[^webhosting-operator]: [https://github.com/timebertt/kubernetes-controller-sharding](https://github.com/timebertt/kubernetes-controller-sharding)

**Requirements**

In order to demonstrate and compare different sharding approaches, an operator is needed that fulfills the following requirements:

- it needs to act on multiple custom resources
  - for demonstrating the sharding by resource type approach
- in addition to watching its own resources, it needs to watch other objects (e.g. owned objects) as well
  - sharding will be difficult here, so add it as a challenge
- it needs to deal with cluster-scoped objects (that are relevant for multiple namespaced objects)
  - this adds side effects (duplicated cache) which need to be taken care of

**Idea**

The idea behind this operator is simple: we want to build a webhosting platform on top of Kubernetes.
This means, we want to be able to configure websites for our customers in a declarative manner.
The desired state is configured via Kubernetes (custom) resources and the operator takes care to spin up websites and expose them.

There are three resources involved:

- `Namespace`
  - each customer project gets its own namespace
- `Theme` (`webhosting.timebertt.dev`, cluster-scoped)
  - represents an offered theme for customer websites (managed by service admin)
  - configures a font family and color for websites
- `Website` (`webhosting.timebertt.dev`, namespaced)
  - represents a single website a customer orders (managed by customer in a project namespace)
  - website simply displays the website's name (static)
  - each website references exactly one theme
  - deploys and configures a simple `nginx` deployment
  - exposes the website via service and ingress


## Architecture

- controller-runtime
- perspective of controller developer / outside of library
- shard lease attached to manager
- sharding configured per controller-watch pair
- ...

## Shard Lease

- sharded runnables
- stopped when shard lease cannot be renewed

## Lease Controller

- explain states
- on shard failure, state label update basically triggers an event that the object sharder acts on
- idea: StatefulSet could be used for stable hostname to minimize movements during rolling updates
- explain event handler, predicates, mappers

## Sharder Controller

- consistent hashing
- ring constructed based on shard leases
- ring cached, reconstructed on lease updates
- 100 tokens per instance (similar to virtual nodes in cassandra), inspired by groupcache
- explain event handler, predicates, mappers

## Object Controller

- reconciler wrapper
  - check shard label, discard object if not assigned to instance
  - remove drain label if present
- explain event handler, predicates, mappers

## Observability

- webhosting-exporter
- kube-state-metrics, kube-prometheus, Grafana
- metrics for sharding: shard sizes, sharder actions, ring calculations
- visualization: dashboards

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
