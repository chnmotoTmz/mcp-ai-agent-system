import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, Dict # Added Dict, Any

# Attempt to import LineBotApi and related classes
try:
    # For SDK v3
    from linebot.v3.messaging import Configuration, ApiClient, MessagingApiBlob
    from linebot.v3.exceptions import ApiException as LineApiExceptionV3
    # For older SDK (line-bot-sdk < 3.0.0)
    # from linebot import LineBotApi as LineBotApiV1
    # from linebot.exceptions import LineBotApiError as LineApiErrorV1
    LINE_SDK_AVAILABLE = True # Assume v3 is primary for new snippets
except ImportError:
    LINE_SDK_AVAILABLE = False
    # Mock classes for standalone execution without SDK
    class Configuration: pass
    class ApiClient: pass
    class MessagingApiBlob: pass # This is the one for getting content in v3
    class LineApiExceptionV3(Exception): pass
    # class LineBotApiV1: pass
    # class LineApiErrorV1(Exception): pass

logger = logging.getLogger(__name__)

def get_line_content_extension(content_type_from_webhook: str) -> str:
    """
    Determines a file extension based on the content type string
    often provided by LINE webhooks (e.g., 'image', 'video', 'audio').

    Args:
        content_type_from_webhook (str): The content type string (e.g., "image", "video").

    Returns:
        str: The corresponding file extension (e.g., ".jpg", ".mp4").
             Defaults to ".bin" for unknown types.
    """
    # This mapping is based on common LINE content types.
    # For images, LINE often converts to JPEG. For audio, often m4a.
    # Videos are usually mp4.
    extensions: Dict[str, str] = {
        'image': '.jpg',  # LINE typically converts images to JPEG when you download them.
        'video': '.mp4',
        'audio': '.m4a',
        # Add other types if needed, e.g., 'file': '.pdf' (if LINE sends files with specific types)
    }
    return extensions.get(content_type_from_webhook.lower(), '.bin')

def download_line_content(
    channel_access_token: str,
    message_id: str,
    download_directory: Union[str, Path],
    filename_prefix: Optional[str] = None, # e.g., "user123_"
    content_type_hint: Optional[str] = "image", # Helps determine extension if not obvious
    line_bot_api_client: Optional[Any] = None, # MessagingApiBlob (v3) or LineBotApi (v1)
    sdk_version: int = 3
) -> Optional[str]:
    """
    Downloads content (image, video, audio) associated with a LINE message ID.

    Args:
        channel_access_token (str): LINE Channel Access Token.
        message_id (str): The ID of the message whose content is to be downloaded.
        download_directory (Union[str, Path]): The directory to save the downloaded file.
        filename_prefix (Optional[str]): A prefix for the filename. If None, a timestamp
                                         and message ID will be used.
        content_type_hint (Optional[str]): A hint for the content type (e.g., "image", "video")
                                           to help determine the file extension. Defaults to "image".
        line_bot_api_client (Optional[Any]): Pre-configured MessagingApiBlob (v3) or LineBotApi (v1).
        sdk_version (int): Major version of the line-bot-sdk (3 or 1).

    Returns:
        Optional[str]: The full path to the downloaded file if successful, None otherwise.
    """
    if not LINE_SDK_AVAILABLE: # Simplified check, assumes v3 primarily
        logger.error("LINE Bot SDK not found. Please install 'line-bot-sdk'.")
        return None

    # --- Client Initialization ---
    actual_bot_api_blob = None # For v3
    # actual_bot_api_v1 = None # For v1
    if line_bot_api_client:
        if sdk_version == 3: actual_bot_api_blob = line_bot_api_client
        # elif sdk_version == 1: actual_bot_api_v1 = line_bot_api_client
    elif sdk_version == 3 and LINE_SDK_AVAILABLE:
        if not channel_access_token:
            logger.error("Channel access token required for LINE SDK v3 (blob) client.")
            return None
        configuration = Configuration(access_token=channel_access_token)
        actual_bot_api_blob = MessagingApiBlob(ApiClient(configuration))
    # Elif for SDK v1
    # elif sdk_version == 1 and LINE_SDK_AVAILABLE: # (Assuming LINE_SDK_V1_AVAILABLE was defined)
    #     if not channel_access_token:
    #         logger.error("Channel access token required for LINE SDK v1 client.")
    #         return None
    #     actual_bot_api_v1 = LineBotApiV1(channel_access_token)
    else:
        logger.error(f"Unsupported SDK version ({sdk_version}) or SDK not available for download.")
        return None

    # --- File Path Preparation ---
    download_dir = Path(download_directory)
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create download directory {download_dir}: {e}")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    extension = get_line_content_extension(content_type_hint or "unknown")

    base_filename = f"{message_id}{extension}"
    if filename_prefix:
        filename = f"{filename_prefix}{timestamp}_{base_filename}"
    else:
        filename = f"{timestamp}_{base_filename}"

    file_path = download_dir / filename

    # --- API Call & Download ---
    try:
        logger.info(f"Attempting to download content for message ID {message_id} to {file_path}")

        if sdk_version == 3 and actual_bot_api_blob:
            # SDK v3 get_message_content returns a file-like object (generator)
            # The SDK handles opening and streaming the content.
            # We need to iterate over the chunks and write to our file.
            # The response is directly the content bytes (StreamingBody).
            message_content_stream = actual_bot_api_blob.get_message_content(message_id=message_id)

            with open(file_path, 'wb') as f:
                for chunk in message_content_stream: # Iterate over bytes
                    f.write(chunk)
            message_content_stream.close() # Important to close the stream

        # Elif for SDK v1
        # elif sdk_version == 1 and actual_bot_api_v1:
        #     message_content = actual_bot_api_v1.get_message_content(message_id) # Returns MessageContent object
        #     with open(file_path, 'wb') as f:
        #         for chunk in message_content.iter_content():
        #             f.write(chunk)
        else: # Should not be reached if client init was correct
            logger.error("No valid API client for download.")
            return None

        logger.info(f"Content for message ID {message_id} downloaded successfully to: {file_path}")
        return str(file_path)

    except LineApiExceptionV3 as e_v3:
        logger.error(f"LINE API Error (v3) downloading content for message {message_id}: Status {e_v3.status} - Body {e_v3.body}")
        return None
    # except LineApiErrorV1 as e_v1:
    #     logger.error(f"LINE API Error (v1) downloading content for message {message_id}: Status {e_v1.status_code} - Error {e_v1.error.message}")
    #     return None
    except Exception as e:
        logger.error(f"Unexpected error downloading content for message {message_id}: {e}", exc_info=True)
        if file_path.exists(): # Attempt to clean up partially downloaded file
            try: os.remove(file_path)
            except OSError: pass
        return None

