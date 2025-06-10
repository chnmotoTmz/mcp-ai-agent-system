# Claude 作業ガイドライン

## 🚨 重要：ファイル作成ルール

### 絶対禁止事項
- `*_fixed.py` `*_backup.py` `*_temp.py` `*_test.py` などの命名
- 既存ファイルがある場合の新規ファイル作成
- 実験的コードの本体ディレクトリへの保存

### 必須事項
1. **既存ファイル編集を最優先**
   - バグ修正 → 元ファイルを直接編集
   - 機能追加 → 元ファイルに追加
   - 新規ファイル作成は最後の手段

2. **作業完了時のクリーンアップ**
   - 不要な一時ファイルの削除確認
   - 重複ファイルの統合
   - ファイル数の最小化

3. **変更理由の記録**
   - 何を変更したか
   - なぜ変更したか
   - どのファイルが最新版か

## 📁 プロジェクト構造（2025年6月現在）

### MCPサーバー（メイン実装）
- `src/mcp_servers/gemini_server.py` - Gemini AI MCP server
- `src/mcp_servers/hatena_server.py` - はてなブログ MCP server  
- `src/mcp_servers/line_server.py` - LINE MCP server
- `src/mcp_servers/imgur_server.py` - Imgur MCP server

### FastMCP実装（代替実装）
- `src/mcp_servers/*_fastmcp.py` - 各サービスのFastMCP版

### Webhookルート
- `src/mcp_servers/routes/webhook_enhanced.py` - メインWebhook（推奨）
- `src/mcp_servers/routes/webhook_ai.py` - AI処理用
- `src/mcp_servers/routes/api.py` - REST API

### 起動スクリプト
- `start_mcp_system.py` - メイン起動スクリプト（推奨）
- `setup_mcp.sh` - 環境セットアップ

## 🔄 過去の問題と学習事項

### 2025年6月の大規模ファイル整理
**問題**: 19個の`*_fixed.py`ファイルが無秩序に作成された
**原因**: Claude Desktopでの作業時に既存ファイル編集ではなく新規作成を選択
**教訓**: 既存ファイルの修正は必ず元ファイルを編集する

### 削除されたファイル例
- `gemini_server_fixed.py` → `gemini_server.py`に統合済み
- `webhook_batch.py` → `webhook_enhanced.py`に統合済み
- `start_simple_*.py` → `start_mcp_system.py`に統合済み

## 💡 作業開始前チェックリスト

1. [ ] 既存ファイルの確認
2. [ ] 修正対象ファイルの特定
3. [ ] 新規作成の必要性検討
4. [ ] ファイル命名規則の確認
5. [ ] 作業完了後のクリーンアップ予定

## 🎯 現在のアクティブファイル（編集対象）

### すぐに編集可能
- `src/mcp_servers/gemini_server.py`
- `src/mcp_servers/hatena_server.py`
- `src/mcp_servers/routes/webhook_enhanced.py`
- `src/services/batch_processing_service.py`

### 慎重に扱うべき
- `start_mcp_system.py` - 本番起動スクリプト
- `requirements.txt` - 依存関係定義
- データベースマイグレーションファイル

## 🚫 今後作成してはいけないファイル
- 任意の`*_fixed.py`
- 任意の`*_backup.py`  
- 任意の`*_temp.py`
- 重複する起動スクリプト
- 重複するrequirementsファイル

---
**最終更新**: 2025年6月10日
**整理完了**: ルートディレクトリ30ファイル（大規模整理後）
