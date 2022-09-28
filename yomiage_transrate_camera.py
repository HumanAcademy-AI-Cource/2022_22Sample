#!/usr/bin/env python3


# 必要なライブラリをインポート
import cv2
import time
import boto3
import random
import signal
import wave
import subprocess
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
polly_client = boto3.client(service_name="polly")
translate_client = boto3.client(service_name="translate")


def translate(text, source, target):
    """
    Translateを使って翻訳する関数
    """
    # 翻訳開始
    response_data = translate_client.translate_text(
        Text=text,
        SourceLanguageCode=source,
        TargetLanguageCode=target
    )
    # レスポンスデータから「translated_text」を取り出す
    translated_text = response_data["TranslatedText"]
    return translated_text


def makeAudioFile(path, data):
    """
    オーディオデータか音楽ファイルを作成する関数
    - 引数: 音楽ファイルを保存するパス, オーディオデータ
    - オーディオデータから音楽ファイル作成
    """
    wave_data = wave.open(path, "wb")
    wave_data.setnchannels(1)
    wave_data.setsampwidth(2)
    wave_data.setframerate(16000)
    wave_data.writeframes(data)
    wave_data.close()


def speechPolly(speech_text, debug_print=False):
    """
    Pollyを使って音声合成して再生する関数
    """
    if debug_print:
        print("発話させる文章: {}".format(speech_text))
    # 音声合成開始
    response_data = polly_client.synthesize_speech(Text=speech_text, OutputFormat="pcm", VoiceId="Mizuki")
    audio_data = response_data["AudioStream"]
    # 音声合成のデータを音楽ファイル化
    makeAudioFile("speech.wav", audio_data.read())
    # 保存したWAVデータを再生
    subprocess.check_call("aplay -D plughw:Headphones {}".format("speech.wav"), shell=True)


def aws_eibun_reader(image):
    """
    AWSのRekognitionを使用して英文を読み取る関数
    """
    text = ""
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
                    image = cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 1)
                    text += d["DetectedText"]
    except Exception as e:
        print("AWSが混み合っていますので、しばらくお待ちください。")
        time.sleep(int(random.uniform(0, 5)))
    return text, image


def infoMessage():
    print("=======================================================================")
    print("英文読み上げシステム")
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
            detect_text, result_image = aws_eibun_reader(image)
            if detect_text != "":
                print("○ 認識した文章: \n{}".format(detect_text))
                print("=======================================================================")
                honyaku_text = translate(detect_text, "en", "ja")
                print("○ 翻訳した文章: \n{}".format(honyaku_text))
                speechPolly(honyaku_text)
            else:
                print("文章が検出されませんでした。")
            infoMessage()
        if press_key == ord("e"):
            print("３秒後にプログラムを終了します。")
            time.sleep(3)
            sys.exit(0)
