#!/bin/bash

# プロジェクトクリーンアップスクリプト
# 使用方法: ./cleanup.sh

echo "🧹 プロジェクトクリーンアップを開始..."

# 不要なファイルパターンを削除
echo "不要ファイルを削除中..."
find . -name "*_fixed.py" -type f -delete 2>/dev/null
find . -name "*_backup.py" -type f -delete 2>/dev/null
find . -name "*_temp.py" -type f -delete 2>/dev/null
find . -name "debug_*.py" -type f -delete 2>/dev/null
find . -name "temp_*" -type f -delete 2>/dev/null
find . -name "*.log" -type f -delete 2>/dev/null
find . -name "test_img.*" -type f -delete 2>/dev/null
find . -name "*:Zone.Identifier" -type f -delete 2>/dev/null

# Python キャッシュクリア
echo "Pythonキャッシュをクリア中..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -type f -delete 2>/dev/null
find . -name "*.pyo" -type f -delete 2>/dev/null

# 現在のファイル数を表示
echo "📊 クリーンアップ完了"
echo "ルートディレクトリファイル数: $(ls -1 | wc -l)"
echo "総Pythonファイル数: $(find . -name "*.py" -type f | grep -v venv | wc -l)"

echo "✅ クリーンアップ完了!"
