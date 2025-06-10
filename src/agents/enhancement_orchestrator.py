"""
Enhancement Orchestrator - フェイズ2品質向上システム
段階的にブログ記事の品質を向上させる
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.database import db, Article, EnhancementLog, ArticleLink
from src.services.enhancement_gemini_service import EnhancementGeminiService

logger = logging.getLogger(__name__)

@dataclass
class EnhancementTask:
    """品質向上タスク定義"""
    name: str
    priority: int
    delay_hours: int
    description: str

class EnhancementOrchestrator:
    """品質向上オーケストレーター"""
    
    def __init__(self):
        self.gemini_service = EnhancementGeminiService()
        
        # 品質向上タスクの定義
        self.enhancement_tasks = [
            EnhancementTask("text_quality", 1, 1, "文章品質向上・誤字脱字修正"),
            EnhancementTask("similar_links", 2, 1, "類似記事検索・内部リンク追加"),
            EnhancementTask("image_analysis", 3, 6, "画像解析・サムネイル最適化"),
            EnhancementTask("content_expansion", 4, 24, "コンテンツ拡張・詳細化"),
        ]
    
    async def find_enhancement_candidates(self) -> List[Article]:
        """品質向上候補の記事を検索"""
        try:
            # 1時間以上前に作成された draft 記事を取得
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            candidates = Article.query.filter(
                Article.status == 'draft',
                Article.created_at <= one_hour_ago,
                Article.published == True  # 投稿済みの記事のみ
            ).order_by(Article.created_at.asc()).limit(10).all()
            
            logger.info(f"Found {len(candidates)} enhancement candidates")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to find enhancement candidates: {e}")
            return []
    
    async def enhance_article_quality(self, article: Article) -> bool:
        """記事品質向上処理"""
        try:
            logger.info(f"Enhancing text quality for article {article.id}")
            
            # Gemini で文章改善
            improved_content = await self._improve_text_quality(article.content)
            
            if improved_content and improved_content != article.content:
                # 履歴を保存
                await self._save_enhancement_log(
                    article.id,
                    "text_quality",
                    "GeminiQualityAgent",
                    article.content,
                    improved_content
                )
                
                # 記事を更新
                article.content = improved_content
                article.enhancement_level += 1
                article.last_enhanced_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Article {article.id} text quality enhanced")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to enhance article quality: {e}")
            await self._save_enhancement_log(
                article.id,
                "text_quality",
                "GeminiQualityAgent",
                article.content,
                None,
                success=False,
                error_message=str(e)
            )
            return False
    
    async def add_similar_links(self, article: Article) -> bool:
        """類似記事のリンクを追加"""
        try:
            logger.info(f"Adding similar links for article {article.id}")
            
            # 類似記事を検索
            similar_articles = await self._find_similar_articles(article)
            
            if similar_articles:
                # リンクを含む新しいコンテンツを生成
                enhanced_content = await self._add_internal_links(article, similar_articles)
                
                if enhanced_content and enhanced_content != article.content:
                    # 履歴を保存
                    await self._save_enhancement_log(
                        article.id,
                        "similar_links",
                        "SimilarLinkAgent",
                        article.content,
                        enhanced_content
                    )
                    
                    # 記事を更新
                    article.content = enhanced_content
                    article.enhancement_level += 1
                    article.last_enhanced_at = datetime.utcnow()
                    db.session.commit()
                    
                    # リンク関係を保存
                    for similar in similar_articles:
                        link = ArticleLink(
                            source_article_id=article.id,
                            target_article_id=similar.id,
                            link_context=f"関連記事として追加: {similar.title}",
                            link_type="related"
                        )
                        db.session.add(link)
                    
                    db.session.commit()
                    logger.info(f"Article {article.id} enhanced with {len(similar_articles)} similar links")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to add similar links: {e}")
            await self._save_enhancement_log(
                article.id,
                "similar_links",
                "SimilarLinkAgent",
                article.content,
                None,
                success=False,
                error_message=str(e)
            )
            return False
    
    async def analyze_and_enhance_images(self, article: Article) -> bool:
        """画像解析・サムネイル最適化"""
        try:
            logger.info(f"Analyzing images for article {article.id}")
            
            # 記事に関連する画像を検索（メッセージから）
            source_messages = article.get_source_messages_list()
            image_paths = []
            
            if source_messages:
                from src.database import Message
                messages = Message.query.filter(
                    Message.line_message_id.in_(source_messages),
                    Message.message_type == 'image'
                ).all()
                
                image_paths = [msg.file_path for msg in messages if msg.file_path]
            
            if image_paths:
                # 画像解析を実行
                enhanced_content = await self._analyze_images_and_enhance_content(
                    article.content, 
                    image_paths
                )
                
                if enhanced_content and enhanced_content != article.content:
                    # 履歴を保存
                    await self._save_enhancement_log(
                        article.id,
                        "image_analysis",
                        "ImageAnalysisAgent",
                        article.content,
                        enhanced_content
                    )
                    
                    # 記事を更新
                    article.content = enhanced_content
                    article.set_image_paths_list(image_paths)
                    article.enhancement_level += 1
                    article.last_enhanced_at = datetime.utcnow()
                    article.status = 'image_added'  # ステータス更新
                    db.session.commit()
                    
                    logger.info(f"Article {article.id} enhanced with image analysis")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to analyze images: {e}")
            await self._save_enhancement_log(
                article.id,
                "image_analysis",
                "ImageAnalysisAgent",
                article.content,
                None,
                success=False,
                error_message=str(e)
            )
            return False
    
    async def run_enhancement_cycle(self):
        """品質向上サイクルを実行"""
        try:
            logger.info("Starting enhancement cycle...")
            
            # 候補記事を取得
            candidates = await self.find_enhancement_candidates()
            
            for article in candidates:
                logger.info(f"Processing article {article.id}: {article.title}")
                
                # 現在の状態に応じて処理を選択
                if article.status == 'draft' and article.enhancement_level == 0:
                    # 文章品質向上
                    await self.enhance_article_quality(article)
                    await self.add_similar_links(article)
                    
                elif article.status == 'draft' and article.enhancement_level >= 1:
                    # 画像解析（6時間後）
                    six_hours_ago = datetime.utcnow() - timedelta(hours=6)
                    if article.created_at <= six_hours_ago:
                        await self.analyze_and_enhance_images(article)
                
                # 少し間隔を空ける
                await asyncio.sleep(1)
            
            logger.info(f"Enhancement cycle completed. Processed {len(candidates)} articles")
            
        except Exception as e:
            logger.error(f"Enhancement cycle failed: {e}")
    
    async def _improve_text_quality(self, content: str) -> Optional[str]:
        """Gemini を使って文章品質を向上"""
        try:
            return self.gemini_service.improve_text_quality(content)
        except Exception as e:
            logger.error(f"Failed to improve text quality: {e}")
            return None
    
    async def _find_similar_articles(self, article: Article) -> List[Article]:
        """類似記事を検索"""
        try:
            # 簡易実装：タグが重複する記事を検索
            article_tags = article.get_tags_list()
            
            if not article_tags:
                return []
            
            # 他の記事を検索（自分以外）
            other_articles = Article.query.filter(
                Article.id != article.id,
                Article.published == True
            ).all()
            
            similar_articles = []
            
            for other in other_articles:
                other_tags = other.get_tags_list()
                # タグの重複をチェック
                common_tags = set(article_tags) & set(other_tags)
                
                if len(common_tags) >= 1:  # 1つ以上のタグが共通
                    similar_articles.append(other)
                
                if len(similar_articles) >= 3:  # 最大3記事
                    break
            
            return similar_articles
            
        except Exception as e:
            logger.error(f"Failed to find similar articles: {e}")
            return []
    
    async def _add_internal_links(self, article: Article, similar_articles: List[Article]) -> Optional[str]:
        """内部リンクを追加した新しいコンテンツを生成"""
        try:
            # 類似記事の情報を辞書形式に変換
            similar_info = []
            for similar in similar_articles:
                similar_info.append({
                    'title': similar.title,
                    'hatena_url': similar.hatena_url or ''
                })
            
            return self.gemini_service.add_internal_links(article.content, similar_info)
            
        except Exception as e:
            logger.error(f"Failed to add internal links: {e}")
            return None
    
    async def _analyze_images_and_enhance_content(self, content: str, image_paths: List[str]) -> Optional[str]:
        """画像解析結果を基にコンテンツを拡張"""
        try:
            # 最初の画像のみ解析（簡易実装）
            if not image_paths:
                return None
            
            image_path = image_paths[0]
            analysis = self.gemini_service.analyze_image_for_enhancement(image_path)
            
            if analysis:
                return self.gemini_service.enhance_content_with_image_analysis(content, analysis)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze images and enhance content: {e}")
            return None
    
    async def _save_enhancement_log(self, article_id: int, enhancement_type: str, 
                                   agent_name: str, before_content: str, 
                                   after_content: Optional[str], success: bool = True,
                                   error_message: Optional[str] = None):
        """品質向上履歴を保存"""
        try:
            log = EnhancementLog(
                article_id=article_id,
                enhancement_type=enhancement_type,
                agent_name=agent_name,
                before_content=before_content,
                after_content=after_content,
                success=success,
                error_message=error_message
            )
            
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to save enhancement log: {e}")

# テスト実行用
async def test_enhancement():
    """品質向上システムのテスト"""
    orchestrator = EnhancementOrchestrator()
    await orchestrator.run_enhancement_cycle()

if __name__ == "__main__":
    import sys
    import os
    
    # Add src to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(test_enhancement())
