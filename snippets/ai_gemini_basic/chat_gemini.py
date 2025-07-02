import logging
import os
from typing import Optional, Dict, Any, List, Union # Added List, Union for chat history

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

# Default fallback message if chat fails
DEFAULT_CHAT_FALLBACK_MESSAGE = "申し訳ございませんが、現在チャット機能で応答を生成できませんでした。"
ERROR_CHAT_FALLBACK_MESSAGE = "チャット中にエラーが発生しました: {error}"

def chat_gemini(
    message: str,
    history: Optional[List[Dict[str, Union[str, List[Dict[str, str]]]]]] = None, # For multi-turn chat history
    model_name: str = "gemini-1.5-flash", # Or a more chat-optimized model if available
    api_key: Optional[str] = None,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None, # Allow passing an already configured GenerativeModel instance
    system_instruction: Optional[str] = None # For setting system-level instructions
) -> str:
    """
    Interacts with the Gemini API in a chat-like fashion.
    Supports multi-turn conversations by accepting a history.

    Args:
        message (str): The user's current message.
        history (Optional[List[Dict[str, Union[str, List[Dict[str, str]]]]]], optional):
            A list representing the conversation history. Each item is a dict with
            "role" ("user" or "model") and "parts" (a list of dicts with "text").
            Example: [{"role": "user", "parts": [{"text": "Hello"}]},
                      {"role": "model", "parts": [{"text": "Hi there!"}]}]
            Defaults to None for a new conversation.
        model_name (str, optional): The Gemini model to use.
        api_key (Optional[str], optional): Gemini API key.
        generation_config (Optional[Dict[str, Any]], optional): Generation settings.
        safety_settings (Optional[Dict[str, Any]], optional): Safety settings.
        configured_model (Optional[Any]): Pre-configured `genai.GenerativeModel` instance.
        system_instruction (Optional[str], optional): A system instruction for the model.
            If provided, a `genai.ChatSession` might be started with this.

    Returns:
        str: The Gemini model's response text, or a fallback message on error.
    """
    if configured_model:
        model_instance = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured for chat.")
             return ERROR_CHAT_FALLBACK_MESSAGE.format(error="API key not configured")

        # Apply system instruction if provided. This usually means starting a chat session.
        # Note: The exact way to apply system_instruction might vary slightly with SDK versions.
        # This example assumes `system_instruction` is a top-level param for GenerativeModel
        # or handled by ChatSession.
        model_args = {}
        if system_instruction and hasattr(genai.GenerativeModel, 'system_instruction'): # Check if supported directly
             model_args['system_instruction'] = system_instruction

        model_instance = genai.GenerativeModel(model_name, **model_args)

        if system_instruction and not model_args.get('system_instruction'):
            # If system_instruction was not directly applicable to GenerativeModel,
            # and we want to use it, we'd typically start a chat session here.
            # For simplicity in this snippet, we'll assume direct model.generate_content
            # can handle context or the user manages the session externally if needed.
            # A more robust solution might involve:
            # chat_session = model_instance.start_chat(history=history or [], system_instruction=system_instruction)
            # response = chat_session.send_message(message, ...)
            # For this snippet, we'll stick to the simpler direct generation for now.
            logger.info("System instruction provided, but direct model generation used. For full effect, consider ChatSession.")

    else:
        logger.error("Gemini SDK not available and no configured_model provided for chat.")
        return ERROR_CHAT_FALLBACK_MESSAGE.format(error="Gemini SDK not available")

    # Construct the prompt for generate_content, including history if provided
    # The `generate_content` method can take a list of alternating user/model messages.
    # Or, for more complex chat, `model.start_chat()` is preferred.
    # This snippet will use `generate_content` with a history list for simplicity.

    full_conversation_history = []
    if system_instruction and not hasattr(model_instance, 'system_instruction'):
        # If system_instruction is not part of the model directly,
        # prepend it as a model-like turn (though this is a workaround).
        # A better approach is `start_chat(system_instruction=...)` if available.
        # For now, let's assume the model or session handles it, or it's part of the user's overall prompt strategy.
        pass # Or: full_conversation_history.append({"role": "system", "parts": [{"text": system_instruction}]}) - API might not support "system" role directly in generate_content history.

    if history:
        full_conversation_history.extend(history)

    # Add the current user message
    # Ensure parts is a list of dicts with a "text" key.
    full_conversation_history.append({"role": "user", "parts": [{"text": message}]})


    try:
        logger.info(f"Sending chat message to Gemini (Model: {model_name}). History length: {len(full_conversation_history)-1}")

        # Using generate_content with the constructed history.
        # For continuous chat, managing a genai.ChatSession object externally would be more robust.
        response = model_instance.generate_content(
            full_conversation_history, # Pass the whole conversation
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info("Gemini chat response received.")
            return response.text.strip()
        else:
            logger.warning("Gemini chat response was empty.")
            return DEFAULT_CHAT_FALLBACK_MESSAGE

    except Exception as e:
        logger.error(f"Gemini API error during chat: {e}", exc_info=True)
        return ERROR_CHAT_FALLBACK_MESSAGE.format(error=str(e))

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)): # type: ignore
        print("Skipping chat test: Gemini SDK not available or API key not configured.")
    else:
        print("\n--- Test Case 1: Simple chat message ---")
        response1 = chat_gemini("こんにちは！今日の天気はどうですか？", api_key=test_api_key)
        print(f"Gemini: {response1}")

        print("\n--- Test Case 2: Chat with history ---")
        chat_hist = [
            {"role": "user", "parts": [{"text": "Pythonで簡単なWebサーバーを立てる方法を教えて。"}]},
            {"role": "model", "parts": [{"text": "Pythonで簡単なWebサーバーを立てるには、http.serverモジュールを使うのが一般的です。例えば、`python -m http.server 8000` というコマンドを実行すると、カレントディレクトリをルートとしてポート8000でサーバーが起動しますよ。"}]}
        ]
        response2 = chat_gemini("ありがとう！ポート番号を変えるにはどうすればいい？", history=chat_hist, api_key=test_api_key)
        print(f"User: ありがとう！ポート番号を変えるにはどうすればいい？")
        print(f"Gemini: {response2}")

        # Update history for a further turn (optional)
        chat_hist.append({"role": "user", "parts": [{"text": "ありがとう！ポート番号を変えるにはどうすればいい？"}]})
        chat_hist.append({"role": "model", "parts": [{"text": response2}]})

        print("\n--- Test Case 3: Chat with a system instruction (conceptual) ---")
        # Note: The effectiveness of system_instruction with direct generate_content might be limited.
        # ChatSession is typically better for this.
        system_instr = "あなたは親切なアシスタントAIです。ユーザーの質問に簡潔かつ正確に答えてください。"
        response3 = chat_gemini(
            "太陽系の惑星の数は？",
            system_instruction=system_instr,
            api_key=test_api_key
        )
        print(f"User (with system instruction '{system_instr}'): 太陽系の惑星の数は？")
        print(f"Gemini: {response3}")

        print("\n--- Test Case 4: Simulating an API error (mocked) ---")
        class MockModelChatFail:
            def generate_content(self, history, generation_config=None, safety_settings=None):
                raise genai.types.generation_types.BlockedPromptException("Simulated content filter block") if genai else Exception("Simulated API error")

        mock_model_chat_fail = MockModelChatFail()
        response4_fail = chat_gemini(
            "This message would be blocked.",
            configured_model=mock_model_chat_fail
        )
        print(f"User: This message would be blocked.")
        print(f"Gemini (Error Fallback): {response4_fail}")
        assert "エラーが発生しました" in response4_fail or "blocked" in response4_fail.lower()
        print("Chat error fallback test passed.")

    print("\nNote: Live API calls to Gemini cost money and depend on network.")
