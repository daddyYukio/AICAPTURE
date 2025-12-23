[![AI CAPTURE](./aicap.jpg)](https://aicap.daddysoffice.com)
# AI検知プログラム集

このリポジトリには、標準搭載のAI検知プログラムや差し替え用プログラムを収録しています。  

## [AIBOX OS 標準搭載AI検知プログラム](./programs/built-in-object-detection)
AIBOX OSに標準搭載のAI検知プログラムです

[![](./programs/built-in-object-detection/detection.jpg)](./programs/built-in-object-detection)

## [熊撃退プログラム](./programs/bear_repellent)
熊などの物体を検知するとPush通知と共に音を出して害獣を追い払います。

[![](./programs/bear_repellent/title.jpg)](./programs/bear_repellent)

## [長時間駐車車両検出プログラム](./programs/stay_counter)
長時間駐車している車両を検出してPush通知を送信する検知プログラムです。

YOLO11のトラッキングを使用して、認識した物体の静止している時間を計測します。

[![](./programs/stay_counter/stay_counter.jpg)](./programs/stay_counter)

## [検知したら電源ON](./programs/power_on_appliance)
人などを検知したら、電源をONにするプログラムです。

BluetoothでSwitchBotプラグミニを制御します。

[![](./programs/power_on_appliance/switchbot.jpg)](./programs/power_on_appliance)


## 開発への参加について

このリポジトリはオープンです。誰でも自由に開発・改善に参加できます。  

- リポジトリを **Fork / Clone** して自由に開発してください。  
- 変更や追加機能は **Commit** して、リポジトリ宛に **Pull Request（PR）** を送ってください。  
- PR は内容を確認した上で **Merge** します。  

また、Issue を立てたり Discussion で提案することも歓迎です。  
## ライセンス

このプロジェクトは MIT License で公開されています。詳細は LICENSE ファイルを参照してください。