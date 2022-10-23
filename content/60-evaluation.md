# Evaluation {#sec:evaluation}

## Monitoring

![Test Plot](../results/base-cpu.pdf)

- monitoring needed for observing and evaluation
- introduce setup with different components
- webhosting-exporter
- kube-state-metrics, kube-prometheus, Grafana
- cadvisor, prometheus
- metrics for sharding: shard sizes, sharder actions, ring calculations
- controller metrics: queue length, reconciliation time
- visualization: dashboards

## Experiment Setup

- using the monitoring setup, experiment is conducted
- evaluate, whether relevant resources from [@tbl:scaling-resources] are actually well-distributed across instances
  - increase capacity (number of objects, size is fixed), throughput (rate of relevant events)
- -> compare resource usage of non-sharded setup with sharded setup
- define measurements
  - measure: compute, memory, network transfer
  - on controller side only, server side future work
- how to measure capacity (incremental scale-out, req. \ref{req:scale-out})?
- scenarios
- describe experiment process
  - look into kubernetes performance tests

## Results

- execute experiment with and without sharding
- compare test results

## Discussion

\todo[inline]{Make this top level chapter?}
