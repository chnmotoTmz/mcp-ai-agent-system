"""
バッチ処理サービス
1分間のメッセージを統合して記事化
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from ..database import db, Message, MessageBuffer, Article
from ..services.google_photos_service import GooglePhotosService  # Google Photosに変更
from ..services.hatena_service import HatenaService
from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class BatchProcessingService:
    """バッチ処理サービス"""
    
    def __init__(self):
        self.google_photos_service = GooglePhotosService()  # Google Photosに変更
        self.hatena_service = HatenaService()
        self.gemini_service = GeminiService()
    
    def create_message_buffer(self, user_id: str) -> MessageBuffer:
        """
        新しいメッセージバッファを作成
        
        Args:
            user_id: ユーザーID
            
        Returns:
            MessageBuffer: 作成されたバッファ
        """
        buffer_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        buffer = MessageBuffer(
            buffer_id=buffer_id,
            user_id=user_id,
            start_time=datetime.now(),
            status='collecting'
        )
        
        db.session.add(buffer)
        db.session.commit()
        
        logger.info(f"Created message buffer: {buffer_id}")
        return buffer
    
    def get_active_buffer(self, user_id: str) -> MessageBuffer:
        """
        アクティブなメッセージバッファを取得（なければ作成）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            MessageBuffer: アクティブなバッファ
        """
        # 1分以内の未処理バッファを検索
        cutoff_time = datetime.now() - timedelta(minutes=1)
        
        buffer = MessageBuffer.query.filter_by(
            user_id=user_id,
            status='collecting'
        ).filter(
            MessageBuffer.start_time > cutoff_time
        ).order_by(MessageBuffer.start_time.desc()).first()
        
        if buffer is None:
            # 新しいバッファを作成
            buffer = self.create_message_buffer(user_id)
        
        return buffer
    
    def add_message_to_buffer(self, message: Message) -> MessageBuffer:
        """
        メッセージをバッファに追加
        
        Args:
            message: 追加するメッセージ
            
        Returns:
            MessageBuffer: 更新されたバッファ
        """
        buffer = self.get_active_buffer(message.user_id)
        
        # メッセージIDをバッファに追加
        message_ids = buffer.get_message_ids_list()
        if message.id not in message_ids:
            message_ids.append(message.id)
            buffer.set_message_ids_list(message_ids)
            
            # カウンターを更新
            buffer.message_count = len(message_ids)
            if message.message_type == 'text':
                buffer.text_count += 1
            elif message.message_type == 'image':
                buffer.image_count += 1
        
        db.session.commit()
        logger.info(f"Added message {message.id} to buffer {buffer.buffer_id}")
        
        return buffer
    
    def get_expired_buffers(self) -> List[MessageBuffer]:
        """
        処理対象の期限切れバッファを取得
        
        Returns:
            List[MessageBuffer]: 処理対象のバッファリスト
        """
        cutoff_time = datetime.now() - timedelta(minutes=1)
        
        buffers = MessageBuffer.query.filter_by(
            status='collecting'
        ).filter(
            MessageBuffer.start_time <= cutoff_time
        ).all()
        
        return buffers
    
    def process_buffer(self, buffer: MessageBuffer) -> Dict[str, Any]:
        """
        バッファの内容を処理して記事を生成
        
        Args:
            buffer: 処理するバッファ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        try:
            logger.info(f"Processing buffer: {buffer.buffer_id}")
            
            # バッファステータスを更新
            buffer.status = 'processing'
            buffer.end_time = datetime.now()
            db.session.commit()
            
            # バッファ内のメッセージを取得
            message_ids = buffer.get_message_ids_list()
            if not message_ids:
                logger.warning(f"No messages in buffer {buffer.buffer_id}")
                buffer.status = 'completed'
                buffer.error_message = 'No messages to process'
                db.session.commit()
                return {'success': False, 'error': 'No messages'}
            
            messages = Message.query.filter(Message.id.in_(message_ids)).order_by(Message.created_at).all()
            
            # メッセージを分類
            text_messages = [m for m in messages if m.message_type == 'text']
            image_messages = [m for m in messages if m.message_type == 'image']
            
            logger.info(f"Processing {len(text_messages)} text messages and {len(image_messages)} images")
            
            # 画像をImgurにアップロード
            image_tags = []
            uploaded_images = []
            
            if image_messages:
                for img_msg in image_messages:
                    logger.info(f"Processing image message: ID={img_msg.id}, file_path={img_msg.file_path}")
                    
                    if not img_msg.file_path:
                        logger.warning(f"Image message {img_msg.id} has no file_path")
                        continue
                        
                    if not os.path.exists(img_msg.file_path):
                        logger.error(f"Image file not found: {img_msg.file_path}")
                        # ファイルが存在しない場合のデバッグ情報
                        logger.error(f"Current working directory: {os.getcwd()}")
                        logger.error(f"Uploads directory exists: {os.path.exists('uploads')}")
                        if os.path.exists('uploads'):
                            logger.error(f"Files in uploads: {os.listdir('uploads')}")
                        continue
                        
                    logger.info(f"Image file found: {img_msg.file_path}, size: {os.path.getsize(img_msg.file_path)} bytes")
                    
                    # Imgur MCP経由で画像をアップロード
                    try:
                        import asyncio
                        import sys
                        sys.path.append('/home/moto/line-gemini-hatena-integration')
                        from src.services.pipedream_imgur_service import PipedreamImgurService
                        
                        # Pipedream MCP経由でアップロード
                        pipedream_imgur = PipedreamImgurService()
                        upload_result = asyncio.run(pipedream_imgur.upload_image(
                            image_path=img_msg.file_path,
                            title=f"Batch_Image_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            description="LINE Bot バッチ処理経由でアップロード（個人アカウント）",
                            privacy="hidden"
                        ))
                        
                        if upload_result.get('success'):
                            # Imgur URLを使用してHTMLタグを作成
                            image_url = upload_result.get('url')
                            image_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{image_url}" alt="アップロード画像" style="max-width: 80%; height: auto; border: 1px solid #ddd; border-radius: 8px;" /></div>'
                            
                            image_tags.append(image_tag)
                            uploaded_images.append({
                                'message_id': img_msg.id,
                                'image_tag': image_tag,
                                'url': image_url,
                                'imgur_id': upload_result.get('imgur_id'),
                                'delete_hash': upload_result.get('delete_hash'),
                                'source': 'pipedream_mcp'
                            })
                            logger.info(f"Pipedream Imgur アップロード成功: {image_url}")
                            logger.info(f"個人アカウント紐付け: {upload_result.get('imgur_id')}")
                        else:
                            logger.error(f"Pipedream Imgur アップロード失敗: {upload_result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Pipedream Imgur アップロードエラー: {e}")
                        # フォールバック: 自作MCPを使用
                        logger.info("フォールバック: 自作Imgur MCPを使用")
                        try:
                            from src.mcp_servers.imgur_server_fastmcp import upload_image
                            upload_result = asyncio.run(upload_image(
                                image_path=img_msg.file_path,
                                title=f"Batch_Image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_fallback",
                                description="LINE Bot バッチ処理経由（フォールバック）",
                                privacy="hidden"
                            ))
                            if upload_result.get('success'):
                                image_url = upload_result.get('url')
                                image_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{image_url}" alt="アップロード画像" style="max-width: 80%; height: auto; border: 1px solid #ddd; border-radius: 8px;" /></div>'
                                image_tags.append(image_tag)
                                logger.info(f"フォールバック成功: {image_url}")
                        except Exception as fallback_error:
                            logger.error(f"フォールバックも失敗: {fallback_error}")
                        # フォールバック: ローカルファイルとして処理
                        logger.info("Falling back to local file processing")
            
            # テキストコンテンツを統合
            combined_text = self._combine_text_messages(text_messages)
            
            # 画像パスを収集（Imgur URLではなくローカルパス）
            image_paths = []
            for img_msg in image_messages:
                if img_msg.file_path and os.path.exists(img_msg.file_path):
                    image_paths.append(img_msg.file_path)
            
            # Geminiで記事を生成（画像解析付き）
            article_content = self._generate_article_with_gemini(
                combined_text, 
                image_paths,  # ローカルファイルパスを渡す
                len(text_messages), 
                len(image_messages)
            )
            
            if not article_content:
                raise Exception("Failed to generate article content")
            
            # はてなブログに投稿
            hatena_result = self._publish_to_hatena(article_content, image_tags)
            
            # Articleレコードを作成
            article = Article(
                title=article_content.get('title', 'バッチ生成記事'),
                content=article_content.get('content', ''),
                summary=article_content.get('summary', ''),
                source_messages=buffer.message_ids,
                published=hatena_result.get('success', False),
                hatena_entry_id=hatena_result.get('entry_id'),
                hatena_url=hatena_result.get('url'),
                status='completed' if hatena_result.get('success') else 'failed'
            )
            
            # タグを設定
            tags = article_content.get('tags', [])
            if uploaded_images:
                tags.append('画像付き')
            tags.append('バッチ処理')
            article.set_tags_list(tags)
            
            # 画像パスを設定
            if uploaded_images:
                image_data = [img['url'] for img in uploaded_images]
                article.set_image_paths_list(image_data)
            
            db.session.add(article)
            db.session.flush()  # IDを取得
            
            # バッファを完了状態に更新
            buffer.status = 'completed'
            buffer.processed_at = datetime.now()
            buffer.article_id = article.id
            
            # メッセージを処理済みに更新
            for message in messages:
                message.processed = True
            
            db.session.commit()
            
            logger.info(f"Buffer processing completed: {buffer.buffer_id} -> Article {article.id}")
            
            return {
                'success': True,
                'buffer_id': buffer.buffer_id,
                'article_id': article.id,
                'hatena_url': hatena_result.get('url'),
                'message_count': len(messages),
                'image_count': len(uploaded_images)
            }
            
        except Exception as e:
            logger.error(f"Failed to process buffer {buffer.buffer_id}: {e}")
            
            # エラー状態に更新
            buffer.status = 'failed'
            buffer.error_message = str(e)
            buffer.processed_at = datetime.now()
            db.session.commit()
            
            return {
                'success': False,
                'buffer_id': buffer.buffer_id,
                'error': str(e)
            }
    
    def _combine_text_messages(self, text_messages: List[Message]) -> str:
        """
        テキストメッセージを統合
        
        Args:
            text_messages: テキストメッセージのリスト
            
        Returns:
            str: 統合されたテキスト
        """
        if not text_messages:
            return ""
        
        # 時系列順にテキストを結合
        combined_texts = []
        for msg in text_messages:
            timestamp = msg.created_at.strftime('%H:%M')
            combined_texts.append(f"[{timestamp}] {msg.content}")
        
        return "\n\n".join(combined_texts)
    
    def _generate_article_with_gemini(self, text_content: str, image_paths: List[str], 
                                    text_count: int, image_count: int) -> Dict[str, Any]:
        """
        Geminiで記事コンテンツを生成（画像解析込み）
        
        Args:
            text_content: 統合されたテキスト
            image_paths: 画像ファイルパスのリスト（Imgur URLは含めない）
            text_count: テキストメッセージ数
            image_count: 画像数
            
        Returns:
            Dict[str, Any]: 生成された記事データ
        """
        try:
            logger.info(f"Gemini記事生成開始: テキスト{text_count}件, 画像{image_count}件")
            
            # 画像解析指示（画像URLではなく解析内容を含める）
            image_analysis = ""
            if image_paths:
                image_analysis = f"\n\n【画像数】{len(image_paths)}枚の画像があります。"
                logger.info(f"画像解析対象: {image_paths}")
            
            prompt = f"""
以下の情報から、ブログ記事を作成してください：

【メッセージ内容】
{text_content}{image_analysis}

【重要な要求事項】
1. タイトルは15文字以内で簡潔にしてください
2. 本文は200文字以上で読みやすく構成してください
3. 画像がある場合は「[画像{i+1}]」という形式で挿入位置を指定してください
4. 適切なタグを3-5個提案してください

【出力形式（必ず以下の通りに出力してください）】
タイトル: [ここに15文字以内のタイトルのみ]

本文:
[ここに本文のみを記述。画像挿入位置は[画像1][画像2]の形式で指定]

要約: [ここに50文字程度の要約のみ]

タグ: [タグ1, タグ2, タグ3]
"""
            
            # Geminiで生成（画像解析付き）
            if image_paths:
                # 画像ファイルも一緒に送信してGeminiで解析
                content = self.gemini_service.generate_content_with_images(prompt, image_paths)
                logger.info("Gemini: 画像解析付きで記事生成")
            else:
                content = self.gemini_service.generate_content(prompt)
                logger.info("Gemini: テキストのみで記事生成")
            
            if not content:
                raise Exception("Gemini generation failed: Empty response")
            logger.info(f"Gemini response received: {content[:200]}...")
            
            # レスポンスを解析
            article_data = self._parse_gemini_response(content, image_tags)
            
            logger.info(f"Article data before image check: title='{article_data['title']}', content_length={len(article_data['content'])}")
            
            # 画像タグが本文に含まれていない場合は追加
            if image_tags and not any(tag in article_data['content'] for tag in image_tags):
                article_data['content'] += "\n\n" + "\n".join(image_tags)
                logger.info("Added image tags to content")
                logger.info(f"Image tags added: {image_tags}")
            else:
                logger.info(f"Image tags already in content or no image tags: {len(image_tags)} tags")
            
            return article_data
            
        except Exception as e:
            logger.error(f"Failed to generate article with Gemini: {e}")
            
            # フォールバック: シンプルな記事を生成
            fallback_title = f"記録 {datetime.now().strftime('%m月%d日 %H:%M')}"
            fallback_content = f"<h2>メッセージ記録</h2>\n{text_content.replace(chr(10), '<br>')}"
            
            if image_tags:
                fallback_content += "\n\n<h2>画像</h2>\n" + "\n".join(image_tags)
            
            return {
                'title': fallback_title,
                'content': fallback_content,
                'summary': f"{text_count}件のメッセージと{image_count}枚の画像から生成",
                'tags': ['日記', 'メモ', 'バッチ処理']
            }
    
    def _parse_gemini_response(self, content: str, image_tags: List[str] = None) -> Dict[str, Any]:
        """
        Geminiレスポンスを解析
        
        Args:
            content: Geminiからの回答
            image_tags: 画像タグのリスト
            
        Returns:
            Dict[str, Any]: 解析された記事データ
        """
        try:
            logger.info(f"Parsing Gemini response: {len(content)} characters")
            
            article_data = {
                'title': '',
                'content': '',
                'summary': '',
                'tags': []
            }
            
            # より柔軟なパーサー実装
            sections = content.split('\n\n')
            current_section = None
            content_lines = []
            
            # 改行で分割して行ごとに処理
            lines = content.strip().split('\n')
            current_section = None
            content_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # タイトルの検出（複数パターン対応）
                if (line.startswith('タイトル:') or line.startswith('- タイトル:') or 
                    line.startswith('■タイトル') or line.startswith('**タイトル')):
                    title = line.split(':', 1)[-1].strip()
                    title = title.replace('*', '').replace('#', '').replace('[', '').replace(']', '').strip()
                    # タイトルの長さ制限と改行削除
                    title = title.split('\n')[0]  # 最初の行のみ取得
                    if len(title) > 30:
                        title = title[:27] + "..."
                    article_data['title'] = title
                    logger.info(f"Found title: {title}")
                
                # 本文の検出
                elif (line.startswith('本文:') or line.startswith('- 本文:') or 
                      line.startswith('内容:') or line.startswith('- 内容:')):
                    current_section = 'content'
                    # 同じ行に内容がある場合
                    if ':' in line:
                        content_part = line.split(':', 1)[1].strip()
                        if content_part:
                            content_lines.append(content_part)
                
                # 要約の検出
                elif (line.startswith('要約:') or line.startswith('- 要約:') or
                      line.startswith('■要約') or line.startswith('**要約')):
                    if current_section == 'content' and content_lines:
                        article_data['content'] = '\n'.join(content_lines).strip()
                        content_lines = []
                        current_section = None
                    
                    summary = line.split(':', 1)[-1].strip()
                    summary = summary.replace('*', '').replace('#', '').strip()
                    article_data['summary'] = summary
                    logger.info(f"Found summary: {summary}")
                
                # タグの検出
                elif (line.startswith('タグ:') or line.startswith('- タグ:') or
                      line.startswith('■タグ') or line.startswith('**タグ')):
                    if current_section == 'content' and content_lines:
                        article_data['content'] = '\n'.join(content_lines).strip()
                        content_lines = []
                        current_section = None
                    
                    tags_str = line.split(':', 1)[-1].strip()
                    tags_str = tags_str.replace('*', '').replace('#', '').strip()
                    # タグの解析（複数の区切り文字に対応）
                    tags = []
                    for delimiter in [',', '、', '#']:
                        if delimiter in tags_str:
                            tags = [tag.strip() for tag in tags_str.split(delimiter) if tag.strip()]
                            break
                    if not tags and tags_str:
                        tags = [tags_str]
                    
                    article_data['tags'] = tags[:5]  # 最大5個まで
                    logger.info(f"Found tags: {tags}")
                
                # 本文の内容を収集
                elif current_section == 'content':
                    content_lines.append(line)
                elif not current_section and line and not any(line.startswith(prefix) for prefix in ['タイトル:', '要約:', 'タグ:', '本文:', '- ', '■', '**']):
                    # セクションが決まっていない場合で、ヘッダー行でない場合は本文として扱う
                    if not article_data['title'] and not article_data['summary'] and not article_data['tags']:
                        content_lines.append(line)
            
            # 最後のセクションを処理
            if current_section == 'content' and content_lines:
                article_data['content'] = '\n'.join(content_lines).strip()

            
            # デフォルト値の設定
            if not article_data['title']:
                article_data['title'] = f"記録 {datetime.now().strftime('%m月%d日 %H:%M')}"
                logger.warning("No title found, using default")
            
            if not article_data['content']:
                # フォールバック: 元のコンテンツから本文を抽出
                article_data['content'] = self._extract_content_fallback(content)
                logger.warning("No content found, using fallback extraction")
            
            if not article_data['summary']:
                article_data['summary'] = "自動生成された記事です"
            
            if not article_data['tags']:
                article_data['tags'] = ['AI生成', 'ブログ', '記事']
            
            logger.info(f"Parsed article: title='{article_data['title']}', content_length={len(article_data['content'])}")
            return article_data
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Raw content: {content[:500]}...")
            
            # 完全フォールバック
            return {
                'title': f"記録 {datetime.now().strftime('%m月%d日 %H:%M')}",
                'content': self._extract_content_fallback(content),
                'summary': '自動生成された記事',
                'tags': ['AI生成', 'バッチ処理']
            }
    
    def _extract_content_fallback(self, content: str) -> str:
        """
        フォールバック用のコンテンツ抽出
        """
        try:
            # 明らかにヘッダー部分でない行を抽出
            lines = content.split('\n')
            content_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # ヘッダー行をスキップ
                if (line.startswith('タイトル:') or line.startswith('本文:') or 
                    line.startswith('要約:') or line.startswith('タグ:') or
                    line.startswith('- ') or line.startswith('■') or
                    line.startswith('**') or line.startswith('##')):
                    continue
                
                content_lines.append(line)
            
            if content_lines:
                return '<p>' + '</p>\n<p>'.join(content_lines) + '</p>'
            else:
                return '<p>記事の内容を生成しました。</p>'
                
        except Exception as e:
            logger.error(f"Fallback content extraction failed: {e}")
            return '<p>記事内容の生成に失敗しました。</p>'
    
    def _publish_to_hatena(self, article_data: Dict[str, Any], image_tags: List[str]) -> Dict[str, Any]:
        """
        はてなブログに記事を投稿
        
        Args:
            article_data: 記事データ
            image_tags: 画像タグ
            
        Returns:
            Dict[str, Any]: 投稿結果
        """
        try:
            # 記事データの確認とログ出力
            title = article_data.get('title', 'バッチ生成記事')
            content = article_data.get('content', '')
            tags = article_data.get('tags', [])
            
            logger.info(f"Publishing to Hatena - Title: '{title}', Content length: {len(content)}, Tags: {tags}")
            
            # タイトルの長さ制限
            if len(title) > 100:
                title = title[:97] + "..."
                logger.warning(f"Title truncated to: '{title}'")
            
            # はてなブログに投稿
            result = self.hatena_service.publish_article(
                title=title,
                content=content,
                tags=tags,
                draft=False  # 公開記事として投稿
            )
            
            if result:
                logger.info(f"Successfully published to Hatena: {result.get('url')}")
                return {
                    'success': True,
                    'entry_id': result.get('id'),
                    'url': result.get('url'),
                    'title': title,
                    'content': content
                }
            else:
                logger.error("Failed to publish to Hatena: No result returned")
                return {
                    'success': False,
                    'error': 'No result returned from publish_article'
                }
            
        except Exception as e:
            logger.error(f"Failed to publish to Hatena: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_all_expired_buffers(self) -> List[Dict[str, Any]]:
        """
        すべての期限切れバッファを処理
        
        Returns:
            List[Dict[str, Any]]: 処理結果のリスト
        """
        expired_buffers = self.get_expired_buffers()
        results = []
        
        logger.info(f"Processing {len(expired_buffers)} expired buffers")
        
        for buffer in expired_buffers:
            try:
                result = self.process_buffer(buffer)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process buffer {buffer.buffer_id}: {e}")
                results.append({
                    'success': False,
                    'buffer_id': buffer.buffer_id,
                    'error': str(e)
                })
        
        return results
