import logging
import time
import os
from typing import Optional, Dict, Any
from datetime import datetime

# Attempt to import google.generativeai, but don't fail if not installed,
# as the snippet user might handle initialization differently or mock it.
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

# Default prompt template for generating blog articles
DEFAULT_BLOG_PROMPT_TEMPLATE = """
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
"""

def create_fallback_content(text: str, error_message: Optional[str] = None) -> str:
    """
    Creates a fallback content string when the primary generation fails.

    Args:
        text (str): The original input text.
        error_message (Optional[str]): An optional error message to include.

    Returns:
        str: A formatted fallback string, typically including a title and the original text.
    """
    current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    lines = text.split('\n')
    first_line = lines[0] if lines else "フォールバック記事"
    title = first_line[:30] + ("..." if len(first_line) > 30 else "")

    content_lines = [f"<p>{line.strip()}</p>" for line in lines if line.strip()]

    error_info = f"<p><small>エラー: {error_message}</small></p>" if error_message else ""

    fallback_html = f"""タイトル: {title} (フォールバック)

本文:
<div style="padding: 10px; border: 1px solid #ccc; background-color: #f9f9f9;">
<p><strong>📝 {current_time} のフォールバック投稿</strong></p>
{''.join(content_lines)}
{error_info}
<p><small>※ AIによる記事生成に失敗したため、元のテキストを基に表示しています。</small></p>
</div>"""
    logger.info(f"Fallback content generated. Length: {len(fallback_html)}")
    return fallback_html

def generate_content_gemini(
    text: str,
    model_name: str = "gemini-1.5-flash", # Or allow passing a configured model instance
    api_key: Optional[str] = None,
    max_retries: int = 3,
    initial_wait_time: float = 1.0, # seconds
    prompt_template: str = DEFAULT_BLOG_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None, # For temperature, top_k etc.
    safety_settings: Optional[Dict[str, Any]] = None, # For safety settings
    configured_model = None # Allow passing an already configured GenerativeModel instance
) -> Optional[str]:
    """
    Generates content (e.g., a blog article) from input text using the Gemini API.
    Includes retry logic with exponential backoff for API call failures.

    Args:
        text (str): The input text to generate content from.
        model_name (str, optional): The name of the Gemini model to use.
            Defaults to "gemini-1.5-flash". Ignored if `configured_model` is provided.
        api_key (Optional[str], optional): The Gemini API key. If not provided,
            it's assumed `genai` is already configured or `GOOGLE_API_KEY` env var is set.
            Ignored if `configured_model` is provided.
        max_retries (int, optional): Maximum number of retries for API calls. Defaults to 3.
        initial_wait_time (float, optional): Initial wait time for retries, in seconds.
            Wait time doubles with each retry. Defaults to 1.0.
        prompt_template (str, optional): A template string for the prompt. Must include
            a `{text}` placeholder for the input text.
            Defaults to DEFAULT_BLOG_PROMPT_TEMPLATE.
        generation_config (Optional[Dict[str, Any]], optional): Configuration for content generation,
            e.g., {"temperature": 0.7, "max_output_tokens": 2048}. Defaults to None.
        safety_settings (Optional[Dict[str, Any]], optional): Safety settings for content generation.
            Defaults to None.
        configured_model (Optional[Any]): An already initialized `genai.GenerativeModel` instance.
            If provided, `model_name` and `api_key` are ignored for model initialization.

    Returns:
        Optional[str]: The generated content as a string if successful,
                       or a fallback content string if all retries fail.
                       Returns None if `genai` module is not available and no `configured_model`.
    """
    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY: # Check if already configured
             logger.error("Gemini API key not provided and genai not configured.")
             return create_fallback_content(text, "API key not configured.")
        model = genai.GenerativeModel(model_name)
    else:
        logger.error("Gemini SDK (google.generativeai) not available and no configured_model provided.")
        return create_fallback_content(text, "Gemini SDK not available.")

    prompt = prompt_template.format(text=text)

    current_retry = 0
    while current_retry < max_retries:
        try:
            logger.info(f"Attempting Gemini API call (Attempt {current_retry + 1}/{max_retries}) for model {model_name}")

            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            if response.text and response.text.strip():
                logger.info(f"Gemini API call successful. Response length: {len(response.text)}")
                return response.text.strip()
            else:
                logger.warning(f"Gemini API response was empty or whitespace only (Attempt {current_retry + 1}).")
                # Treat empty response as a failure to allow retry, unless it's the last attempt.
                if current_retry == max_retries - 1:
                    logger.error("Gemini API returned empty response on final attempt.")
                    return create_fallback_content(text, "API returned empty response.")

        except Exception as e:
            logger.error(f"Gemini API error on attempt {current_retry + 1}: {e}", exc_info=True)
            if current_retry == max_retries - 1:
                logger.error("All retry attempts failed for Gemini API call.")
                return create_fallback_content(text, f"API error after all retries: {e}")

        current_retry += 1
        if current_retry < max_retries:
            wait_time = initial_wait_time * (2 ** (current_retry -1)) # Exponential backoff
            logger.info(f"Waiting {wait_time:.2f} seconds before next retry...")
            time.sleep(wait_time)

    # This part should ideally not be reached if logic is correct,
    # but as a safeguard:
    logger.error("Exited retry loop without returning a value. This indicates a logic error.")
    return create_fallback_content(text, "Exited retry loop unexpectedly.")


