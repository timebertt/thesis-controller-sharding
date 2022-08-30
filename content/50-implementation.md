# Implementation

This chapter describes how the design presented in [chapter @sec:design] is implemented in practice.
First, the webhosting operator is introduced which serves as an example operator for implementing sharding in Kubernetes controllers.
Then, the overall architecture of the implementation is described followed by detailed descriptions of the most important aspects.

The presented implementation is used for evaluation in [chapter @sec:evaluation].

## Webhosting Operator

[^webhosting-operator]: [https://github.com/timebertt/kubernetes-controller-sharding](https://github.com/timebertt/kubernetes-controller-sharding)

In order to implement and evaluate the presented design, an operator is needed that serves as an example.
The sample operator should fulfill the following criteria so that the most important aspects of sharding in Kubernetes controllers can be covered and evaluated:

1. The operator should be composed of a single controller performing reconciliations for one (custom) resource.
With this, the operator's capacity and throughput can be measured and compared more easily as they are mainly determined by the amount and event rate of this one resource. 

2. In addition to watching the reconciled objects, the controller should also watch all relevant objects.
This includes owned objects, that the controller manages for realizing the intent of the reconciled objects.
Also, it should watch objects that might be referenced by multiple reconciled objects.
Both of these scenarios are common upon controllers, which makes the example operator a good representative.

3. Finally, the operator needs to follow controller best practices [@k8sdesign].
Most importantly, it should be level-based, meaning it performs reconciliations purely based on desired state and currently observed state but independent of observed changes to these states.
However, it should be edge-triggered for performance and responsiveness, i.e. start reconciliations based on relevant change events.
Reconciliations should be short and must not block until desired and actual state converge.
Lastly, the operator should hold all relevant state in memory, meaning it should cache all API resources it works with.
Following these best practices in the example operator is important, because most controllers are implemented in compliance with them.
Hence, the evaluation can only provide meaningful insights if the measured implementation follows the best practices.

Webhosting Operator [^webhosting-operator]
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

\todo[inline]{move to next chapter?}

- webhosting-exporter
- kube-state-metrics, kube-prometheus, Grafana
- metrics for sharding: shard sizes, sharder actions, ring calculations
- visualization: dashboards

## Challenges ?

- sharding of owned objects is only eventually consistent
  - could lead to problems?
  - owned object assigned later than owner
  - owner is drained, owned object immediately reassigned

## Benefits / Applications ?

- dynamic scaling up and down
  - e.g. targeted queue wait duration, sharding size, active/idle workers
  - HPA on custom metrics
- canary rollout for controllers (separate deployment per version, number of virtual nodes)
- equally sized controller replicas
  - easier to right-size / scale vertically
