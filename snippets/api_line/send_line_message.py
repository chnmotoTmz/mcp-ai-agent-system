import logging
import os
from typing import Optional, List, Union, Dict, Any

# Attempt to import LineBotApi and related classes
try:
    from linebot.v3.messaging import (
        Configuration,
        ApiClient,
        MessagingApi,
        PushMessageRequest,
        TextMessage,
        # Other message types can be imported as needed:
        # ImageMessage, VideoMessage, AudioMessage, LocationMessage, StickerMessage, TemplateMessage
    )
    from linebot.v3.exceptions import ApiException as LineApiExceptionV3
    # For older SDK (line-bot-sdk < 3.0.0)
    # from linebot import LineBotApi as LineBotApiV1
    # from linebot.exceptions import LineBotApiError as LineApiErrorV1
    # from linebot.models import TextSendMessage as TextSendMessageV1
    LINE_SDK_V3_AVAILABLE = True
except ImportError:
    LINE_SDK_V3_AVAILABLE = False
    # Mock classes or indicate unavailability if needed for standalone execution without SDK
    class Configuration: pass
    class ApiClient: pass
    class MessagingApi: pass
    class PushMessageRequest: pass
    class TextMessage: pass
    class LineApiExceptionV3(Exception): pass
    # For older SDK:
    # class LineBotApiV1: pass
    # class LineApiErrorV1(Exception): pass
    # class TextSendMessageV1: pass


logger = logging.getLogger(__name__)

