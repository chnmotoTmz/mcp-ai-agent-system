import logging
import os
from typing import Optional, Dict, Any, Union

# Attempt to import google.generativeai and PIL.Image
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

try:
    from PIL import Image
    # For PIL.Image.Resampling if available (Pillow >= 7.1.0)
    if hasattr(Image, 'Resampling'):
        DEFAULT_RESAMPLING_LANCZOS_ENH = Image.Resampling.LANCZOS
    else: # Fallback for older Pillow versions
        DEFAULT_RESAMPLING_LANCZOS_ENH = Image.LANCZOS # type: ignore
except ImportError:
    Image = None # type: ignore
    DEFAULT_RESAMPLING_LANCZOS_ENH = None


logger = logging.getLogger(__name__)

DEFAULT_IMAGE_ENHANCEMENT_PROMPT = """
この画像について詳しく分析し、ブログ記事の内容を豊かにするための具体的な要素や描写を抽出してください。

分析ポイント：
- 画像に映っている主要な被写体、場所、人物（もしいる場合）の詳細な説明。
- 色彩のトーン、光の具合、全体的な雰囲気、構図の特徴。
- 背景にあるものや、見落としがちな細かいディテール。
- この画像から想起される可能性のあるストーリー、感情、テーマ。
- ブログ記事に織り込む際に役立つ、五感を刺激するような具体的な描写の提案（例：音、匂い、手触りなど、画像から推測できる範囲で）。

分析結果は、箇条書きや短いパラグラフの形式で、ブログ記事の執筆者がそのまま参考にして内容を拡張できるような形で提供してください。
"""

# Fallback messages (similar to analyze_image_gemini_enhanced.py)
FALLBACK_ENH_ANALYSIS_UNAVAILABLE = "画像が添付されていますが、拡張用の詳細分析は一時的に利用できません。"
FALLBACK_ENH_ANALYSIS_ERROR = "画像拡張用分析中にエラーが発生しました。"
FALLBACK_ENH_FILE_NOT_FOUND = "指定された画像ファイルが見つかりません（拡張用分析）。"
FALLBACK_ENH_FILE_TOO_LARGE = "画像ファイルサイズが大きすぎるため処理できませんでした（拡張用分析）。"


