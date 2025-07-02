import logging
import os
from typing import Optional, Dict, Any, Union

# Attempt to import google.generativeai and PIL.Image, but don't fail if not installed.
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

try:
    from PIL import Image
except ImportError:
    Image = None # type: ignore

logger = logging.getLogger(__name__)

# Default prompt template for analyzing an image and generating a blog post
DEFAULT_IMAGE_BLOG_PROMPT_TEMPLATE = """
{user_prompt}

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
"""

def analyze_image_for_blog_gemini(
    image_source: Union[str, Any], # File path or PIL Image object
    user_prompt: str = "この画像について詳しく説明してください",
    model_name: str = "gemini-1.5-flash", # Vision capable model
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_IMAGE_BLOG_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None # Allow passing an already configured GenerativeModel instance
) -> Optional[str]:
    """
    Analyzes an image and generates a blog post using the Gemini API (Vision model).

    Args:
        image_source (Union[str, Image.Image]): Path to the image file or a PIL Image object.
        user_prompt (str, optional): A specific prompt to guide the image analysis.
            Defaults to "この画像について詳しく説明してください".
        model_name (str, optional): The name of the Gemini vision model to use.
            Defaults to "gemini-1.5-flash" (or compatible vision model).
            Ignored if `configured_model` is provided.
        api_key (Optional[str], optional): The Gemini API key. If not provided,
            it's assumed `genai` is already configured or `GOOGLE_API_KEY` env var is set.
            Ignored if `configured_model` is provided.
        prompt_template (str, optional): A template string for the full prompt.
            Must include a `{user_prompt}` placeholder.
            Defaults to DEFAULT_IMAGE_BLOG_PROMPT_TEMPLATE.
        generation_config (Optional[Dict[str, Any]], optional): Configuration for content generation.
        safety_settings (Optional[Dict[str, Any]], optional): Safety settings for content generation.
        configured_model (Optional[Any]): An already initialized `genai.GenerativeModel` instance.
            If provided, `model_name` and `api_key` are ignored for model initialization.

    Returns:
        Optional[str]: The generated blog post (title and HTML content) as a string if successful,
                       None otherwise.
    """
    if not Image:
        logger.error("PIL (Pillow) library is not available, which is required for image handling.")
        return None
    if not genai and not configured_model:
        logger.error("Gemini SDK (google.generativeai) not available and no configured_model provided.")
        return None

    try:
        if isinstance(image_source, str):
            if not os.path.exists(image_source):
                logger.error(f"Image file not found at path: {image_source}")
                return None
            image = Image.open(image_source)
        elif isinstance(image_source, Image.Image):
            image = image_source
        else:
            logger.error(f"Invalid image_source type: {type(image_source)}. Must be path string or PIL Image.")
            return None
    except Exception as e:
        logger.error(f"Error opening or processing image: {e}", exc_info=True)
        return None

    if configured_model:
        model = configured_model
    elif genai: # genai must exist here due to earlier check
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return None # Or a fallback string indicating error
        model = genai.GenerativeModel(model_name) # Ensure this model is vision-capable
    else: # Should not be reached
        return None


    full_prompt = prompt_template.format(user_prompt=user_prompt)

    contents = [full_prompt, image]

    try:
        logger.info(f"Attempting Gemini API call for image analysis (Model: {model_name})")
        response = model.generate_content(
            contents,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info(f"Gemini image analysis successful. Response length: {len(response.text)}")
            return response.text.strip()
        else:
            logger.warning("Gemini API response for image analysis was empty or whitespace only.")
            return None # Or a fallback string

    except Exception as e:
        logger.error(f"Gemini API error during image analysis: {e}", exc_info=True)
        return None # Or a fallback string

# Example Usage (requires google.generativeai, Pillow, an API key, and a test image)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Configuration for testing ---
    test_api_key = os.getenv("GOOGLE_API_KEY")

    # Create a dummy image for testing if Pillow is available
    dummy_image_path = "dummy_test_image.png"
    if Image:
        try:
            img = Image.new('RGB', (100, 100), color = 'red')
            img.save(dummy_image_path)
            print(f"Created dummy image: {dummy_image_path}")
        except Exception as e:
            print(f"Could not create dummy image: {e}")
            # dummy_image_path = None # Ensure it's None if creation fails
    else:
        print("Pillow not installed, cannot create dummy image for testing.")
        dummy_image_path = None


    if not genai or not Image:
        print("Skipping test: Gemini SDK or Pillow not installed.")
    elif not test_api_key and (genai and not genai.API_KEY):
         print("Skipping test: GOOGLE_API_KEY not set and genai not configured.")
    elif not dummy_image_path or not os.path.exists(dummy_image_path):
        print(f"Skipping test: Dummy image '{dummy_image_path}' not available.")
    else:
        print("\n--- Test Case 1: Analyze dummy image with default prompt ---")
        # It's better to use a real image for meaningful results,
        # but a dummy image tests the pipeline.
        result1 = analyze_image_for_blog_gemini(dummy_image_path, api_key=test_api_key)
        if result1:
            print(f"Generated Blog from Image (Dummy Image):\n{result1[:500]}...")
        else:
            print("Failed to generate blog from dummy image.")

        print("\n--- Test Case 2: Analyze dummy image with a custom user prompt ---")
        custom_prompt = "Describe this image as if it were a mysterious artifact."
        result2 = analyze_image_for_blog_gemini(
            dummy_image_path,
            user_prompt=custom_prompt,
            api_key=test_api_key
        )
        if result2:
            print(f"Generated Blog (Custom Prompt):\n{result2[:500]}...")
        else:
            print("Failed to generate blog with custom prompt.")

        print("\n--- Test Case 3: Using a pre-configured vision model instance ---")
        if genai:
            try:
                if test_api_key: genai.configure(api_key=test_api_key)
                # Ensure you use a model name compatible with vision, e.g., 'gemini-pro-vision' or 'gemini-1.5-flash'
                pre_configured_vision_model = genai.GenerativeModel("gemini-1.5-flash")
                pil_image = Image.open(dummy_image_path)
                result3 = analyze_image_for_blog_gemini(pil_image, configured_model=pre_configured_vision_model)
                if result3:
                    print(f"Generated Blog (Pre-configured model with PIL image):\n{result3[:500]}...")
                else:
                    print("Failed with pre-configured model and PIL image.")
            except Exception as e:
                print(f"Could not run pre-configured model test: {e}")

        # Clean up dummy image
        if os.path.exists(dummy_image_path):
            try:
                os.remove(dummy_image_path)
                print(f"Removed dummy image: {dummy_image_path}")
            except Exception as e:
                print(f"Error removing dummy image {dummy_image_path}: {e}")


    print("\nNote: Live API calls to Gemini Vision models cost money and depend on network.")
    print("For best results, test with a real, meaningful image.")
