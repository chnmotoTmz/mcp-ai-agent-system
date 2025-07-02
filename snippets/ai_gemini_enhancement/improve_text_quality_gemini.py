import logging
import os
from typing import Optional, Dict, Any, List

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_IMPROVE_QUALITY_PROMPT_TEMPLATE = """
以下のブログ記事を校正・改善してください：

{original_content}

改善ポイント：
- 誤字脱字の修正 (例: 「ておはに」の修正、句読点の適切な使用)
- 文章の流れをより自然で読みやすいものに (例: 冗長な表現の削除、接続詞の適切な使用)
- 読者のエンゲージメントを高めるための表現の改善 (例: 具体的な描写の追加、問いかけの導入)
- 適切な改行や段落分けによる視認性の向上
- 全体として、より魅力的でプロフェッショナルな印象を与える文章へ

要求事項：
- 出力は必ずHTML形式で記述してください（マークダウンは使用禁止）。
- HTMLタグ（例: <p>, <br>, <strong>, <em>, <ul>, <li>, <h2>, <h3>）を適切に使用してください。
- 元の記事の主要な内容、意図、雰囲気は保持してください。大幅な内容変更や情報の追加・削除は避けてください。
- 改善された記事全文をHTML形式で出力してください。タイトルは含めないでください。
"""

def improve_text_quality_gemini(
    original_content: str,
    model_name: str = "gemini-1.5-flash", # Or a model known for strong instruction following
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_IMPROVE_QUALITY_PROMPT_TEMPLATE,
    custom_improvement_points: Optional[List[str]] = None, # Allow users to add more points
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None
) -> Optional[str]:
    """
    Improves the quality of a given text (e.g., a blog article) using the Gemini API.
    Focuses on proofreading, flow, readability, and engaging language.

    Args:
        original_content (str): The original text content to be improved.
        model_name (str, optional): The Gemini model to use.
        api_key (Optional[str], optional): Gemini API key.
        prompt_template (str, optional): Template for the improvement prompt.
            Must include `{original_content}`.
        custom_improvement_points (Optional[List[str]], optional): Additional specific
            points to instruct the model for improvement, appended to the default points.
        generation_config, safety_settings, configured_model: Standard Gemini config.

    Returns:
        Optional[str]: The improved text content as an HTML string if successful,
                       None otherwise.
    """
    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return None # Or return original_content as a fallback
        model = genai.GenerativeModel(model_name)
    else:
        logger.error("Gemini SDK not available and no configured_model provided.")
        return None

    # Construct the prompt
    # If custom_improvement_points are provided, integrate them into the prompt
    # This is a simple integration; more sophisticated templating might be needed for complex cases
    final_prompt_text = prompt_template.format(original_content=original_content)
    if custom_improvement_points:
        # Find the "改善ポイント：" line and insert custom points after it
        # This is a bit naive and depends on the exact wording of the default template.
        insertion_marker = "改善ポイント："
        if insertion_marker in final_prompt_text:
            parts = final_prompt_text.split(insertion_marker, 1)
            custom_points_str = "\n".join([f"- {point}" for point in custom_improvement_points])
            final_prompt_text = f"{parts[0]}{insertion_marker}\n{custom_points_str}\n{parts[1]}"
        else: # Fallback: just append if marker not found
            final_prompt_text += "\n\n追加の改善ポイント：\n" + "\n".join([f"- {point}" for point in custom_improvement_points])


    try:
        logger.info(f"Attempting Gemini API call to improve text quality (Model: {model_name})")
        response = model.generate_content(
            final_prompt_text,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info("Text quality improvement successful.")
            # It's assumed the model returns the full improved HTML content as requested.
            return response.text.strip()
        else:
            logger.warning("Gemini API response for text quality improvement was empty.")
            return None # Or original_content

    except Exception as e:
        logger.error(f"Gemini API error during text quality improvement: {e}", exc_info=True)
        return None # Or original_content

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)): # type: ignore
        print("Skipping text improvement test: Gemini SDK not available or API key not configured.")
    else:
        sample_text_to_improve = """
        <p>こんにちわ、皆さん。今日は私のペットの猫、タマに付いて書きます。
        タマは、とても可愛くて、毎日私を癒してくれます。朝早く起こしに来るのが玉に瑕ですけど。
        昨日、タマは新しいおもちゃで遊びました、それはネズミの形でした。
        彼女はそれを追いかけて、ジャンプして、とても楽しそうでした。見てる私も楽しかったです。
        ペットを飼うのは大変なこともあるけど、それ以上に幸せをくれる。そう思いませんか？</p>
        """

        print("\n--- Test Case 1: Improve text quality with default prompt ---")
        improved_text1 = improve_text_quality_gemini(sample_text_to_improve, api_key=test_api_key)
        if improved_text1:
            print("Improved Text (Default Prompt):")
            print(improved_text1)
        else:
            print("Failed to improve text (Test 1).")

        print("\n--- Test Case 2: Improve text with custom improvement points ---")
        custom_points = [
            "よりユーモラスな表現を加える。",
            "読者への共感を促す一文を末尾に追加する。"
        ]
        improved_text2 = improve_text_quality_gemini(
            sample_text_to_improve,
            custom_improvement_points=custom_points,
            api_key=test_api_key
        )
        if improved_text2:
            print("\nImproved Text (With Custom Points):")
            print(improved_text2)
        else:
            print("Failed to improve text with custom points (Test 2).")

        print("\n--- Test Case 3: Simulating an API error (mocked) ---")
        class MockModelImproveFail:
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                raise Exception("Simulated API failure for text improvement")

        mock_model_fail = MockModelImproveFail()
        improved_text_fail = improve_text_quality_gemini(
            "Some text.",
            configured_model=mock_model_fail
        )
        print(f"Result on failure: {improved_text_fail}")
        assert improved_text_fail is None # Expecting None on error
        print("Text improvement error handling test passed.")

    print("\nNote: Live API calls to Gemini cost money and depend on network.")
    print("The effectiveness of improvement depends heavily on the prompt and model capabilities.")
