# Study Thesis on Kubernetes Controller Sharding

[![Build Status](https://github.com/timebertt/thesis-controller-sharding/actions/workflows/build.yaml/badge.svg)](https://github.com/timebertt/thesis-controller-sharding/actions/workflows/build.yaml)

Get the current PDF by clicking the badge above️, navigating to the latest build and downloading the `paper` artifact.

You can find the implementation that was done as part of this thesis in the repository [kubernetes-controller-sharding](https://github.com/timebertt/kubernetes-controller-sharding).

## Abstract

Controllers play an essential role in every Kubernetes cluster by realizing the desired state specified declaratively in API objects – a process referred to as reconciliation.
To prevent uncoordinated and conflicting actions of concurrent reconciliations, controllers use a leader election mechanism to determine a single active controller instance.
Because of this, reconciliations cannot be distributed among multiple controller instances which effectively limits the system's capacity and throughput by the available machine sizes and network bandwidth of the underlying infrastructure.
I.e., leader election prevents Kubernetes controllers from being horizontally scalable.

This thesis presents a design that allows distributing reconciliation of Kubernetes objects across multiple controller instances.
It shows that proven sharding mechanisms used in distributed databases can be applied to Kubernetes controllers to overcome the mentioned scalability limitation.
An example implementation demonstrates the feasibility of the proposed design and experiments are conducted to prove that resource requirements are distributed across instances.
With this, first steps towards horizontally scalable Kubernetes controllers are performed.

## About

This is a study thesis (study project / half-time thesis) part of my master's studies in Computer Science at the [DHBW Center for Advanced Studies](https://www.cas.dhbw.de/) (CAS).

Copyright (c) 2022 Tim Ebert
