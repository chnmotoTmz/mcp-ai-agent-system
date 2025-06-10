#!/bin/bash

# AI Agent MCP システムのセットアップスクリプト

echo "🚀 AI Agent MCP システムをセットアップ中..."

# Python パスを設定
export PYTHONPATH="/home/moto/line-gemini-hatena-integration:$PYTHONPATH"

# 仮想環境があるかチェック
if [ ! -d "venv" ]; then
    echo "📦 仮想環境を作成中..."
    python3 -m venv venv
fi

# 仮想環境をアクティベート
source venv/bin/activate

# MCPの依存関係をインストール
echo "📚 依存関係をインストール中..."
pip install -r requirements.txt

# アップロードディレクトリを作成
echo "📁 アップロードディレクトリを作成中..."
mkdir -p uploads

# データベースディレクトリを作成
echo "🗃️ データベースディレクトリを作成中..."
mkdir -p instance

# 権限設定
chmod +x start.sh

echo "✅ セットアップ完了！"
echo ""
echo "🔧 次のステップ:"
echo "1. .envファイルに必要な環境変数を設定"
echo "2. ./start.sh でシステムを起動"
echo ""
echo "🧪 テスト方法:"
echo "curl -X POST http://localhost:8084/api/webhook/test -H 'Content-Type: application/json' -d '{\"message\": \"AIエージェントのテストです\", \"user_id\": \"test_user\"}'"
