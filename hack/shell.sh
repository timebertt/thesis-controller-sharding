#!/usr/bin/env bash

container="$(docker-compose ps --filter name=paper -q)"

if ! [ "$( docker container inspect -f '{{.State.Status}}' "$container" 2>/dev/null)" == "running" ]; then
  >&2 echo "service paper is not running, please run \`./hack/up.sh\` and try again"
  exit 1
fi

docker exec -it "$container" "${@:-sh}"
