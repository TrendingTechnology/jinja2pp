#!/bin/bash

set -eu
set -o pipefail

# docker-compose up -d --build

docker tag $1 msjpq/jinja2pp:latest

docker push msjpq/jinja2pp:latest