# Example Usage
if __name__ == "__main__":
    from pathlib import Path
    import shutil # For cleaning up test directory

    logging.basicConfig(level=logging.INFO)

    # IMPORTANT: For this test to work, you need:
    # 1. A valid LINE Channel Access Token.
    # 2. A valid `message_id` from a message sent by a user to your bot that CONTAINS CONTENT (image, video, audio).
    #    You can get this from webhook events. Text message IDs won't work for content download.
    try:
        LINE_CHANNEL_TOKEN_DOWNLOAD = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        # Replace with a REAL message ID that has downloadable content from your bot's logs/webhook
        LINE_CONTENT_MESSAGE_ID = os.environ.get("LINE_CONTENT_MESSAGE_ID_FOR_TEST")
    except KeyError:
        print("Please set LINE_CHANNEL_ACCESS_TOKEN environment variable.")
        LINE_CHANNEL_TOKEN_DOWNLOAD = None
        LINE_CONTENT_MESSAGE_ID = None

    TEST_DOWNLOAD_DIR = Path("./line_downloads_test")

    if not LINE_SDK_AVAILABLE:
        print("LINE Bot SDK (v3) is not installed. Skipping download tests.")
    elif not LINE_CHANNEL_TOKEN_DOWNLOAD:
        print("LINE_CHANNEL_ACCESS_TOKEN not set. Skipping download tests.")
    elif not LINE_CONTENT_MESSAGE_ID:
        print("LINE_CONTENT_MESSAGE_ID_FOR_TEST not set in environment. Skipping live download test.")
        print("To test, send an image/video to your bot and use that message ID.")
    else:
        print(f"--- Test Case 1: Download content for message ID {LINE_CONTENT_MESSAGE_ID} ---")
        # Assuming the content is an image for this test's content_type_hint
        downloaded_file_path = download_line_content(
            channel_access_token=LINE_CHANNEL_TOKEN_DOWNLOAD,
            message_id=LINE_CONTENT_MESSAGE_ID,
            download_directory=TEST_DOWNLOAD_DIR,
            content_type_hint="image" # Adjust if your test message_id has different content
        )

        if downloaded_file_path:
            print(f"Content downloaded to: {downloaded_file_path}")
            assert Path(downloaded_file_path).exists()
            assert Path(downloaded_file_path).is_file()
            assert Path(downloaded_file_path).stat().st_size > 0 # Check file is not empty
        else:
            print(f"Failed to download content for message ID {LINE_CONTENT_MESSAGE_ID}.")

        print("\n--- Test Case 2: Download with a filename prefix ---")
        downloaded_file_path_prefix = download_line_content(
            channel_access_token=LINE_CHANNEL_TOKEN_DOWNLOAD,
            message_id=LINE_CONTENT_MESSAGE_ID, # Use the same ID
            download_directory=TEST_DOWNLOAD_DIR,
            filename_prefix="mybot_",
            content_type_hint="image" # Adjust if different
        )
        if downloaded_file_path_prefix:
            print(f"Content with prefix downloaded to: {downloaded_file_path_prefix}")
            assert Path(downloaded_file_path_prefix).name.startswith("mybot_")
        else:
            print("Failed to download content with prefix.")

        # Clean up test directory
        if TEST_DOWNLOAD_DIR.exists():
            try:
                shutil.rmtree(TEST_DOWNLOAD_DIR)
                print(f"\nCleaned up test directory: {TEST_DOWNLOAD_DIR}")
            except Exception as e:
                print(f"\nError cleaning up test directory {TEST_DOWNLOAD_DIR}: {e}")

    print("\nNote: Live LINE API calls for content download require a message ID with actual content.")
    print("Ensure the bot has permission and the message ID is valid.")
