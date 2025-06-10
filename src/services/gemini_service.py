"""
Gemini AI Service - 新API対応版
Gemini APIを使用してメッセージから記事を生成（マルチモーダル対応）
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from PIL import Image
import google.generativeai as genai

from src.config import Config
from src.database import db, Message, Article

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        self.vision_model = genai.GenerativeModel(Config.GEMINI_MODEL)
    
    def generate_content(self, text: str) -> Optional[str]:
        """シンプルなテキストからコンテント生成（リトライ機能付き）"""
        import time
        
        # Gemini APIがエラーの場合のフォールバック処理
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Gemini API呼び出し試行 {attempt + 1}/{max_retries}")
                
                response = self.model.generate_content(f"""
以下のテキストメッセージをもとに、ブログ記事を作成してください。

メッセージ内容:
{text}

要求事項:
- 読みやすく、興味深い記事にしてください
- 適切なタイトルを付けてください
- 記事の本文を作成してください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文は必ずHTML形式で記述してください（マークダウンは使用禁止）
- HTMLタグを使用してください: <p>、<br>、<strong>、<em>、<ul>、<li>、<h2>、<h3>など
- マークダウン記法（##、**、-など）は一切使用しないでください

以下の形式で回答してください:
タイトル: [記事タイトル]

本文:
[HTML形式の記事本文]
""")
                
                if response.text and response.text.strip():
                    logger.info(f"Gemini API成功: {len(response.text)}文字")
                    return response.text.strip()
                else:
                    logger.warning(f"Gemini API応答が空 (試行{attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Gemini API エラー (試行{attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数バックオフ
                    logger.info(f"{wait_time}秒待機後にリトライします")
                    time.sleep(wait_time)
                else:
                    logger.error("全ての試行が失敗しました")
        
        # 全試行失敗時のフォールバック
        logger.warning("Gemini API失敗、フォールバック記事を生成")
        return self._create_fallback_content(text)
    
    def _create_fallback_content(self, text: str) -> str:
        """Gemini API失敗時のフォールバック記事生成"""
        from datetime import datetime
        
        # 基本的な記事テンプレート
        current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        
        # テキストから最初の30文字を抽出してタイトルに
        lines = text.split('\n')
        first_line = lines[0] if lines else "投稿記事"
        title = first_line[:30] + ("..." if len(first_line) > 30 else "")
        
        # 本文を構築
        content_lines = []
        
        for line in lines:
            if line.strip():
                # 【画像解析結果】などの特殊タグを処理
                if "【画像解析結果】" in line:
                    image_desc = line.replace("【画像解析結果】", "").strip()
                    content_lines.append(f"<p>📸 {image_desc}</p>")
                elif "【メッセージ】" in line:
                    msg_content = line.replace("【メッセージ】", "").strip()
                    content_lines.append(f"<p>{msg_content}</p>")
                else:
                    content_lines.append(f"<p>{line.strip()}</p>")
        
        # 基本構造
        fallback_content = f"""タイトル: {title}

本文:
<div style="padding: 20px; border-left: 4px solid #007cba; background-color: #f9f9f9;">
<p><strong>📝 {current_time} の投稿</strong></p>
{''.join(content_lines)}
<p><small>※ AI生成サービスが一時的に利用できないため、シンプルな形式で投稿しています。</small></p>
</div>"""
        
        logger.info(f"フォールバック記事生成完了: {len(fallback_content)}文字")
        return fallback_content
    
    def analyze_image_for_blog(self, image_path: str, prompt: str = "この画像について詳しく説明してください") -> Optional[str]:
        """画像を分析してブログ記事を生成（新API対応）"""
        try:
            # Use PIL Image for compatibility
            image = Image.open(image_path)
            
            response = self.vision_model.generate_content([
                f"""
{prompt}

この画像について詳しく分析し、ブログ記事を作成してください。

要求事項:
- 画像の内容を詳細に説明してください
- 興味深い観点や背景情報を加えてください
- 適切なタイトルを付けてください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文は必ずHTML形式で記述してください（マークダウンは使用禁止）
- HTMLタグを使用してください: <p>、<br>、<strong>、<em>、<ul>、<li>、<h2>、<h3>など
- マークダウン記法（##、**、-など）は一切使用しないでください

以下の形式で回答してください:
タイトル: [記事タイトル]

