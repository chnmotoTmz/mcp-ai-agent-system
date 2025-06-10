#!/bin/bash

# 本番環境テストスクリプト
# Line-Gemini-Hatena Integration System

set -e

echo "=================================="
echo "本番環境テストスクリプト"
echo "=================================="

# 色付きメッセージ
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 基本ヘルスチェック
test_health_endpoint() {
    log_info "ヘルスチェックエンドポイントをテスト中..."
    
    local url="http://localhost:8000/health"
    local response=$(curl -s -w "%{http_code}" -o /tmp/health_response "$url")
    
    if [ "$response" = "200" ]; then
        log_info "✅ ヘルスチェック成功"
        cat /tmp/health_response
    else
        log_error "❌ ヘルスチェック失敗 (HTTP $response)"
        cat /tmp/health_response
        return 1
    fi
}

# Webhook エンドポイントテスト
test_webhook_endpoint() {
    log_info "Webhookエンドポイントをテスト中..."
    
    local url="http://localhost:8000/webhook"
    local test_data='{"events":[],"destination":"test"}'
    
    local response=$(curl -s -w "%{http_code}" -o /tmp/webhook_response \
        -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$test_data")
    
    if [ "$response" = "200" ]; then
        log_info "✅ Webhook エンドポイント応答正常"
    else
        log_warn "⚠️  Webhook エンドポイント (HTTP $response) - 認証エラーの可能性"
        log_info "これは正常な場合があります（LINE署名検証のため）"
    fi
}

# メモリ使用量チェック
test_memory_usage() {
    log_info "メモリ使用量をチェック中..."
    
    local container_stats=$(docker stats --no-stream --format "{{.MemUsage}}" line-gemini-hatena-app 2>/dev/null || echo "N/A")
    
    if [ "$container_stats" != "N/A" ]; then
        log_info "📊 メモリ使用量: $container_stats"
    else
        log_warn "⚠️  コンテナ統計情報を取得できませんでした"
    fi
}

# ログ出力テスト
test_log_output() {
    log_info "ログ出力をチェック中..."
    
    if [ -f "./logs/app.log" ]; then
        local log_lines=$(tail -5 ./logs/app.log 2>/dev/null || echo "")
        if [ -n "$log_lines" ]; then
            log_info "✅ ログファイル出力正常"
            echo "最新のログ（5行）:"
            echo "$log_lines"
        else
            log_warn "⚠️  ログファイルが空です"
        fi
    else
        log_warn "⚠️  ログファイルが見つかりません: ./logs/app.log"
    fi
}

# データベース接続テスト
test_database_connection() {
    log_info "データベース接続をテスト中..."
    
    if [ -f "./instance/app.db" ]; then
        log_info "✅ データベースファイルが存在します"
        
        # データベースサイズ確認
        local db_size=$(ls -lh "./instance/app.db" | awk '{print $5}')
        log_info "📊 データベースサイズ: $db_size"
    else
        log_warn "⚠️  データベースファイルが見つかりません（初回起動の場合は正常）"
    fi
}

# 環境変数チェック
test_environment_variables() {
    log_info "重要な環境変数をチェック中..."
    
    # Dockerコンテナ内の環境変数確認
    local env_check=$(docker exec line-gemini-hatena-app printenv | grep -E "^(LINE_|GEMINI_|HATENA_)" | wc -l 2>/dev/null || echo "0")
    
    if [ "$env_check" -gt 0 ]; then
        log_info "✅ 環境変数が設定されています（$env_check 個）"
    else
        log_error "❌ 重要な環境変数が設定されていません"
        return 1
    fi
}

# ポート確認
test_port_accessibility() {
    log_info "ポートアクセシビリティをテスト中..."
    
    if nc -z localhost 8000 2>/dev/null; then
        log_info "✅ ポート8000にアクセス可能"
    else
        log_error "❌ ポート8000にアクセスできません"
        return 1
    fi
}

# SSL/TLS テスト（HTTPS設定時）
test_ssl_configuration() {
    local domain="${1:-localhost}"
    
    if [ "$domain" != "localhost" ]; then
        log_info "SSL/TLS設定をテスト中..."
        
        if command -v openssl &> /dev/null; then
            local ssl_check=$(echo | timeout 5 openssl s_client -connect "$domain:443" 2>/dev/null | grep "Verify return code:")
            
            if [ -n "$ssl_check" ]; then
                log_info "✅ SSL証明書確認: $ssl_check"
            else
                log_warn "⚠️  SSL証明書の確認ができませんでした"
            fi
        else
            log_warn "⚠️  opensslがインストールされていません"
        fi
    else
        log_info "⏭️  SSL/TLSテストをスキップ（localhost）"
    fi
}

# 負荷テスト（軽量）
test_load_performance() {
    log_info "軽量負荷テストを実行中..."
    
    if command -v ab &> /dev/null; then
        log_info "Apache Bench による負荷テスト (10リクエスト)"
        ab -n 10 -c 2 http://localhost:8000/health 2>/dev/null | grep -E "(Requests per second|Time per request)"
    elif command -v curl &> /dev/null; then
        log_info "curl による連続リクエストテスト"
        local start_time=$(date +%s)
        for i in {1..5}; do
            curl -s http://localhost:8000/health > /dev/null
        done
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_info "📊 5リクエスト完了時間: ${duration}秒"
    else
        log_warn "⚠️  負荷テストツールがありません（ab または curl）"
    fi
}

# メイン実行
main() {
    local domain="${1:-localhost}"
    local failed_tests=0
    
    log_info "本番環境テスト開始..."
    log_info "対象: $domain"
    echo ""
    
    # テスト実行
    test_port_accessibility || ((failed_tests++))
    echo ""
    
    test_health_endpoint || ((failed_tests++))
    echo ""
    
    test_webhook_endpoint || ((failed_tests++))
    echo ""
    
    test_environment_variables || ((failed_tests++))
    echo ""
    
    test_database_connection
    echo ""
    
    test_memory_usage
    echo ""
    
    test_log_output
    echo ""
    
    test_ssl_configuration "$domain"
    echo ""
    
    test_load_performance
    echo ""
    
    # 結果表示
    echo "=================================="
    echo "テスト結果サマリー"
    echo "=================================="
    
    if [ $failed_tests -eq 0 ]; then
        log_info "🎉 すべてのテストが成功しました！"
        log_info "本番環境は正常に動作しています。"
    else
        log_error "❌ $failed_tests 個のテストが失敗しました。"
        log_error "問題を確認して修正してください。"
        exit 1
    fi
    
    echo ""
    log_info "📋 追加確認項目:"
    log_info "1. LINE Webhook URL設定: https://$domain/webhook"
    log_info "2. SSL証明書の有効期限確認"
    log_info "3. 定期バックアップの設定"
    log_info "4. モニタリング・アラートの設定"
}

# 使用方法表示
if [ "$1" = "--help" ]; then
    echo "使用方法: $0 [ドメイン名]"
    echo "例: $0 your-domain.com"
    echo "    $0  # localhost でテスト"
    exit 0
fi

# スクリプト実行
main "$@"