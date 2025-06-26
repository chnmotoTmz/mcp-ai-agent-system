# LINE Bot Webhook エラー復旧ガイド

## 🚨 主要エラーと対処法

### 1. Google Generative AI upload_file エラー

**症状**: `genai.upload_file()` でファイルアップロードが失敗
**原因**: APIキー権限、ファイルサイズ、ネットワーク接続問題
**修正済み**: 3段階フォールバック処理を実装済み

```python
# 修正内容: src/services/gemini_service.py:420-479
# 1. upload_file方式（推奨）
# 2. PIL Image方式（フォールバック）  
# 3. 簡易応答（最終フォールバック）
```

### 2. Gemini API 500エラー

**症状**: Gemini APIから500 Internal Server Errorが返される
**原因**: API制限、リクエスト内容の問題、一時的なサービス問題
**修正済み**: フォールバック記事生成機能を追加

```python
# 修正内容: src/services/gemini_service.py:365-407
# APIエラー時でも記事生成を継続
```

### 3. バッチ処理での画像分析失敗

**症状**: バッチ処理中に画像分析でエラーが発生し処理が停止
**原因**: 画像ファイル破損、API制限、メモリ不足
**修正済み**: 詳細ログとエラーハンドリング強化

```python  
# 修正内容: src/routes/webhook_enhanced.py:337-364
# エラー時でもバッチ処理を継続
```

## 🔍 デバッグ方法

### ログ確認
```bash
tail -f logs/app.log | grep -E "(エラー|ERROR|分析)"
```

### 画像分析テスト
```bash
# 手動で画像分析テスト
python -c "
from src.services.gemini_service import GeminiService
service = GeminiService()
result = service.analyze_image('uploads/test.jpg')
print(result)
"
```

### API接続確認
```bash
# Gemini API接続テスト
python -c "
import google.generativeai as genai
from src.config import Config
genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')
response = model.generate_content('Hello')
print(response.text)
"
```

## ⚙️ 設定確認事項

### 1. 環境変数
- `GEMINI_API_KEY`: 正しいAPIキーが設定されているか
- `GEMINI_MODEL`: 利用可能なモデル名か（推奨: gemini-1.5-pro）

### 2. ファイル権限
- `uploads/` ディレクトリの書き込み権限
- 画像ファイルの読み込み権限

### 3. API制限
- Gemini APIの利用制限を確認
- 1分間のリクエスト数制限
- 1日の利用量制限

## 🛠️ トラブルシューティング

### エラーが継続する場合

1. **APIキー確認**
   ```bash
   echo $GEMINI_API_KEY
   ```

2. **依存関係更新**
   ```bash
   pip install --upgrade google-generativeai pillow
   ```

3. **ログレベル調整**
   ```python
   # より詳細なログ出力
   logging.getLogger().setLevel(logging.DEBUG)
   ```

4. **フォールバック無効化テスト**
   ```python
   # 一時的にフォールバック処理をコメントアウトして原因特定
   ```

## 📊 監視推奨項目

- 画像分析成功率
- API応答時間
- エラー発生頻度
- フォールバック処理実行回数

---
**更新日**: 2025年6月10日
**対象バージョン**: LINE-Gemini-Hatena統合システム v1.0