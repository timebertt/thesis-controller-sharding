#!/usr/bin/env bash

container=$(basename $PWD)_paper_1

if ! [ "$( docker container inspect -f '{{.State.Status}}' $container 2>/dev/null)" == "running" ]; then
  >&2 echo "container $container is not running, please run \`./hack/up.sh\` and try again"
  exit 1
fi

docker exec -it $container "${@:-sh}"
