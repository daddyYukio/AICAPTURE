from datetime import datetime, timezone
import math
import subprocess
import sys
import os
import time
import json
from io import BytesIO
from ultralytics import YOLO
from PIL import Image, ImageDraw

# プイビュー用画像の保存パス
PREVIEW_IMAGE_PATH = os.environ["PREVIEW_IMAGE_PATH"]

# 使用するYoloモデルファイルの名前
# パス指定する場合はソースコードからの相対パスで指定
MODEL_FILE_NAME = os.environ["MODEL_FILE_NAME"]

# モデルファイルを絶対パスに変換(このソースコードの場所を起点)
MODEL_FILE_PATH = os.path.join(os.path.dirname(__file__), MODEL_FILE_NAME)

# confidence threshold
# 検出信頼度の閾値(0.0 ~ 1.0)
# これを下回る検出信頼度(confidence score)の検出は、結果に含めない
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
# 例えば、車、バス、オートバイを検出するには　CLASSES = [2, 3, 4]
#
CLASSES = [2]

#
# 警告静止時間(秒)
# 黄枠で結果画像に描画
WARNING_SEC = 30

#
# アラート静止時間(秒)
# 赤枠で結果画像に描画
ALERT_SEC = 60

#
# オブジェクトの保持時間(秒)
# track処理で検出されなかったオブジェクトを保持しておく時間
# 一度外れても、再度検出された場合に同じと判断されれば、同一のオブジェクトＩＤが付与されるので
# ここで設定された時間はtracking_objects配列に保持しておく
OBJECT_RETENTION_TIME_SEC = 10

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
    

def create_result_jpeg(img : Image, tracking_objects : list) -> bytes:
    """
    tracking_objectsの内容を画像に書き込みます
    
    Args:
        img (Image)   : カメラフレーム画像のPIL Image
        tracking_objects (list) : トラッキングオブジェクトを格納した配列

    Returns:
        bytes : 結果を書き込んだJPEG画像
    """
   
    draw = ImageDraw.Draw(img)
    font_size = 30 # 静止時間を書き込む際の文字の大きさ

    for p in tracking_objects:

        if not p["tracked"]:
            continue

        stay_sec = p["stay_sec"]

        # 枠の色を決める
        if stay_sec < WARNING_SEC:
            cr = (255, 255, 255)
        elif stay_sec < ALERT_SEC:
            cr = (255, 255, 0)
        else:
            cr = (255, 0, 0)

        # 静止時間
        hour = math.floor(stay_sec / 60 / 60)
        min = math.floor(stay_sec / 60) - hour * 60
        sec = math.floor(stay_sec%60)
        parking_time = str(min).zfill(2) + ":" + str(sec).zfill(2)
        if hour > 0:
            parking_time = str(hour) + ":" + parking_time

        text = f'{parking_time}'

        x1 = p["box"]["x1"]
        y1 = p["box"]["y1"]
        x2 = p["box"]["x2"]
        y2 = p["box"]["y2"]

        draw.rectangle((x1, y1, x2, y2), fill=None, outline=cr, width=5)

        text_box = draw.textbbox((x1, y1), text, font_size=font_size, anchor='lt')
        draw.rectangle(text_box, fill=cr, outline=None)
        draw.text((x1, y1), text, fill=(0,0,0), font_size=font_size, anchor='lt')

    dst = BytesIO()
    img.save(dst, format='JPEG', quality=75)
    dst.seek(0)

    return dst.getvalue()


def parse_results(results : list, timestamp : int, tracking_objects : list):
    """
    trackの結果をtracking_objectsに設定します。
    
    Args:
        results (list)   : trackの処理結果
        timestamp (int)  : 時間(Unixtime)
        tracking_objects (list) : トラッキングオブジェクトを格納した配列

    """

    # いったんすべてのオブジェクトのtrackedをFalseで初期化
    for p in tracking_objects:
        p["tracked"] = False

    for box in reversed(results[0].boxes):

        if box.id is None:
            continue

        # 結果を扱いやすいように成形
        id = int(box.id)
        cls = box.cls.tolist()
        conf = box.conf.tolist()
        r = box.xyxy.tolist()

        x1 = int(r[0][0])
        y1 = int(r[0][1])
        x2 = int(r[0][2])
        y2 = int(r[0][3])

        pos_x = int(x1 + (x2 - x1) / 2)
        pos_y = int(y1 + (y2 - y1) / 2)

        # 今回の処理で検出されたオブジェクトのIDが
        # tracking_objectsに存在するかどうかを確認
        p = next((t for t in tracking_objects if t["id"] == id), None)

        if p is None:
            # 初めて検知されたオブジェクトなので
            # 新規に追加

            p = {
                    "id" : id, 
                    "pos" : {"x" : pos_x, "y" : pos_y}, 
                    "box" : {"x1" : x1, "y1" : y1, "x2" : x2, "y2" : y2}, 
                    "prev_timestamp" : timestamp, 
                    "stay_sec" : 0, # 0秒から開始
                    "state" : "stay", 
                    "conf" : conf[0],
                    "cls" : int(cls[0]),
                    "tracked" : True
                }
            
            tracking_objects.append(p)

        else:
            # すでにトラッキングされているオブジェクトが
            # 今回の処理でも見つかったので
            # 情報を更新

            p["tracked"] = True
            p["conf"] = conf[0]

            prev_x = p["pos"]["x"]
            prev_y = p["pos"]["y"]

            #
            # 前回から動いているか？
            # 10ピクセル以上動いていたら動いたと判断
            move_x = abs(prev_x - pos_x)
            move_y = abs(prev_y - pos_y)
            move = move_x > 10 or move_y > 10

            p["pos"] = {"x" : pos_x, "y" : pos_y}
            p["box"] = {"x1" : x1, "y1" : y1, "x2" : x2, "y2" : y2}

            if move:
                p["state"] = "move"
            else:
                # 静止している場合は静止時間を加算
                p["stay_sec"] = p["stay_sec"] + timestamp - p["prev_timestamp"]
                p["state"] = "stay"

            p["prev_timestamp"] = timestamp


def main():

    # トラッキングオブジェクト情報を格納する配列
    tracking_objects = []

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
                tracking_objects = []

            # トラッキング実行
            results = model.track(
                img, 
                conf=CONF, 
                iou=IOU, 
                persist=True,
                classes=CLASSES, 
                verbose=True)

            # 結果を確認し、tracking_objects配列に格納する
            parse_results(results, timestamp, tracking_objects)

            # 結果を書き込んだJPEG画像の生成
            frame = create_result_jpeg(img, tracking_objects)

            # ALERT_SECを超えているオブジェクトがあればPush通知
            if len([p for p in tracking_objects if p["stay_sec"] > ALERT_SEC]) > 0:

                # PUSH通知
                # エラーはここでキャッチしてそのまま処理を流す
                try:
                    push(timestamp, frame, tracking_objects)
                except Exception as e:
                    print(str(e))    


            # 時間がたったオブジェクトは削除する
            tracking_objects = [p for p in tracking_objects if timestamp - p["prev_timestamp"] < OBJECT_RETENTION_TIME_SEC]

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
