# Motivation

In Kubernetes, the desired and actual state of the distributed system are stored centrally in etcd [@etcddocs] and exposed by the Kubernetes API server.
The logic for turning the desired state into the actual state of the system (reconciliation) is implemented in dedicated components called controllers.
Storing the desired and actual state is the API server's responsibility and reconciling both is the task of controllers.
Because these tasks are decoupled Kubernetes is an asynchronous and eventually consistent [@brewer2000towards; @vogels2008eventually] system. [@k8sdocs]

Kubernetes controllers as such are stateless components, they persist the state they work on in external systems – in etcd via the API server.
I.e., the system doesn't lose any important state if controllers fail or restart.
However, Kubernetes controllers typically use a leader election mechanism to determine a single active controller instance (leader).
When deploying multiple instances of the same controller, there will only be one active instance at any given time, other instances will be on standby.
This is done to prevent controllers from performing uncoordinated and conflicting actions.

If the current leader stops or loses leadership (e.g., during a rolling update or network partition) another instance takes over leadership and becomes the active instance.
Such a setup can be described as an "active-passive high-availability (HA) setup" [@ahluwalia2006high].
It minimizes controller downtime and facilitates fast failovers.
However, it cannot be considered horizontal scaling because work is not distributed across multiple instances [@bondi2000characteristics; @jogalekar2000evaluating].
Because of this, Kubernetes controllers are not horizontally scalable.

This restriction imposes scalability limitations for Kubernetes controllers.
I.e., the rate of reconciliations, amount of objects, etc. are limited by the available machine size and network bandwidth of the underlying infrastructure.
In contrast to usual stateless applications, one cannot increase the capacity and throughput of the system by adding more instances (horizontal scaling) but only by using instances with more resources (vertical scaling).

This thesis explores approaches for distributing the reconciliation of Kubernetes objects across multiple controller instances.
It attempts to lift the restriction of having only one active instance per controller.
For this, mechanisms are required for determining which instance is responsible for which object to prevent conflicting actions.
The thesis evaluates how proven mechanisms for sharding and partitioning from the field of distributed databases [@abadi2009data; @agrawal2004integrating] can be applied to this problem.
