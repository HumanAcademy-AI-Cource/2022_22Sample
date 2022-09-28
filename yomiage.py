#!/usr/bin/env python3


# 必要なライブラリをインポート
import cv2
import time
import boto3
import random
import signal
import wave
import subprocess


# 終了処理
signal.signal(signal.SIGINT, signal.SIG_DFL)

# AWSのクライアントを用意
rekognition_client = boto3.client(service_name="rekognition")
polly_client = boto3.client(service_name="polly")


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


if __name__ == "__main__":
    image = cv2.imread("./images/eibun.png")
    detect_text, result_image = aws_eibun_reader(image)
    print("=======================================================================")
    print("○ 認識した文章: {}".format(detect_text))
    print("=======================================================================")
    print("[s]キーを押すと読み上げを開始します。")
    print("=======================================================================")
    cv2.imshow("ResultImage", result_image)
    cv2.waitKey(0)
    speechPolly(detect_text)
    cv2.destroyAllWindows()
