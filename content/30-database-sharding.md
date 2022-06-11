# Sharding in Distributed Databases

- background on distributed databases
- look into Cassandra, MongoDB, CockroachDB, Spanner/F1, ...
- consensus vs sharding algorithms?
  - paxos, raft, ...

## Sharding Criteria

- input for sharding algorithms
- object / row ID (primary key)
- arbitrary sharding key
  - natural sharding key in product (e.g. workspace, project, etc.)

## Algorithms

- consistent hashing
