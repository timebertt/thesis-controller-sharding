# Conclusion and Future Work

## Conclusion

- sharding of owned objects is only eventually consistent
  - could lead to problems?
  - owned object assigned later than owner
  - owner is drained, owned object immediately reassigned
- equally sized controller replicas
  - easier to right-size / scale vertically than leader elected

## Future Work

- optimizations
  - run sharder as separate deployment
  - perform initial assignments in webhook
- evaluate performance impact on API server and etcd, [@tbl:scaling-resources-server]
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
- challenge: relation between objects of same kind
  - example: scheduler: pod anti affinity
