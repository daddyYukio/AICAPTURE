#!/bin/sh

set -e

# extmopdディレクトリに移動
EXTMOD_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$EXTMOD_DIR"

docker compose up -d

