# Conclusion and Future Work

This thesis presented first steps towards horizontally scalable Kubernetes controllers.
As part of the motivation for this work, it was shown that the current leader election mechanisms effectively prevents from scaling Kubernetes controllers horizontally.
Because of this, Kubernetes controllers can only be scaled vertically which restricts their scalability by the available machine sizes and network bandwidth of the underlying infrastructure.
After laying out the relevant background of Kubernetes controllers for this thesis, important proven sharding mechanisms of distributed databases were summarized.
This served as a basis for analyzing what is required for removing the current scalability limitations of Kubernetes controllers and scaling them horizontally.
Based on this analysis, a design was presented that applies well-known sharding mechanisms from the field of distributed databases to the specific problem of sharding in Kubernetes controllers.
The proposed design gives an architectural overview and then describes details how the listed requirements can be fulfilled.
The second half of the thesis described how the proposed design is implemented and evaluated.
For this, the webhosting operator was implemented as an example operator for demonstrating the sharding mechanisms in practice.
The operator was implemented using the controller-runtime library, which was enhanced to realize the presented sharding design in a generic way.
In the last chapter, the implementation was used as a basis for evaluation in an experiment.
After describing the deployment and monitoring setup in detail, a load test experiment was conducted to measure how well the sharded operator scales horizontally.
\todo[inline]{add sec. references?}

To summarize, this thesis showed that well-known sharding mechanisms from the field of distributed databases can be applied well to Kubernetes controllers.
The resulting design allows to remove the current scalability limitation of controllers and scale them horizontally.
The conducted evaluation shows that the presented sharding implementation works realizes a good distribution of responsibility for objects amongst multiple controller instances.
Furthermore, the resource requirements of the singleton controller is distributed across multiple shards.
However, the sharder instance still has a high resource usage and thus faces similar scalability limitations in the vertical direction as the singleton controller setup.
Nevertheless, the measurements lead to the conclusion that this limitation can be removed by deploying the sharder components separately from the shard components.


future work:

- sharding of owned objects is only eventually consistent
  - not relevant: Kubernetes controllers need to be able to handle eventual consistency!
  - could lead to problems?
  - owned object assigned later than owner
  - owner is drained, owned object immediately reassigned
- optimizations
  - run sharder as separate deployment
  - perform initial assignments in webhook
- evaluate performance impact on API server and etcd, [@tbl:scaling-resources-server]
- this evaluation only static set of instances, measure resource usage during changes to instance set
- movement on rolling updates
  - idea: StatefulSet could be used for stable hostname to minimize movements during rolling updates
  - idea: smoothen rolling updates by specifying `minReadySeconds`
- dynamic scaling up and down
  - e.g. targeted queue wait duration, sharding size, active/idle workers
  - HPA on custom metrics
- canary rollout for controllers (separate deployment per version, number of virtual nodes)
  - number of virtual nodes per instance specified by label on lease
- challenge: labels must not be mutated by user
  - can be prevented via validating webhook
- challenge: multiple controllers in same instance might work on the same object kind, share the same cache by default
  - idea: multiple caches with different selectors?
- challenge: relationship between objects of same kind
  - example: scheduler pod anti affinity
- apply to kubernetes core components as well?
  - not implemented in controller-runtime
  - design can be implemented nevertheless

wrap-up:

- good first step towards horizontally scalable controllers
- controller sharding is worth looking into
- comes with overhead (as with any other sharding mechanism)
- probably not relevant for small controllers/cluster
- interesting for heavily loaded controllers/clusters
- not ready for production setups, but future work has been laid out and can be done to make it to production
