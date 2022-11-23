# Evaluation {#sec:evaluation}

This chapter describes how the presented implementation ([chapter @sec:implementation]) is used for the evaluation of the proposed design ([chapter @sec:design]).
First, the deployment environment is described.
Next, the monitoring setup is introduced which is used to observe the webhosting operator and to take measurements.
After that, the conducted experiment is described in detail.
Last, the experiment's results are presented and discussed.

## Deployment {#sec:deployment}

For evaluation of the proposed design, the webhosting operator implementation is deployed to a Kubernetes cluster along with other tools for monitoring and experimentation.
The Kubernetes cluster[^shoot] is managed by Gardener[^gardener] and runs on Google Cloud Platform (region `europe-west1`).
The cluster runs Kubernetes version `1.24`.

For isolation purposes and accurate measurements during load tests, the following worker pools are used to run the different components:

| worker pool | instance type | components                          | count |
|-------------|---------------|-------------------------------------|-------|
| system      | n1-standard-8 | cluster system, monitoring, ingress | 1     |
| operator    | n1-standard-4 | webhosting operator                 | 1     |
| websites    | n1-standard-8 | website deployments                 | 10    |

: Worker pools of the evaluation cluster {#tbl:worker-pools}

Both the `operator` and `websites` worker pools are configured with taints [@k8sdocs] to repel all workload pods by default.
With this, all pods are scheduled to the system worker pool if not configured otherwise.
Kyverno policies [@kyvernodocs] are used to add tolerations and scheduling constraints to all webhosting operator and website pods so that they are scheduled to the respective dedicated worker pools.
To reduce the resource requirements of load tests, the websites worker pool is configured to run up to 800 pods per node.
Additional policies are used to replace the `nginx` image in website pods with the `pause` image during load tests.
With this, websites are not functional but have a low memory footprint without affecting the experiment's measurements.

[^shoot]: [Cluster specification](https://github.com/timebertt/kubernetes-controller-sharding/blob/v1.0/webhosting-operator/shoot.yaml)
[^gardener]: [https://github.com/gardener/gardener](https://github.com/gardener/gardener)

## Monitoring

For observing and measuring the implementation, a monitoring setup is deployed in the Kubernetes cluster in addition to the webhosting operator itself.
The monitoring setup serves two purposes: for general evaluation that the sharded controllers are working as desired and for providing accurate measurements of the operator's resource usage.

The deployed monitoring setup is based on kube-prometheus[^kube-prometheus], which is a collection of monitoring tools and configurations for Kubernetes clusters.
Most importantly, it includes a Prometheus [@promdocs] instance which collects metrics for containers running on the cluster and metrics about the state of Kubernetes API objects.
Container metrics are scraped from the kubelet's cadvisor endpoint [@k8sdocs], kube-state-metrics[^kube-state-metrics] is used as an exporter for metrics about API objects.
Furthermore, the setup includes a Grafana [@grafanadocs] instance, which visualizes the metrics collected by prometheus in different dashboards.

![Webhosting dashboard](../assets/dashboard-webhosting.png){#fig:dashboard-webhosting}

In addition to the components included in kube-prometheus, the webhosting exporter[^webhosting-exporter] is deployed which exposes metrics about the state of websites.
It is implemented using the kube-state-metrics library and complements the metrics offered by kube-state-metrics by adding similar metrics about the webhosting operator's API objects.
For example, one metric indicates the websites' phase, and another one states which shard websites are assigned to.
Additionally, the webhosting exporter is used to collect metrics about the state of the operator's shards, which is determined from the individual shard leases.

![Sharding dashboard](../assets/dashboard-sharding.png){#fig:dashboard-sharding}

Finally, Prometheus is configured to collect metrics from the webhosting operator as well.
It exposes metrics from the controller-runtime library about controllers, work queues, and the Kubernetes client ([@fig:dashboard-controller-runtime]).
For example, these metrics offer information on the rate and duration of reconciliations, and for how long objects are queued before being reconciled.
Additionally, metrics are added about the sharder controllers' actions, i.e. assignment and drain operations.

![Controller-runtime dashboard](../assets/dashboard-controller-runtime.png){#fig:dashboard-controller-runtime}

For general evaluation of the implementation, a sample generator[^samples-generator] is implemented to create a configurable number of random website objects in different namespaces.
[@Fig:dashboard-webhosting] shows the overview dashboard over webhosting API objects and their state based on metrics exposed by webhosting exporter and kube-state-metrics.
It demonstrates, that all websites are successfully reconciled by the sharded operator and reach the `Ready` phase as expected.
The sharding overview in [@fig:dashboard-sharding] indicates that all 3 shards are healthy and properly maintain their shard lease.
It also shows that responsibility for website objects is well-distributed across all 3 shards, with each shard being assigned roughly a third of all objects.

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

Finally, the measure[^measure] tool is implemented for retrieving the relevant measurements from the Prometheus metrics store via the HTTP API [@promdocs].
It fetches time series over a given time range and stores the result matrices in CSV-formatted files for further analysis and visualization.
[@Lst:measure-queries] shows the query configuration that is used to determine the operator's resource usage in the following experiment.

[^kube-prometheus]: [https://github.com/prometheus-operator/kube-prometheus](https://github.com/prometheus-operator/kube-prometheus)
[^kube-state-metrics]: [https://github.com/kubernetes/kube-state-metrics](https://github.com/kubernetes/kube-state-metrics)
[^webhosting-exporter]: [webhosting exporter source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/v1.0/webhosting-operator/cmd/webhosting-exporter)
[^samples-generator]: [samples generator source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/v1.0/webhosting-operator/cmd/samples-generator)
[^measure]: [measure source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/v1.0/webhosting-operator/cmd/measure)

## Experiment

Using the described deployment and monitoring setup, an experiment is conducted to evaluate the sharding implementation in the webhosting operator.
The experiment aims to determine whether the relevant resources from [@tbl:scaling-resources] are well-distributed across the individual instances.
In other words, the experiment verifies if the system's capacity and throughput are increased with the resources used by the additional instances.
It assesses how well the sharded operator scales horizontally.

For this purpose, the experiment tool[^experiment] is implemented to conduct load tests for the webhosting operator.
The tool generates load by constantly creating objects and triggering reconciliations over a certain time span.
It thereby increases the capacity and throughput of the system to measure the resulting resource usage.
As described in [@sec:deployment], the webhosting operator is deployed on nodes isolated from all other workloads.
This ensures that the operator is able to consume as many resources as it needs to handle the actual capacity and throughput of the system.
By this, the experiment allows concluding how much resources are needed to handle a certain capacity and throughput, and how both increase with the number of resources added to the system.

For now, only one experiment scenario is implemented, which is called `base`[^base-scenario].
In this scenario, the tool generates 50 random `Theme` objects and 20 random project namespaces.
Over 10 minutes it then generates random `Website` objects in different project namespaces using different `Themes`.
To make the load tests more realistic, `Websites` are also randomly deleted, though at a lower rate than creation.
During the load test, the tool generates 14 random `Websites` per second and deletes 1 object per second, hence there are about 7800 `Websites` after 10 minutes.
To simulate frequent changes to `Website` objects by users, the tool triggers individual reconciliations of each object once per minute but 100 reconciliations per second at maximum.
Additionally, the tool also simulates occasional changes to `Theme` objects by service administrators.
For this, it picks one random `Theme` per minute and mutates its specification.
As described in [@sec:webhosting-operator], this update triggers reconciliations for all `Website` objects referencing the `Theme`.
After 10 minutes, the tool generates about 103 reconciliations per second on average with bursts of roughly 256 reconciliations per second.
This load is sustained for 5 more minutes before all objects generated by the experiment are cleaned up.
[@Fig:base-websites] shows how the amount of websites is increased over the experiment's timespan and how they are distributed across the operator's shards.

[^experiment]: [experiment source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/v1.0/webhosting-operator/cmd/experiment)
[^base-scenario]: [base scenario source code](https://github.com/timebertt/kubernetes-controller-sharding/tree/v1.0/webhosting-operator/pkg/experiment/scenario/base)

![Load generated by base scenario](../results/base-websites.pdf){#fig:base-websites}

[@Tbl:metrics] shows which metrics are used for measurements of the operator's resource usage during the experiment.
All the metrics originate from kubelet's cadvisor endpoint.
For memory measurements, the resident set size (RSS) metric is used instead of the working set size (WSS) [@kerneldocs].
This is because the WSS includes pages that are already freed by the process but not reclaimed by the kernel yet.
The RSS on the other hand does not include such pages and hence provides a more precise measurement of how much memory the operator process actually requires.

| resource                      | metric                                 |
|-------------------------------|----------------------------------------|
| CPU                           | container_cpu_usage_seconds_total      |
| memory                        | container_memory_rss                   |
| network bandwidth received    | container_network_receive_bytes_total  |
| network bandwidth transmitted | container_network_transmit_bytes_total |

: Experiment resource usage measurements {#tbl:metrics}

Network bandwidth measurements are split by direction: one measurement for received bytes and one for transmitted bytes.
These metrics include network transfer related to Prometheus scraping the pods' metrics endpoints.
However, this can be neglected in this experiment as the transfer only occurs every 10 seconds and includes a short plain text in comparison to the size of the transferred API objects.
Note that these resource measurements only cover the operator processes but not the Kubernetes API server.
Investigating the resource implications of sharding on the control plane components is out of the scope of this thesis.

The load test is executed twice: once for the singleton operator and once for the sharded operator.
For this, the deployment mechanism offers a switch for deploying the operator in either mode.
In the sharded mode, the operator is deployed with three instances, and in the singleton mode only with one instance.
Note that singleton operators are typically deployed with multiple instances for fast failovers (active-passive HA setup) in production environments.
As the passive instances of the operator also have a given base resource usage, the total resource usage of the system would be higher than in the conducted experiments.
After each load test, the measurements are retrieved from Prometheus via the measure tool.
Then, the measured resource usage of both tests is compared.

## Results

This section compares the resource usage by individual pods in both tests for each measured resource ([@tbl:metrics]).

![CPU usage by pod](../results/base-cpu.pdf){#fig:base-cpu}

First, [@fig:base-cpu] compares the CPU usage of pods in both setups.
In the sharded setup, the pod with the highest CPU usage is the active sharder.
The comparison shows that the sharder's CPU usage is almost as high as the singleton's usage.
It only consumed 12% less CPU time than the singleton over the entire test duration.
The other two shards' total CPU time is about 48% of the singleton's usage.

![Memory usage by pod](../results/base-memory.pdf){#fig:base-memory}

The comparison of the pods' memory usage ([@fig:base-memory]) reveals that the sharder's memory usage is almost as high as the singleton's memory usage – similar to the CPU usage.
On average, the sharder's RSS is about 89% of the singleton's RSS.
The other two shards use significantly less memory: on average, roughly 40% of the singleton.

![Network bandwidth by pod](../results/base-network.pdf){#fig:base-network}

Finally, [@fig:base-network] compares the used network bandwidth of both setups by direction.
It shows that the amount of transmitted bytes is very similar in each instance of the sharded setup, while the sharder receives significantly more bytes than the other two shards.
The total bytes received by the sharder are 89% of the singleton's total, while the other two shards receive 42% as many bytes as the singleton.
The sharded operator instances transmit about 44% as many bytes as the singleton.

## Discussion

The results presented in the previous section demonstrate that the proposed design for sharding in Kubernetes controllers achieves a distribution of the required resources across controller instances.
First of all, the implemented mechanisms realize a good distribution of responsibility for API objects among the three shards.
It is shown that the individual shards of the system require roughly half as many resources in comparison to the singleton controller.
With that, the presented sharding mechanism overcomes the current scalability limitation of Kubernetes controllers and makes them horizontally scalable.
Using such an architecture allows increasing the system's capacity and throughput by adding more controller instances.

However, the results also highlight that the instance that is the active sharder consumes almost as many resources as the singleton controller.
This limits the scalability of the system again by the available machine sizes and network bandwidth similar to the singleton controller architecture.
Hence, the scalability limitations described in [@sec:limitations] are not removed entirely.
It is important to note, that in the evaluated deployment setup, the sharder runs both the sharder and shard components.
I.e., it is responsible for assigning objects to individual instances as well as running the actual object controllers just like the other instances.
This results in significantly higher resource consumption in comparison to the other instances that only run the shard components.

Nevertheless, the presented design does not prescribe that the sharder must also act as a shard at the same time.
The deployment setup could be adapted to run the shard and sharder in dedicated instance sets (i.e., `Deployments`).
Based on the presented experiment results, it is expected that this results in better distribution of resource requirements.
With that, the original scalability limitation in the vertical direction can be overcome entirely and the system's scalability can be increased even further.

The results also show that the two pods that only run the shard components have very similar resource usage.
In a typical singleton controller setup with multiple instances for active-passive HA, there is a much more heterogeneous resource usage as the passive instances consume almost no resources in comparison to the leader.
With this, the sharded setup also brings advantages for vertical scaling as equally-sized instances can be right-sized more easily to minimize wasting reserved resources.

Last, it is worth noting that the simulated load is still very low in comparison to some production deployments of controllers.
With even more and larger API objects in the system, the difference between the sharder's and singleton's resource usage might be more significant.
