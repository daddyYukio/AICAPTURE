# aicap for development

開発用のaicapコマンドです。

開発環境(Linux/Mac/Windows)上で、検知プログラムを開発する際のスタブモジュールです。

コマンド引数などは、AIBOX OSに搭載されているaicapコマンドと同じなので、パスが通る場所に配置して、検知プログラムを開発することができます。

開発用aicapコマンドでは。ローカルに接続されたUVC接続のカメラを使用し、Push通知の送信画像やJson文字列は、指定したローカルディレクトリに保存されます。

[コマンドの詳細はこちらを参照](https://aicap.daddysoffice.com/ja/command_help.html)

> ⚠️ ffmpegが必要ですので、開発環境にインストールしてから使用してください。

## 使い方
### 1. 開発環境にffmpegをインストール

### 2. 環境にあったaicapモジュールを開発環境にダウンロード

### 3. UVCカメラを開発環境に接続

### 4. UVCカメラのデバイス情報を取得
#### Linuxの場合
- V4L2(Video for Linux2)が入っていなければインストール。(sudo apt install v4l2-utils)
- v4l2-ctl --list-devicesで、接続したUVCカメラのデバイスパスを表示

```shell
$ v4l2-ctl --list-devices

Microsoft® LifeCam HD-3000: Mi (usb-0000:00:0b.0-1):
	/dev/video0
	/dev/video1
```
- 番号の若い方をコピーする。(上記の場合、/dev/video0)

#### Windowsの場合
- コマンドプロンプトで「ffmpeg -list_devices true -f dshow -i dummy」を入力
```shell
$ ffmpeg -list_devices true -f dshow -i dummy

[dshow @ 000002d291eebb80] "HD Webcam eMeet C960" (video)
[dshow @ 000002d291eebb80]   Alternative name "@device_pnp_\\?\usb#vid_328f&pid_2013&mi_00#7&39fbeec7&0&0000#{65e8773d-8f56-11d0-a3b9-00a0c9223196}\global"
[dshow @ 000002d291eebb80] "マイク (4- USB PnP Audio Device)" (audio)
[dshow @ 000002d291eebb80]   Alternative name "@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\wave_{8C2D500B-1450-43FA-8404-5A2B25817267}"
[dshow @ 000002d291eebb80] "マイク (HD Webcam eMeet C960)" (audio)
[dshow @ 000002d291eebb80]   Alternative name "@device_cm_{33D9A762-90C8-11D0-BD43-00A0C911CE86}\wave_{44545183-13C6-4A8E-A80C-20BD4E517837}"
```
- videoデバイスの名前をコピーする。(上記の場合、HD Webcam eMeet C960)
#### Macの場合
- ターミナルで「ffmpeg -list_devices true -f avfoundation -i dummy」を入力
```shell
$ ffmpeg -list_devices true -f avfoundation -i dummy

[AVFoundation indev @ 0x7f8b4af05000] AVFoundation video devices:
[AVFoundation indev @ 0x7f8b4af05000] [0] Microsoft® LifeCam HD-3000
[AVFoundation indev @ 0x7f8b4af05000] [1] Capture screen 0
[AVFoundation indev @ 0x7f8b4af05000] AVFoundation audio devices:
[AVFoundation indev @ 0x7f8b4af05000] [0] Microsoft® LifeCam HD-3000
```
- videoデバイスの番号を覚えておく。(上記の場合、[0])

### 5. aicapと同じ場所にaicap.confファイルを作成する
パラメータは2つ
- VideoCaptureDevice : 使用するUVCカメラのデバイス情報
- PushResultOutputPath : pushコマンド実行時に指定した画像/Jsonパラメータを保存する場所

#### Linux用
```json
{
    "VideoCaptureDevice" : "/dev/video0",
    "PushResultOutputPath" : "/home/user/work/temp"
}
```

#### Windows用
```json
{
    "VideoCaptureDevice" : "HD Webcam eMeet C960",
    "PushResultOutputPath" : "/home/user/work/temp"
}
```

#### Mac用
```json
{
    "VideoCaptureDevice" "0": ,
    "PushResultOutputPath" : "/home/user/work/temp"
}
```

### 6. 開発環境にaicapコマンドまでのパスを設定する
システムのパスに追加してもOKですが、VisualStudio Codeを使用している場合は、launch.jsonのenvにPATHを追加することでコマンドを実行できます。

```json
{
    "version": "0.2.0",
    "configurations": [

        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "extmod.py",
            "console": "integratedTerminal",
            "args": [],
            "env": {
                "MODEL_FILE_NAME" : "yolo11m.pt",
                "PREVIEW_IMAGE_PATH" : "C:/Users/yukio/Desktop/temp/result.jpg",

                // WindowsのPATHの区切りは [;]
                // Linux/Macは [:]
                "PATH": "${env:PATH};C:/Users/yukio/work"
            }
        }
    ]
}
```