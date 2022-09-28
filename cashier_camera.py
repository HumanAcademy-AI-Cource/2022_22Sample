#!/usr/bin/env python3

# 必要なライブラリをインポート
import cv2
import subprocess
import wave
import csv
import time
import sys
import boto3


def makeAudioFile(path, data):
    # 引数: 音楽ファイルを保存するパス, オーディオデータ
    # オーディオデータから音楽ファイル作成
    wave_data = wave.open(path, "wb")
    wave_data.setnchannels(1)
    wave_data.setsampwidth(2)
    wave_data.setframerate(16000)
    wave_data.writeframes(data)
    wave_data.close()


def speechPolly(speech_text):
    # ----------------------------
    # Polly
    # ----------------------------
    print("発話内容: {}".format(speech_text))
    # 音声合成開始
    speech_data = polly_client.synthesize_speech(
        Text=speech_text, OutputFormat="pcm", VoiceId="Mizuki"
    )["AudioStream"]
    # 音声合成のデータを音楽ファイル化
    makeAudioFile("speech.wav", speech_data.read())
    # 保存したWAVデータを再生
    subprocess.check_call('aplay -D plughw:Headphones {}'.format("speech.wav"), shell=True)


def infoMessage():
    print("=======================================================================")
    print("無人レジシステム")
    print("  - カメラウィンドウを選択した状態で[s]キーを押すと商品スキャン")
    print("  - お会計は[e]キー")
    print("=======================================================================")


# Webカメラの設定
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
# フレームレート設定
cap.set(cv2.CAP_PROP_FPS, 30)
# 横方向の解像度設定(320px)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
# 縦方向の解像度設定(240px)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# Boto3を使ってAWSのサービスを使う準備
# Rekognitionのクライアントを用意
rekognition_client = boto3.client(service_name="rekognition")
# Translateのクライアントを用意
translate_client = boto3.client(service_name="translate")
# Pollyのクライアントを用意
polly_client = boto3.client(service_name="polly")

database = {}
# CSVをファイルを開く
with open("./database.csv", "r") as f:
    # ヘッダーはスキップ
    next(csv.reader(f))
    # データを読み取る
    csv_data = csv.reader(f)
    # for文でCSVデータを展開
    for i, row in enumerate(csv_data):
        if len(row) > 0:
            # モノの名前を取り出す
            name = row[0]
            # 価格を取り出す
            price = row[1]
            # 辞書型のデータとして記録
            database[name] = price

# 会計の合計額を記録する変数
goukei = 0

# 案内用のメッセージを表示
infoMessage()
while True:
    # カメラ画像を取得
    success, image = cap.read()
    # 取得したカメラ画像を表示
    cv2.imshow("Camera", image)

    press_key = cv2.waitKey(1)
    if press_key == ord("s"):
        # カメラ画像のファイル名を設定
        image_filename = "./images/camera.png"
        # カメラ画像を保存
        cv2.imwrite(image_filename, image)

        with open(image_filename, "rb") as f:
            # 画像を読み込む
            image = f.read()
            # Rekognitionを使ってモノを認識
            response_data = rekognition_client.detect_labels(Image={"Bytes": image})

            # レスポンスデータから「Labels」を取り出す
            labels = response_data["Labels"]

            # データベースにあるものだけをピックアップ
            items = []
            for label in labels:
                # ラベルデータからラベルの名称を取り出す
                name = label["Name"]
                if name in database:
                    price = database[name]
                    items.append((name, database[name]))

            if len(items) == 0:
                print("商品が見つかりませんでした。スタッフを呼んでください。")
                print("=======================================================================")
                # 案内文を音声合成して再生
                speechPolly("商品が見つかりませんでした。スタッフを呼んでください。")
            else:
                # 会計対象のモノの名前を取り出す
                name = items[0][0]
                price = items[0][1]

                # Translateを使って翻訳
                response_data = translate_client.translate_text(
                    Text=name, SourceLanguageCode="en", TargetLanguageCode="ja"
                )
                # レスポンスデータから「translated_text」を取り出す
                transrated_name = response_data["TranslatedText"]

                print("スキャンされた商品: {}(¥{})".format(transrated_name, price))
                # 案内文を音声合成
                speechPolly("{}がスキャンされました。価格は{}円です。".format(transrated_name, price))

                # 合計金額を計算
                goukei += int(price)
            infoMessage()
    if press_key == ord("e"):
        # 会計モード
        print("お会計は¥{}です。".format(goukei))
        print("お支払いは不要です。ご利用ありがとうございました！")
        speechPolly("お会計は¥{}です。お支払いは不要です。ご利用ありがとうございました！".format(goukei))
        print("=======================================================================")
        print("３秒後にプログラムを終了します。")
        time.sleep(3)
        # 終了処理
        sys.exit(0)
