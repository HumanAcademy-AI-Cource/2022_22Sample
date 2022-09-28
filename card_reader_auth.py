#!/usr/bin/env python3


# 必要なライブラリをインポート
from re import U
import cv2
import time
import boto3
import random
import signal
import csv

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


def readUserList():
    database = {}
    # CSVをファイルを開く
    with open("./user_list.csv", "r") as f:
        # ヘッダーはスキップ
        next(csv.reader(f, delimiter=","))
        # データを読み取る
        csv_data = csv.reader(f, delimiter=",")
        # for文でCSVデータを展開
        for i, row in enumerate(csv_data):
            if len(row) > 0:
                # IDを取り出す
                user_id = str(row[0])
                # 名前を取り出す
                name = str(row[1])
                # 辞書型のデータとして記録
                database[user_id] = name
    return database


if __name__ == "__main__":
    # ユーザリストを取得
    user_list = readUserList()

    # 認証が失敗するカード画像（ユーザ情報が登録されている）
    image = cv2.imread("./images/card.png")

    # 認証が失敗するカード画像（ユーザ情報が登録されていない例）
    # image = cv2.imread("./images/card2.png")

    detect_text, result_image = aws_card_reader(image)

    # ユーザIDを記録する変数
    user_id = None
    for d in detect_text:
        # =======================
        # ユーザIDの検出処理
        # =======================
        space_num = d.count(" ")
        # スペースが3個含まれている場合はユーザIDの可能性が高い
        if space_num == 3:
            # 文字列からスペースを除去
            replace_text = d.replace(" ", "")
            # 文字数（桁数）を調べる
            ketasu = len(replace_text)
            # 桁数が16であった場合、ユーザIDとして扱う
            if ketasu == 16:
                # ユーザIDとして保存
                user_id = str(replace_text)

    # ===================================
    # データベースを参照してユーザの確認
    # ===================================
    if user_id in user_list:
        print("ID（{}）の認証: ◯".format(user_id))
    else:
        print("ID（{}）の認証: ☓".format(user_id))

    result_image = cv2.resize(result_image, dsize=None, fx=0.5, fy=0.5)
    cv2.imshow("ResultImage", result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