本文:
[HTML形式の記事本文]
""",
                image
            ])
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"画像分析エラー: {e}")
            return None
    
    def analyze_video(self, video_path: str, prompt: str = "この動画について詳しく説明してください") -> Optional[str]:
        """動画を分析してコンテンツ生成（新API対応）"""
        try:
            # Upload video file using upload_file
            uploaded_file = genai.upload_file(video_path)
            
            response = self.model.generate_content([
                f"""
{prompt}

この動画について詳しく分析し、ブログ記事を作成してください。

分析ポイント:
- 動画の内容やシーンを詳細に描写
- 音声がある場合はその内容も分析
- 動きやアクションの説明
- 興味深い観点や背景情報を追加

要求事項:
- 本文は必ずHTML形式で記述してください（マークダウンは使用禁止）
- HTMLタグを使用してください: <p>、<br>、<strong>、<em>、<ul>、<li>、<h2>、<h3>など
- マークダウン記法（##、**、-など）は一切使用しないでください

以下の形式で回答してください:
タイトル: [記事タイトル]

本文:
[HTML形式の記事本文]
""",
                uploaded_file
            ])
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"動画分析エラー: {e}")
            return None
    
    def analyze_multiple_media(self, media_items: List[Dict], context_text: str = "") -> Optional[str]:
        """複数のメディアを統合的に分析（新機能）
        
        Args:
            media_items: [{'type': 'image', 'path': '...'}, {'type': 'video', 'path': '...'}]
            context_text: 関連するテキスト情報
        
        Returns:
            str: 統合分析結果
        """
        try:
            contents = []
            
            # コンテキストテキストがある場合は最初に追加
            if context_text:
                contents.append(f"関連テキスト: {context_text}")
            
            # 各メディアをコンテンツに追加
            for item in media_items:
                if item['type'] == 'image':
                    image = Image.open(item['path'])
                    contents.append(image)
                elif item['type'] == 'video':
                    uploaded_file = genai.upload_file(item['path'])
                    contents.append(uploaded_file)
            
            # 統合分析用のプロンプト
            contents.append(f"""
これらのメディアを統合的に分析し、一つの統一されたブログ記事を作成してください。

分析ポイント:
- 各メディアの内容を詳細に分析
- メディア間の関連性やストーリーを探る
- コンテキストテキストとの関連性を考慮
- 統一感のあるストーリーとして構成

以下の形式で回答してください:
タイトル: [統合記事のタイトル]

本文:
[統合記事の本文]
""")
            
            response = self.model.generate_content(contents)
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"複数メディア分析エラー: {e}")
            return None

    def create_blog_post(self, content: str, title_hint: str = "", tags: List[str] = None) -> Dict:
        """ブログ記事を作成（MCP対応）
        
        Args:
            content: 記事の元となるコンテンツ
            title_hint: タイトルのヒント
            tags: 記事のタグリスト
        
        Returns:
            dict: 作成されたブログ記事
        """
        try:
            # タグをデフォルト設定
            if tags is None:
                tags = ["AI生成", "ブログ"]
            
            # プロンプト作成
            prompt = f"""
以下の内容をもとに、魅力的なブログ記事を作成してください。

内容:
{content}

"""
            
            if title_hint:
                prompt += f"\nタイトルのヒント: {title_hint}\n"
            
            prompt += f"""
要求事項:
- 読みやすく、興味深い記事にしてください
- 適切なタイトルを付けてください（{title_hint}を参考に）
- 記事の要約も含めてください
- 関連するタグを提案してください（既存タグ: {', '.join(tags)}）
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）

以下の形式で回答してください:
タイトル: [記事タイトル]
要約: [記事の要約]
タグ: [タグ1], [タグ2], [タグ3]
本文:
[記事本文]
"""

            response = self.model.generate_content(prompt)
            
            if response.text:
                article_data = self._parse_article_response(response.text)
                
                # タグをマージ
                merged_tags = list(set(tags + article_data['tags']))
                article_data['tags'] = merged_tags
                
                return {
                    'title': article_data['title'],
                    'content': article_data['content'],
                    'summary': article_data['summary'],
                    'tags': article_data['tags'],
                    'category': '日記',  # デフォルトカテゴリ
                    'created_at': datetime.utcnow().isoformat()
                }
            else:
                raise ValueError("Geminiからの応答が空です")
                
        except Exception as e:
            logger.error(f"ブログ記事作成エラー: {e}")
            raise
    
    def generate_article_from_content(self, content: str, style: str = "blog") -> Dict:
        """コンテンツから記事を生成（MCP対応）
        
        Args:
            content: 元となるコンテンツ
            style: 記事のスタイル
        
        Returns:
            dict: 生成された記事
        """
        try:
            style_prompts = {
                'blog': '親しみやすいブログ記事',
                'news': 'ニュース記事風',
                'casual': 'カジュアルな文章',
                'formal': 'フォーマルな記事'
            }
            
            style_desc = style_prompts.get(style, 'ブログ記事')
            
            prompt = f"""
