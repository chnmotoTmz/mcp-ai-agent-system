"""
LangGraph エージェント ノード実装
LINE→Gemini→Hatena 統合フローの各処理ノード
"""

import asyncio
import logging
import time
from typing import Dict, Any, List
from datetime import datetime

from .state import AgentState, ProcessingStage, MessageType
from .mcp_client import MCPClientManager

logger = logging.getLogger(__name__)

class BlogGenerationNodes:
    """ブログ生成フローのノード実装"""
    
    def __init__(self):
        self.mcp_client = MCPClientManager()
    
    async def receive_line_message(self, state: AgentState) -> AgentState:
        """LINE メッセージ受信処理ノード"""
        start_time = time.time()
        
        try:
            logger.info(f"LINE メッセージ受信処理開始: {state.session_id}")
            state.update_stage(ProcessingStage.RECEIVED)
            
            # メッセージの基本検証
            if not state.line_message:
                raise ValueError("LINE メッセージが設定されていません")
            
            # メッセージタイプに応じた前処理
            if state.line_message.message_type == MessageType.TEXT:
                if not state.line_message.content:
                    raise ValueError("テキストメッセージに内容がありません")
                
                logger.info(f"テキストメッセージ受信: {len(state.line_message.content)}文字")
                
            elif state.line_message.message_type in [MessageType.IMAGE, MessageType.VIDEO]:
                if not state.line_message.file_path:
                    raise ValueError("ファイルメッセージにファイルパスがありません")
                
                # ファイルの存在確認
                import os
                if not os.path.exists(state.line_message.file_path):
                    raise ValueError(f"ファイルが存在しません: {state.line_message.file_path}")
                
                logger.info(f"{state.line_message.message_type.value}ファイル受信: {state.line_message.file_path}")
            
            # 処理時間の記録
            processing_time = time.time() - start_time
            state.processing_time += processing_time
            
            logger.info(f"LINE メッセージ受信処理完了: {processing_time:.2f}秒")
            return state
            
        except Exception as e:
            state.add_error(ProcessingStage.RECEIVED, "MessageReceiveError", str(e))
            logger.error(f"LINE メッセージ受信エラー: {e}")
            return state
    
    async def analyze_with_gemini(self, state: AgentState) -> AgentState:
        """Gemini による分析処理ノード"""
        start_time = time.time()
        
        try:
            logger.info(f"Gemini 分析処理開始: {state.session_id}")
            state.update_stage(ProcessingStage.ANALYZING)
            
            if not state.line_message:
                raise ValueError("分析対象のメッセージがありません")
            
            # メッセージタイプに応じた分析
            if state.line_message.message_type == MessageType.TEXT:
                result = await self._analyze_text_message(state)
                
            elif state.line_message.message_type == MessageType.IMAGE:
                result = await self._analyze_image_message(state)
                
            elif state.line_message.message_type == MessageType.VIDEO:
                result = await self._analyze_video_message(state)
                
            else:
                raise ValueError(f"サポートされていないメッセージタイプ: {state.line_message.message_type}")
            
            if not result.get('success'):
                raise Exception(f"Gemini 分析失敗: {result.get('error')}")
            
            # 分析結果を状態に保存
            state.set_gemini_analysis(
                title=result.get('title', ''),
                content=result.get('content', ''),
                summary=result.get('summary', ''),
                tags=result.get('tags', []),
                analysis_type=state.line_message.message_type.value,
                confidence=result.get('confidence', 0.8)
            )
            
            processing_time = time.time() - start_time
            state.processing_time += processing_time
            
            logger.info(f"Gemini 分析処理完了: {processing_time:.2f}秒")
            return state
            
        except Exception as e:
            state.add_error(ProcessingStage.ANALYZING, "GeminiAnalysisError", str(e))
            logger.error(f"Gemini 分析エラー: {e}")
            return state
    
    async def generate_article(self, state: AgentState) -> AgentState:
        """記事生成処理ノード"""
        start_time = time.time()
        
        try:
            logger.info(f"記事生成処理開始: {state.session_id}")
            state.update_stage(ProcessingStage.GENERATING)
            
            if not state.gemini_analysis:
                raise ValueError("Gemini 分析結果がありません")
            
            # 既に記事が生成されている場合はスキップ
            if state.gemini_analysis.content:
                logger.info("記事は既に生成済みです")
                processing_time = time.time() - start_time
                state.processing_time += processing_time
                return state
            
            # 追加のコンテキスト情報を準備
            context = self._prepare_context(state)
            
            # 記事生成スタイルを決定
            style = state.config.get('article_style', 'blog')
            
            # Gemini で記事生成
            source_content = state.line_message.content or f"ファイル分析結果: {state.gemini_analysis.summary}"
            
            result = await self.mcp_client.call_gemini_generate_article(
                content=source_content,
                style=style,
                context=context
            )
            
            if not result.get('success'):
                raise Exception(f"記事生成失敗: {result.get('error')}")
            
            # 記事情報を更新
            state.gemini_analysis.title = result.get('title', state.gemini_analysis.title)
            state.gemini_analysis.content = result.get('content', '')
            state.gemini_analysis.summary = result.get('summary', state.gemini_analysis.summary)
            state.gemini_analysis.tags = result.get('tags', state.gemini_analysis.tags)
            
            processing_time = time.time() - start_time
            state.processing_time += processing_time
            
            logger.info(f"記事生成処理完了: {processing_time:.2f}秒")
            return state
            
        except Exception as e:
            state.add_error(ProcessingStage.GENERATING, "ArticleGenerationError", str(e))
            logger.error(f"記事生成エラー: {e}")
            return state
    
    async def upload_images_if_needed(self, state: AgentState) -> AgentState:
        """画像アップロード処理ノード（必要時のみ）"""
        start_time = time.time()
        
        try:
            logger.info(f"画像アップロード処理開始: {state.session_id}")
            state.update_stage(ProcessingStage.UPLOADING_IMAGES)
            
            # 画像アップロードが必要かチェック
            if not self._needs_image_upload(state):
                logger.info("画像アップロードは不要です")
                processing_time = time.time() - start_time
                state.processing_time += processing_time
                return state
            
            # 画像ファイルのアップロード
            if state.line_message.message_type == MessageType.IMAGE and state.line_message.file_path:
                
                # Imgur にアップロード
                result = await self.mcp_client.call_imgur_upload(
                    image_path=state.line_message.file_path,
                    title=state.gemini_analysis.title if state.gemini_analysis else "LINE画像",
                    description=state.gemini_analysis.summary if state.gemini_analysis else "",
                    privacy="hidden"
                )
                
                if result.get('success'):
                    state.add_imgur_upload(
                        imgur_url=result.get('imgur_url'),
                        imgur_id=result.get('imgur_id'),
                        delete_hash=result.get('delete_hash'),
                        title=result.get('title'),
                        success=True
                    )
                    
                    # 記事内容に画像URLを追加
                    if state.gemini_analysis and state.imgur_uploads:
                        img_url = state.imgur_uploads[-1].imgur_url
                        state.gemini_analysis.content += f"\\n\\n![画像]({img_url})"
                    
                    logger.info(f"画像アップロード成功: {result.get('imgur_url')}")
                else:
                    logger.warning(f"画像アップロード失敗: {result.get('error')}")
                    state.add_imgur_upload(
                        imgur_url="",
                        imgur_id="",
                        delete_hash="",
                        title="",
                        success=False,
                        error=result.get('error')
                    )
            
            processing_time = time.time() - start_time
            state.processing_time += processing_time
            
            logger.info(f"画像アップロード処理完了: {processing_time:.2f}秒")
            return state
            
        except Exception as e:
            state.add_error(ProcessingStage.UPLOADING_IMAGES, "ImageUploadError", str(e))
            logger.error(f"画像アップロードエラー: {e}")
            return state
    
    async def publish_to_hatena(self, state: AgentState) -> AgentState:
        """はてなブログ投稿処理ノード"""
        start_time = time.time()
        
        try:
            logger.info(f"はてなブログ投稿処理開始: {state.session_id}")
            state.update_stage(ProcessingStage.PUBLISHING)
            
            if not state.gemini_analysis:
                raise ValueError("投稿する記事がありません")
            
            if not state.gemini_analysis.content:
                raise ValueError("記事の内容が生成されていません")
            
            # 投稿設定
            title = state.gemini_analysis.title or "AI生成記事"
            content = state.gemini_analysis.content
            tags = state.gemini_analysis.tags or ["AI生成", "LINE Bot"]
            category = state.config.get('blog_category', '日記')
            draft = state.config.get('publish_as_draft', False)
            
            # はてなブログに投稿
            result = await self.mcp_client.call_hatena_publish_article(
                title=title,
                content=content,
                tags=tags,
                category=category,
                draft=draft
            )
            
            if not result.get('success'):
                raise Exception(f"はてなブログ投稿失敗: {result.get('error')}")
            
            # 投稿結果を状態に保存
            state.set_hatena_post(
                article_id=result.get('article_id', ''),
                url=result.get('url', ''),
                title=title,
                tags=tags,
                category=category,
                draft=draft,
                success=True
            )
            
            processing_time = time.time() - start_time
            state.processing_time += processing_time
            
            logger.info(f"はてなブログ投稿完了: {result.get('url')} ({processing_time:.2f}秒)")
            return state
            
        except Exception as e:
            state.add_error(ProcessingStage.PUBLISHING, "HatenaPublishError", str(e))
            logger.error(f"はてなブログ投稿エラー: {e}")
            return state
    
    async def notify_user(self, state: AgentState) -> AgentState:
        """ユーザー通知処理ノード"""
        start_time = time.time()
        
        try:
            logger.info(f"ユーザー通知処理開始: {state.session_id}")
            state.update_stage(ProcessingStage.NOTIFYING)
            
            # 通知メッセージを作成
            message = self._create_notification_message(state)
            
            # LINE でユーザーに通知
            if state.user_id:
                result = await self.mcp_client.call_line_send_message(
                    user_id=state.user_id,
                    message=message
                )
                
                if not result.get('success'):
                    logger.warning(f"通知送信失敗: {result.get('error')}")
                else:
                    logger.info("通知送信成功")
            
            # 処理完了
            state.update_stage(ProcessingStage.COMPLETED)
            
            processing_time = time.time() - start_time
            state.processing_time += processing_time
            
            total_time = state.processing_time
            logger.info(f"全体処理完了: {total_time:.2f}秒")
            
            return state
            
        except Exception as e:
            state.add_error(ProcessingStage.NOTIFYING, "NotificationError", str(e))
            logger.error(f"通知エラー: {e}")
            return state
    
    async def handle_error(self, state: AgentState) -> AgentState:
        """エラーハンドリングノード"""
        try:
            logger.info(f"エラーハンドリング開始: {state.session_id}")
            
            # リトライ可能かチェック
            if state.can_retry():
                state.increment_retry()
                logger.info(f"リトライ実行: {state.retry_count}/{state.max_retries}")
                
                # エラーステージに応じて適切なノードに戻る
                last_error = state.errors[-1] if state.errors else None
                if last_error:
                    if last_error.stage == ProcessingStage.ANALYZING:
                        state.update_stage(ProcessingStage.RECEIVED)
                    elif last_error.stage == ProcessingStage.GENERATING:
                        state.update_stage(ProcessingStage.ANALYZING)
                    elif last_error.stage == ProcessingStage.UPLOADING_IMAGES:
                        state.update_stage(ProcessingStage.GENERATING)
                    elif last_error.stage == ProcessingStage.PUBLISHING:
                        state.update_stage(ProcessingStage.UPLOADING_IMAGES)
                    else:
                        state.update_stage(ProcessingStage.RECEIVED)
                
                return state
            else:
                # 最大リトライ数に達した場合
                state.update_stage(ProcessingStage.FAILED)
                
                # エラー通知をユーザーに送信
                error_message = self._create_error_message(state)
                if state.user_id:
                    try:
                        await self.mcp_client.call_line_send_message(
                            user_id=state.user_id,
                            message=error_message
                        )
                    except Exception as notify_error:
                        logger.error(f"エラー通知送信失敗: {notify_error}")
                
                logger.error(f"処理失敗（最大リトライ数到達）: {state.session_id}")
                return state
        
        except Exception as e:
            logger.error(f"エラーハンドリング自体でエラー: {e}")
            state.update_stage(ProcessingStage.FAILED)
            return state
    
    # ヘルパーメソッド
    
    async def _analyze_text_message(self, state: AgentState) -> Dict[str, Any]:
        """テキストメッセージの分析"""
        return await self.mcp_client.call_gemini_generate_article(
            content=state.line_message.content,
            style="blog"
        )
    
    async def _analyze_image_message(self, state: AgentState) -> Dict[str, Any]:
        """画像メッセージの分析"""
        # 画像分析 + 記事生成
        analysis_result = await self.mcp_client.call_gemini_analyze_image(
            image_path=state.line_message.file_path,
            prompt="この画像について詳しく分析し、興味深いブログ記事のネタを提供してください"
        )
        
        if analysis_result.get('success'):
            # 分析結果をもとに記事生成
            return await self.mcp_client.call_gemini_generate_article(
                content=analysis_result.get('analysis', ''),
                style="blog",
                context="画像分析結果をもとにした記事"
            )
        else:
            return analysis_result
    
    async def _analyze_video_message(self, state: AgentState) -> Dict[str, Any]:
        """動画メッセージの分析（現在は簡易版）"""
        # 動画ファイル情報をもとに記事生成
        import os
        filename = os.path.basename(state.line_message.file_path)
        
        return await self.mcp_client.call_gemini_generate_article(
            content=f"動画ファイル '{filename}' に関するコンテンツ",
            style="blog",
            context="動画ファイルの投稿"
        )
    
    def _prepare_context(self, state: AgentState) -> str:
        """記事生成用のコンテキスト情報を準備"""
        context_parts = []
        
        if state.line_message:
            context_parts.append(f"投稿タイプ: {state.line_message.message_type.value}")
            context_parts.append(f"投稿時刻: {state.line_message.timestamp}")
        
        if state.config.get('user_preferences'):
            context_parts.append(f"ユーザー設定: {state.config['user_preferences']}")
        
        return " | ".join(context_parts)
    
    def _needs_image_upload(self, state: AgentState) -> bool:
        """画像アップロードが必要かチェック"""
        return (
            state.line_message and
            state.line_message.message_type == MessageType.IMAGE and
            state.line_message.file_path and
            len(state.imgur_uploads) == 0  # まだアップロードしていない
        )
    
    def _create_notification_message(self, state: AgentState) -> str:
        """通知メッセージを作成"""
        if state.hatena_post and state.hatena_post.success:
            return f"""🎉 ブログ記事が投稿されました！

📝 タイトル: {state.hatena_post.title}
🔗 URL: {state.hatena_post.url}
🏷️ タグ: {', '.join(state.hatena_post.tags)}
⏱️ 処理時間: {state.processing_time:.1f}秒

記事をお楽しみください！"""
        else:
            return "記事の投稿処理が完了しましたが、詳細な結果を確認できませんでした。"
    
    def _create_error_message(self, state: AgentState) -> str:
        """エラーメッセージを作成"""
        error_count = len(state.errors)
        last_error = state.errors[-1] if state.errors else None
        
        message = f"""❌ 記事投稿処理でエラーが発生しました

🔄 試行回数: {state.retry_count}/{state.max_retries}
📊 エラー数: {error_count}"""

        if last_error:
            message += f"\\n⚠️ 最新エラー: {last_error.error_message}"
        
        message += "\\n\\n申し訳ございません。しばらく時間をおいて再度お試しください。"
        
        return message
