import logging
import os
from typing import Optional, Dict, Any, List, Union

# Attempt to import google.generativeai and PIL.Image
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

try:
    from PIL import Image
except ImportError:
    Image = None # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_MULTI_MEDIA_PROMPT_TEMPLATE = """
これらのメディア（画像、動画、テキスト）を統合的に分析し、一つの統一されたブログ記事を作成してください。

分析ポイント:
- 各メディアの内容を詳細に分析（画像は描写、動画はシーンやアクション、音声内容など）
- メディア間の関連性や共通のテーマ、ストーリーを探る
- 提供されたコンテキストテキストとの関連性を考慮
- 統一感のあるストーリーとして記事を構成する

以下の形式で回答してください:
タイトル: [統合記事のタイトル]

本文:
[HTML形式の統合記事の本文。HTMLタグ（<p>, <br>, <strong>など）を使用し、マークダウンは使用しないでください。]
"""

def analyze_multiple_media_gemini(
    media_items: List[Dict[str, str]], # Expected: [{'type': 'image'/'video'/'text', 'path_or_text': 'path/to/file_or_actual_text'}]
    context_text: str = "",
    user_prompt_suffix: str = "", # Optional suffix to add to the main prompt
    model_name: str = "gemini-1.5-pro", # A model known for strong multi-modal capabilities
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_MULTI_MEDIA_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None,
    upload_timeout_seconds: int = 300
) -> Optional[str]:
    """
    Analyzes multiple media items (images, videos, text) and context to generate integrated content.

    Args:
        media_items (List[Dict[str, str]]): A list of dictionaries, where each dict
            represents a media item. Expected keys:
            - 'type': str - "image", "video", or "text".
            - 'path_or_text': str - Filesystem path for "image" or "video",
                                    or the actual text content for "text".
        context_text (str, optional): Additional text providing context for the analysis.
        user_prompt_suffix (str, optional): Text to append to the main analysis prompt,
                                            allowing for more specific instructions.
        model_name (str, optional): Gemini model name. Defaults to "gemini-1.5-pro".
                                    Ignored if `configured_model` is provided.
        api_key (Optional[str], optional): Gemini API key.
                                           Ignored if `configured_model` or pre-configuration.
        prompt_template (str, optional): Template for the main analysis prompt.
        generation_config (Optional[Dict[str, Any]], optional): Generation settings.
        safety_settings (Optional[Dict[str, Any]], optional): Safety settings.
        configured_model (Optional[Any]): Pre-configured `genai.GenerativeModel` instance.
        upload_timeout_seconds (int): Timeout for uploading media files.

    Returns:
        Optional[str]: Generated integrated content (e.g., blog post) as a string, or None on failure.
    """

    if not genai and not configured_model:
        logger.error("Gemini SDK not available and no configured_model provided.")
        return None
    if Image is None and any(item['type'] == 'image' for item in media_items):
        logger.error("Pillow (PIL) is required for image items but not installed.")
        return None

    if configured_model:
        model = configured_model
    elif genai: # genai must exist
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return None
        model = genai.GenerativeModel(model_name)
    else: # Should not be reached
        return None

    # --- Prepare contents for Gemini API ---
    api_contents: List[Union[str, Any]] = [] # PIL.Image.Image or genai.types.File
    uploaded_file_names: List[str] = [] # Keep track of uploaded file names for cleanup

    if context_text:
        api_contents.append(f"関連コンテキストテキスト:\n{context_text}\n---")

    for item in media_items:
        media_type = item.get("type")
        path_or_text = item.get("path_or_text")

        if not media_type or not path_or_text:
            logger.warning(f"Skipping invalid media item: {item}")
            continue

        if media_type == "text":
            api_contents.append(f"提供されたテキスト:\n{path_or_text}\n---")
        elif media_type == "image":
            if not Image: continue # Should have been caught earlier
            if not os.path.exists(path_or_text):
                logger.warning(f"Image file not found: {path_or_text}. Skipping.")
                continue
            try:
                image = Image.open(path_or_text)
                api_contents.append(image)
                logger.info(f"Added image {path_or_text} to API contents.")
            except Exception as e:
                logger.error(f"Error opening image {path_or_text}: {e}", exc_info=True)
        elif media_type == "video":
            if not os.path.exists(path_or_text):
                logger.warning(f"Video file not found: {path_or_text}. Skipping.")
                continue
            uploaded_file = None
            try:
                logger.info(f"Uploading video: {path_or_text} (timeout: {upload_timeout_seconds}s)")
                request_options = {"timeout": upload_timeout_seconds}
                uploaded_file = genai.upload_file(path=path_or_text, request_options=request_options)
                api_contents.append(uploaded_file) # Add the File object
                uploaded_file_names.append(uploaded_file.name)
                logger.info(f"Video {path_or_text} uploaded as {uploaded_file.name}, added to API contents.")
            except Exception as e:
                logger.error(f"Failed to upload video {path_or_text}: {e}", exc_info=True)
                if uploaded_file: # Attempt cleanup if upload started but failed
                    try:
                        genai.delete_file(uploaded_file.name)
                    except Exception as del_e:
                        logger.error(f"Error cleaning up partially uploaded video {uploaded_file.name}: {del_e}")
        else:
            logger.warning(f"Unsupported media type '{media_type}' for item: {item}")

    if not any(c for c in api_contents if not isinstance(c, str) or "関連コンテキストテキスト" not in c and "提供されたテキスト" not in c): # Check if any actual media was added
        logger.warning("No valid media items (image/video) were processed to send to API beyond text.")
        # Depending on desired behavior, could return or proceed if only text items were given.
        # For this snippet, we'll proceed if there's at least some content.
        if not api_contents:
             logger.error("No content (text, image, or video) to analyze.")
             return None


    # Append the main analytical prompt
    final_prompt = prompt_template
    if user_prompt_suffix:
        final_prompt += f"\n\n追加の指示:\n{user_prompt_suffix}"
    api_contents.append(final_prompt)

    try:
        logger.info(f"Attempting Gemini API call for multi-media analysis (Model: {model_name})")
        response = model.generate_content(
            api_contents, # Send the list of parts
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info(f"Gemini multi-media analysis successful. Response length: {len(response.text)}")
            return response.text.strip()
        else:
            logger.warning("Gemini API response for multi-media analysis was empty.")
            return None

    except Exception as e:
        logger.error(f"Gemini API error during multi-media analysis: {e}", exc_info=True)
        return None
    finally:
        # Clean up any uploaded video files
        for file_name in uploaded_file_names:
            try:
                logger.info(f"Deleting uploaded file from Gemini: {file_name}")
                genai.delete_file(file_name)
                logger.info(f"Successfully deleted file: {file_name}")
            except Exception as e:
                logger.error(f"Error deleting uploaded file {file_name}: {e}", exc_info=True)

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    # Dummy files for testing (assumes Pillow and ffmpeg are available for creation)
    dummy_image_path_multi = "dummy_multi_image.png"
    dummy_video_path_multi = "dummy_multi_video.mp4"
    files_created_by_script = []

    if Image:
        try:
            img = Image.new('RGB', (80, 60), color = 'blue')
            img.save(dummy_image_path_multi)
            files_created_by_script.append(dummy_image_path_multi)
            print(f"Created dummy image: {dummy_image_path_multi}")
        except Exception as e:
            print(f"Could not create dummy image for multi-media test: {e}")
            dummy_image_path_multi = None
    else:
        dummy_image_path_multi = None

    if not os.path.exists(dummy_video_path_multi):
        try:
            import subprocess
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            command = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=green:s=320x240:d=1",
                "-vf", "format=yuv420p", dummy_video_path_multi
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            files_created_by_script.append(dummy_video_path_multi)
            print(f"Created dummy video for multi-media test: {dummy_video_path_multi}")
        except Exception as e:
            print(f"Could not create dummy video for multi-media test ({e}).")
            dummy_video_path_multi = None

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)):
        print("Skipping multi-media test: Gemini SDK not available or API key not configured.")
    elif not dummy_image_path_multi or not dummy_video_path_multi:
        print("Skipping multi-media test: Dummy image or video not available.")
    else:
        print("\n--- Test Case: Analyze multiple media items ---")
        test_media_items = [
            {"type": "text", "path_or_text": "This is a day at the park."},
            {"type": "image", "path_or_text": dummy_image_path_multi},
            {"type": "video", "path_or_text": dummy_video_path_multi},
            {"type": "text", "path_or_text": "The weather was sunny and children were playing."}
        ]
        context = "This is a blog post about a family outing."

        result = analyze_multiple_media_gemini(
            media_items=test_media_items,
            context_text=context,
            user_prompt_suffix="Focus on the joyful aspects.",
            api_key=test_api_key,
            model_name="gemini-1.5-flash" # Flash might be more suitable for quicker tests if Pro is too slow/costly
        )

        if result:
            print(f"Generated Content from Multiple Media:\n{result[:600]}...")
        else:
            print("Failed to generate content from multiple media.")

    # Clean up dummy files created by this script
    for f_path in files_created_by_script:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
                print(f"Removed dummy file: {f_path}")
            except Exception as e:
                print(f"Error removing dummy file {f_path}: {e}")

    print("\nNote: Multi-modal analysis with Gemini can be complex and resource-intensive.")
    print("Ensure you use a model capable of handling all provided media types.")
