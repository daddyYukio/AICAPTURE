#!/bin/sh

# extmopdディレクトリに移動
EXTMOD_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$EXTMOD_DIR"

docker compose down