以下の内容をもとに、{style_desc}を作成してください。

内容:
{content}

要求事項:
- {style_desc}のスタイルで書いてください
- 読みやすく、魅力的な文章にしてください
- 適切なタイトルを付けてください
- 記事の要約も含めてください
- 関連するタグを3-5個提案してください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）

以下の形式で回答してください:
タイトル: [記事タイトル]
要約: [記事の要約]
タグ: [タグ1], [タグ2], [タグ3]
本文:
[記事本文]
"""

            response = self.model.generate_content(prompt)
            
            if response.text:
                article_data = self._parse_article_response(response.text)
                article_data['style'] = style
                return article_data
            else:
                raise ValueError("Geminiからの応答が空です")
                
        except Exception as e:
            logger.error(f"記事生成エラー: {e}")
            raise
    
    def create_integrated_article(self, text_content: str, image_analyses: List[str]) -> Optional[str]:
        """統合記事を作成（エラーハンドリング強化版）
        
        Args:
            text_content: 統合されたテキストコンテンツ
            image_analyses: 画像分析結果のリスト
        
        Returns:
            str: 生成された記事コンテンツ
        """
        try:
            # 統合プロンプトを作成
            prompt = f"""
以下の情報を基に、自然で読みやすいブログ記事を作成してください：

ユーザーのメッセージ：
{text_content if text_content else '（テキストメッセージなし）'}

画像の内容：
{chr(10).join(image_analyses) if image_analyses else '（画像なし）'}

要求事項：
- ユーザーのメッセージを主体として、画像の内容を自然に組み込んだ記事を作成してください
- 読みやすく、興味深い内容にしてください
- 適切なタイトルを付けてください
- 記事の本文を作成してください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）

以下の形式で回答してください：
タイトル: [記事タイトル]

本文:
[記事本文]
"""

            # APIキー設定確認
            if not hasattr(self, 'model') or self.model is None:
                logger.error("Geminiモデルが初期化されていません")
                return self._create_fallback_article(text_content, image_analyses)

            try:
                response = self.model.generate_content(prompt)
                
                if response and response.text and response.text.strip():
                    logger.info("統合記事生成成功")
                    return response.text.strip()
                else:
                    logger.warning("Geminiからの応答が空")
                    return self._create_fallback_article(text_content, image_analyses)
                    
            except Exception as api_error:
                logger.error(f"Gemini API呼び出しエラー: {api_error}")
                return self._create_fallback_article(text_content, image_analyses)
            
        except Exception as e:
            logger.error(f"統合記事作成で予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_article(text_content, image_analyses)
    
    def _create_fallback_article(self, text_content: str, image_analyses: List[str]) -> str:
        """フォールバック記事を作成
        
        Args:
            text_content: テキストコンテンツ
            image_analyses: 画像分析結果
            
        Returns:
            str: フォールバック記事
        """
        try:
            from datetime import datetime
            
            title = "投稿記事"
            if text_content and len(text_content.strip()) > 0:
                # テキストから簡単なタイトルを生成
                first_line = text_content.strip().split('\n')[0]
                if len(first_line) > 30:
                    title = first_line[:30] + "..."
                else:
                    title = first_line
            
            content_parts = []
            
            if text_content and text_content.strip():
                content_parts.append(text_content.strip())
            
            if image_analyses:
                content_parts.append("\n📸 画像について:")
                for i, analysis in enumerate(image_analyses, 1):
                    content_parts.append(f"{i}. {analysis}")
            
            if not content_parts:
                content_parts.append("投稿内容を処理中です...")
            
            article_content = f"タイトル: {title}\n\n本文:\n" + "\n".join(content_parts)
            
            logger.info("フォールバック記事を生成しました")
            return article_content
            
        except Exception as e:
            logger.error(f"フォールバック記事作成エラー: {e}")
            return "タイトル: 投稿記事\n\n本文:\n投稿を受信しましたが、処理中にエラーが発生しました。"
    
    def chat(self, message: str, context: str = "") -> str:
        """Geminiとチャット（MCP対応）
        
        Args:
            message: ユーザーメッセージ
            context: 追加のコンテキスト
        
        Returns:
            str: Geminiの応答
        """
        try:
            if context:
                prompt = f"コンテキスト: {context}\n\nユーザー: {message}"
            else:
                prompt = message
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            else:
                return "申し訳ございませんが、応答を生成できませんでした。"
                
        except Exception as e:
            logger.error(f"チャットエラー: {e}")
            return f"エラーが発生しました: {str(e)}"
    
    def get_model_info(self) -> Dict:
        """モデル情報を取得（MCP対応）
        
        Returns:
            dict: モデル情報
        """
        return {
            'model_name': Config.GEMINI_MODEL,
            'version': '1.0',
            'max_tokens': 30720,  # Gemini 1.5 Proの制限
            'capabilities': ['text_generation', 'image_analysis', 'chat']
        }
    
    def analyze_image(self, image_path: str, prompt: str = "この画像について詳しく説明してください") -> str:
        """画像を分析（リトライ機能付き・エラーハンドリング強化版）
        
        Args:
            image_path: 分析対象の画像パス
            prompt: 分析用のプロンプト
            
        Returns:
            str: 画像分析結果
        """
        import time
        
        try:
            from PIL import Image
            import google.generativeai as genai
            import os
            
            # ファイル存在チェック
            if not os.path.exists(image_path):
                logger.error(f"画像ファイルが存在しません: {image_path}")
                return "画像ファイルが見つかりません。"
            
            full_prompt = f"""
{prompt}

