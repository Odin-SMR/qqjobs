#! /usr/bin/env bash
docker run --rm -v ~/odin.cfg:/odin.cfg:ro odinsmr/microq_admin "$@"
