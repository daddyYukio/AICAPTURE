
import subprocess
import json

# ========================================
# aicap関連関数
# ========================================

def get_frame() -> bytes:
    """
    カメラフレーム画像をJPEGで取得します
    (aicap get_frameコマンド実行)

    Returns:
        bytes : カメラフレーム画像(JPEG)
    """

    try:
        #
        # aicap get_frameコマンド
        # 引数なしの場合は、標準出力にJPEG画像データが返却される
        result = subprocess.run(
            ["aicap", "get_frame"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.stdout
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Command failed (exit code {e.returncode}): "
            f"{e.stderr.decode(errors='ignore')}"
        ) from e
    

def push(timestamp: int, image: bytes, result: dict):
    """
    Push通知を行います
    (aicap pushコマンド実行)

    Args:
        timestamp (int) : 時間(Unixtime)
        image (bytes)   : 画像
        result (dict)   : 結果情報

    Returns:
        なし
    """
    #
    # aicap pushコマンド
    # -i を　"-"　で指定すると、標準入力(stdin)から画像データを受け取る
    cmd = [
        "aicap", "push",
        "-t", str(timestamp),
        "-i", "-",         # -i - で stdin から画像を受け取る
        "-J", json.dumps(result)
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            input=image, # 画像バイナリを stdin に渡す
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Command failed (exit code {e.returncode}): "
            f"{e.stderr.decode(errors='ignore')}"
        ) from e

