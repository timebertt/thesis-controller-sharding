# Motivation

- kubernetes [@k8sdocs] controllers are the "brains of the cluster"
- controllers as such are stateless
- only state they carry is leadership
- leader election: only active/passive HA-setups
- scalability limits: machine size, network bandwidth (-> cost implications)
- no canary rollout: no able to gradually shift leadership
