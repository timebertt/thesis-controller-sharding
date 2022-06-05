#!/usr/bin/env bash

docker-compose up -d

$(dirname "$0")/make.sh install-python-requirements

>&2 cat <<EOF
Containerized setup is running now. Use
  ./hack/make.sh to execute make inside the container
  ./hack/shell.sh to get a shell into the container
  ./hack/down.sh to shutdown the container
EOF
