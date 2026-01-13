from datetime import datetime, timezone
import sys
import os
import time
from io import BytesIO
from ultralytics import YOLO
from PIL import Image, ImageDraw
import aicap

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
# 例えば、車、バス、オートバイを検出するには　CLASSES = [2, 3, 4]
#
CLASSES = [0]


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
            frame = aicap.get_frame()
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
                
                # 検知枠を書き込んだJPEG画像の生成
                frame = create_result_jpeg(img, res)

                # PUSH通知
                # エラーはここでキャッチしてそのまま処理を流す
                try:
                    aicap.push(timestamp, frame, res)
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