要求事項:
- 画像の内容を詳細に分析してください
- 客観的で正確な説明をしてください
- 興味深い観点があれば追加してください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 分析結果はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）
"""

            # リトライ機能付きで画像解析
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"画像解析試行 {attempt + 1}/{max_retries}: {image_path}")
                    
                    # メソッド1: upload_file を使用（推奨）
                    try:
                        # ファイルサイズチェック（20MB以下）
                        file_size = os.path.getsize(image_path)
                        if file_size > 20 * 1024 * 1024:
                            logger.warning(f"ファイルサイズが大きすぎます: {file_size} bytes")
                            raise ValueError("ファイルサイズが大きすぎます")
                        
                        # MIMEタイプを自動判定
                        mime_type = "image/jpeg"
                        if image_path.lower().endswith('.png'):
                            mime_type = "image/png"
                        elif image_path.lower().endswith('.webp'):
                            mime_type = "image/webp"
                        elif image_path.lower().endswith('.gif'):
                            mime_type = "image/gif"
                        
                        uploaded_file = genai.upload_file(image_path, mime_type=mime_type)
                        response = self.vision_model.generate_content([full_prompt, uploaded_file])
                        
                        if response and response.text:
                            logger.info("upload_file方式で画像分析成功")
                            return response.text.strip()
                        else:
                            logger.warning("upload_file方式でレスポンスが空")
                            raise ValueError("レスポンスが空です")
                            
                    except Exception as upload_error:
                        logger.warning(f"upload_file方式失敗: {upload_error}")
                        
                        # メソッド2: 直接PIL Image使用（フォールバック）
                        try:
                            logger.info("PIL Image方式にフォールバック")
                            image = Image.open(image_path)
                            
                            # 画像サイズが大きすぎる場合はリサイズ
                            max_size = (1024, 1024)
                            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                                logger.info(f"画像をリサイズしました: {image.size}")
                            
                            # RGBモードに変換（必要に応じて）
                            if image.mode != 'RGB':
                                image = image.convert('RGB')
                            
                            response = self.vision_model.generate_content([full_prompt, image])
                            
                            if response and response.text:
                                logger.info("PIL Image方式で画像分析成功")
                                return response.text.strip()
                            else:
                                logger.warning("PIL Image方式でレスポンスが空")
                                raise ValueError("レスポンスが空です")
                                
                        except Exception as pil_error:
                            logger.error(f"PIL Image方式も失敗: {pil_error}")
                            
                            # リトライ間隔
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt
                                logger.info(f"{wait_time}秒待機後にリトライします")
                                time.sleep(wait_time)
                            else:
                                # メソッド3: 簡易応答（最終フォールバック）
                                logger.info("簡易応答にフォールバック")
                                return "画像が添付されています（詳細分析は一時的に利用できません）"
                        
                except Exception as retry_error:
                    logger.error(f"リトライ {attempt + 1} 失敗: {retry_error}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"{wait_time}秒待機後にリトライします")
                        time.sleep(wait_time)
                    else:
                        logger.info("全試行失敗、簡易応答にフォールバック")
                        return "画像が添付されています（詳細分析は一時的に利用できません）"
            
        except Exception as e:
            logger.error(f"画像分析で予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
            return "画像分析中にエラーが発生しました"
    
    def generate_article_from_message(self, message: Message) -> Optional[Dict]:
        """単一メッセージから記事を生成"""
        try:
            if message.message_type == 'text':
                return self._generate_from_text(message)
            elif message.message_type == 'image':
                return self._generate_from_image(message)
            elif message.message_type == 'video':
                return self._generate_from_video(message)
            else:
                logger.warning(f"サポートされていないメッセージタイプ: {message.message_type}")
                return None
                
        except Exception as e:
            logger.error(f"記事生成エラー: {e}")
            return None
    
    def generate_article_from_messages(self, message_ids: List[int]) -> Optional[Dict]:
        """複数メッセージから記事を生成"""
        try:
            messages = Message.query.filter(Message.id.in_(message_ids)).all()
            if not messages:
                return None
            
            # メッセージ内容をまとめる
            combined_content = self._combine_messages(messages)
            
            # 記事生成プロンプト
            prompt = self._create_article_prompt(combined_content)
            
            # Geminiで記事生成
            response = self.model.generate_content(prompt)
            
            if response.text:
                article_data = self._parse_article_response(response.text)
                
                # データベースに保存
                article = Article(
                    title=article_data['title'],
                    content=article_data['content'],
                    summary=article_data['summary'],
                    gemini_prompt=prompt,
                    gemini_response=response.text
                )
                article.set_tags_list(article_data['tags'])
                article.set_source_messages_list(message_ids)
                
                db.session.add(article)
                db.session.commit()
                
                logger.info(f"記事生成完了: {article.id}")
                return article.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"複数メッセージからの記事生成エラー: {e}")
            return None
    
    def _generate_from_text(self, message: Message) -> Optional[Dict]:
        """テキストメッセージから記事生成"""
        try:
            prompt = f"""
