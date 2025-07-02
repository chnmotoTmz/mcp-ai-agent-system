import logging
from typing import Dict, List, Optional, Any # Added Any for genai.GenerativeModel

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

def get_model_info_gemini(
    model_name: str,
    api_key: Optional[str] = None,
    configured_model_instance: Optional[Any] = None # genai.GenerativeModel
) -> Optional[Dict[str, Any]]:
    """
    Retrieves information about a specified Gemini model.
    This typically involves making a call to the `genai.get_model` function.

    Args:
        model_name (str): The name of the model to get information for (e.g., "gemini-1.5-flash").
        api_key (Optional[str], optional): Gemini API key. If not provided,
            it's assumed `genai` is already configured or GOOGLE_API_KEY env var is set.
            Ignored if `configured_model_instance` is provided and has this info.
        configured_model_instance (Optional[Any], optional): An already initialized
            `genai.GenerativeModel` instance. If provided, its `model_name` might be used,
            or this function could try to fetch info for the given `model_name` string
            assuming the SDK is configured through this instance's setup.
            However, `genai.get_model()` is a static-like method usually.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing model information if successful,
                                  None otherwise. The dictionary structure depends on the
                                  SDK's `get_model` response (e.g., name, version,
                                  input_token_limit, output_token_limit, supported_generation_methods).
    """
    if not genai:
        logger.error("Gemini SDK (google.generativeai) not available.")
        return None

    # Configure API key if provided and genai is not already configured.
    # Note: configured_model_instance doesn't directly help with genai.get_model() auth
    # unless genai was globally configured when it was created.
    if api_key and (not hasattr(genai, 'API_KEY') or not genai.API_KEY):
        try:
            genai.configure(api_key=api_key)
            logger.info("Gemini SDK configured with provided API key for get_model_info.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini SDK with API key: {e}")
            return None
    elif not api_key and (not hasattr(genai, 'API_KEY') or not genai.API_KEY) and not os.getenv("GOOGLE_API_KEY"):
         logger.error("Gemini API key not provided and genai not configured.")
         return None


    try:
        logger.info(f"Fetching information for model: {model_name}")
        # genai.get_model returns a Model object
        # ref: https://ai.google.dev/api/python/google/generativeai/get_model
        model_info = genai.get_model(f"models/{model_name}") # Name needs to be prefixed with "models/"

        if model_info:
            # Convert Model object to a dictionary for easier use/serialization
            # Attributes might include: name, version, display_name, description,
            # input_token_limit, output_token_limit, supported_generation_methods, etc.
            info_dict = {
                "name": model_info.name,
                "base_model_id": getattr(model_info, 'base_model_id', ''), # Might not exist on all model info objects
                "version": model_info.version,
                "display_name": model_info.display_name,
                "description": model_info.description,
                "input_token_limit": model_info.input_token_limit,
                "output_token_limit": model_info.output_token_limit,
                "supported_generation_methods": model_info.supported_generation_methods,
                # Add other relevant attributes if needed
            }
            logger.info(f"Successfully fetched information for model: {model_name}")
            return info_dict
        else:
            logger.warning(f"No information returned for model: {model_name}")
            return None

    except Exception as e:
        logger.error(f"Error fetching model information for '{model_name}': {e}", exc_info=True)
        return None

# Example Usage
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Make sure to set your GOOGLE_API_KEY environment variable
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai:
        print("Skipping model info test: Gemini SDK not installed.")
    elif not test_api_key and (not hasattr(genai, 'API_KEY') or not genai.API_KEY):
         print("Skipping model info test: GOOGLE_API_KEY not set and genai not configured.")
    else:
        print("\n--- Test Case 1: Get info for a known model (e.g., gemini-1.5-flash) ---")
        # model_to_check = "gemini-1.0-pro" # A common model
        model_to_check = "gemini-1.5-flash-latest" # Or a specific version like "gemini-1.5-flash-001"

        info1 = get_model_info_gemini(model_to_check, api_key=test_api_key)
        if info1:
            print(f"Information for model '{model_to_check}':")
            for key, value in info1.items():
                print(f"  {key}: {value}")
        else:
            print(f"Failed to get information for model '{model_to_check}'.")

        print("\n--- Test Case 2: Get info for a potentially non-existent model ---")
        non_existent_model = "gemini-non-existent-model-xyz"
        info2 = get_model_info_gemini(non_existent_model, api_key=test_api_key)
        if info2:
            print(f"Information for model '{non_existent_model}': {info2}")
        else:
            print(f"Correctly failed to get information for non-existent model '{non_existent_model}'.")
            # Expect this to fail and return None or log an error.

        # Example with configured_model_instance (less direct for get_model, but for completeness)
        # print("\n--- Test Case 3: Using configured_model_instance (conceptual for this function) ---")
        # if genai:
        # try:
        # if test_api_key: genai.configure(api_key=test_api_key)
        #     # model_instance = genai.GenerativeModel(model_to_check)
        #     # info3 = get_model_info_gemini(model_to_check, configured_model_instance=model_instance)
        #     # if info3:
        #     #     print(f"Info for {model_to_check} via instance context: {info3.get('display_name')}")
        #     # else:
        #     #     print("Failed with configured_model_instance context.")
        #     # This test case is less relevant here as get_model is static-like.
        #     print("Test case with configured_model_instance is more conceptual for get_model_info.")
        # except Exception as e:
        # print(f"Could not run configured_model_instance test: {e}")


    print("\nNote: `genai.get_model()` requires the model name to be prefixed with 'models/'.")
    print("The snippet handles this prefix automatically.")
