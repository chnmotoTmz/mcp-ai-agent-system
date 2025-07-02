import logging
import os
import time # For potential retries, though not explicitly implemented here yet
from typing import Optional, Dict, Any

# Attempt to import google.generativeai, but don't fail if not installed.
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

# Default prompt template for analyzing a video and generating a blog post
DEFAULT_VIDEO_BLOG_PROMPT_TEMPLATE = """
{user_prompt}

この動画について詳しく分析し、ブログ記事を作成してください。

分析ポイント:
- 動画の内容やシーンを詳細に描写
- 音声がある場合はその内容も分析（可能であれば）
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
"""

def analyze_video_gemini(
    video_path: str,
    user_prompt: str = "この動画について詳しく説明してください",
    model_name: str = "gemini-1.5-flash", # Ensure this model supports video analysis
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_VIDEO_BLOG_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None, # Allow passing an already configured GenerativeModel instance
    upload_timeout_seconds: int = 300 # Timeout for genai.upload_file
) -> Optional[str]:
    """
    Analyzes a video and generates a blog post using the Gemini API.
    This function first uploads the video using `genai.upload_file`.

    Args:
        video_path (str): Path to the video file.
        user_prompt (str, optional): A specific prompt to guide the video analysis.
            Defaults to "この動画について詳しく説明してください".
        model_name (str, optional): The name of the Gemini model to use (must support video).
            Defaults to "gemini-1.5-flash". Ignored if `configured_model` is provided.
        api_key (Optional[str], optional): The Gemini API key.
            Ignored if `configured_model` is provided or genai is pre-configured.
        prompt_template (str, optional): Template for the full prompt.
            Must include a `{user_prompt}` placeholder.
            Defaults to DEFAULT_VIDEO_BLOG_PROMPT_TEMPLATE.
        generation_config (Optional[Dict[str, Any]], optional): Config for content generation.
        safety_settings (Optional[Dict[str, Any]], optional): Safety settings.
        configured_model (Optional[Any]): An already initialized `genai.GenerativeModel`.
        upload_timeout_seconds (int): Timeout in seconds for uploading the video file.

    Returns:
        Optional[str]: The generated blog post (title and HTML content) as a string if successful,
                       None otherwise.
    """
    if not genai and not configured_model:
        logger.error("Gemini SDK (google.generativeai) not available and no configured_model provided.")
        return None

    if not os.path.exists(video_path):
        logger.error(f"Video file not found at path: {video_path}")
        return None

    if configured_model:
        model = configured_model
    elif genai: # genai must exist here
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return None
        model = genai.GenerativeModel(model_name)
    else: # Should not be reached
        return None

    uploaded_file = None
    try:
        logger.info(f"Uploading video file: {video_path} (timeout: {upload_timeout_seconds}s)")
        # The upload_file function might be long-running.
        # Consider how to handle timeouts or make it truly async if needed in a larger app.
        # For a snippet, a simple blocking call with timeout (if supported by SDK version) is shown.
        # Note: As of early 2024, genai.upload_file itself doesn't have a direct timeout parameter.
        # This timeout would need to be handled by the calling mechanism if long uploads are an issue.
        # The `request_options` can sometimes be used for underlying transport timeouts.
        request_options = {"timeout": upload_timeout_seconds} if upload_timeout_seconds else {}
        uploaded_file = genai.upload_file(path=video_path, request_options=request_options)
        logger.info(f"Video file uploaded successfully: {uploaded_file.name} ({uploaded_file.uri})")
    except Exception as e:
        logger.error(f"Failed to upload video file '{video_path}': {e}", exc_info=True)
        if uploaded_file: # Clean up if upload started but failed to complete in some way
            try:
                genai.delete_file(uploaded_file.name)
                logger.info(f"Cleaned up partially uploaded file: {uploaded_file.name}")
            except Exception as del_e:
                logger.error(f"Error cleaning up file {uploaded_file.name}: {del_e}")
        return None


    full_prompt = prompt_template.format(user_prompt=user_prompt)
    contents = [full_prompt, uploaded_file] # Pass the File object

    try:
        logger.info(f"Attempting Gemini API call for video analysis (Model: {model_name})")
        response = model.generate_content(
            contents,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info(f"Gemini video analysis successful. Response length: {len(response.text)}")
            return response.text.strip()
        else:
            logger.warning("Gemini API response for video analysis was empty or whitespace only.")
            return None

    except Exception as e:
        logger.error(f"Gemini API error during video analysis: {e}", exc_info=True)
        return None
    finally:
        # Clean up the uploaded file from Google's servers
        if uploaded_file:
            try:
                logger.info(f"Deleting uploaded video file from Gemini: {uploaded_file.name}")
                genai.delete_file(uploaded_file.name)
                logger.info(f"Successfully deleted video file: {uploaded_file.name}")
            except Exception as e:
                logger.error(f"Error deleting uploaded video file {uploaded_file.name}: {e}", exc_info=True)


# Example Usage (requires google.generativeai, an API key, and a test video file)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_api_key = os.getenv("GOOGLE_API_KEY")

    # For testing, you'd need a small video file.
    # Let's assume a file 'test_video.mp4' exists in the same directory.
    # Creating a dummy video programmatically is complex, so we'll rely on an existing file.
    dummy_video_path = "test_video.mp4" # Replace with your test video path

    # Create a small dummy MP4 if ffmpeg is available for more robust testing, otherwise skip.
    # This is an advanced step for local testing; for CI, you might provide a small video file.
    if not os.path.exists(dummy_video_path):
        try:
            import subprocess
            # Check if ffmpeg is installed
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            # Create a 1-second black video
            command = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1",
                "-vf", "format=yuv420p", dummy_video_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Created dummy video for testing: {dummy_video_path}")
        except (ImportError, FileNotFoundError, subprocess.CalledProcessError) as e:
            print(f"Could not create dummy video ({e}). Please provide a '{dummy_video_path}' or tests will be skipped.")
            dummy_video_path = None # Ensure it's None if creation fails


    if not genai:
        print("Skipping test: Gemini SDK not installed.")
    elif not test_api_key and (genai and not genai.API_KEY):
         print("Skipping test: GOOGLE_API_KEY not set and genai not configured.")
    elif not dummy_video_path or not os.path.exists(dummy_video_path):
        print(f"Skipping test: Test video '{dummy_video_path or 'test_video.mp4'}' not available.")
    else:
        print(f"\n--- Test Case 1: Analyze video '{dummy_video_path}' with default prompt ---")
        result1 = analyze_video_gemini(dummy_video_path, api_key=test_api_key)
        if result1:
            print(f"Generated Blog from Video:\n{result1[:500]}...")
        else:
            print(f"Failed to generate blog from video '{dummy_video_path}'.")

        print(f"\n--- Test Case 2: Analyze video '{dummy_video_path}' with a custom user prompt ---")
        custom_prompt_vid = "Describe this video focusing on any surprising elements."
        result2 = analyze_video_gemini(
            dummy_video_path,
            user_prompt=custom_prompt_vid,
            api_key=test_api_key
        )
        if result2:
            print(f"Generated Blog (Custom Video Prompt):\n{result2[:500]}...")
        else:
            print("Failed to generate blog with custom video prompt.")

        # Clean up dummy video if created by this script
        if "ffmpeg" in locals() and os.path.exists(dummy_video_path) and "lavfi" in " ".join(command): # A bit heuristic
             try:
                os.remove(dummy_video_path)
                print(f"Removed dummy video: {dummy_video_path}")
             except Exception as e:
                print(f"Error removing dummy video {dummy_video_path}: {e}")


    print("\nNote: Video analysis with Gemini can be time-consuming and costly.")
    print("Ensure you are using a model that supports video input (e.g., 'gemini-1.5-pro' or 'gemini-1.5-flash' for some video tasks).")
    print("File uploads and deletions are managed via the Gemini API.")