以下のテキストメッセージをもとに、ブログ記事を作成してください。

メッセージ内容:
{message.content}

要求事項:
- 読みやすく、興味深い記事にしてください
- 適切なタイトルを付けてください
- 記事の要約も含めてください
- 関連するタグを3-5個提案してください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）

以下の形式で回答してください:
タイトル: [記事タイトル]
要約: [記事の要約]
タグ: [タグ1], [タグ2], [タグ3]
本文:
[記事本文]
"""

            response = self.model.generate_content(prompt)
            
            if response.text:
                article_data = self._parse_article_response(response.text)
                
                # データベースに保存
                article = Article(
                    title=article_data['title'],
                    content=article_data['content'],
                    summary=article_data['summary'],
                    gemini_prompt=prompt,
                    gemini_response=response.text
                )
                article.set_tags_list(article_data['tags'])
                article.set_source_messages_list([message.id])
                
                db.session.add(article)
                db.session.commit()
                
                return article.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"テキストからの記事生成エラー: {e}")
            return None
    
    def _generate_from_image(self, message: Message) -> Optional[Dict]:
        """画像メッセージから記事生成"""
        try:
            if not message.file_path:
                return None
            
            # 画像を読み込み
            image = Image.open(message.file_path)
            
            prompt = """
この画像について詳しく分析し、ブログ記事を作成してください。

要求事項:
- 画像の内容を詳細に説明してください
- 興味深い観点や背景情報を加えてください
- 適切なタイトルを付けてください
- 記事の要約も含めてください
- 関連するタグを3-5個提案してください

以下の形式で回答してください:
タイトル: [記事タイトル]
要約: [記事の要約]
タグ: [タグ1], [タグ2], [タグ3]
本文:
[記事本文]
"""

            # Use PIL Image for compatibility
            image = Image.open(message.file_path)
            
            response = self.vision_model.generate_content([prompt, image])
            
            if response.text:
                article_data = self._parse_article_response(response.text)
                
                # データベースに保存
                article = Article(
                    title=article_data['title'],
                    content=article_data['content'],
                    summary=article_data['summary'],
                    gemini_prompt=prompt,
                    gemini_response=response.text
                )
                article.set_tags_list(article_data['tags'])
                article.set_source_messages_list([message.id])
                
                db.session.add(article)
                db.session.commit()
                
                return article.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"画像からの記事生成エラー: {e}")
            return None
    
    def _generate_from_video(self, message: Message) -> Optional[Dict]:
        """動画メッセージから記事生成（ファイル情報ベース）"""
        try:
            prompt = f"""
