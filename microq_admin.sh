#! /usr/bin/env bash
docker run --rm -v ~/odin.cfg:/odin.cfg:ro docker2.molflow.com/devops/microq_admin "$@"
