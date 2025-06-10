# Line-Gemini-Hatena Integration - 本番環境デプロイメントガイド

## 概要

本システムはLINE Bot、Gemini AI、はてなブログを統合したコンテンツ作成システムです。本ガイドでは本番環境へのデプロイ方法を説明します。

## 🚀 クイックスタート

### 1. 前提条件

- Docker & Docker Compose がインストール済み
- ドメイン名の取得（推奨）
- 各種APIキーの取得

### 2. 環境変数設定

```bash
# テンプレートから本番用設定ファイルを作成
cp .env.production.template .env.production

# 実際の値を設定
nano .env.production
```

### 3. デプロイ実行

```bash
# 一括デプロイ（推奨）
./deploy.sh

# バックアップをスキップする場合
./deploy.sh --skip-backup

# デプロイ後にログを確認
./deploy.sh --logs
```

## 📋 詳細なデプロイ手順

### ステップ1: システム要件確認

```bash
# Docker確認
docker --version
docker-compose --version

# ポート確認（8000番が空いていることを確認）
sudo netstat -tulpn | grep :8000
```

### ステップ2: プロジェクトファイル準備

```bash
# プロジェクトディレクトリに移動
cd /path/to/line-gemini-hatena-integration

# 必要なディレクトリ作成
mkdir -p logs uploads instance ssl
```

### ステップ3: 環境変数設定

#### 必須設定項目

```bash
# LINE Bot設定
LINE_CHANNEL_ACCESS_TOKEN=your-token-here
LINE_CHANNEL_SECRET=your-secret-here

# Gemini API設定
GEMINI_API_KEY=your-api-key-here

# はてなブログ設定
HATENA_ID=your-hatena-id
HATENA_BLOG_ID=your-blog-id
HATENA_API_KEY=your-api-key
```

#### オプション設定項目

```bash
# Google Photos（画像管理）
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Imgur（画像ホスティング）
IMGUR_CLIENT_ID=your-client-id
IMGUR_CLIENT_SECRET=your-client-secret
```

### ステップ4: SSL設定（HTTPS使用時）

```bash
# SSL証明書を配置
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem

# Nginx設定でHTTPS有効化
nano nginx.conf
# SSL設定のコメントアウトを解除
```

### ステップ5: デプロイ実行

```bash
# 自動デプロイスクリプト実行
./deploy.sh

# 手動でのデプロイ
docker-compose build
docker-compose up -d
```

## 🔧 運用管理

### サービス状態確認

```bash
# コンテナ状態確認
docker-compose ps

# リソース使用状況
docker stats

# ログ確認
docker-compose logs -f
```

### サービス制御

```bash
# サービス停止
docker-compose down

# サービス再起動
docker-compose restart

# 設定更新後の再デプロイ
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### バックアップ・復元

```bash
# 手動バックアップ
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cp -r instance logs uploads backups/$(date +%Y%m%d_%H%M%S)/

# 復元（例）
docker-compose down
cp -r backups/20240101_120000/* ./
docker-compose up -d
```

## 🔍 トラブルシューティング

### よくある問題

#### 1. ポート8000が使用中

```bash
# 使用中のプロセス確認
sudo lsof -i :8000

# プロセス終了
sudo kill -9 <PID>
```

#### 2. 環境変数エラー

```bash
# 環境変数確認
docker-compose config

# コンテナ内で確認
docker exec -it line-gemini-hatena-app env
```

#### 3. Webhook接続エラー

```bash
# ヘルスチェック
curl http://localhost:8000/health

# Webhook設定確認
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

#### 4. メモリ不足

```bash
# メモリ使用量確認
docker stats --no-stream

# ログファイルクリーンアップ
docker-compose exec line-gemini-hatena-app find logs -name "*.log" -mtime +7 -delete
```

### ログレベル調整

```bash
# デバッグモード（開発時のみ）
echo "LOG_LEVEL=DEBUG" >> .env.production
docker-compose restart

# 本番環境では INFO または WARN 推奨
echo "LOG_LEVEL=INFO" >> .env.production
```

## 🚨 セキュリティ考慮事項

### 基本セキュリティ

1. **ファイアウォール設定**
```bash
# 必要なポートのみ開放
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

2. **定期アップデート**
```bash
# 定期的にイメージ更新
docker-compose pull
docker-compose up -d
```

3. **ログローテーション**
```bash
# logrotateで設定
sudo nano /etc/logrotate.d/line-gemini-hatena
```

### 機密情報管理

- `.env.production`ファイルの権限を制限: `chmod 600 .env.production`
- API키는 環境変数でのみ管理、コードにハードコーディングしない
- 定期的なAPIキーのローテーション

## 📊 監視・モニタリング

### ヘルスチェック

```bash
# 外部からのヘルスチェック
curl https://your-domain.com/health

# 定期監視スクリプト（cron設定推奨）
*/5 * * * * curl -f http://localhost:8000/health || echo "Service down" | mail admin@your-domain.com
```

### パフォーマンス監視

```bash
# リソース使用量ログ
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" >> performance.log
```

## 🔄 アップデート手順

### マイナーアップデート

```bash
# 新しいコードを取得
git pull origin main

# 再デプロイ
./deploy.sh
```

### メジャーアップデート

```bash
# バックアップ作成
./deploy.sh --skip-backup=false

# データベースマイグレーション（必要に応じて）
docker-compose exec line-gemini-hatena-app python -c "from src.database import db; db.create_all()"

# 動作確認
curl http://localhost:8000/health
```

## 📞 サポート

問題が発生した場合：

1. **ログ確認**: `docker-compose logs`
2. **ヘルスチェック**: `curl http://localhost:8000/health`
3. **設定確認**: `docker-compose config`
4. **リソース確認**: `docker stats`

---

**注意**: 本番環境では必ずHTTPS（SSL/TLS）を使用し、定期的なバックアップを実施してください。