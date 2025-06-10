#!/bin/bash

# LINE → Gemini → はてな統合システム起動スクリプト

echo "🚀 LINE → Gemini → はてな統合システムを起動中..."

# 仮想環境の確認・作成
if [ ! -d "venv" ]; then
    echo "📦 仮想環境を作成中..."
    python3 -m venv venv
fi

# 仮想環境のアクティベート
echo "🔄 仮想環境をアクティベート中..."
source venv/bin/activate

# 依存パッケージのインストール
echo "📋 依存パッケージをインストール中..."
pip install -r requirements.txt

# 環境変数ファイルの確認
if [ ! -f ".env" ]; then
    echo "⚠️  .envファイルが見つかりません"
    echo "📝 .env.exampleを参考に.envファイルを作成してください"
    exit 1
fi

# データベースディレクトリの作成
mkdir -p uploads
mkdir -p logs

# アプリケーションの起動
echo "🌟 アプリケーションを起動中..."
python main.py