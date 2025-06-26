# Imgur API セットアップガイド

## 🔧 Imgur Client ID取得手順

### 1. Imgurアカウント作成・ログイン
1. [Imgur](https://imgur.com) にアクセス
2. アカウントを作成またはログイン

### 2. API Application登録
1. [Imgur API](https://api.imgur.com/oauth2/addclient) にアクセス
2. 以下の情報を入力：
   - **Application name**: `LINE Bot Image Upload`
   - **Authorization type**: `Anonymous usage without user authorization`
   - **Authorization callback URL**: 空欄でOK
   - **Application website**: `http://localhost` (テスト用)
   - **Email**: あなたのメールアドレス
   - **Description**: `LINE Bot用画像アップロード機能`

### 3. Client ID取得
- 登録完了後、**Client ID**が表示されます
- この値を控えておいてください

### 4. 環境変数設定
`.env`ファイルに以下を追加：
```
IMGUR_CLIENT_ID=your_client_id_here
```

## ⚠️ 現在の問題

現在のテストで429エラー（レート制限）が発生しています。これは：

1. **デフォルトClient ID**: 古いまたは制限に達している
2. **API制限**: 
   - Client: 12,500リクエスト/日
   - User: 500リクエスト/時

## 🧪 テスト手順

新しいClient IDを取得後：

```bash
# 環境変数設定後
export IMGUR_CLIENT_ID=your_new_client_id

# テスト実行
python test_imgur_mcp.py
```

## 📊 制限情報

- **ファイルサイズ**: 最大20MB
- **対応形式**: JPEG, PNG, GIF, APNG, TIFF, BMP, PDF, XCF
- **レート制限**: 
  - 12,500リクエスト/日（Client）
  - 500リクエスト/時（User）

## 🔒 セキュリティ

- Client IDは公開されても安全（認証なしアクセス用）
- ただし使用量制限があるため適切に管理
- 本番環境では独自のClient IDを使用推奨