def analyze_image_for_enhancement_gemini(
    image_source: Union[str, Any], # File path or PIL Image object
    user_prompt_override: Optional[str] = None, # Allow overriding the default enhancement prompt
    model_name: str = "gemini-1.5-flash", # Vision capable model
    api_key: Optional[str] = None,
    max_retries: int = 1, # Typically, enhancement analysis might not need as many retries
    initial_wait_time: float = 1.0,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None,
    max_image_size_bytes: int = 20 * 1024 * 1024,
    pil_resize_threshold: tuple[int, int] = (2048, 2048),
    upload_timeout_seconds: int = 180
) -> Optional[str]:
    """
    Analyzes an image to extract detailed elements and descriptions that can be used
    to enrich or enhance blog content, using the Gemini API.
    This is similar to `analyze_image_gemini_enhanced` but uses a prompt more focused
    on extracting "enhancement materials."

    Args:
        image_source (Union[str, Image.Image]): Path to image or PIL Image object.
        user_prompt_override (Optional[str]): If provided, this prompt will be used
            instead of the DEFAULT_IMAGE_ENHANCEMENT_PROMPT.
        model_name, api_key, max_retries, initial_wait_time, generation_config,
        safety_settings, configured_model, max_image_size_bytes, pil_resize_threshold,
        upload_timeout_seconds: Arguments similar to `analyze_image_gemini_enhanced`.

    Returns:
        Optional[str]: A string containing detailed analysis and descriptive elements
                       for content enhancement, or None on failure.
    """
    if not genai and not configured_model:
        logger.error("Gemini SDK not available for enhancement analysis.")
        return None # Or a specific fallback
    if not Image and isinstance(image_source, str):
        logger.error("Pillow (PIL) required for image path for enhancement analysis.")
        return None

    # --- Model Configuration ---
    if configured_model:
        model = configured_model
    elif genai:
        if api_key: genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided/configured for enhancement analysis.")
             return None
        model = genai.GenerativeModel(model_name)
    else: return None

    # --- Image Preparation (similar to analyze_image_gemini_enhanced) ---
    pil_image_obj: Optional[Any] = None
    uploaded_file_obj = None
    image_path_for_upload: Optional[str] = None

    if isinstance(image_source, str):
        if not os.path.exists(image_source):
            logger.error(f"Image file not found: {image_source}")
            return FALLBACK_ENH_FILE_NOT_FOUND
        image_path_for_upload = image_source # Assume it might be used by upload_file
        if os.path.getsize(image_source) > max_image_size_bytes:
            if Image and DEFAULT_RESAMPLING_LANCZOS_ENH:
                try: pil_image_obj = Image.open(image_source)
                except Exception as e:
                    logger.error(f"PIL failed to open large image {image_source}: {e}")
                    return FALLBACK_ENH_FILE_TOO_LARGE
            else: return FALLBACK_ENH_FILE_TOO_LARGE
    elif Image and isinstance(image_source, Image.Image):
        pil_image_obj = image_source
    else:
        logger.error(f"Invalid image_source type: {type(image_source)}")
        return FALLBACK_ENH_ANALYSIS_ERROR

    # --- Prompt ---
    final_prompt = user_prompt_override if user_prompt_override is not None else DEFAULT_IMAGE_ENHANCEMENT_PROMPT

    # --- API Call with Retry ---
    current_retry = 0
    last_exception = None

    while current_retry < max_retries:
        attempt_num = current_retry + 1
        logger.info(f"Image enhancement analysis API call attempt {attempt_num}/{max_retries}")
        api_contents: list[Union[str, Any]] = [final_prompt] # Start with prompt

        # Prefer PIL object if available (e.g., already opened or passed in)
        if pil_image_obj:
            if Image and DEFAULT_RESAMPLING_LANCZOS_ENH: # Ensure Pillow components are available
                temp_pil_image = pil_image_obj # Work on a copy if modifications are needed
                if temp_pil_image.size[0] > pil_resize_threshold[0] or temp_pil_image.size[1] > pil_resize_threshold[1]:
                    temp_pil_image.thumbnail(pil_resize_threshold, DEFAULT_RESAMPLING_LANCZOS_ENH)
                if temp_pil_image.mode != 'RGB': temp_pil_image = temp_pil_image.convert('RGB')
                api_contents.append(temp_pil_image)
                logger.info("Using (potentially resized/converted) PIL Image for API call.")
            else: # Should not happen if initial checks passed
                logger.error("Pillow components missing for PIL object processing.")
                return FALLBACK_ENH_ANALYSIS_ERROR

        # Fallback to upload_file if only path was suitable initially
        elif image_path_for_upload and genai:
            try:
                mime_type = "image/jpeg" # Simplified
                if image_path_for_upload.lower().endswith('.png'): mime_type = "image/png"
                # ... add other mime types
                request_options = {"timeout": upload_timeout_seconds}
                uploaded_file_obj = genai.upload_file(path=image_path_for_upload, mime_type=mime_type, request_options=request_options)
                api_contents.append(uploaded_file_obj)
                logger.info(f"Using genai.upload_file for {image_path_for_upload} (as {uploaded_file_obj.name}).")
            except Exception as e:
                logger.error(f"genai.upload_file failed for {image_path_for_upload}: {e}")
                last_exception = e
                # No immediate retry for upload failure here, will fall through to main retry logic
        else: # No valid image source determined
             logger.error("No valid image data to send to API for enhancement analysis.")
             return FALLBACK_ENH_ANALYSIS_ERROR

        # Check if we actually have an image part in api_contents
        if len(api_contents) < 2: # Only prompt, no image
            logger.warning("No image content was successfully prepared for the API call.")
            # This might happen if upload_file failed and there was no PIL fallback
            # Fall through to retry logic or error out if retries exhausted
            if not last_exception: last_exception = ValueError("Image preparation failed.")

        if last_exception is None: # Proceed only if image prep seemed okay for this attempt
            try:
                response = model.generate_content(
                    api_contents,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                if response.text and response.text.strip():
                    logger.info("Image enhancement analysis successful.")
                    return response.text.strip()
                else:
                    logger.warning(f"Gemini API response empty (Attempt {attempt_num}).")
                    last_exception = ValueError("API returned empty response.")
            except Exception as e:
                logger.error(f"Gemini API error (Attempt {attempt_num}): {e}", exc_info=True)
                last_exception = e

        # Cleanup uploaded file if this attempt used it, before next retry or exiting
        if uploaded_file_obj:
            try: genai.delete_file(uploaded_file_obj.name); uploaded_file_obj = None
            except Exception as del_e: logger.error(f"Error deleting {uploaded_file_obj.name}: {del_e}")

        current_retry += 1
        if current_retry < max_retries:
            time.sleep(initial_wait_time * (2 ** (current_retry -1)))

    logger.error(f"All retries failed for image enhancement analysis. Last error: {last_exception}")
    return None # Or FALLBACK_ENH_ANALYSIS_UNAVAILABLE

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    dummy_image_path_enh = "dummy_enh_image.png"
    if Image and DEFAULT_RESAMPLING_LANCZOS_ENH:
        try:
            img = Image.new('RGB', (250, 150), color = 'lightgreen')
            img.save(dummy_image_path_enh)
            print(f"Created dummy image: {dummy_image_path_enh}")
        except Exception as e:
            print(f"Could not create dummy image: {e}")
            dummy_image_path_enh = None
    else:
        print("Pillow not installed, cannot create dummy image for enhancement analysis test.")
        dummy_image_path_enh = None

    if not genai or not Image or not DEFAULT_RESAMPLING_LANCZOS_ENH:
        print("Skipping enhancement analysis test: Gemini SDK or Pillow not fully available.")
    elif not test_api_key and (genai and not genai.API_KEY):
         print("Skipping test: GOOGLE_API_KEY not set and genai not configured.")
    elif not dummy_image_path_enh or not os.path.exists(dummy_image_path_enh):
        print(f"Skipping test: Dummy image '{dummy_image_path_enh}' not available.")
    else:
        print("\n--- Test Case 1: Analyze image for enhancement (default prompt) ---")
        analysis1 = analyze_image_for_enhancement_gemini(dummy_image_path_enh, api_key=test_api_key)
        if analysis1:
            print(f"Enhancement Analysis (Default Prompt):\n{analysis1[:500]}...")
        else:
            print("Failed to get enhancement analysis (Test 1).")

        custom_prompt_enh = "Identify three distinct textures visible or implied in this image and describe them poetically."
        print("\n--- Test Case 2: Analyze image for enhancement (custom prompt) ---")
        analysis2 = analyze_image_for_enhancement_gemini(
            dummy_image_path_enh,
            user_prompt_override=custom_prompt_enh,
            api_key=test_api_key
        )
        if analysis2:
            print(f"Enhancement Analysis (Custom Prompt):\n{analysis2[:500]}...")
        else:
            print("Failed to get enhancement analysis with custom prompt (Test 2).")

        if os.path.exists(dummy_image_path_enh):
            try: os.remove(dummy_image_path_enh); print(f"Removed dummy image: {dummy_image_path_enh}")
            except Exception as e: print(f"Error removing dummy image {dummy_image_path_enh}: {e}")

    print("\nNote: Live API calls to Gemini Vision models are resource-intensive.")
