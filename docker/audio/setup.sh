#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_DIR="$(dirname "$SCRIPT_DIR")"

CMDLINE_FILE="/boot/firmware/cmdline.txt"
TARGET_OPTION="overlayroot=tmpfs:recurse=0"

set -e

# 標準エラーに出力してexit 1で抜ける
ERROR_EXIT() {
    echo "ERROR: $1" >&2
    exit 1
}

# コマンドの実行結果を確認し、標準エラーに出力があったらERROR_EXITで抜ける
WITH_ERROR_CHECK() {
    local error_msg
    error_msg=$("$@" 2>&1) || ERROR_EXIT "$1 Failed: $error_msg"
}



# root ユーザーとして実行されているか確認
if [ "$EUID" -ne 0 ]; then
  ERROR_EXIT "[ERROR] This script must be run as root. Use sudo:"
fi

# cmdline.txt が存在するか確認
if [ ! -f "$CMDLINE_FILE" ]; then
  ERROR_EXIT "[ERROR] $CMDLINE_FILE not found!"
fi

# RAMディスク化されていたらエラー
if grep -q "$TARGET_OPTION" "$CMDLINE_FILE"; then
  ERROR_EXIT "[ERROR] Overlayroot is enabled!"
fi

# capture.serviceを停止
echo "[INFO] Stopping capture.service..."
WITH_ERROR_CHECK systemctl stop capture.service

# Docker build
echo "[INFO] Building docker image..."
WITH_ERROR_CHECK docker build . -t aicap/arm64/ultralytics:1.0.250923-audio 

# persistにコピー
echo "[INFO] Copying current docker images..."
WITH_ERROR_CHECK /usr/local/aicap/script/docker/dockersave.sh

# 終了
echo "[INFO] Finished!"


