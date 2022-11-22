# Implementation

This chapter describes how the design presented in [chapter @sec:design] is implemented in practice.
First, the webhosting operator is introduced which serves as an example operator for implementing sharding in Kubernetes controllers.
Then, the overall architecture of the implementation is described followed by detailed descriptions of the most important aspects.
The presented implementation is used for evaluation in [chapter @sec:evaluation].

## Webhosting Operator {#sec:webhosting-operator}

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
Additionally, `Website` reconciliations can be triggered by annotation changes for load test purposes.
The reconciliations themselves are very short, making the controller responsive and scalable.

## Architecture

The webhosting operator is leveraging the controller-runtime[^controller-runtime] library.
The library provides reusable constructs for building custom Kubernetes controllers – operators – in the Go programming language.
In controller-runtime, the `Manager` is the most important construct.
A `Manager` is initialized and started once per operator as the root component and manages all other components like controllers, webhook server and handlers, leader election, metrics endpoints, loggers, etc.

[^controller-runtime]: [https://github.com/kubernetes-sigs/controller-runtime](https://github.com/kubernetes-sigs/controller-runtime)

Individual controllers can be implemented by creating a corresponding `Controller` construct and configuring a `Reconciler`, watches, and event handlers.
The `Reconciler` contains the business logic of a controller.
It is invoked with a reconciliation request containing an object's name and namespace.
On each invocation, it has to ensure that the actual state of the system matches the desired state of the given object, i.e. perform reconciliation of the object.
The configured watches and event handlers are responsible for enqueuing reconciliation requests in response to watch events.
Typically, `Predicates` are used to filter for relevant watch events emitted by the API server.
The `Controller` itself ensures that all components including cache, event handlers, work queue and worker routines are correctly set up.
All `Controllers` are registered with the `Manager` which then ensures that the controllers are started when leader election is won and stopped as soon as leader election is lost.
It also injects shared dependencies like client, cache and loggers into the individual controllers.

As part of this thesis, the presented design ([chapter @sec:design]) was fully implemented in the controller-runtime library in a generic way that allows reusing the mechanisms in all operators built upon the controller-runtime library.
The webhosting operator makes use of the implemented sharding mechanisms in controller-runtime for demonstration and evaluation purposes. 

For adding controller sharding to an operator based on controller-runtime, there are two places involved: when configuring the `Manager` and when setting up a sharded `Controller`.
First, sharding has to be enabled by setting `manager.Options.Sharded=true`.
With this, the `Manager` is configured to maintain a shard lease while it is running ([-@sec:impl-shard-lease]).
Furthermore, it adds a second cache to the `Manager` which uses a label selector `shard=<shard-id>` for all objects.
This cache is then used by sharded controllers as a filtered cache that only contains objects that the shard is responsible for, hence it is referred to as sharded cache.
In controller-runtime, the cache is empty on startup and watches are only started on-demand when the cache is read from.
The `Manager`'s default cache (unfiltered) is still available for retrieval of non-sharded objects.
However, as long as controllers use the correct cache when reading objects, watches will only be started in one cache for any `GroupVersionKind` and thus are filtered correctly.
For development purposes, the shard ID can be overwritten optionally.
Also, `ShardMode` allows configuring whether the manager should only run the sharder components (when leading), only the shard components or both (default).

```go
mgr, err := manager.New(restConfig, manager.Options{
  // enable sharding for this manager
  Sharded: true,
  // optionally configure overwrites for development purposes
  ShardID:   "custom-shard-id",
  ShardMode: sharding.ModeSharder,
})
```

: Configuring the controller-runtime manager for sharding {#lst:manager-setup}

There are two sharder components: the lease controller and the sharder controllers.
Both are added in all instances, but they are only running when the instance has acquired leadership.
The lease controller ([-@sec:impl-lease-controller]) is running only once per leader and is mainly responsible for acquiring leases of unavailable shards (see [-@sec:des-membership]).
The sharder controllers are coupled to the setup of the sharded controllers themselves, though they only run in the leader.

```go
controller, err := builder.ControllerManagedBy(mgr).
  For(&webhostingv1alpha1.Website{}, builder.Sharded{}).
  // watch deployments in order to update phase on relevant changes
  Owns(&appsv1.Deployment{}, builder.Sharded{}).
  // watch themes to roll out theme changes to all referencing websites
  Watches(
    &source.Kind{Type: &webhostingv1alpha1.Theme{}},
    handler.EnqueueRequestsFromMapFunc(r.MapThemeToWebsites),
    builder.WithPredicates(predicate.GenerationChangedPredicate{}),
  ).
  Build(reconciler)
```

: Setup of a sharded controller {#lst:controller-setup}

For setting up a sharded controller, the `builder` package must be used.
With this, sharded controllers are configured like normal controllers however with an additional `builder.Sharded` option.
This option is supplied to the controller's main object type (in `For`) and all additional object types that should be sharded (in `Owns` and `Watches`).
When setting the `Sharded` option, the builder performs the following tasks:

- it adds a sharder controller ([-@sec:impl-sharder-controllers]) for the corresponding `GroupVersionKind`
- it modifies the actual controller ([-@sec:impl-object-controller]) to properly handle the sharding mechanisms

The next sections explain implementation of the different components in more detail.

## Shard Lease {#sec:impl-shard-lease}

When configured for sharding, the manager keeps performing leader election ([-@sec:leader-election]) and runs the sharder components only when it has successfully acquired leadership.
In addition to that, the manager also maintains the individual shard lease ([-@sec:des-membership]).
The mechanism executes the same leader election code, however with an individual lease name.
For shard leases, the instance's hostname is used for both the lease name and holder identity.
As long as the manager is able to renew the shard lease it keeps running the sharded controllers.

When adding controllers or other `Runnables` to a manager via `manager.Add` they can signal whether they need to run under leader election or not by implementing the `LeaderElectionRunnable` interface.
For example, controllers implement this interface by default to always run with leader election.
A new interface is introduced to distinguish between usual and sharded controllers: `ShardedRunnable`.

```go
// ShardedRunnable knows if a Runnable needs to be run in the sharded mode.
type ShardedRunnable interface {
	// IsSharded returns true if the Runnable needs to be run in the sharded mode.
	IsSharded() bool
}
```

: The ShardedRunnable interface {#lst:sharded-runnable}

When creating a sharded controller using the builder, the manager recognizes the `SharedRunnable` implementation and starts it as soon as the shard lease has been acquired even if the instance is currently not the leader.
Similar to usual leader election, the manager process exits immediately when it fails to renew its shard lease.
When the manager is stopped, it engages a graceful termination procedure and releases its shard lease to signal voluntary disruption, i.e. sets `spec.holderIdentity=null`.

## Lease Controller {#sec:impl-lease-controller}

The lease controller watches the shard leases that individual instances maintain.
For a given shard lease, it first determines the instance's state and then adds the state to the lease object as the `state` label for observability purposes.
The shard states are defined by the following rules:

- `Ready`: the lease is held by the shard itself (`metadata.name` is equal to the `holderIdentity`) and has not expired (`renewTime + leaseDurationSeconds` has not passed yet)
- `Expired`: the lease is held by the shard but has expired up to `leaseDurationSeconds` ago 
- `Uncertain`: the lease is held by the shard and has expired more than `leaseDurationSeconds` ago
- `Dead`: the lease is not held by the shard anymore, either because the shard released its lease or it was acquired by the sharder (lease controller)
- `Orphaned`: the lease is in state `Dead` and has expired at least 1 minute ago

The main responsibility of the lease controller is to act on leases of unavailable shards.
Once shard leases transition to state `Uncertain`, it acquires the lease by setting `holderIdentity` to `sharder`.
For this, it uses a `leaseDuration` twice as long as the `leaseDuration` of the shard.
Acquiring the shard lease is done to ensure the API server is functioning before removing the shard from partitioning (see [-@sec:des-membership]).
Additionally, the lease controller deletes shard leases in state `Orphaned` to not pollute the system.
The shard controller reconciles leases as soon as its state changes, either because of a create/update event or because one of the relevant durations has passed.

## Sharder Controllers {#sec:impl-sharder-controllers}

For every sharded object kind, the controller builder adds a sharder controller that runs under leader election.
It is responsible for assigning the sharded objects to available shards by setting the `shard` label based on the shard state information.
For this, it starts a lightweight metadata-only watch on the respective object kind.
As soon as objects are created or need to be re-assigned the controller performs reconciliation.
Additionally, it watches leases and enqueues relevant sharded objects when a shard's availability changes.

On every reconciliation, the controller lists all shard leases from the cache.
It then constructs a hash ring including all shards that are not in state `Dead` or `Orphaned`.
As this operation is executed for every sharder reconciliation, it is saved for reuse in a dedicated cache that is shared across all sharder controller belonging to a given sharded controller.
The cached ring is recalculated when a lease is updated.
In the hash ring, 100 tokens are added per shard by default for better distribution of objects across a low number of shards (inspired by groupcache [@groupcache]).

```go
type Hash func(data []byte) uint64

type Ring struct {
	hash          Hash // defaults to 64-bit implementation of xxHash (XXH64)
	tokensPerNode int  // defaults to 100

	tokens      []uint64
	tokenToNode map[uint64]string
}

func (r *Ring) AddNodes(nodes ...string) {
	for _, node := range nodes {
		for i := 0; i < r.tokensPerNode; i++ {
			t := r.hash([]byte(fmt.Sprintf("%s-%d", node, i)))
			r.tokens = append(r.tokens, t)
			r.tokenToNode[t] = node
		}
	}

	// sort all tokens on the ring for binary searches
	sort.Slice(r.tokens, func(i, j int) bool {
		return r.tokens[i] < r.tokens[j]
	})
}
```

: Adding shards to the hash ring {#lst:ring-add}

After retrieving the hash ring, the object is mapped to a partition key.
For the main object kind of sharded controllers, the partition key follows this pattern:

`<kind>.<group>/<namespace>/<name>/<uid>`

For any owned objects of the main object kind, the partition key of the owner is calculated using the object's owner references.
The calculated partition key is then used to determine the desired shard for the object by hashing the key onto the hash ring.

```go
func (r *Ring) Hash(key string) string {
	// Hash key and walk the ring until we find the next virtual node
	h := r.hash([]byte(key))

	// binary search
	i := sort.Search(len(r.tokens), func(i int) bool {
		return r.tokens[i] >= h
	})

	// walked the whole ring
	if i == len(r.tokens) {
		i = 0
	}

	return r.tokenToNode[r.tokens[i]]
}
```

: Consistent hashing of object keys {#lst:ring-hash}

If the object is not assigned yet, the sharder controller simply patches the object's `shard` label to the desired shard.
However, if the object is already assigned to a different shard, the sharder controller first adds the `drain` label to object in order to wait for acknowledgment by the current shard (see [-@sec:des-concurrency]).
This operation is only performed for the main object kind of the sharded controller, as it does not perform mutating actions on owned objects as long as it isn't responsible for the owning object.
Hence, concurrency is already prevented by the drain operation of the main object and doesn't need to be handled separately for owned objects.

## Object Controller {#sec:impl-object-controller}

The actual sharded controller is modified by the builder to handle the sharding mechanisms.
First, the controller implements the `ShardedRunnable` interface so that all instances run the controller instead of only the leader.
Also, the builder constructs a cache that automatically delegates all read operations to either the sharded (filtered) cache or unfiltered cache according to whether they are configured to be sharded or not.
This cache is injected into the object controller instead of the unfiltered cache.
With this, the sharded controller automatically uses the filtered cache as desired while it is still able to read other non-sharded objects.

Furthermore, the builder makes sure that the controller respects the shard assignments and acknowledges drain operations.
This is done by wrapping the actual reconciler with another generic reconciler.
On each reconciliation, it checks if the object is still assigned to the respective shard by reading the `shard` label.
If the object is not assigned to the shard anymore, it is discarded.
Before delegating reconciliation requests to the actual reconciler, it also checks the `drain` label.
In case the `drain` label is present, the controller removes both the `shard` and `drain` label from the object and stops reconciling it.
Lastly, the controller's predicates are adjusted to immediately react to events in which the object has the `drain` label.
This effectively allows setting up a sharded controller without changes to the controller's code.

```go
func (r *Reconciler) Reconcile(ctx context.Context, request reconcile.Request) (reconcile.Result, error) {
  // read object from cache...
  labels := obj.GetLabels()
  if shard, ok := labels[sharding.ShardLabel]; !ok || shard != r.ShardID {
    // forget object
    return reconcile.Result{}, nil
  }

  if _, drain := labels[sharding.DrainLabel]; drain {
    // acknowledge drain operation
    patch := client.MergeFromWithOptions(obj.DeepCopyObject().(client.Object), client.MergeFromWithOptimisticLock{})
    delete(labels, sharding.ShardLabel)
    delete(labels, sharding.DrainLabel)
    
    if err := r.client.Patch(ctx, obj, patch); err != nil {
      return reconcile.Result{}, fmt.Errorf("error draining object: %w", err)
    }

    // forget object
    return reconcile.Result{}, nil
  }

  // we are responsible, reconcile object
  return r.Do.Reconcile(ctx, request)
}
```

: Wrapping reconciler for sharded controllers (simplified) {#lst:wrapping-reconciler}
