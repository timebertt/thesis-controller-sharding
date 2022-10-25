# Evaluation {#sec:evaluation}

This chapter describes how the implementation (chapter [-@sec:implementation]) is used for evaluation of the proposed design (chapter [-@sec:design]).
First, the deployment environment is presented.
Next, the monitoring setup is introduced which is used to observe the webhosting operator and to take measurements.
After that, the conducted experiment is described in detail.
Last, results from conducting the experiment are presented and discussed.

## Deployment

For evaluation of the proposed design, the webhosting operator implementation is deployed to a Kubernetes cluster along with other tooling for monitoring and experimentation.
The Kubernetes cluster[^shoot] is managed by Gardener[^gardener] and runs on Google Cloud Platform (region `europe-west1`).
The cluster runs Kubernetes version `1.24`.

For isolation purposes and accurate measurements during load tests, the following worker pools are used to run the different components:

| worker pool | instance type | components                                     | count |
|-------------|---------------|------------------------------------------------|-------|
| system      | n1-standard-8 | cluster system, monitoring, ingress controller | 1     |
| operator    | n1-standard-4 | webhosting operator                            | 1     |
| websites    | n1-standard-8 | website deployments                            | 10    |

: Worker pools of the evaluation cluster {#tbl:worker-pools}

Both the `operator` and `websites` worker pools are configured with taints [@k8sdocs] to repel all workload pods by default.
With this, all pods are scheduled to the system worker pool if not configured otherwise.
Kyverno[^kyverno] policies are used to add tolerations and scheduling constraints to all webhosting operator and website pods so that they are scheduled to the respective dedicated worker pools.
To reduce the resource requirements of load tests, the websites worker pool is configured run up to 800 pods per node.
Additional policies are used to replace the `nginx` image in website pods with the `pause` image during load tests.
With this, websites are not functional but have a low memory footprint without affecting the experiment's measurements.

[^shoot]: [Cluster specification](https://github.com/timebertt/kubernetes-controller-sharding/blob/master/webhosting-operator/shoot.yaml)
[^gardener]: [https://github.com/gardener/gardener](https://github.com/gardener/gardener)
[^kyverno]: [https://github.com/kyverno/kyverno](https://github.com/kyverno/kyverno)

## Monitoring

For observing and measuring the implementation, a monitoring setup is deployed in the Kubernetes cluster in addition to the webhosting operator itself.
The monitoring setup serves two purposes: for general evaluation that the sharded controllers are working as desired and for providing accurate measurements of operator's resource usage.

The deployed monitoring setup is based on kube-prometheus[^kube-prometheus], which is a collection of monitoring tools and configuration for Kubernetes clusters.
Most importantly, it includes a Prometheus [@promdocs] instance which collects metrics for containers running on the cluster and metrics about the state of Kubernetes API objects.
Container metrics are scraped from the kubelet's cadvisor endpoint [@k8sdocs], kube-state-metrics[^kube-state-metrics] is used as an exporter for metrics about API objects.
Furthermore, the setup includes a Grafana [@grafanadocs] instance, which visualizes the metrics collected by prometheus in different dashboards.

![Webhosting dashboard](../assets/dashboard-webhosting.png)

In addition to the components included in kube-prometheus, the webhosting exporter[^webhosting-exporter] is deployed which exposes metrics about the state of websites.
It is implemented using the kube-state-metrics library and complements the metrics offered by kube-state-metrics by adding similar metrics about the webhosting operator's API objects.
For example, one metric indicates the websites' phase, another one states which shard websites are assigned to.
Additionally, the webhosting exporter is used to collect metrics about the state of the operator's shards, which is determined from the individual shard leases.

![Sharding dashboard](../assets/dashboard-sharding.png)

Finally, Prometheus is configured to collect metrics from the webhosting operator as well.
It exposes metrics from the controller-runtime library about controllers, workqueues, and the Kubernetes client.
E.g., these metrics offer information on the rate and duration of reconciliations, and how long objects are queued before being reconciled.
Additionally, metrics have been added about the sharder controllers' actions, i.e. assignment and drain operations.

![Controller-runtime dashboard](../assets/dashboard-controller-runtime.png)


- webhosting-exporter
  - metrics for sharding: shard sizes
- webhosting-operator
  - controller metrics: queue length, reconciliation time
- visualization in dashboards -> general evaluation
- explain measure tool -> experiments

[^kube-prometheus]: [https://github.com/prometheus-operator/kube-prometheus](https://github.com/prometheus-operator/kube-prometheus)
[^kube-state-metrics]: [https://github.com/kubernetes/kube-state-metrics](https://github.com/kubernetes/kube-state-metrics)
[^webhosting-exporter]: [Webhosting exporter source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/master/webhosting-operator/cmd/webhosting-exporter)

## Experiment

general evaluation/testing?

- object distribution
- testing rolling updates
- testing scale-out/in

experiment

- using the monitoring setup, experiment is conducted
- evaluate, whether relevant resources from [@tbl:scaling-resources] are actually well-distributed across instances
  - increase capacity (number of objects, size is fixed)
  - increase throughput (rate of relevant events)
- compare resource usage of singleton setup with sharded setup
  - deployment modes for sharded and singleton
- note: singleton setup might have multiple replicas for HA
- define measurements
  - measure: compute, memory, network transfer
  - on controller side only, server side future work
- how to prove incremental scale-out (req. \ref{req:scale-out}) is fulfilled
- explain experiment tool
- scenarios
  - base scenario

![Load generated by experiment](../results/base-cpu.pdf)

## Results

- execute scenario against sharded and singleton controller
- compare measurements

![CPU usage by pod](../results/base-cpu.pdf)

![Memory usage by pod](../results/base-memory.pdf)

![Network bandwidth by pod](../results/base-network.pdf)

- network metrics include metrics scraping
  - can be neglected

## Discussion

\todo[inline]{Make this top level chapter?}