# Example Usage (requires google.generativeai and an API key)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Configuration for testing ---
    # Make sure to set your GOOGLE_API_KEY environment variable
    # or pass the api_key argument.
    # For actual use, you'd get the API key securely.
    test_api_key = os.getenv("GOOGLE_API_KEY") # Replace with your key if not using env var

    if not test_api_key and not genai:
        print("Skipping test: Gemini SDK not installed or GOOGLE_API_KEY not set.")
    elif not test_api_key and genai and not genai.API_KEY:
         print("Skipping test: GOOGLE_API_KEY not set and genai not configured with a key.")
    else:
        sample_text_short = "今日は天気が良いので公園に行きました。楽しかったです。"
        sample_text_long = """
        AI技術の進化は目覚ましく、私たちの生活や仕事に大きな変化をもたらしています。
        特に自然言語処理の分野では、人間と自然に対話できるAIが登場し、
        カスタマーサポートや教育、コンテンツ作成など、多岐にわたる応用が期待されています。
        しかし、その一方で、倫理的な課題や雇用の問題など、慎重に議論すべき点も存在します。
        私たちは、AIの恩恵を最大限に享受しつつ、潜在的なリスクにも対処していく必要があります。
        """

        print("\n--- Test Case 1: Short text, default prompt ---")
        result1 = generate_content_gemini(sample_text_short, api_key=test_api_key)
        if result1:
            print(f"Generated Content (Short Text):\n{result1[:300]}...") # Print first 300 chars
        else:
            print("Failed to generate content for short text.")

        print("\n--- Test Case 2: Long text, custom generation config ---")
        custom_gen_config = {"temperature": 0.8, "max_output_tokens": 500}
        result2 = generate_content_gemini(
            sample_text_long,
            api_key=test_api_key,
            generation_config=custom_gen_config
        )
        if result2:
            print(f"Generated Content (Long Text with custom config):\n{result2[:500]}...")
        else:
            print("Failed to generate content for long text.")

        print("\n--- Test Case 3: Using a pre-configured model instance ---")
        if genai:
            try:
                if test_api_key: genai.configure(api_key=test_api_key)
                pre_configured_model = genai.GenerativeModel("gemini-1.5-flash")
                result3 = generate_content_gemini(sample_text_short, configured_model=pre_configured_model)
                if result3:
                    print(f"Generated Content (Pre-configured model):\n{result3[:300]}...")
                else:
                    print("Failed with pre-configured model.")
            except Exception as e:
                print(f"Could not run pre-configured model test: {e}")
        else:
            print("Skipping pre-configured model test as genai is not imported.")

        print("\n--- Test Case 4: API call failure simulation (mocking) ---")
        # This requires more advanced mocking to simulate genai.GenerativeModel().generate_content throwing an error.
        # For a simple snippet, we'll just note that the retry logic is there.
        # To truly test this, you might use unittest.mock.
        class MockModel:
            def __init__(self, model_name):
                self.model_name = model_name
                self.call_count = 0
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                self.call_count += 1
                if self.call_count < 2: # Fail first time
                    raise Exception("Simulated API Error")
                # Succeed on second attempt
                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                return MockResponse("Successfully generated after one failure.")

        mock_model_instance = MockModel("gemini-1.5-flash")
        result4 = generate_content_gemini(
            "Test retry logic",
            configured_model=mock_model_instance,
            max_retries=2 # Ensure it can succeed on the second try
        )
        print(f"Retry Test (Mocked): Call count: {mock_model_instance.call_count}")
        if result4:
            print(f"Content: {result4}")
        else:
            print("Retry test failed or did not produce expected output.")
        assert mock_model_instance.call_count == 2, "Mock model should have been called twice for retry test."
        assert result4 == "Successfully generated after one failure."
        print("Retry logic test with mock passed.")


        print("\n--- Test Case 5: All retries fail (mocking) ---")
        class MockModelFailAll:
            def __init__(self, model_name):
                self.model_name = model_name
                self.call_count = 0
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                self.call_count += 1
                raise Exception(f"Simulated Persistent API Error attempt {self.call_count}")

        mock_model_fail_all_instance = MockModelFailAll("gemini-1.5-flash")
        result5 = generate_content_gemini(
            "Test all retries fail",
            configured_model=mock_model_fail_all_instance,
            max_retries=2
        )
        print(f"All Retries Fail Test (Mocked): Call count: {mock_model_fail_all_instance.call_count}")
        if "フォールバック" in result5: # Check if fallback content is returned
            print(f"Content: {result5[:300]}...")
            assert "Simulated Persistent API Error attempt 2" in result5
            print("All retries fail test with mock passed.")
        else:
            print(f"All retries fail test did not produce expected fallback. Got: {result5}")
        assert mock_model_fail_all_instance.call_count == 2

    print("\nNote: Live API calls to Gemini cost money and depend on network.")
