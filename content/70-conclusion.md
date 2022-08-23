# Conclusion and Future Work

## Conclusion

## Future Work

- number of virtual nodes per instance specified by label on lease
- challenge: labels must not be mutated by user
  - can be prevented via validating webhook
- challenge: multiple controllers in same instance might work on the same object kind, share the same cache by default
  - idea: multiple caches with different selectors?
- challenge: relation between objects of same kind
  - example: scheduler: pod anti affinity
