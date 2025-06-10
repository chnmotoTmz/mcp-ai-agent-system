"""
Enhancement Gemini Service - 品質向上専用
フェイズ2の品質向上システム用にシンプル化されたGeminiサービス
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import google.generativeai as genai
from PIL import Image
import os

logger = logging.getLogger(__name__)

class EnhancementGeminiService:
    """品質向上専用のGeminiサービス"""
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def improve_text_quality(self, content: str) -> Optional[str]:
        """文章品質を向上させる"""
        try:
            prompt = f"""
以下のブログ記事を校正・改善してください：

{content}

改善ポイント：
- 誤字脱字の修正
- 文章の流れを自然に
- 読みやすさの向上
- 適切な改行・段落分け
- より魅力的な表現

要求事項：
- 出力は必ずHTML形式で記述してください（マークダウンは使用禁止）
- HTMLタグを使用してください: <p>、<br>、<strong>、<em>、<ul>、<li>、<h2>、<h3>など
- マークダウン記法（##、**、-など）は一切使用しないでください

元の内容や雰囲気は保ちつつ、品質を向上させてください。
改善された記事全文をHTML形式で出力してください。
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"文章品質向上エラー: {e}")
            return None
    
    def add_internal_links(self, article_content: str, similar_articles: List[Dict]) -> Optional[str]:
        """内部リンクを追加した新しいコンテンツを生成"""
        try:
            similar_info = []
            for article in similar_articles:
                similar_info.append(f"- {article['title']}: {article.get('hatena_url', '')}")
            
            similar_text = "\n".join(similar_info)
            
            prompt = f"""
以下のブログ記事に、関連記事への自然なリンクを追加してください：

元記事：
{article_content}

関連記事：
{similar_text}

要求：
- 記事の内容を損なわずに、自然な流れで関連記事を紹介
- 「関連記事」「こちらもおすすめ」などの適切な文言を使用
- リンクは記事の最後に追加
- 元の記事の雰囲気を保持

出力要求事項：
- 出力は必ずHTML形式で記述してください（マークダウンは使用禁止）
- HTMLタグを使用してください: <p>、<br>、<strong>、<em>、<ul>、<li>、<h2>、<h3>、<a>など
- マークダウン記法（##、**、-など）は一切使用しないでください

改善された記事全文をHTML形式で出力してください。
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"内部リンク追加エラー: {e}")
            return None
    
    def analyze_image_for_enhancement(self, image_path: str) -> Optional[str]:
        """画像を解析してブログ記事の拡張材料を取得"""
        try:
            image = Image.open(image_path)
            
            prompt = """
この画像について詳しく分析し、ブログ記事の内容を豊かにする要素を抽出してください。

分析ポイント：
- 画像に映っているもの、場所、人物の詳細
- 色彩、雰囲気、構図の特徴
- 背景や細かいディテール
- ストーリーや感情を想起させる要素
- ブログ記事に織り込める具体的な描写

ブログ記事に活用できる形で、詳細な分析結果を提供してください。
"""
            
            response = self.model.generate_content([prompt, image])
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"画像解析エラー: {e}")
            return None
    
    def enhance_content_with_image_analysis(self, content: str, image_analysis: str) -> Optional[str]:
        """画像解析結果を基にコンテンツを拡張"""
        try:
            prompt = f"""
以下のブログ記事を、画像解析結果を基に拡張・改善してください：

元記事：
{content}

画像解析結果：
{image_analysis}

要求：
- 画像の内容を自然に記事に織り込む
- 具体的な描写や詳細を追加
- 読者の理解を深める内容にする
- 元の記事の流れを保持
- より臨場感のある表現に

改善された記事全文を出力してください。
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"コンテンツ拡張エラー: {e}")
            return None
    
    def generate_content_summary(self, content: str) -> Optional[str]:
        """記事の要約を生成"""
        try:
            prompt = f"""
以下のブログ記事の簡潔な要約を作成してください：

{content}

要求：
- 3-4行程度の簡潔な要約
- 記事の主なポイントを含める
- 読者の興味を引く表現
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"要約生成エラー: {e}")
            return None

# テスト用
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the service
    service = EnhancementGeminiService()
    
    test_content = """
今日は歯医者に行きました。詰め物が取れてしまって困っていたんです。
先生に診てもらったら、詰め物はできないと言われました。
でも、どうしても今日直したくて、お願いしたら接着だけしてもらえました。
また外れたら、今度はちゃんと治療しようと思います。
"""
    
    print("Testing text quality improvement...")
    improved = service.improve_text_quality(test_content)
    if improved:
        print("Improved content:")
        print(improved)
    else:
        print("Failed to improve content")
