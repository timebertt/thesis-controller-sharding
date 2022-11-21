# Towards Horizontally Scalable Kubernetes Controllers

[![Build Status](https://github.com/timebertt/thesis-controller-sharding/actions/workflows/build.yaml/badge.svg)](https://github.com/timebertt/thesis-controller-sharding/actions/workflows/build.yaml)

Get the current PDF by clicking the badge above️, navigating to the latest build and downloading the `paper` artifact.

## About

This is a study thesis (study project / half-time thesis) part of my master's studies in Computer Science at the [DHBW Center for Advanced Studies](https://www.cas.dhbw.de/) (CAS).

You can find the implementation that was done as part of this thesis in the repository [kubernetes-controller-sharding](https://github.com/timebertt/kubernetes-controller-sharding).

## Abstract

Controllers play an essential role in every Kubernetes cluster by realizing the desired state specified declaratively in API objects – a process referred to as reconciliation.
To prevent uncoordinated and conflicting actions of concurrent reconciliations, controllers use a leader election mechanism to determine a single active controller instance.
Because of this, reconciliations cannot be distributed among multiple controller instances which effectively limits the system's capacity and throughput by the available machine sizes and network bandwidth of the underlying infrastructure.
I.e., leader election prevents Kubernetes controllers from being horizontally scalable.

This thesis presents the first steps towards horizontally scalable Kubernetes controllers by introducing a design for distributing the reconciliation of API objects across multiple controller instances, i.e., sharding for Kubernetes controllers.
It shows that proven sharding mechanisms used in distributed databases can be applied to the problem space of Kubernetes controllers as well to overcome the mentioned scalability limitation.
The proposed design includes lease-based membership and failure detection as well as consistent hashing for partitioning.
Kubernetes API machinery primitives – namely, labels and label selectors – facilitate coordination between controller instances and prevent concurrent reconciliations of individual objects by multiple instances.

For demonstration and evaluation, the sharding design is implemented based on the controller-runtime library and used in an example operator.
Systematic load test experiments show that the sharding implementation achieves a good distribution of object responsibility and resource usage across individual shard instances.
However, the experiment results also point out that one of the controller instances always has a high resource footprint in comparison to the other shards which limits the scalability of the system.
Nevertheless, future work can perform optimizations of the presented design to overcome the discovered flaw.

The presented design and implementation allow scaling Kubernetes controllers horizontally providing potential for a wide range of applications in the Kubernetes ecosystem.
