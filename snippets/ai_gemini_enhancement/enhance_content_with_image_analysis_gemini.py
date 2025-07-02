import logging
import os
from typing import Optional, Dict, Any

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_ENHANCE_WITH_IMAGE_PROMPT_TEMPLATE = """
以下のブログ記事を、提供された画像解析結果を基に、より豊かで魅力的な内容に拡張・改善してください。

元の記事（HTML形式）:
```html
{original_html_content}
```

画像解析結果（この画像を説明するテキスト）:
```text
{image_analysis_text}
```

改善の要求事項:
- 画像解析結果で示された情景や要素を、元の記事の文脈に自然に織り込んでください。
- 単に情報を追加するだけでなく、具体的な描写、比喩、感情表現などを加えて、読者の想像力を掻き立てるような記述を目指してください。
- 元の記事の主要なテーマやメッセージ、トーン＆マナーは維持してください。
- 画像の内容が記事の中心的な要素となるように、あるいは記事の特定のセクションを効果的に補強するように、構成を調整しても構いません。
- より臨場感があり、読者の共感を呼ぶような表現を心がけてください。
- 最終的な出力は、改善された記事全体の完全なHTML形式でなければなりません。
- HTMLタグ（例: <p>, <br>, <strong>, <em>, <img>, <blockquote>）を適切に使用してください。
- マークダウン記法は使用しないでください。
"""

def enhance_content_with_image_analysis_gemini(
    original_html_content: str,
    image_analysis_text: str,
    model_name: str = "gemini-1.5-pro", # A model capable of nuanced content integration
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_ENHANCE_WITH_IMAGE_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None
) -> Optional[str]:
    """
    Enhances and expands given HTML content by integrating textual analysis of an image,
    using the Gemini API.

    Args:
        original_html_content (str): The original HTML content of the article.
        image_analysis_text (str): Textual description or analysis of an image
                                   that should be woven into the content.
        model_name, api_key, prompt_template, generation_config, safety_settings, configured_model:
            Standard Gemini configuration arguments.

    Returns:
        Optional[str]: The enhanced HTML content as a string if successful,
                       None otherwise.
    """
    if not original_html_content and not image_analysis_text:
        logger.warning("Both original content and image analysis are empty. Nothing to enhance.")
        return original_html_content # Or an empty string

    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return None # Or return original_html_content as a fallback
        model = genai.GenerativeModel(model_name)
    else:
        logger.error("Gemini SDK not available and no configured_model provided.")
        return None

    prompt = prompt_template.format(
        original_html_content=original_html_content or "（元の記事テキストはありませんでした）",
        image_analysis_text=image_analysis_text or "（画像分析結果はありませんでした）"
    )

    try:
        logger.info(f"Attempting Gemini API call to enhance content with image analysis (Model: {model_name})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info("Content enhancement with image analysis successful.")
            # Model is expected to return the full, enhanced HTML content.
            return response.text.strip()
        else:
            logger.warning("Gemini API response for content enhancement was empty.")
            # Fallback: maybe return a simple combination or just the original?
            # For this snippet, returning None indicates an issue with generation.
            return None

    except Exception as e:
        logger.error(f"Gemini API error during content enhancement: {e}", exc_info=True)
        return None

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)): # type: ignore
        print("Skipping content enhancement test: Gemini SDK not available or API key not configured.")
    else:
        sample_original_html = """
        <h2>公園での静かな午後</h2>
        <p>今日は近所の公園でのんびり過ごしました。ベンチに座って本を読んでいると、心地よい風が吹いてきました。</p>
        <p>空を見上げると、ゆっくりと雲が流れていくのが見えました。平和な時間です。</p>
        """
        sample_image_analysis = """
        公園の池のほとりで撮影された写真。池には数羽のカモが優雅に泳いでおり、そのうちの一羽が水面から顔を出して羽ばたこうとしている瞬間が捉えられている。
        水面には周囲の木々や空が反射し、キラキラと輝いている。背景には青々とした芝生と、初夏の緑葉をつけた木々が広がり、遠くには子供たちが遊んでいる様子もかすかに見える。
        全体的に穏やかで牧歌的な雰囲気。
        """

        print("\n--- Test Case 1: Enhance content with image analysis ---")
        enhanced_content1 = enhance_content_with_image_analysis_gemini(
            sample_original_html,
            sample_image_analysis,
            api_key=test_api_key,
            model_name="gemini-1.5-flash" # Using flash for faster test, pro might yield better results
        )
        if enhanced_content1:
            print("Enhanced Content (Test 1):")
            print(enhanced_content1)
            # Basic check: ensure some part of image analysis is in the output
            assert "カモ" in enhanced_content1 or "池" in enhanced_content1
        else:
            print("Failed to enhance content (Test 1).")

        print("\n--- Test Case 2: Original content is empty, only image analysis provided ---")
        enhanced_content2 = enhance_content_with_image_analysis_gemini(
            "", # Empty original content
            "夕暮れ時、海岸線に沈む太陽。空はオレンジと紫のグラデーションに染まり、海面には太陽の光の道がまっすぐに伸びている。数隻の漁船がシルエットとして浮かんでいる。",
            api_key=test_api_key,
            model_name="gemini-1.5-flash"
        )
        if enhanced_content2:
            print("\nEnhanced Content (Test 2 - Image Analysis Only):")
            print(enhanced_content2)
            assert "夕暮れ" in enhanced_content2 or "太陽" in enhanced_content2
        else:
            print("Failed to enhance content (Test 2 - Image Analysis Only).")

        print("\n--- Test Case 3: Image analysis is empty, only original content ---")
        # This should ideally just refine the original or return it with minor changes if any.
        # The prompt asks to "integrate" image analysis, so if none, its behavior might vary.
        enhanced_content3 = enhance_content_with_image_analysis_gemini(
            "<p>古い灯台についての物語です。</p>",
            "", # Empty image analysis
            api_key=test_api_key,
            model_name="gemini-1.5-flash"
        )
        if enhanced_content3:
            print("\nEnhanced Content (Test 3 - Original Content Only):")
            print(enhanced_content3)
            assert "灯台" in enhanced_content3
        else:
            print("Failed to enhance content (Test 3 - Original Content Only).")


    print("\nNote: Live API calls to Gemini cost money and depend on network.")
    print("The quality of enhancement relies heavily on the model's ability to creatively integrate the provided texts.")
