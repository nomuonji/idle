# Idol MV Bot (Snow Man Edition)

アイドルグループのMV再生回数を監視し、マイルストーン達成時や応援が必要なタイミングでX (Twitter) に自動投稿するボットです。

## セットアップ手順

1. **必要ライブラリのインストール**
   ```powershell
   pip install -r requirements.txt
   ```

2. **設定ファイルの編集**
   `config/config.yaml` をテキストエディタで開きます。
   - `api_keys.twitter`: X APIキーを入力（なければ空欄でシミュレーションモード動作）
   - `targets`: 監視対象のグループやマイルストーン設定を変更可能
   - `title_keywords`: "MV" などで絞り込みたい場合はリストに記述（現在は `[]` で全動画対象）

3. **実行**
   ```powershell
   python src/main.py
   ```
   コンソールに動作ログが表示され、条件を満たした場合は投稿（または投稿シミュレーション）が行われます。
   デフォルトでは60分ごとにチェックを行います。

## グループ・アカウントの追加（拡張方法）

新しいアイドルグループを追加し、専用のXアカウントで投稿させる手順は以下の通りです。

1. **`config/config.yaml` への追加**
   `targets` リストに新しいエントリを追加します。`account_id` を一意に決めて設定してください。
   ```yaml
   - artist_name: "新しいグループ名"
     account_id: "NEWGROUP"  # 識別ID（半角英大文字推奨）
     channel_id: "UCxxxxxxxxxxxx" # YouTubeチャンネルID
     title_keywords: ["Music Video", "MV"]
     milestones:
       step: 1000000
       initial_target: 1000000
     # ...他設定はSnow Manを参考にコピー
   ```

2. **APIキーの設定**
   `account_id` に対応するX APIキーを設定します。キー名は `{ACCOUNT_ID}_TWITTER_...` の形式である必要があります。

   **ローカル実行の場合 (`.env`)**:
   ```env
   # New Group (ID: NEWGROUP)
   NEWGROUP_TWITTER_CONSUMER_KEY=xxxxxx
   NEWGROUP_TWITTER_CONSUMER_SECRET=xxxxxx
   NEWGROUP_TWITTER_ACCESS_TOKEN=xxxxxx
   NEWGROUP_TWITTER_ACCESS_TOKEN_SECRET=xxxxxx
   ```

   **GitHub Actionsの場合 (Secrets)**:
   リポジトリ設定の Secrets に同様の変数名で値を登録してください。
   また、`.github/workflows/mv_monitor.yml` の `env` セクションにも、その変数を読み込む記述を追加する必要があります。
   ```yaml
       env:
         # ... 既存のキー
         NEWGROUP_TWITTER_CONSUMER_KEY: ${{ secrets.NEWGROUP_TWITTER_CONSUMER_KEY }}
         # ... 他3つも同様に追加
   ```

## ファイル構成
- `config/config.yaml`: 設定全般
- `db/mv_data.db`: 再生数履歴データベース
- `src/`: プログラム本体
- `logs/`: (将来的なログ保存場所)
