from datetime import datetime, timezone
import subprocess
import threading
import sys
import os
import time
import json
from io import BytesIO
from ultralytics import YOLO
from PIL import Image, ImageDraw
import sounddevice as sd
import soundfile as sf
import numpy as np

# プイレビュー用画像の保存パス
PREVIEW_IMAGE_PATH = os.environ["PREVIEW_IMAGE_PATH"]

# 使用するYoloモデルファイルの名前
# パス指定する場合はソースコードからの相対パスで指定
MODEL_FILE_NAME = os.environ["MODEL_FILE_NAME"]

# モデルファイルを絶対パスに変換(このソースコードの場所を起点)
MODEL_FILE_PATH = os.path.join(os.path.dirname(__file__), MODEL_FILE_NAME)

# confidence threshold
# 検出信頼度の閾値(0.0 ~ 1.0)
# これを下回る検出信頼度(confidence score)の検出は、結果に含めない1
CONF = 0.3

# Intersection over Union
# 検出BOXの重なり具合(0.0 ~ 1.0)
# YOLOは画像中で同じ物体を複数の候補BOXで検出することがあり、
# その中で、結果として残すBOXを決める閾値 = 重複検出を回避するための閾値
IOU = 0.5

#
# 検出する物体のラベルID
# 複数指定可能（配列で指定)
# Yoloで提供されているモデルを使用する場合は
# COCO(Common Objects in Context)のインデックスを指定する
# (抜粋)
# ID	クラス名
# 0	    person
# 1	    bicycle
# 2	    car
# 3	    motorcycle
# 5	    bus
# 16	dog
# 17	horse
# 18	sheep
# 19	cow
# 21    bear
# 77    teddy bear
# 例えば、車、バス、オートバイを検出するには　CLASSES = [2, 3, 4]
#
CLASSES = [21]

#
# 音声出力サウンドの名前
# 検索するので名称の一部分でOK
# USB接続なので、下記の文字列が名称に入る
OUTPUT_AUDIO_DEVICE_NAME = "USB Audio"

# 再生するWAVファイルの名前
# 配置場所はこのpythonファイルと同じ場所を想定
WAVFILE_NAME = "alert.wav"
WAVFILE_PATH = os.path.join(os.path.dirname(__file__), WAVFILE_NAME)

# 再生継続時間(秒)
WAV_PLAY_TIME_SEC = 10

# 再生時のブロックサイズ（秒)
# １回のコールバックで処理する音声データの長さ
BLOCK_DURATION_SEC = 2.0

# 再生停止時間(unixtime)の格納用変数
stop_wav_time = 0

# 再生スレッド
play_thread = None

# 再生停止イベント変数
stop_event = threading.Event()

def play_wav(wav_path : str):
    """
    WAVファイルを再生します
    再生は非同期で行われ、stop_wav()関数がコールされるか、WAV_PLAY_TIME_SEC経過するまでリピート再生します
    すでに再生中にコールされた場合は、再生停止時間が延長されます

    Args:
        wav_path (str) : 再生するWAVファイルのパス

    Returns:
        なし
    """
    global stop_wav_time, play_thread

    # 停止時間を設定
    # 再生指示があった時間＋WAV_PLAY_TIME_SECで止める
    # すでに再生中の場合は、時間が延長される
    stop_wav_time = int(datetime.now(tz=timezone.utc).timestamp()) + WAV_PLAY_TIME_SEC

    if play_thread and play_thread.is_alive():
        # 再生中なら延長のみ
        return

    # 再生開始
    stop_event.clear()
    play_thread = threading.Thread(target=_play_wav_thread, args=(wav_path,), daemon=True)
    play_thread.start()


def stop_wav():
    """
    再生中のWAVファイルを停止します
    """
    print("stop wav!")
    stop_event.set()


