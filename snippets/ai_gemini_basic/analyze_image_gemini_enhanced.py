import logging
import os
import time # For retry logic
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
        DEFAULT_RESAMPLING_LANCZOS = Image.Resampling.LANCZOS
    else: # Fallback for older Pillow versions
        DEFAULT_RESAMPLING_LANCZOS = Image.LANCZOS # type: ignore
except ImportError:
    Image = None # type: ignore
    DEFAULT_RESAMPLING_LANCZOS = None


logger = logging.getLogger(__name__)

DEFAULT_IMAGE_ANALYSIS_PROMPT_TEMPLATE = """
{user_prompt}

要求事項:
- 画像の内容を詳細に分析してください
- 客観的で正確な説明をしてください
- 興味深い観点があれば追加してください
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 分析結果はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）
"""

FALLBACK_ANALYSIS_UNAVAILABLE = "画像が添付されていますが、詳細分析は一時的に利用できません。"
FALLBACK_ANALYSIS_ERROR = "画像分析中にエラーが発生しました。"
FALLBACK_FILE_NOT_FOUND = "指定された画像ファイルが見つかりません。"
FALLBACK_FILE_TOO_LARGE = "画像ファイルサイズが大きすぎるため処理できませんでした。"


def analyze_image_gemini_enhanced(
    image_source: Union[str, Any], # File path or PIL Image object
    user_prompt: str = "この画像について詳しく説明してください",
    model_name: str = "gemini-1.5-flash", # Vision capable model
    api_key: Optional[str] = None,
    max_retries: int = 2,
    initial_wait_time: float = 1.0,
    prompt_template: str = DEFAULT_IMAGE_ANALYSIS_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None,
    max_image_size_bytes: int = 20 * 1024 * 1024, # 20MB
    pil_resize_threshold: tuple[int, int] = (2048, 2048), # Resize if larger than this
    upload_timeout_seconds: int = 180
) -> str: # Returns analysis string or a fallback message
    """
    Analyzes an image using Gemini API with enhanced features like retry logic,
    file size checks, multiple upload methods (genai.upload_file vs PIL Image),
    and image resizing for PIL method.

    Args:
        image_source (Union[str, Image.Image]): Path to image or PIL Image object.
        user_prompt (str): Specific prompt for analysis.
        model_name (str): Gemini vision model name.
        api_key (Optional[str]): Gemini API key.
        max_retries (int): Max retries for API calls.
        initial_wait_time (float): Initial wait time for retries.
        prompt_template (str): Template for the full analysis prompt.
        generation_config (Optional[Dict[str, Any]]): Generation settings.
        safety_settings (Optional[Dict[str, Any]]): Safety settings.
        configured_model: Pre-configured `genai.GenerativeModel` instance.
        max_image_size_bytes (int): Max file size for `genai.upload_file`.
        pil_resize_threshold (tuple[int, int]): Dimensions (width, height) above which
                                                PIL images will be resized.
        upload_timeout_seconds (int): Timeout for genai.upload_file (conceptual, actual support varies).


    Returns:
        str: Image analysis result as a string, or a fallback error/status message.
    """
    if not genai and not configured_model:
        logger.error("Gemini SDK not available and no configured_model provided.")
        return FALLBACK_ANALYSIS_ERROR
    if not Image and isinstance(image_source, str): # Pillow needed if path is string
        logger.error("Pillow (PIL) is required to open image paths but not installed.")
        return FALLBACK_ANALYSIS_ERROR

    # --- Model Configuration ---
    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return FALLBACK_ANALYSIS_ERROR
        model = genai.GenerativeModel(model_name) # Ensure this model is vision-capable
    else: # Should not be reached
        return FALLBACK_ANALYSIS_ERROR

    # --- Image Preparation ---
    pil_image_obj: Optional[Any] = None # PIL.Image.Image
    uploaded_file_obj = None # genai.types.File

    if isinstance(image_source, str): # Path provided
        if not os.path.exists(image_source):
            logger.error(f"Image file not found: {image_source}")
            return FALLBACK_FILE_NOT_FOUND

        file_size = os.path.getsize(image_source)
        if file_size > max_image_size_bytes:
            logger.warning(f"File size {file_size} bytes exceeds limit {max_image_size_bytes} bytes.")
            # Try to open with PIL and resize as a fallback for large files if upload_file might fail
            if Image:
                try:
                    pil_image_obj = Image.open(image_source)
                    logger.info(f"Opened large file {image_source} with PIL for potential resizing.")
                except Exception as e:
                    logger.error(f"Could not open large image {image_source} with PIL: {e}")
                    return FALLBACK_FILE_TOO_LARGE # Or more generic error
            else: # No PIL to resize
                return FALLBACK_FILE_TOO_LARGE
        # If not too large, image_path will be used by genai.upload_file later
        image_path_for_upload = image_source

    elif Image and isinstance(image_source, Image.Image):
        pil_image_obj = image_source
        image_path_for_upload = None # We have a PIL object, not a path for upload_file
    else:
        logger.error(f"Invalid image_source type: {type(image_source)}. Must be path string or PIL Image.")
        return FALLBACK_ANALYSIS_ERROR

    # --- Prompt ---
    full_prompt = prompt_template.format(user_prompt=user_prompt)

    # --- API Call with Retry Logic ---
    current_retry = 0
    last_exception = None

    while current_retry < max_retries:
        attempt_num = current_retry + 1
        logger.info(f"Image analysis API call attempt {attempt_num}/{max_retries}")
        api_contents = [full_prompt]

        try:
            # Method 1: Use genai.upload_file if image_path_for_upload is available and no PIL object yet for it
            if image_path_for_upload and not pil_image_obj: # i.e. path was given and file not too large initially
                logger.info(f"Attempting analysis using genai.upload_file for {image_path_for_upload}")
                # Determine MIME type (simplified)
                mime_type = "image/jpeg"
                if image_path_for_upload.lower().endswith('.png'): mime_type = "image/png"
                elif image_path_for_upload.lower().endswith('.webp'): mime_type = "image/webp"
                elif image_path_for_upload.lower().endswith('.gif'): mime_type = "image/gif"

                request_options = {"timeout": upload_timeout_seconds}
                uploaded_file_obj = genai.upload_file(path=image_path_for_upload, mime_type=mime_type, request_options=request_options)
                api_contents.append(uploaded_file_obj)
                logger.info(f"File {image_path_for_upload} uploaded as {uploaded_file_obj.name}")

            # Method 2: Use PIL Image object (if provided directly, or as fallback for large files, or if upload_file failed)
            elif pil_image_obj:
                logger.info("Attempting analysis using PIL Image object.")
                # Resize if necessary
                if pil_image_obj.size[0] > pil_resize_threshold[0] or pil_image_obj.size[1] > pil_resize_threshold[1]:
                    pil_image_obj.thumbnail(pil_resize_threshold, DEFAULT_RESAMPLING_LANCZOS)
                    logger.info(f"Resized PIL image to: {pil_image_obj.size}")
                # Convert to RGB if not already (common requirement for models)
                if pil_image_obj.mode != 'RGB':
                    pil_image_obj = pil_image_obj.convert('RGB')
                api_contents.append(pil_image_obj)
            else: # Should not happen if logic is correct
                 logger.error("No valid image data (path or PIL object) to send to API.")
                 return FALLBACK_ANALYSIS_ERROR


            response = model.generate_content(
                api_contents,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            if response.text and response.text.strip():
                logger.info("Gemini image analysis successful.")
                return response.text.strip()
            else:
                logger.warning(f"Gemini API response was empty (Attempt {attempt_num}).")
                last_exception = ValueError("API returned empty response.") # Treat as an error to allow retry

        except Exception as e:
            logger.error(f"Gemini API error on attempt {attempt_num}: {e}", exc_info=True)
            last_exception = e # Store last known exception

        # If we are here, it's either an error or empty response
        current_retry += 1
        if current_retry < max_retries:
            wait_time = initial_wait_time * (2 ** (current_retry -1))
            logger.info(f"Waiting {wait_time:.2f} seconds before next retry...")
            time.sleep(wait_time)

        # Cleanup uploaded file if this attempt used it and failed, before next retry or exiting
        if uploaded_file_obj:
            try:
                logger.info(f"Cleaning up (deleting) file {uploaded_file_obj.name} after failed attempt.")
                genai.delete_file(uploaded_file_obj.name)
                uploaded_file_obj = None # Reset for next attempt or if loop exits
            except Exception as del_e:
                logger.error(f"Error deleting uploaded file {uploaded_file_obj.name} during retries: {del_e}")

    # All retries failed
    logger.error(f"All {max_retries} retry attempts failed for image analysis. Last error: {last_exception}")
    return FALLBACK_ANALYSIS_UNAVAILABLE


# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    dummy_image_path_enhanced = "dummy_enhanced_image.jpg"
    if Image and DEFAULT_RESAMPLING_LANCZOS: # Check if Pillow is available
        try:
            img = Image.new('RGB', (300, 200), color = 'skyblue')
            img.save(dummy_image_path_enhanced)
            print(f"Created dummy image: {dummy_image_path_enhanced}")
        except Exception as e:
            print(f"Could not create dummy image: {e}")
            dummy_image_path_enhanced = None
    else:
        print("Pillow not installed, cannot create dummy image for enhanced analysis test.")
        dummy_image_path_enhanced = None

    if not genai or not Image or not DEFAULT_RESAMPLING_LANCZOS:
        print("Skipping enhanced image analysis test: Gemini SDK or Pillow not fully available.")
    elif not test_api_key and (genai and not genai.API_KEY):
         print("Skipping test: GOOGLE_API_KEY not set and genai not configured.")
    elif not dummy_image_path_enhanced or not os.path.exists(dummy_image_path_enhanced):
        print(f"Skipping test: Dummy image '{dummy_image_path_enhanced}' not available.")
    else:
        print("\n--- Test Case 1: Analyze image with enhanced function (path) ---")
        analysis1 = analyze_image_gemini_enhanced(dummy_image_path_enhanced, api_key=test_api_key)
        print(f"Analysis (Enhanced, Path):\n{analysis1[:500]}...")

        print("\n--- Test Case 2: Analyze image with enhanced function (PIL object) ---")
        try:
            pil_img = Image.open(dummy_image_path_enhanced)
            analysis2 = analyze_image_gemini_enhanced(pil_img, user_prompt="Describe the colors in this image.", api_key=test_api_key)
            print(f"Analysis (Enhanced, PIL Object):\n{analysis2[:500]}...")
        except Exception as e:
            print(f"Failed to run PIL object test: {e}")

        # Clean up dummy image
        if dummy_image_path_enhanced and os.path.exists(dummy_image_path_enhanced):
            try:
                os.remove(dummy_image_path_enhanced)
                print(f"Removed dummy image: {dummy_image_path_enhanced}")
            except Exception as e:
                print(f"Error removing dummy image {dummy_image_path_enhanced}: {e}")

    print("\nNote: Live API calls to Gemini Vision models cost money and depend on network.")
