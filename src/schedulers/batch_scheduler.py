"""
バッチ処理スケジューラー
定期的にメッセージバッファを処理
"""

import logging
import threading
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.batch_processing_service import BatchProcessingService
from ..config import Config

logger = logging.getLogger(__name__)

class BatchScheduler:
    """バッチ処理スケジューラー"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self.batch_service = None
        self.is_running = False
        
    def init_app(self, app):
        """Flaskアプリケーションと連携"""
        self.app = app
        
    def start(self):
        """スケジューラーを開始"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        try:
            # バッチ処理サービスを初期化
            self.batch_service = BatchProcessingService()
            
            # スケジューラーを設定
            self.scheduler = BackgroundScheduler(
                timezone='Asia/Tokyo',
                job_defaults={\n                    'coalesce': True,\n                    'max_instances': 1\n                }\n            )\n            \n            # 1分間隔でバッチ処理を実行\n            self.scheduler.add_job(\n                func=self._run_batch_processing,\n                trigger=IntervalTrigger(minutes=Config.BATCH_INTERVAL_MINUTES),\n                id='batch_processing',\n                name='Message Buffer Batch Processing',\n                replace_existing=True\n            )\n            \n            # スケジューラーを開始\n            self.scheduler.start()\n            self.is_running = True\n            \n            logger.info(f\"Batch scheduler started with {Config.BATCH_INTERVAL_MINUTES}-minute interval\")\n            \n        except Exception as e:\n            logger.error(f\"Failed to start batch scheduler: {e}\")\n            raise\n    \n    def stop(self):\n        \"\"\"スケジューラーを停止\"\"\"\n        if self.scheduler and self.is_running:\n            self.scheduler.shutdown(wait=True)\n            self.is_running = False\n            logger.info(\"Batch scheduler stopped\")\n    \n    def _run_batch_processing(self):\n        \"\"\"バッチ処理を実行（スケジューラーから呼び出し）\"\"\"\n        if not self.app:\n            logger.error(\"Flask app not available for batch processing\")\n            return\n            \n        # Flaskアプリケーションコンテキスト内で実行\n        with self.app.app_context():\n            self.run_batch_processing()\n    \n    def run_batch_processing(self):\n        \"\"\"バッチ処理を手動実行\"\"\"\n        try:\n            start_time = datetime.now()\n            logger.info(\"Starting batch processing...\")\n            \n            # 期限切れバッファを処理\n            results = self.batch_service.process_all_expired_buffers()\n            \n            # 結果をログ出力\n            end_time = datetime.now()\n            duration = (end_time - start_time).total_seconds()\n            \n            successful = len([r for r in results if r.get('success')])\n            failed = len([r for r in results if not r.get('success')])\n            \n            logger.info(\n                f\"Batch processing completed in {duration:.2f}s: \"\n                f\"{successful} successful, {failed} failed, {len(results)} total\"\n            )\n            \n            # 詳細結果をログ出力\n            for result in results:\n                if result.get('success'):\n                    logger.info(\n                        f\"✅ Buffer {result['buffer_id']}: \"\n                        f\"Article {result.get('article_id')} created with \"\n                        f\"{result.get('message_count', 0)} messages, \"\n                        f\"{result.get('image_count', 0)} images\"\n                    )\n                else:\n                    logger.error(\n                        f\"❌ Buffer {result['buffer_id']}: \"\n                        f\"Failed - {result.get('error', 'Unknown error')}\"\n                    )\n            \n            return {\n                'success': True,\n                'processed_count': len(results),\n                'successful_count': successful,\n                'failed_count': failed,\n                'duration_seconds': duration,\n                'results': results\n            }\n            \n        except Exception as e:\n            logger.error(f\"Batch processing failed: {e}\")\n            import traceback\n            traceback.print_exc()\n            \n            return {\n                'success': False,\n                'error': str(e)\n            }\n    \n    def get_status(self) -> dict:\n        \"\"\"スケジューラーの状態を取得\"\"\"\n        if not self.scheduler:\n            return {\n                'running': False,\n                'jobs': [],\n                'next_run': None\n            }\n        \n        jobs = []\n        for job in self.scheduler.get_jobs():\n            jobs.append({\n                'id': job.id,\n                'name': job.name,\n                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,\n                'trigger': str(job.trigger)\n            })\n        \n        next_run = None\n        if jobs:\n            next_runs = [job['next_run'] for job in jobs if job['next_run']]\n            if next_runs:\n                next_run = min(next_runs)\n        \n        return {\n            'running': self.is_running,\n            'jobs': jobs,\n            'next_run': next_run,\n            'interval_minutes': Config.BATCH_INTERVAL_MINUTES\n        }\n    \n    def force_run(self) -> dict:\n        \"\"\"バッチ処理を強制実行\"\"\"\n        if not self.app:\n            return {\n                'success': False,\n                'error': 'Flask app not available'\n            }\n        \n        with self.app.app_context():\n            return self.run_batch_processing()\n\n# グローバルスケジューラーインスタンス\nbatch_scheduler = BatchScheduler()\n\ndef init_scheduler(app):\n    \"\"\"スケジューラーを初期化\"\"\"\n    batch_scheduler.init_app(app)\n    \n    # アプリケーション終了時にスケジューラーを停止\n    import atexit\n    atexit.register(batch_scheduler.stop)\n    \n    return batch_scheduler\n\ndef start_scheduler():\n    \"\"\"スケジューラーを開始\"\"\"\n    batch_scheduler.start()\n\ndef stop_scheduler():\n    \"\"\"スケジューラーを停止\"\"\"\n    batch_scheduler.stop()\n\ndef get_scheduler_status():\n    \"\"\"スケジューラーの状態を取得\"\"\"\n    return batch_scheduler.get_status()\n\ndef force_batch_processing():\n    \"\"\"バッチ処理を強制実行\"\"\"\n    return batch_scheduler.force_run()\n