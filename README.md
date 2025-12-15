# Idol MV Bot (Snow Man Edition)

アイドルグループのMV再生回数を監視し、マイルストーン達成時や応援が必要なタイミングでX (Twitter) に自動投稿するボットです。

## 特徴

- 📊 **マイルストーン自動検出**: 100万回、1000万回、1億回などの節目を自動検出
- 🎯 **動的ルール**: 再生数に応じてマイルストーン間隔を自動調整（例: 1億回超えたら1億単位）
- 📢 **応援通知**: マイルストーンまであと少しのときに応援投稿
- 🔢 **漢字表記**: 「7000万回」「1億回」など、インパクトのある表現
- 🛡️ **スパム防止**: 1回の実行で最大3件まで投稿制限
- 🎲 **テンプレートランダム化**: 複数のテンプレートからランダム選択

## セットアップ手順

### 1. 必要ライブラリのインストール
```powershell
pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env` ファイルを編集し、APIキーを設定します。
```env
YOUTUBE_API_KEY=your_youtube_api_key

# X (Twitter) APIキー（なければシミュレーションモードで動作）
SNOWMAN_TWITTER_CONSUMER_KEY=xxxxx
SNOWMAN_TWITTER_CONSUMER_SECRET=xxxxx
SNOWMAN_TWITTER_ACCESS_TOKEN=xxxxx
SNOWMAN_TWITTER_ACCESS_TOKEN_SECRET=xxxxx
```

### 3. 初期化（初回のみ）
現在のマイルストーン状態をDBに記録します。これにより、次回以降は**新規達成のみ**投稿されます。
```powershell
python src/main.py --init
```

### 4. 通常実行
```powershell
python src/main.py
```

## コマンドオプション

| オプション | 説明 |
|------------|------|
| (なし) | 通常実行。最新50本のMVをチェックし、DBに記録済みの動画も更新 |
| `--init` | 初期化モード。投稿せずに現在のマイルストーン状態をDBに記録（初回セットアップ用） |
| `--full-scan` | フルスキャン。チャンネルの全動画をスキャン |

## 設定ファイル

### config/config.yaml

```yaml
system:
  check_interval_minutes: 60  # チェック間隔
  log_level: "INFO"
  max_posts_per_run: 3  # 1回の実行での最大投稿数（スパム防止）

targets:
  - artist_name: "Snow Man"
    account_id: "SNOWMAN"
    channel_id: "UCuFPaemAaMR8R5cHzjy23dQ"
    hashtags: ["#SnowMan", "#スノ担と繋がりたい"]
    title_keywords: ["Music Video", "MV", "Performance Video"]
    
    custom_vars:
      fan_name: "スノ担"
      oshi_mark: "☃️"
      cheer_msg: "Snow Manしか勝たん👊✨"
    
    milestones:
      dynamic_rules:
        - threshold: 100000000  # 1億回以上 → 1億刻み
          step: 100000000
        - threshold: 10000000   # 1000万回以上 → 1000万刻み
          step: 10000000
        - threshold: 0          # それ未満 → 100万刻み
          step: 1000000
      initial_target: 1000000
    
    support_trigger:
      - remaining: 100000  # 残り10万回で応援投稿
      - remaining: 10000   # 残り1万回で応援投稿
```

## グループ・アカウントの追加

1. **`config/config.yaml` への追加**
   ```yaml
   - artist_name: "新しいグループ名"
     account_id: "NEWGROUP"  # 識別ID（半角英大文字推奨）
     channel_id: "UCxxxxxxxxxxxx"
     title_keywords: ["Music Video", "MV"]
     # ...他設定はSnow Manを参考にコピー
   ```

2. **APIキーの設定**
   `.env` または GitHub Secrets に以下を追加:
   ```env
   NEWGROUP_TWITTER_CONSUMER_KEY=xxxxx
   NEWGROUP_TWITTER_CONSUMER_SECRET=xxxxx
   NEWGROUP_TWITTER_ACCESS_TOKEN=xxxxx
   NEWGROUP_TWITTER_ACCESS_TOKEN_SECRET=xxxxx
   ```

## 投稿例

### マイルストーン達成時
```
🎊【Snow Man】
「EMPIRE Music Video」が7000万回再生を突破しました！
おめでとうございます！ ☃️✨

これからもたくさん愛されますように…🙏
#SnowMan #スノ担と繋がりたい
https://www.youtube.com/watch?v=xxxxx
```

### 応援（マイルストーン間近）
```
🔥【拡散希望】
「EMPIRE Music Video」あと5万回で8000万回再生達成です！

今こそ団結のとき！みんなで押し上げよう！😤💨

#SnowMan #スノ担と繋がりたい
https://www.youtube.com/watch?v=xxxxx
```

## ファイル構成

```
idle/
├── config/
│   └── config.yaml     # 設定ファイル
├── db/
│   └── mv_data.db      # SQLiteデータベース
├── src/
│   ├── main.py         # メインスクリプト
│   ├── youtube_client.py
│   ├── x_client.py
│   └── db_manager.py
├── .env                # 環境変数（APIキー）
├── requirements.txt
└── README.md
```

## 注意事項

- X APIキーがない場合は**シミュレーションモード**で動作します（DBには記録されますが、実際には投稿されません）
- 初回実行時は必ず `--init` オプションで初期化してください。これをしないと、既存のマイルストーンが全て投稿対象になります
- `max_posts_per_run` でスパム防止の投稿制限を設定できます（デフォルト: 3件）

