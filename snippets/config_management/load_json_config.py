import json
import logging
import os
from typing import Dict, Any, Optional, Union, TypeVar, Type # Added TypeVar, Type for generic return

logger = logging.getLogger(__name__)

T = TypeVar('T') # Generic type for the expected config structure

def load_json_config(
    config_path: Union[str, os.PathLike],
    expected_type: Optional[Type[T]] = None, # For type hinting the expected structure (e.g., a dataclass or TypedDict)
    default_on_error: Optional[T] = None, # Return this if loading or validation fails
    create_if_not_exists: bool = False,
    default_content_on_create: Optional[Dict[str, Any]] = None
) -> Optional[T]: # Returns the parsed config (model of type T) or None/default_on_error
    """
    Loads configuration from a JSON file with basic error handling.
    Optionally creates the file with default content if it doesn't exist.

    Args:
        config_path (Union[str, os.PathLike]): Path to the JSON configuration file.
        expected_type (Optional[Type[T]], optional): If you are using type hints for your
            config structure (e.g., a dataclass or TypedDict), you can pass its type here.
            This is primarily for static analysis and doesn't perform runtime validation
            unless you add it. Defaults to None, returning Dict[str, Any].
        default_on_error (Optional[T], optional): Value to return if any error occurs
            during file reading or JSON parsing. If None, errors will result in None return.
        create_if_not_exists (bool, optional): If True and the config file does not exist,
            it will be created with `default_content_on_create`. Defaults to False.
        default_content_on_create (Optional[Dict[str, Any]], optional): Content to write
            if the file is created. Used only if `create_if_not_exists` is True.
            Defaults to an empty dictionary.

    Returns:
        Optional[T]: The parsed configuration data (as a dictionary or an instance of
                     `expected_type` if a deserialization mechanism were added),
                     or `default_on_error` if specified and an error occurs,
                     or None if an error occurs and no default is set.
    """
    absolute_config_path = os.path.abspath(config_path)

    if not os.path.exists(absolute_config_path):
        if create_if_not_exists:
            logger.info(f"Configuration file not found at {absolute_config_path}. Creating with default content.")
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(absolute_config_path), exist_ok=True)
                with open(absolute_config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_content_on_create or {}, f, indent=2, ensure_ascii=False)
                # After creating, try to load it (it will be the default_content_on_create)
            except Exception as e:
                logger.error(f"Failed to create default configuration file at {absolute_config_path}: {e}", exc_info=True)
                return default_on_error
        else:
            logger.warning(f"Configuration file not found at {absolute_config_path}. File creation not requested.")
            return default_on_error

    try:
        with open(absolute_config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        logger.info(f"Configuration loaded successfully from {absolute_config_path}.")
        # If expected_type was a Pydantic model or dataclass, you could add validation/deserialization here:
        # if expected_type and hasattr(expected_type, 'parse_obj'): # Pydantic example
        #     return expected_type.parse_obj(config_data)
        return config_data # Returns Dict[str, Any] by default
    except FileNotFoundError: # Should be caught by the block above if create_if_not_exists is False
        logger.error(f"Configuration file not found (should not happen if create_if_not_exists=False and already checked): {absolute_config_path}")
        return default_on_error
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from configuration file {absolute_config_path}: {e}", exc_info=True)
        return default_on_error
    except Exception as e:
        logger.error(f"Unexpected error loading configuration from {absolute_config_path}: {e}", exc_info=True)
        return default_on_error

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_config_file = os.path.join(current_dir, "sample_config.json")
    non_existent_config_file = os.path.join(current_dir, "non_existent_config.json")
    default_error_config = {"error_default": True}

    # --- Test Case 1: Load existing valid JSON ---
    sample_data = {"setting1": "value1", "feature_enabled": True, "threshold": 100}
    with open(test_config_file, "w", encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)

    print("\n--- Test Case 1: Load existing valid JSON ---")
    config1 = load_json_config(test_config_file)
    if config1:
        print("Config 1 Loaded:", config1)
        assert config1.get("setting1") == "value1"
    else:
        print("Failed to load config 1.")

    # --- Test Case 2: File not found, no creation, no default_on_error ---
    print("\n--- Test Case 2: File not found (no creation, no default_on_error) ---")
    if os.path.exists(non_existent_config_file): os.remove(non_existent_config_file) # Ensure it doesn't exist
    config2 = load_json_config(non_existent_config_file)
    print(f"Config 2 Loaded: {config2}")
    assert config2 is None

    # --- Test Case 3: File not found, no creation, with default_on_error ---
    print("\n--- Test Case 3: File not found (no creation, with default_on_error) ---")
    if os.path.exists(non_existent_config_file): os.remove(non_existent_config_file)
    config3 = load_json_config(non_existent_config_file, default_on_error=default_error_config)
    print(f"Config 3 Loaded: {config3}")
    assert config3 == default_error_config

    # --- Test Case 4: File not found, with creation ---
    print("\n--- Test Case 4: File not found (with creation and default content) ---")
    if os.path.exists(non_existent_config_file): os.remove(non_existent_config_file)
    default_create_content = {"new_setting": "created_default", "version": 1}
    config4 = load_json_config(
        non_existent_config_file,
        create_if_not_exists=True,
        default_content_on_create=default_create_content
    )
    if config4:
        print(f"Config 4 Loaded (created): {config4}")
        assert config4 == default_create_content
        assert os.path.exists(non_existent_config_file) # Check file was created
        # Clean up created file
        if os.path.exists(non_existent_config_file): os.remove(non_existent_config_file)
    else:
        print("Failed to load/create config 4.")


    # --- Test Case 5: Invalid JSON content ---
    with open(test_config_file, "w", encoding='utf-8') as f:
        f.write("{'invalid_json': True,}") # Invalid JSON (single quotes, trailing comma)

    print("\n--- Test Case 5: Load invalid JSON (with default_on_error) ---")
    config5 = load_json_config(test_config_file, default_on_error=default_error_config.copy()) # Pass a copy for safety
    if config5:
        print(f"Config 5 Loaded (should be default): {config5}")
        assert config5 == default_error_config
    else:
        print("Failed to handle invalid JSON for config 5 as expected (should have returned default).")


    # Clean up test_config_file
    if os.path.exists(test_config_file):
        os.remove(test_config_file)
    print("\nAll JSON config loading tests completed.")
