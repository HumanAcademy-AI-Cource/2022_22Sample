#!/usr/bin/env python3


# 必要なライブラリをインポート
import signal
import random
import cv2
import time
import boto3
import card_reader
import signal
import sys

# Webカメラの設定
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
# フレームレート設定
cap.set(cv2.CAP_PROP_FPS, 30)
# 横方向の解像度設定(320px)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
# 縦方向の解像度設定(240px)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# 終了処理
signal.signal(signal.SIGINT, signal.SIG_DFL)

# AWSのクライアントを用意
rekognition_client = boto3.client(service_name="rekognition")


def aws_card_reader(image, draw_text=True):
    """
    AWSのRekognitionを使用してカード情報を読み取る関数
    """
    text = []
    encode_image = cv2.imencode(".JPEG", image)[1].tobytes()
    try:
        # Rekognitionのdetect_textを利用して画像内の文字を認識
        detext_text_data = rekognition_client.detect_text(Image={"Bytes": encode_image})
        # 画像内に文字があった場合には処理を続行
        if len(detext_text_data["TextDetections"]) != 0:
            # 認識結果から認識した文字の情報だけ取り出す
            for d in detext_text_data["TextDetections"]:
                if d["Type"] == "LINE":
                    x = int(d["Geometry"]["BoundingBox"]["Left"] * image.shape[1])
                    y = int(d["Geometry"]["BoundingBox"]["Top"] * image.shape[0])
                    w = int(d["Geometry"]["BoundingBox"]["Width"] * image.shape[1])
                    h = int(d["Geometry"]["BoundingBox"]["Height"] * image.shape[0])
                    image = cv2.rectangle(image, (x, y), (x + w, y + h), (0, 241, 255), 3)
                    if draw_text:
                        image = cv2.putText(image, d["DetectedText"], (x, y + h + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 241, 255), thickness=5)
                    text.append(d["DetectedText"])
    except Exception as e:
        print("AWSが混み合っていますので、しばらくお待ちください。")
        time.sleep(int(random.uniform(0, 5)))
    return text, image


def infoMessage():
    print("=======================================================================")
    print("カード読み取りシステム")
    print("  - カメラウィンドウを選択した状態で[s]キーを押すと読み取り開始")
    print("  - [e]キーを押すと終了します。")
    print("=======================================================================")


if __name__ == '__main__':
    infoMessage()
    while True:
        # カメラ画像を取得
        success, image = cap.read()
        cv2.imshow("Camera", image)
        press_key = cv2.waitKey(1)
        if press_key == ord("s"):
            # カメラ画像のファイル名を設定
            image_filename = "./images/camera.png"
            # カメラ画像を保存
            cv2.imwrite(image_filename, image)
            # 認識開始
            detect_text, result_image = aws_card_reader(image)
            print("○ 認識したカードの情報")
            for d in detect_text:
                print(d)
            infoMessage()
        if press_key == ord("e"):
            print("３秒後にプログラムを終了します。")
            time.sleep(3)
            sys.exit(0)
