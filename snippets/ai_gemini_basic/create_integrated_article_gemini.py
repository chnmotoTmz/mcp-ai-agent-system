import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime # For fallback content timestamp

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

# Default prompt template for integrating text and image analyses into an article
DEFAULT_INTEGRATED_ARTICLE_PROMPT_TEMPLATE = """
以下の情報を基に、自然で読みやすいブログ記事を作成してください：

ユーザーのメッセージ：
{text_content_block}

画像の内容：
{image_analyses_block}

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

def _create_fallback_integrated_article(text_content: str, image_analyses: List[str], error_info: str = "") -> str:
    """
    Creates a fallback article string when Gemini API fails or returns an error.
    Combines text_content and image_analyses into a simple structure.
    """
    from datetime import datetime # Local import for fallback only

    title_prefix = "統合記事 (フォールバック): "
    title_text = text_content.split('\n')[0][:30] if text_content else "提供された情報に基づく記事"
    title = title_prefix + title_text + "..." if len(title_text) >=30 else title_prefix + title_text

    body_parts = []
    if text_content:
        body_parts.append(f"<h3>ユーザー提供のテキスト：</h3><p>{text_content.replace(chr(10), '<br>')}</p>")

    if image_analyses:
        body_parts.append("<h3>画像分析結果：</h3><ul>")
        for i, analysis in enumerate(image_analyses):
            body_parts.append(f"<li>画像 {i+1}: {analysis.replace(chr(10), '<br>')}</li>")
        body_parts.append("</ul>")

    if not body_parts:
        body_parts.append("<p>記事を生成するための十分なコンテンツがありませんでした。</p>")

    error_html = f"<p><strong><i>生成エラー: {error_info}</i></strong></p>" if error_info else ""
    timestamp_html = f"<p><small>フォールバック生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>"

    return f"タイトル: {title}\n\n本文:\n{error_html}<div>{''.join(body_parts)}</div>{timestamp_html}"


def create_integrated_article_gemini(
    text_content: str,
    image_analyses: List[str], # List of strings, each being an analysis of an image
    model_name: str = "gemini-1.5-flash",
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_INTEGRATED_ARTICLE_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None
) -> Optional[str]:
    """
    Creates an integrated article by combining text content and image analyses
    using the Gemini API.

    Args:
        text_content (str): The main textual content from the user.
        image_analyses (List[str]): A list of strings, where each string is the
                                    textual analysis/description of an image.
        model_name, api_key, prompt_template, generation_config, safety_settings, configured_model:
            Similar to other Gemini snippets for model and API configuration.

    Returns:
        Optional[str]: The generated integrated article (title and HTML body) as a string.
                       Returns a fallback article string on failure.
                       Returns None if critical components (like SDK) are missing.
    """

    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return _create_fallback_integrated_article(text_content, image_analyses, "API key not configured")
        model = genai.GenerativeModel(model_name)
    else:
        logger.error("Gemini SDK (google.generativeai) not available and no configured_model provided.")
        return None # Cannot even generate fallback without datetime if that's not global

    text_content_block = text_content if text_content else '（テキストメッセージなし）'

    if image_analyses:
        image_analyses_block = "\n".join([f"- 画像{i+1}の分析: {analysis}" for i, analysis in enumerate(image_analyses)])
    else:
        image_analyses_block = '（画像なし、または画像分析結果なし）'

    prompt = prompt_template.format(
        text_content_block=text_content_block,
        image_analyses_block=image_analyses_block
    )

    try:
        logger.info(f"Attempting Gemini API call for integrated article (Model: {model_name})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info(f"Gemini integrated article generation successful. Response length: {len(response.text)}")
            return response.text.strip()
        else:
            logger.warning("Gemini API response for integrated article was empty.")
            return _create_fallback_integrated_article(text_content, image_analyses, "API returned empty response")

    except Exception as e:
        logger.error(f"Gemini API error during integrated article generation: {e}", exc_info=True)
        return _create_fallback_integrated_article(text_content, image_analyses, str(e))

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)):
        print("Skipping test: Gemini SDK not available or API key not configured.")
    else:
        sample_text = "週末は家族でピクニックに行きました。天気も良くて最高！"
        sample_image_analyses = [
            "赤いチェックのレジャーシートの上にお弁当箱と水筒が置かれている。背景には緑の芝生と木々が見える。",
            "子供がシャボン玉を追いかけて楽しそうに笑っている。空は快晴だ。"
        ]

        print("\n--- Test Case 1: Create integrated article with text and image analyses ---")
        article1 = create_integrated_article_gemini(
            sample_text,
            sample_image_analyses,
            api_key=test_api_key
        )
        if article1:
            print("Generated Integrated Article (Test 1):")
            print(article1) # Full output as it includes title and body
        else:
            print("Failed to create integrated article (Test 1).")

        print("\n--- Test Case 2: Only text content, no image analyses ---")
        article2 = create_integrated_article_gemini(
            "今日は一日中、家でプログラミングの勉強をしていました。新しい概念を学ぶのは難しいけど、面白い！",
            [], # Empty list for image_analyses
            api_key=test_api_key
        )
        if article2:
            print("Generated Integrated Article (Test 2 - Text Only):")
            print(article2)
        else:
            print("Failed to create integrated article (Test 2 - Text Only).")

        print("\n--- Test Case 3: No text content, only image analyses ---")
        article3 = create_integrated_article_gemini(
            "", # Empty string for text_content
            ["夕焼け空がオレンジ色と紫色に染まり、非常に美しいグラデーションを作り出している。シルエットになった山並みが見える。"],
            api_key=test_api_key
        )
        if article3:
            print("Generated Integrated Article (Test 3 - Images Only):")
            print(article3)
        else:
            print("Failed to create integrated article (Test 3 - Images Only).")

        print("\n--- Test Case 4: Fallback simulation (mocking API error) ---")
        class MockModelIntegratedFail:
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                raise Exception("Simulated API failure for integration")

        mock_model_fail = MockModelIntegratedFail()
        article4_fallback = create_integrated_article_gemini(
            "Test fallback.",
            ["Image analysis for fallback test."],
            configured_model=mock_model_fail
        )
        print("Generated Fallback Article (Test 4):")
        print(article4_fallback)
        assert "フォールバック" in article4_fallback
        assert "Simulated API failure for integration" in article4_fallback
        print("Fallback test passed.")


    print("\nNote: Live API calls to Gemini cost money and depend on network.")
