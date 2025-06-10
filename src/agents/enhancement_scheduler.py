"""
Enhancement Scheduler - フェイズ2定期実行システム
品質向上処理を定期的に実行
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from src.agents.enhancement_orchestrator import EnhancementOrchestrator

logger = logging.getLogger(__name__)

class EnhancementScheduler:
    """品質向上定期実行スケジューラー"""
    
    def __init__(self, interval_minutes: int = 60):
        self.interval_minutes = interval_minutes
        self.orchestrator = EnhancementOrchestrator()
        self.running = False
    
    async def start(self):
        """スケジューラーを開始"""
        self.running = True
        logger.info(f"Enhancement scheduler started (interval: {self.interval_minutes} minutes)")
        
        while self.running:
            try:
                logger.info("Starting scheduled enhancement cycle...")
                start_time = time.time()
                
                # 品質向上サイクルを実行
                await self.orchestrator.run_enhancement_cycle()
                
                end_time = time.time()
                duration = end_time - start_time
                
                logger.info(f"Enhancement cycle completed in {duration:.2f} seconds")
                
                # 指定された間隔で待機
                await asyncio.sleep(self.interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Enhancement scheduler error: {e}")
                # エラー時は5分待機してリトライ
                await asyncio.sleep(300)
    
    def stop(self):
        """スケジューラーを停止"""
        self.running = False
        logger.info("Enhancement scheduler stopped")

# 手動実行用関数
async def run_enhancement_now():
    """品質向上処理を今すぐ実行"""
    try:
        # Flask アプリコンテキストを設定
        import sys
        import os
        sys.path.append('/home/moto/line-gemini-hatena-integration')
        
        from main import create_app
        
        app = create_app()
        with app.app_context():
            orchestrator = EnhancementOrchestrator()
            await orchestrator.run_enhancement_cycle()
            logger.info("Manual enhancement run completed")
    
    except Exception as e:
        logger.error(f"Manual enhancement run failed: {e}")

if __name__ == "__main__":
    import sys
    import os
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add src to path for imports
    sys.path.append('/home/moto/line-gemini-hatena-integration')
    
    if len(sys.argv) > 1 and sys.argv[1] == "run-now":
        # 即座実行
        asyncio.run(run_enhancement_now())
    else:
        # 定期実行
        scheduler = EnhancementScheduler(interval_minutes=60)  # 1時間毎
        try:
            asyncio.run(scheduler.start())
        except KeyboardInterrupt:
            scheduler.stop()
            logger.info("Enhancement scheduler terminated by user")
