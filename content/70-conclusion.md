# Conclusion and Future Work

This thesis performed the first steps toward horizontally scalable Kubernetes controllers.
As part of the motivation ([chapter @sec:motivation]), it was shown that the current leader election mechanisms effectively prevent scaling Kubernetes controllers horizontally.
Because of this, Kubernetes controllers can only be scaled vertically which restricts their scalability to the available machine sizes and network bandwidth of the underlying infrastructure.
After laying out the relevant background of Kubernetes controllers for this thesis, important proven sharding mechanisms of distributed databases were summarized ([chapter @sec:background]).
This served as a basis for analyzing what is required for removing the current scalability limitations of Kubernetes controllers and scaling them horizontally ([chapter @sec:requirement-analysis]).
Based on this analysis, a design was presented that applies well-known sharding mechanisms from the field of distributed databases to the specific problem of sharding in Kubernetes controllers.
The proposed design gives an architectural overview and then describes the details of how the listed requirements can be fulfilled ([chapter @sec:design]).
The second half of the thesis described how the proposed design is implemented and evaluated.
For this, the webhosting operator was implemented as an example operator for demonstrating the sharding mechanisms in practice.
The operator was implemented using the controller-runtime library, which was enhanced to generically realize the presented sharding design ([chapter @sec:implementation]).
In the last chapter, the implementation was used as a basis for evaluation in an experiment.
After describing the deployment and monitoring setup in detail, a load test experiment was conducted to measure how well the sharded operator scales horizontally ([chapter @sec:evaluation]).

To summarize, this thesis showed that well-known sharding mechanisms from the field of distributed databases can be applied well to Kubernetes controllers.
The resulting design allows for overcoming the current scalability limitation of controllers and scaling them horizontally.
The conducted evaluation shows that the presented sharding implementation works well and realizes a good distribution of responsibility for objects among multiple controller instances.
Furthermore, the resource requirements of the singleton controller are distributed across multiple shards.
However, the sharder instance still has a high resource usage and thus faces similar scalability limitations in the vertical direction as the singleton controller setup ([@sec:results]).
Nevertheless, the measurements lead to the conclusion that this limitation can be removed by deploying the sharder components separately from the shard components ([@sec:discussion]).

Apart from this improvement, this thesis lays the ground for future work in several areas: further optimizations, solving different challenges, evaluation of more aspects, and advanced applications.
First, it should be investigated how the use of webhooks for sharded API objects could improve the design and reduce the resource requirements of the sharder components.
E.g., a mutating webhook could be used to assign API objects to shards during admission instead of in a dedicated controller.
Furthermore, the proposed design faces the challenge that the `shard` and `drain` labels on API objects should not be mutated by humans.
If operators grant end users access to the Kubernetes API, validating webhooks could be leveraged to deny user requests that mutate or remove sharding-related labels.
Another challenge is, that a single component might run multiple controllers that act on the same object kind but can't share the same sharded cache.
In this case, it needs to be investigated how this challenge could be solved by introducing dedicated caches with different selectors.
Additionally, some controllers evaluate relationships between objects of the same kind.
E.g., the Kubernetes scheduler considers scheduling constraints in form of inter-pod anti-affinities that allow the spreading of related pods across different failure domains.
Future work could investigate whether sharding mechanisms can be applied to such use cases as well.

Furthermore, it should be evaluated what impact the presented sharding mechanisms have on the resource requirements and scalability of Kubernetes control plane components, i.e. the Kubernetes API server and etcd ([@tbl:scaling-resources-server]).
Also, this thesis only evaluated the resource requirements of a static set of sharded controller instances.
Future work could conduct experiments that additionally perform rolling updates of the operator `Deployment` or scale-out/in the operator.
The impact of reassignment operations during such changes to the instance set needs to be investigated and possibly further optimizations of the design need to be implemented.

Last, future work could evaluate advanced applications of the presented sharding mechanisms.
E.g., the sharding design could be implemented in Kubernetes core components like the controller manager.
The Kubernetes core controllers are not based on the controller-runtime library [@k8s], hence they can't reuse the implementation done for this thesis.
Nevertheless, the proposed design could still be applied to these controllers as well.
Another idea for future work is to investigate how sharded controllers could be scaled up or down automatically based on utilization.
E.g., a `HorizontalPodAutoscaler` [@k8sdocs] could be introduced which adds more controller instances when the average queue wait duration exceeds a certain target or removes instances when most of the controller workers are inactive.
Furthermore, another advanced application of the presented sharding mechanisms is to make the number of virtual nodes per controller instance configurable and thereby control the expected distribution of objects.
This could be used to implement canary rollout approaches for controllers [@schermann2018; @adams2015practice].
I.e., when a new controller version is rolled out, only a small subset of objects is assigned to the new version.
The object distribution could then be gradually shifted towards the new version to increase the operator's confidence in the new version.

To conclude, this thesis laid the ground and performed the first steps toward horizontally scalable Kubernetes controllers.
It shows that this can be achieved by applying proven sharding mechanisms used in distributed databases to Kubernetes controllers.
Performing sharding for Kubernetes controllers comes with a certain overhead, as any other sharding mechanism does as well.
Hence, it is not relevant for small controllers or clusters.
However, it proves to be interesting for scaling controllers and clusters further that are already heavily loaded and running into scalability limitations.
The presented design and implementation are not ready for production deployments yet, but important next steps have been listed that can be performed to make Kubernetes controller sharding production-ready.