def send_line_message(
    channel_access_token: str,
    user_id: str,
    messages: Union[List[Dict[str, Any]], Dict[str, Any], str], # Can be a single message dict, list of dicts, or simple text
    line_bot_api_client: Optional[Any] = None, # Allow passing a pre-configured MessagingApi (v3) or LineBotApi (v1)
    sdk_version: int = 3 # Specify SDK version, default to 3
) -> bool:
    """
    Sends one or more messages to a specified LINE user using their user ID.
    Supports both line-bot-sdk v3 (default) and older v1 (if specified).

    Args:
        channel_access_token (str): LINE Channel Access Token.
        user_id (str): The user ID of the recipient.
        messages (Union[List[Dict[str, Any]], Dict[str, Any], str]):
            - For SDK v3: A list of Message objects (e.g., [TextMessage(...)]) or a single Message object.
                         For simplicity in this snippet, if a string is passed, it's wrapped in TextMessage.
                         If a dict is passed, it's assumed to be a single Message-like dict (e.g. TextMessage.from_dict).
                         If a list of dicts, assumed to be list of Message-like dicts.
            - For SDK v1: A list of SendMessage objects or a single SendMessage object.
                         If a string is passed, it's wrapped in TextSendMessageV1.
        line_bot_api_client (Optional[Any]): An already initialized MessagingApi (for v3)
                                             or LineBotApi (for v1) instance.
                                             If provided, channel_access_token is ignored for client init.
        sdk_version (int): The major version of the line-bot-sdk being used (e.g., 3 or 1).

    Returns:
        bool: True if the message(s) were sent successfully, False otherwise.
    """
    if not LINE_SDK_V3_AVAILABLE and sdk_version == 3:
        logger.error("LINE Bot SDK v3 not found, but specified. Please install 'line-bot-sdk>=3.0.0'.")
        return False
    # Add similar check for v1 if you need to support it more robustly without v3 present
    # if not LINE_SDK_V1_AVAILABLE and sdk_version == 1:
    #     logger.error("LINE Bot SDK v1 not found, but specified. Please install 'line-bot-sdk<3.0.0'.")
    #     return False


    # --- Client Initialization ---
    actual_bot_api = None
    if line_bot_api_client:
        actual_bot_api = line_bot_api_client
    elif sdk_version == 3 and LINE_SDK_V3_AVAILABLE:
        if not channel_access_token:
            logger.error("Channel access token is required for LINE SDK v3 when client not provided.")
            return False
        configuration = Configuration(access_token=channel_access_token)
        actual_bot_api = MessagingApi(ApiClient(configuration))
    # Elif for SDK v1 initialization (if supporting it)
    # elif sdk_version == 1 and LINE_SDK_V1_AVAILABLE:
    #     if not channel_access_token:
    #         logger.error("Channel access token is required for LINE SDK v1 when client not provided.")
    #         return False
    #     actual_bot_api = LineBotApiV1(channel_access_token)
    else:
        logger.error(f"Unsupported SDK version ({sdk_version}) or SDK not available.")
        return False

    # --- Message Preparation ---
    message_objects_to_send = []
    if isinstance(messages, str): # Simple text message
        if sdk_version == 3 and LINE_SDK_V3_AVAILABLE:
            message_objects_to_send.append(TextMessage(text=messages))
        # elif sdk_version == 1 and LINE_SDK_V1_AVAILABLE:
        #     message_objects_to_send.append(TextSendMessageV1(text=messages))
    elif isinstance(messages, dict): # Single message object (or dict for v3)
        if sdk_version == 3 and LINE_SDK_V3_AVAILABLE:
             # Attempt to create from dict if it looks like a message model
            if "type" in messages: # Heuristic for SDK v3 message models
                try:
                    # This is a simplified way; robustly creating from_dict would need to know the type
                    # For now, we'll assume if it's a dict, it's likely a TextMessage for simplicity
                    if messages.get("type") == "text" and "text" in messages:
                         message_objects_to_send.append(TextMessage(text=messages["text"]))
                    else: # For other types, user should pass the actual Message object
                        logger.warning(f"Received a dict for SDKv3 message, but it's not a simple text. Pass Message objects directly. Dict: {messages}")
                        # Or try a generic model creation if SDK supports it easily based on 'type'
                except Exception as e:
                    logger.error(f"Failed to create SDKv3 Message from dict: {e}")
                    return False
            else: # Assume it's already a Message object if not a dict with type
                 message_objects_to_send.append(messages) # User passes actual Message object
        # elif sdk_version == 1 and LINE_SDK_V1_AVAILABLE:
        #     message_objects_to_send.append(messages) # User passes SendMessage object
    elif isinstance(messages, list):
        if sdk_version == 3 and LINE_SDK_V3_AVAILABLE:
            for msg_item in messages:
                if isinstance(msg_item, str):
                    message_objects_to_send.append(TextMessage(text=msg_item))
                elif isinstance(msg_item, dict) and "type" in msg_item and msg_item.get("type") == "text" and "text" in msg_item :
                     message_objects_to_send.append(TextMessage(text=msg_item["text"]))
                elif hasattr(msg_item, 'type'): # Check if it's already a Message object
                    message_objects_to_send.append(msg_item)
                else:
                    logger.warning(f"Skipping invalid message item in list for SDKv3: {msg_item}")
        # elif sdk_version == 1 and LINE_SDK_V1_AVAILABLE:
        #     for msg_item in messages: # Assume items are SendMessage objects or strings
        #         if isinstance(msg_item, str): message_objects_to_send.append(TextSendMessageV1(text=msg_item))
        #         else: message_objects_to_send.append(msg_item) # Assume SendMessage object
    else:
        logger.error(f"Invalid 'messages' type: {type(messages)}. Must be str, dict, list, or Message object.")
        return False

    if not message_objects_to_send:
        logger.warning("No valid messages to send.")
        return False

    # --- API Call ---
    try:
        if not user_id or not isinstance(user_id, str):
            logger.error(f"Invalid user_id: {user_id}")
            return False

        # Test user ID handling (from original code)
        if user_id.startswith('test_') or user_id == 'test_user':
            logger.info(f"Test message send (actual sending skipped): To {user_id} -> Messages: {message_objects_to_send}")
            return True # Simulate success for test users

        # LINE User ID format check (U or C for users/groups, R for rooms)
        if not (user_id.startswith('U') or user_id.startswith('C') or user_id.startswith('R')):
            logger.warning(f"Possible invalid LINE user_id format: {user_id}")

        if sdk_version == 3 and LINE_SDK_V3_AVAILABLE:
            # For SDK v3, PushMessageRequest takes a list of Message objects
            push_message_request = PushMessageRequest(to=user_id, messages=message_objects_to_send)
            actual_bot_api.push_message(push_message_request)
        # elif sdk_version == 1 and LINE_SDK_V1_AVAILABLE:
        #     actual_bot_api.push_message(user_id, message_objects_to_send) # v1 takes list directly

        logger.info(f"Message(s) sent successfully to user_id: {user_id}")
        return True

    except LineApiExceptionV3 as e_v3: # Specific to SDK v3+
        logger.error(f"LINE API Error (v3): Status Code {e_v3.status} - Body: {e_v3.body}")
        # Original code's test environment error ignoring:
        if user_id.startswith('test_') or user_id == 'test_user':
            logger.info("Ignoring LINE API error for test user (v3).")
            return True # Simulate success for test users in case of API error
        return False
    # except LineApiErrorV1 as e_v1: # For SDK v1
    #     logger.error(f"LINE API Error (v1): Status Code {e_v1.status_code} - Error: {e_v1.error.message}")
    #     if user_id.startswith('test_') or user_id == 'test_user':
    #         logger.info("Ignoring LINE API error for test user (v1).")
    #         return True
    #     return False
    except Exception as e:
        logger.error(f"Unexpected error sending LINE message: {e}", exc_info=True)
        return False

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # IMPORTANT: Store your Channel Access Token and a test User ID securely.
    # DO NOT hardcode them for production. Use environment variables or a config file.
    try:
        LINE_CHANNEL_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
        # This should be a user ID that has added your bot as a friend
        # Or your own user ID if testing with `line-bot-sdk profile` command
        LINE_TEST_USER_ID = os.environ["LINE_TEST_USER_ID"]
    except KeyError:
        print("Please set LINE_CHANNEL_ACCESS_TOKEN and LINE_TEST_USER_ID environment variables to run this example.")
        LINE_CHANNEL_TOKEN = None
        LINE_TEST_USER_ID = None # Ensure it's None if not set

    if not LINE_SDK_V3_AVAILABLE:
        print("LINE Bot SDK v3 is not installed. Skipping live tests.")
    elif not LINE_CHANNEL_TOKEN or not LINE_TEST_USER_ID:
        print("LINE Channel Access Token or Test User ID not configured in environment. Skipping live tests.")
    else:
        print("--- Test Case 1: Send a single text message (SDK v3) ---")
        success1 = send_line_message(
            channel_access_token=LINE_CHANNEL_TOKEN,
            user_id=LINE_TEST_USER_ID,
            messages="Hello from the LINE API Snippet! (SDK v3)"
        )
        print(f"Test Case 1 Success: {success1}")

        print("\n--- Test Case 2: Send multiple text messages as a list of strings (SDK v3) ---")
        messages_list = [
            "This is message 1/2.",
            "And this is message 2/2. Sent via SDK v3."
        ]
        success2 = send_line_message(
            LINE_CHANNEL_TOKEN,
            LINE_TEST_USER_ID,
            messages_list
        )
        print(f"Test Case 2 Success: {success2}")

        print("\n--- Test Case 3: Send a message using a pre-configured client (SDK v3) ---")
        # Pre-configure client
        config_v3 = Configuration(access_token=LINE_CHANNEL_TOKEN)
        api_client_v3 = ApiClient(config_v3)
        messaging_api_v3 = MessagingApi(api_client_v3)

        # Pass the TextMessage object directly
        text_message_obj = TextMessage(text="Sent with pre-configured v3 client!")
        success3 = send_line_message(
            channel_access_token=LINE_CHANNEL_TOKEN, # Will be ignored by function
            user_id=LINE_TEST_USER_ID,
            messages=[text_message_obj], # Send as a list containing the Message object
            line_bot_api_client=messaging_api_v3
        )
        print(f"Test Case 3 Success: {success3}")

        print("\n--- Test Case 4: Send to a 'test_user' (should be skipped) ---")
        success4 = send_line_message(
            LINE_CHANNEL_TOKEN,
            "test_user_example", # A test user ID
            "This message to test_user should be logged but not sent."
        )
        print(f"Test Case 4 (test_user) Success: {success4}")
        assert success4 is True # Should simulate success

        print("\n--- Test Case 5: Send with an invalid user ID (expecting API error, then False) ---")
        # This will likely result in an API error from LINE if the ID is truly invalid.
        # The function should catch it and return False.
        success5 = send_line_message(
            LINE_CHANNEL_TOKEN,
            "UxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxY", # Invalid format
            "Testing invalid user ID."
        )
        print(f"Test Case 5 (invalid user ID) Success: {success5}")
        # We expect this to be False unless the API doesn't immediately reject it.
        # assert success5 is False # This might vary based on LINE API behavior for invalid IDs

    print("\nNote: Live LINE API calls require a valid Channel Access Token and a User ID that has added your bot.")
    print("Messages will be sent to the specified LINE_TEST_USER_ID.")
