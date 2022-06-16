# Motivation

In Kubernetes [@k8sdocs], desired and actual state of the distributed system are stored centrally in etcd [@etcddocs] and exposed by the Kubernetes API server.
The logic for turning the desired state into the actual state of the system (reconciliation) is implemented in distributed components called controllers.
Storing desired state (API server) and making that state reality (controllers) are decoupled, which makes Kubernetes an asynchronous and eventually consistent system.

Kubernetes controllers as such are stateless components, they persist the state they work on in external systems -- in etcd via the API server.
I.e., the system doesn't lose any important state if controllers fail or restart.
However, Kubernetes controllers typically use a leader election mechanism to determine a single active controller instance (leader).
When deploying multiple instances of the same controller, there will only be one active instance at any given time, other instances will be in stand-by.
This is done to prevent controllers from performing uncoordinated and conflicting actions.

If the current leader fails and loses leadership (e.g. network failure, rolling update) another instance takes over leadership and becomes the active instance.
Such setup can be described as an "active-passive high-availability (HA) setup".
It minimizes "controller downtime" and facilitates fast fail-overs.
However, it cannot be considered as horizontal scaling because work is not distributed or replicated among multiple instances.
Leadership can be seen as state that Kubernetes controllers carry which prevents from scaling them horizontally.

This restriction imposes scalability limitations for Kubernetes controllers.
I.e., the rate of reconciliations, amount of objects, etc. is limited by the machine size that the active controller runs on and the network bandwidth it can use.
In contrast to usual stateless applications, one cannot increase the throughput of the system by adding more instances (scaling horizontally) but only by using bigger instances (scaling vertically).

This thesis explores approaches for distributing reconciliation of Kubernetes objects across multiple controller instances.
It attempts to lift the restriction of having only one active replica per controller.
For this, mechanisms are required for determining which instance is responsible for which object to prevent conflicting actions.
The thesis evaluates if and how proven sharding mechanisms from the field of distributed databases can be applied to this problem.

\todo{canary rollout?}