def _play_wav_thread(wav_path : str):
    """
    WAVファイルを再生するスレッド関数
    aplayコマンドを実行してWAVファイルの再生を開始します

    Args:
        wav_path (str) : 再生するWAVファイルのパス

    Returns:
        なし
    """
    global stop_event

    print(f"Start playing wav!: {wav_path}")

    try:

        # WAVファイル読み込み
        data, fs = sf.read(wav_path, dtype='float32')

        # モノラル対策：1次元配列を (N, 1) に変換
        if data.ndim == 1:
            data = data[:, np.newaxis]

        channels = data.shape[1] if data.ndim > 1 else 1
        length = len(data)
        
        # blocksize をサンプリングレートから計算（目的秒数分）
        blocksize = int(fs * BLOCK_DURATION_SEC)
        if blocksize < 64:
            blocksize = 64  # 最低値の保護
        print(f"sample_rate={fs}, channels={channels}, wav_length_frames={length}, blocksize={blocksize}")

        # 出力デバイスを名前で検索
        devices = sd.query_devices()
        device_index = None

        for idx, dev in enumerate(devices):
            if OUTPUT_AUDIO_DEVICE_NAME.lower() in dev['name'].lower() and dev['max_output_channels'] > 0:
                device_index = idx
                break

        if device_index is None:
            raise RuntimeError(f"Could not find the device! '{OUTPUT_AUDIO_DEVICE_NAME}'")

        print(f"Use this device: {devices[device_index]['name']}")

        # 音声データの位置
        pos = 0

        # 音声再生コールバック
        def audio_callback(outdata, frames, time_info, status):
            nonlocal pos
            if status:
                print(f"Playback warning: {status}")

            # 出力先のサイズを初期化
            outdata.fill(0.0)

            frames_written = 0
            while frames_written < frames:
                remaining_data = length - pos
                remaining_out = frames - frames_written
                chunk = min(remaining_data, remaining_out)

                # 一部だけコピー
                outdata[frames_written:frames_written+chunk] = data[pos:pos+chunk]
                pos = (pos + chunk) % length
                frames_written += chunk

        # 再生開始
        with sd.OutputStream(
            samplerate=fs,
            channels=channels,
            dtype='float32',
            device=device_index,
            blocksize=blocksize,
            callback=audio_callback
        ):
            while True:
                # 指定時間経過か、イベントがセットされるまでループ再生
                timestamp = int(datetime.now(tz=timezone.utc).timestamp())
                if timestamp >= stop_wav_time or stop_event.is_set():
                    break
                time.sleep(0.1)

    except Exception as e:
        print(f"Error during playback: {e}")

    print("Playback stopped.")



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
    

def create_result_jpeg(img : Image, result : list) -> bytes:
    """
    parse_results関数で成形された検出物体のBOXを画像に書き込みます
    
    Args:
        img (Image)   : カメラフレーム画像のPIL Image
        result (list) : parse_results関数で成形された結果リスト

    Returns:
        bytes : BOXを書き込んだJPEG画像
    """

    draw = ImageDraw.Draw(img)

    for r in result:

        cr = (255, 0, 0)

        x1 = r["box"]["x1"]
        y1 = r["box"]["y1"]
        x2 = r["box"]["x2"]
        y2 = r["box"]["y2"]

        draw.rectangle((x1, y1, x2, y2), fill=None, outline=cr, width=5)

    dst = BytesIO()
    img.save(dst, format='JPEG', quality=75)
    dst.seek(0)

    return dst.getvalue()


def parse_results(results : list) -> list:
    """
    yolo predictの結果を以下の形に成形します

    {
        "pos"  : {"x" : x, "y" : y}, <= 検出物体中心座標
        "box"  : {"x1" : x1, "y1" : y1, "x2" : x2, "y2" : y2}, <= BOX座標
        "conf" : 検出信頼度[confidence score](0.0 ~ 1.0),
        "cls"  : 検出クラス
    }
    
    Args:
        results (list) : predictの結果リスト

    Returns:
        list : 成形した結果のリスト
    """

    res = []

    for box in reversed(results[0].boxes):

        cls = box.cls.tolist()
        conf = box.conf.tolist()
        r = box.xyxy.tolist()

        x1 = int(r[0][0])
        y1 = int(r[0][1])
        x2 = int(r[0][2])
        y2 = int(r[0][3])

        pos_x = int(x1 + (x2 - x1) / 2)
        pos_y = int(y1 + (y2 - y1) / 2)

        res.append({
                "pos" : {"x" : pos_x, "y" : pos_y}, 
                "box" : {"x1" : x1, "y1" : y1, "x2" : x2, "y2" : y2}, 
                "conf" : conf[0],
                "cls" : int(cls[0])
            })

    return res    


def main():

    frame_w = 0
    frame_h = 0

    while True:

        try:
            # ビデオ映像取得
            frame = get_frame()
            timestamp = int(datetime.now(tz=timezone.utc).timestamp())

            # PLI Imageに変換
            img = Image.open(BytesIO(frame))

            # 画像サイズが変わったらモデルの最初期化を行う
            if img.width != frame_w or img.height != frame_h:
                model = YOLO(model=MODEL_FILE_PATH)
                frame_w = img.width
                frame_h = img.height

            # 物体検知実行
            results = model.predict(
                img, 
                conf=CONF, 
                iou=IOU, 
                classes=CLASSES, 
                verbose=True)

            # 結果を整形
            res = parse_results(results)

            # 物体を検知したか？
            if len(res) > 0:

                # 音を鳴らす
                play_wav(WAVFILE_PATH)

                # 検知枠を書き込んだJPEG画像の生成
                frame = create_result_jpeg(img, res)

                # PUSH通知
                # エラーはここでキャッチしてそのまま処理を流す
                try:
                    push(timestamp, frame, res)
                except Exception as e:
                    print(str(e))    
            

            # 結果確認用のプレビューイメージの保存
            with open(PREVIEW_IMAGE_PATH, 'wb') as f:
                f.write(frame)

            time.sleep(0.1)  # フレームレート制御

        except KeyboardInterrupt:
            print("Received SIGINT (Ctrl+C), exiting...")
            sys.exit(0)

        except Exception as e:
            print(str(e))    
            time.sleep(5)

if __name__ == "__main__":
    main()
