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
With this, the operator's capacity and throughput can be measured and compared more easily as they are mainly determined by the amount of objects and event rate for this one resource. 

2. In addition to watching the reconciled objects, the controller should also watch all relevant objects.
This includes owned objects, that the controller manages for realizing the intent of the reconciled objects.
Also, it should watch objects that might be referenced by multiple reconciled objects.
Both of these are common patterns in controllers, which makes the example operator a good representative.

3. Finally, the operator needs to follow controller best practices [@k8sdesign].
Most importantly, it should be level-based, meaning it performs reconciliations purely based on desired state and currently observed state but independent of observed changes to these states.
However, it should be edge-triggered for performance and responsiveness, i.e. start reconciliations based on relevant change events.
Reconciliations should be short and must not block until desired and actual state converge.
Lastly, the operator should hold all relevant state in memory, meaning it should cache all API resources it works with.
Following these best practices in the example operator is important, because most production-grade controllers are implemented in compliance with them.
Hence, the evaluation can only provide meaningful insights if the measured implementation follows the best practices.

Based on these criteria, the webhosting operator[^webhosting-operator] was designed and built.
The operator and its resources are modelled to form a webhosting-like platform, where customers can create and manage websites in a declarative manner via the Kubernetes API.
Websites reside in a project namespace, have a name, and specify a website theme, which defines color and font family.
The desired state of websites is declared via Kubernetes resources and the operator manages the required webservers and exposes them to the internet.

```yaml
apiVersion: webhosting.timebertt.dev/v1alpha1
kind: Theme
metadata:
  name: exciting
spec:
  color: darkcyan
  fontFamily: Menlo
---
apiVersion: webhosting.timebertt.dev/v1alpha1
kind: Website
metadata:
  name: homepage
  namespace: project-foo
spec:
  theme: exciting
```

: Example webhosting operator objects {#lst:webhosting}

Three API resources are involved when managing websites using the webhosting operator:

1. `Namespaces` are used to separate website of different customers and projects.
I.e., one could provide new customers with access to their own namespace upon registration to the service.

2. `Theme` is a custom resource of the webhosting operator and part of the `webhosting.timebertt.dev` API group.
`Themes` are cluster-scoped and can be referenced by `Websites` in all namespaces.
They are managed by the service administrator and configure an HTML color and font family.

3. `Websites` are also part of the operator's custom API group, but are namespaced.
A `Website` object represents a single website managed by a customer in a respective project namespace.
It references exactly one of the offered `Themes`.
For each `Website` object, the operator creates and configures an nginx `Deployment` to host a simple static website that displays the website's name and technical ID ("server name").
The website uses the color of the referenced `Theme` as a background color as well as the declared font family.
Additionally, the `Deployment` is exposed via an `Ingress` object on the URL path `/<namespace>/<website-name>`.

![Sample website managed by webhosting operator](../assets/sample-website.png)

The webhosting operator contains a single controller for realizing the webhosting functionality.
On each reconciliation of a `Website` object it ensures that owned objects of the `Website` are correctly configured: the nginx `ConfigMap` and `Deployment` as well as `Service` and `Ingress` for exposing the `Deployment`.
It adds owner references from all of these objects to the owning `Website` object.
In addition to watching `Website` objects, it also watches these owned objects and enqueues the owning `Website` for reconciliation on relevant changes, e.g. when the `Deployment` object's readiness status changes.
This facilitates self-healing capabilities of websites, as the operator ensures that all required objects have the desired state.
Additionally, it allows the controller to immediately report the status of the `Website` object in the `status.phase` field based on the status of the nginx `Deployment`.

Furthermore, the controller watches all available `Themes` and enqueues all `Website` objects that reference a `Theme` for reconciliation, if its specification changes.
With this, changes to `Themes` are immediately rolled out to all `Websites` that use them.
Also, `Website` reconciliations are very short, making the controller responsive and scalable.

## Architecture

The webhosting operator is leveraging the controller-runtime[^controller-runtime] library.
The library provides reusable constructs for building custom Kubernetes controllers -- operators -- in the Go programming language.
In controller-runtime, the `Manager` is the most important construct.
A `Manager` is initialized and started once per operator as the root component and manages all other components like controllers, webhook server and handlers, leader election, metrics endpoints, loggers, etc.

[^controller-runtime]: [https://github.com/kubernetes-sigs/controller-runtime](https://github.com/kubernetes-sigs/controller-runtime)

Individual controllers can be implemented by creating a corresponding `Controller` construct and configuring a `Reconciler` and watches.
The `Reconciler` contains the business logic of a controller.
It is invoked with a reconciliation request containing an object's name and namespace.
On each invocation, it has to ensure that the actual state of the system matches the desired state of the given object, i.e. perform reconciliation of the object.
The configured watches and event handlers are responsible for enqueuing reconciliation requests in response to relevant watch event emitted by the API server.
The `Controller` ensures that all other components like workqueue, cache and worker routines are correctly set up.
All `Controllers` are registered with the `Manager` which then ensures that the controllers are started when leader election is won and stopped as soon as leader election is lost.
It also injects shared dependencies like client, cache and loggers into the individual controllers.

As part of this thesis, the presented design (chapter [-@sec:design]) was implemented in the controller-runtime library in a generic way that allows reusing the mechanisms in all operators built upon the controller-runtime library.
The webhosting operator only makes use of the implemented sharding mechanisms in controller-runtime for demonstration and evaluation purposes. 

When adding controller sharding to an operator based on controller-runtime, there are two places involved: when configuring the `Manager` and when setting up the sharded `Controller`.



- perspective of controller developer / outside of library
  - new fields on manager / manager options for sharding
  - builder: offers new options for configuring sharded controllers/objects
- shard ID, lease attached to manager
- sharded cache attached to manager (filtered )
- lease controller once per manager
- sharder controller added per sharded object
- reconciler wrapper

## Shard Lease

- sharded runnables
- stopped when shard lease cannot be renewed

## Lease Controller

- explain shard states determined from shard leases
- shard state label on leases
- on shard failure, state label update basically triggers an event that the object sharder acts on
- explain event handler, predicates, mappers

## Sharder Controller

- consistent hashing
- ring constructed based on shard leases
- ring cached, reconstructed on lease updates
- 100 tokens per instance (similar to virtual nodes in cassandra), inspired by groupcache
- explain event handler, predicates, mappers

## Reconciler Wrapper

- injected for the reconciler of sharded controllers
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
- movement on rolling updates, idea: StatefulSet could be used for stable hostname to minimize movements during rolling updates

## Benefits / Applications ?

- dynamic scaling up and down
  - e.g. targeted queue wait duration, sharding size, active/idle workers
  - HPA on custom metrics
- canary rollout for controllers (separate deployment per version, number of virtual nodes)
- equally sized controller replicas
  - easier to right-size / scale vertically
