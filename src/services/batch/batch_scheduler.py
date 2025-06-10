"""
バッチ処理スケジューラー
定期実行とタスク管理
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import schedule
import time
import threading

from src.services.batch.batch_processor import BatchProcessor

logger = logging.getLogger(__name__)

class BatchScheduler:
    """バッチ処理スケジューラー"""
    
    def __init__(self, interval_minutes: int = 15):
        self.interval_minutes = interval_minutes
        self.processor = BatchProcessor(batch_interval_minutes=interval_minutes)
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        logger.info(f"バッチスケジューラー初期化完了 (間隔: {interval_minutes}分)")
    
    def start(self):
        """スケジューラーを開始"""
        if self.running:
            logger.warning("スケジューラーは既に実行中です")
            return
        
        logger.info("バッチスケジューラー開始")
        self.running = True
        
        # スケジュール設定
        schedule.every(self.interval_minutes).minutes.do(self._run_batch_job)
        
        # 別スレッドでスケジューラーを実行
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"バッチ処理が{self.interval_minutes}分間隔で実行されます")
    
    def stop(self):
        """スケジューラーを停止"""
        if not self.running:
            return
        
        logger.info("バッチスケジューラー停止中...")
        self.running = False
        
        # スケジュールをクリア
        schedule.clear()
        
        # スレッドの終了を待機
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("バッチスケジューラー停止完了")
    
    def _scheduler_loop(self):
        """スケジューラーのメインループ"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"スケジューラーループエラー: {e}")
                time.sleep(5)
    
    def _run_batch_job(self):
        """バッチジョブを実行"""
        try:
            logger.info("スケジュール済みバッチジョブ開始")
            
            # 新しいイベントループでバッチ処理を実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self.processor._process_batch_cycle())
            finally:
                loop.close()
            
            logger.info("スケジュール済みバッチジョブ完了")
            
        except Exception as e:
            logger.error(f"バッチジョブエラー: {e}")
    
    def run_manual_batch(self):
        """手動でバッチ処理を実行"""
        logger.info("手動バッチ処理実行")
        self._run_batch_job()
    
    def get_next_run_time(self) -> Optional[datetime]:
        """次回実行時刻を取得"""
        jobs = schedule.jobs
        if jobs:
            next_job = min(jobs, key=lambda x: x.next_run)
            return next_job.next_run
        return None
    
    def get_status(self) -> dict:
        """スケジューラーの状態を取得"""
        return {
            'running': self.running,
            'interval_minutes': self.interval_minutes,
            'next_run': self.get_next_run_time(),
            'jobs_count': len(schedule.jobs)
        }

# グローバルスケジューラーインスタンス
_batch_scheduler: Optional[BatchScheduler] = None

def get_batch_scheduler(interval_minutes: int = 15) -> BatchScheduler:
    """バッチスケジューラーのシングルトンインスタンスを取得"""
    global _batch_scheduler
    
    if _batch_scheduler is None:
        _batch_scheduler = BatchScheduler(interval_minutes)
    
    return _batch_scheduler

def start_batch_system(interval_minutes: int = 15):
    """バッチシステムを開始"""
    scheduler = get_batch_scheduler(interval_minutes)
    scheduler.start()
    return scheduler

def stop_batch_system():
    """バッチシステムを停止"""
    global _batch_scheduler
    
    if _batch_scheduler:
        _batch_scheduler.stop()
        _batch_scheduler = None

# 使用例とテスト
if __name__ == "__main__":
    import sys
    import signal
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def signal_handler(sig, frame):
        """終了シグナルハンドラー"""
        logger.info("終了シグナル受信")
        stop_batch_system()
        sys.exit(0)
    
    # シグナルハンドラー設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # バッチシステム開始
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 1  # テスト用に1分間隔
    
    logger.info(f"バッチシステムテスト開始 (間隔: {interval}分)")
    
    scheduler = start_batch_system(interval)
    
    try:
        # メインループ
        while True:
            status = scheduler.get_status()
            logger.info(f"スケジューラー状態: {status}")
            time.sleep(60)  # 1分ごとに状態確認
            
    except KeyboardInterrupt:
        logger.info("キーボード割り込み")
    finally:
        stop_batch_system()
