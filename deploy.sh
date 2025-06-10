#!/bin/bash

# 本番環境デプロイスクリプト
# Line-Gemini-Hatena Integration System

set -e  # エラー時に停止

echo "=================================="
echo "Line-Gemini-Hatena Integration"
echo "本番環境デプロイスクリプト"
echo "=================================="

# 設定
PROJECT_NAME="line-gemini-hatena"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# 色付きメッセージ
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 前提条件チェック
check_prerequisites() {
    log_info "前提条件をチェック中..."
    
    # Docker確認
    if ! command -v docker &> /dev/null; then
        log_error "Dockerがインストールされていません"
        exit 1
    fi
    
    # Docker Compose確認
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Composeがインストールされていません"
        exit 1
    fi
    
    # 環境変数ファイル確認
    if [ ! -f ".env.production" ]; then
        log_error ".env.productionファイルが見つかりません"
        log_info ".env.production.templateを参考に設定してください"
        exit 1
    fi
    
    log_info "前提条件チェック完了"
}

# バックアップ作成
create_backup() {
    if [ "$1" = "--skip-backup" ]; then
        log_warn "バックアップをスキップします"
        return
    fi
    
    log_info "既存データのバックアップを作成中..."
    
    mkdir -p "$BACKUP_DIR"
    
    # データベースバックアップ
    if [ -d "./instance" ]; then
        cp -r ./instance "$BACKUP_DIR/"
        log_info "データベースをバックアップしました: $BACKUP_DIR/instance"
    fi
    
    # ログバックアップ
    if [ -d "./logs" ]; then
        cp -r ./logs "$BACKUP_DIR/"
        log_info "ログをバックアップしました: $BACKUP_DIR/logs"
    fi
    
    # アップロードファイルバックアップ
    if [ -d "./uploads" ]; then
        cp -r ./uploads "$BACKUP_DIR/"
        log_info "アップロードファイルをバックアップしました: $BACKUP_DIR/uploads"
    fi
    
    log_info "バックアップ完了: $BACKUP_DIR"
}

# 既存コンテナ停止
stop_existing() {
    log_info "既存のコンテナを停止中..."
    
    # プロジェクト名で停止
    docker-compose -p "$PROJECT_NAME" down || true
    
    # 個別コンテナも停止
    docker stop "${PROJECT_NAME}-app" 2>/dev/null || true
    docker stop "${PROJECT_NAME}-nginx" 2>/dev/null || true
    
    log_info "既存コンテナの停止完了"
}

# イメージビルド
build_image() {
    log_info "Dockerイメージをビルド中..."
    
    # 古いイメージをクリーンアップ
    docker image prune -f || true
    
    # 新しいイメージをビルド
    docker-compose build --no-cache
    
    log_info "イメージビルド完了"
}

# 必要なディレクトリ作成
create_directories() {
    log_info "必要なディレクトリを作成中..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p instance
    mkdir -p ssl  # SSL証明書用（必要に応じて）
    
    # 権限設定
    chmod 755 logs uploads instance
    
    log_info "ディレクトリ作成完了"
}

# アプリケーション起動
start_application() {
    log_info "アプリケーションを起動中..."
    
    # Docker Composeでサービス起動
    docker-compose -p "$PROJECT_NAME" up -d
    
    log_info "アプリケーション起動完了"
}

# ヘルスチェック
health_check() {
    log_info "ヘルスチェック実行中..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_info "ヘルスチェック成功！"
            return 0
        fi
        
        log_warn "ヘルスチェック失敗 (試行 $attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "ヘルスチェックが失敗しました"
    return 1
}

# ログ表示
show_logs() {
    log_info "最新のログを表示します（Ctrl+Cで終了）:"
    docker-compose -p "$PROJECT_NAME" logs -f
}

# ステータス表示
show_status() {
    log_info "デプロイ状況:"
    docker-compose -p "$PROJECT_NAME" ps
    
    echo ""
    log_info "リソース使用状況:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# メイン処理
main() {
    local skip_backup=false
    local show_logs_flag=false
    
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                skip_backup=true
                shift
                ;;
            --logs)
                show_logs_flag=true
                shift
                ;;
            --help)
                echo "使用方法: $0 [オプション]"
                echo "オプション:"
                echo "  --skip-backup  バックアップをスキップ"
                echo "  --logs         デプロイ後にログを表示"
                echo "  --help         このヘルプを表示"
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                exit 1
                ;;
        esac
    done
    
    # デプロイ実行
    check_prerequisites
    
    if [ "$skip_backup" = false ]; then
        create_backup
    else
        create_backup --skip-backup
    fi
    
    stop_existing
    create_directories
    build_image
    start_application
    
    # ヘルスチェック
    if health_check; then
        log_info "🎉 デプロイが正常に完了しました！"
        show_status
        
        echo ""
        log_info "📱 LINE Webhook URL: http://your-domain.com/webhook"
        log_info "🏥 ヘルスチェック URL: http://your-domain.com/health"
        
        if [ "$show_logs_flag" = true ]; then
            echo ""
            show_logs
        fi
    else
        log_error "❌ デプロイに失敗しました"
        log_info "ログを確認してください:"
        docker-compose -p "$PROJECT_NAME" logs --tail 50
        exit 1
    fi
}

# スクリプト実行
main "$@"