動画ファイルに関するブログ記事を作成してください。

ファイル情報:
- ファイルパス: {message.file_path}
- アップロード日時: {message.created_at}

要求事項:
- 動画コンテンツの可能性について考察してください
- 興味深い記事にしてください
- 適切なタイトルを付けてください
- 記事の要約も含めてください
- 関連するタグを3-5個提案してください

以下の形式で回答してください:
タイトル: [記事タイトル]
要約: [記事の要約]
タグ: [タグ1], [タグ2], [タグ3]
本文:
[記事本文]
"""

            response = self.model.generate_content(prompt)
            
            if response.text:
                article_data = self._parse_article_response(response.text)
                
                # データベースに保存
                article = Article(
                    title=article_data['title'],
                    content=article_data['content'],
                    summary=article_data['summary'],
                    gemini_prompt=prompt,
                    gemini_response=response.text
                )
                article.set_tags_list(article_data['tags'])
                article.set_source_messages_list([message.id])
                
                db.session.add(article)
                db.session.commit()
                
                return article.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"動画からの記事生成エラー: {e}")
            return None
    
    def _combine_messages(self, messages: List[Message]) -> str:
        """複数メッセージを結合"""
        combined = []
        for msg in messages:
            if msg.message_type == 'text':
                combined.append(f"テキスト: {msg.content}")
            else:
                combined.append(f"{msg.message_type}: {msg.summary}")
        
        return "\n\n".join(combined)
    
    def _create_article_prompt(self, content: str) -> str:
        """記事生成用プロンプト作成"""
        return f"""
以下の情報をもとに、興味深いブログ記事を作成してください。

情報:
{content}

要求事項:
- 読みやすく、魅力的な記事にしてください
- 適切なタイトルを付けてください
- 記事の要約も含めてください
- 関連するタグを3-5個提案してください

以下の形式で回答してください:
タイトル: [記事タイトル]
要約: [記事の要約]
タグ: [タグ1], [タグ2], [タグ3]
本文:
[記事本文]
"""
    
    def _parse_article_response(self, response_text: str) -> Dict:
        """Geminiの応答を解析して記事データに変換"""
        try:
            lines = response_text.strip().split('\n')
            
            title = ""
            summary = ""
            tags = []
            content_lines = []
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('タイトル:'):
                    title = line.replace('タイトル:', '').strip()
                elif line.startswith('要約:'):
                    summary = line.replace('要約:', '').strip()
                elif line.startswith('タグ:'):
                    tags_str = line.replace('タグ:', '').strip()
                    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                elif line.startswith('本文:'):
                    current_section = 'content'
                    continue
                elif current_section == 'content' and line:
                    content_lines.append(line)
                elif not current_section and line and not any(line.startswith(prefix) for prefix in ['タイトル:', '要約:', 'タグ:', '本文:']):
                    # タイトル、要約、タグ、本文のラベルがない場合は、本文として扱う
                    if not title and not summary and not tags:
                        content_lines.append(line)
            
            content = '\n'.join(content_lines).strip()
            
            # より厳密なパターンマッチングを追加
            if not title and response_text:
                # タイトルが見つからない場合、最初の行を使用
                first_lines = response_text.strip().split('\n')[:3]
                for line in first_lines:
                    line = line.strip()
                    if line and not line.startswith(('要約:', 'タグ:', '本文:')):
                        title = line[:50]  # 最大50文字に制限
                        break
            
            # デフォルト値設定
            if not title:
                title = "生成された記事"
            if not summary:
                summary = content[:100] + "..." if len(content) > 100 else content
            if not tags:
                tags = ["AI生成", "ブログ", "記事"]
            if not content:
                content = "記事内容の生成に失敗しました。"
            
            # デバッグログ出力
            logger.info(f"パース結果 - タイトル: {title[:50]}..., 要約: {summary[:50]}..., タグ数: {len(tags)}, 本文長: {len(content)}")
            
            return {
                'title': title,
                'summary': summary,
                'tags': tags,
                'content': content
            }
            
        except Exception as e:
            logger.error(f"記事レスポンス解析エラー: {e}")
            logger.error(f"レスポンステキスト: {response_text[:200]}...")
            return {
                'title': "記事タイトル",
                'summary': "記事の要約",
                'tags': ["AI生成"],
                'content': response_text
            }