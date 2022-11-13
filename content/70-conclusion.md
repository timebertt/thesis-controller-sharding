# Conclusion and Future Work

Conclusion:

- summary
  - requirement analysis
  - design
  - implementation
  - evaluation
- first step towards horizontally scalable controllers
- proposed design allows to scale controllers horizontally
- removes current scalability limitation
- evaluation shows sharding works
  - well-distributed amongst instances
  - sharder has high overhead, similar scalability limitations (vertically) as singleton
- equally sized controller replicas
  - easier to right-size / scale vertically than singleton HA setup

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
