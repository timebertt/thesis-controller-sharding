# Evaluation {#sec:evaluation}

This chapter describes how the implementation (chapter [-@sec:implementation]) is used for evaluation of the proposed design (chapter [-@sec:design]).
First, the deployment environment is presented.
Next, the monitoring setup is introduced which is used to observe the webhosting operator and to take measurements.
After that, the conducted experiment is described in detail.
Last, results from conducting the experiment are presented and discussed.

## Deployment {#sec:deployment}

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

![Webhosting dashboard](../assets/dashboard-webhosting.png){#fig:dashboard-webhosting}

In addition to the components included in kube-prometheus, the webhosting exporter[^webhosting-exporter] is deployed which exposes metrics about the state of websites.
It is implemented using the kube-state-metrics library and complements the metrics offered by kube-state-metrics by adding similar metrics about the webhosting operator's API objects.
For example, one metric indicates the websites' phase, another one states which shard websites are assigned to.
Additionally, the webhosting exporter is used to collect metrics about the state of the operator's shards, which is determined from the individual shard leases.

![Sharding dashboard](../assets/dashboard-sharding.png){#fig:dashboard-sharding}

Finally, Prometheus is configured to collect metrics from the webhosting operator as well.
It exposes metrics from the controller-runtime library about controllers, workqueues, and the Kubernetes client ([@fig:dashboard-controller-runtime]).
For example, these metrics offer information on the rate and duration of reconciliations, and for how long objects are queued before being reconciled.
Additionally, metrics are added about the sharder controllers' actions, i.e. assignment and drain operations.

![Controller-runtime dashboard](../assets/dashboard-controller-runtime.png){#fig:dashboard-controller-runtime}

For general evaluation of the implementation, a sample generator[^sample-generator] is implemented to create a configurable amount of random website objects in different namespaces.
[@Fig:dashboard-webhosting] shows the overview dashboard over webhosting API objects and their state based on metrics exposed by webhosting exporter and kube-state-metrics.
It demonstrates, that all websites are successfully reconciled by the sharded operator and reach the `Ready` phase.
The sharding overview in [@fig:dashboard-sharding] indicates that all 3 shards are healthy and properly maintain their shard lease.
It also shows that responsibility for website objects is well-distributed across all 3 shards, with each shard being assinged roughly a third of all objects.

Finally, the measure[^measure] tool is implemented for retrieving the relevant measurements from the Prometheus metrics store via the HTTP API.
It fetches time series over a given time range and stores the result matrices in CSV-formatted files for further analysis and visualization.
[@Lst:measure-queries] shows the query configuration that is used to determine the operator's resource usage in the following experiment.

```yaml
queries:
- name: cpu
  query: sum(rate(container_cpu_usage_seconds_total{namespace="webhosting-system", container="manager"}[2m])) by (pod)
- name: memory
  query: sum(container_memory_rss{namespace="webhosting-system", container="manager"}) by (pod)
- name: network_receive
  query: sum(irate(container_network_receive_bytes_total{namespace="webhosting-system", pod=~"webhosting-operator-.+"}[2m])) by (pod)
- name: network_transmit
  query: sum(irate(container_network_transmit_bytes_total{namespace="webhosting-system", pod=~"webhosting-operator-.+"}[2m])) by (pod)
```

: Queries configuration for experiments {#lst:measure-queries}

[^kube-prometheus]: [https://github.com/prometheus-operator/kube-prometheus](https://github.com/prometheus-operator/kube-prometheus)
[^kube-state-metrics]: [https://github.com/kubernetes/kube-state-metrics](https://github.com/kubernetes/kube-state-metrics)
[^webhosting-exporter]: [webhosting exporter source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/master/webhosting-operator/cmd/webhosting-exporter)
[^sample-generator]: [sample generator source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/master/webhosting-operator/cmd/sample-generator)
[^measure]: [measure source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/master/webhosting-operator/cmd/measure)

## Experiment

Using the described deployment and monitoring setup, an experiment is conducted to evaluate the sharding implementation in the webhosting operator.
The experiment's aim is to determine whether the relevant resources from [@tbl:scaling-resources] are well-distributed across the individual instances.
In other words, the experiment verifies that the system's capacity and throughput are increased with the resources used by the additional instances.
It assesses how well the sharded operator scales horizontally.

For this purpose, the experiment tool[^experiment] is implemented to conduct load tests for the webhosting operator.
The tool generates load by constantly creating objects and triggering reconciliations over a certain timespan.
It thereby increases the capacity and throughput of the system to measure the resulting resource usage.
As described in [@sec:deployment], the webhosting operator is deployed on nodes isolated from all other workload.
This ensures that the operator is able to consume as many resources as it needs to handle the actual capacity and throughput of the system.
By this, the experiment allows to draw conclusions about how much resources are needed to handle a certain capacity and throughput and how both increase with the amount of resources added to the system.

For now, only one experiment scenario is implemented, which is called `base`[^base-scenario].
In this scenario, the tool generates 50 random `Theme` objects and 20 random project namespaces.
Over the course of 10 minutes it then generates random `Website` objects in different project namespaces using different `Themes`.
To make the load tests more realistic, `Websites` are also randomly deleted, though with a lower rate than creation.
During the load test, the tool generates 14 random `Websites` per second and deletes 1 object per second, hence there are about 7800 `Websites` after 10 minutes.
To simulate frequent changes to `Website` objects by users, the tool triggers individual reconciliations of each object once per minute but 100 reconciliations per second at maximum.
Additionally, the tool also simulates occasional changes to `Theme` objects by service administrators.
For this, it picks one random `Theme` per minute and mutates its specification.
As described in [@sec:webhosting-operator], this update triggers reconciliations for all `Website` objects referencing the `Theme`.
After 10 minutes, the tool generates a total of about 103 reconciliations per second on average with bursts of roughly 256 reconciliations per second.
This load is sustained for 5 more minutes before all objects generated by the experiment are cleaned up.
[@Fig:base-websites] shows how the amount of websites is increased over the experiment's timespan and how they are distributed across the operator's shards.

![Load generated by base scenario](../results/base-websites.pdf){#fig:base-websites}


- define measurements
  - measure: CPU, memory, network bandwidth
  - memory: RSS instead of WSS (we are not interested in when the kernel reclaims memory)
  - on controller side only, server side future work
  - network metrics include metrics scraping; can be neglected
- compare resource usage of singleton setup with sharded setup
  - explain deployment modes for sharded and singleton
  - note: in reality, singleton setup might have multiple replicas for HA
- (additional scenarios): rolling update, scale-out/in
- how to prove incremental scale-out (req. \ref{req:scale-out}) is fulfilled?

[^experiment]: [experiment source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/master/webhosting-operator/cmd/experiment)
[^base-scenario]: [base scenario source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/master/webhosting-operator/pkg/experiment/scenario/base)

<!--### Base Scenario-->

![CPU usage by pod](../results/base-cpu.pdf)

![Memory usage by pod](../results/base-memory.pdf)

![Network bandwidth by pod](../results/base-network.pdf)

## Discussion

\todo[inline]{Make this top level chapter?}
