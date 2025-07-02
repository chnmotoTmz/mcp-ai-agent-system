import asyncio
import logging
import os
import json
from typing import Dict, Any, Optional, Tuple # Added Tuple
from datetime import datetime, timezone # Added timezone for UTC

logger = logging.getLogger(__name__)

# Default path for MCP configuration. Can be overridden.
DEFAULT_MCP_CONFIG_PATH = "mcp_config.json" # Assumed to be in the same dir or accessible

def _load_mcp_config_imgur(config_path: str = DEFAULT_MCP_CONFIG_PATH) -> Optional[Dict[str, Any]]:
    """
    Loads the Imgur-specific section from the MCP configuration file.

    Args:
        config_path (str): Path to the MCP JSON configuration file.

    Returns:
        Optional[Dict[str, Any]]: The Imgur server configuration if found, else None.
    """
    try:
        abs_config_path = os.path.abspath(config_path)
        if not os.path.exists(abs_config_path):
            logger.error(f"MCP configuration file not found at: {abs_config_path}")
            return None

        with open(abs_config_path, 'r') as f:
            full_config = json.load(f)

        imgur_config = full_config.get("mcpServers", {}).get("imgur")
        if not imgur_config:
            logger.error("'imgur' configuration not found within 'mcpServers' in MCP config.")
            return None

        logger.info(f"Imgur MCP configuration loaded successfully from {abs_config_path}.")
        return imgur_config
    except FileNotFoundError:
        logger.error(f"MCP configuration file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding MCP JSON configuration from {config_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading MCP configuration from {config_path}: {e}", exc_info=True)
        return None

def _get_utc_timestamp() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

async def _call_mcp_imgur_tool(
    imgur_mcp_config: Dict[str, Any],
    tool_name: str,
    tool_input_params: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Helper function to call a generic tool via the Imgur MCP.

    Args:
        imgur_mcp_config (Dict[str, Any]): The Imgur specific part of MCP config.
        tool_name (str): The name of the MCP tool to call (e.g., "upload_image").
        tool_input_params (Dict[str, Any]): Parameters for the tool, to be JSON stringified.

    Returns:
        Tuple[Optional[Dict[str, Any]], Optional[str]]:
            A tuple containing (result_dict, error_message).
            result_dict is the parsed JSON response on success.
            error_message contains a description of the error on failure.
    """
    cmd = imgur_mcp_config.get("command")
    base_args = imgur_mcp_config.get("args", [])

    if not cmd:
        return None, "Imgur MCP 'command' not defined in configuration."

    # Construct arguments for the subprocess
    # Ensure all parts of command and args are strings.
    full_command_args = [str(cmd)] + [str(arg) for arg in base_args] + [
        "--tool", tool_name,
        "--input", json.dumps(tool_input_params)
    ]

    logger.info(f"Executing Imgur MCP command: {' '.join(full_command_args)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *full_command_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            try:
                result = json.loads(stdout.decode('utf-8'))
                logger.info(f"Imgur MCP tool '{tool_name}' executed successfully.")
                return result, None
            except json.JSONDecodeError as e:
                err_msg = f"Failed to parse JSON response from Imgur MCP tool '{tool_name}': {e}. Raw output: {stdout.decode('utf-8')[:200]}"
                logger.error(err_msg)
                return None, err_msg
        else:
            error_output = stderr.decode('utf-8').strip() if stderr else "Unknown error from MCP process."
            err_msg = f"Imgur MCP tool '{tool_name}' failed. Return code: {process.returncode}. Error: {error_output}"
            logger.error(err_msg)
            return None, err_msg

    except FileNotFoundError: # If the cmd itself is not found
        err_msg = f"Imgur MCP command '{cmd}' not found. Ensure it is installed and in PATH."
        logger.error(err_msg)
        return None, err_msg
    except Exception as e:
        err_msg = f"Unexpected error executing Imgur MCP tool '{tool_name}': {e}"
        logger.error(err_msg, exc_info=True)
        return None, err_msg


async def upload_image_via_pipedream_mcp(
    image_path: str,
    title: str = "",
    description: str = "",
    privacy: str = "hidden", # Or other Imgur privacy settings like "public", "secret"
    mcp_config_file_path: str = DEFAULT_MCP_CONFIG_PATH
) -> Dict[str, Any]:
    """
    Uploads an image using a Pipedream-hosted (or similar) Imgur MCP (Media Control Proxy) script.
    The MCP script is expected to be callable from the command line.

    Args:
        image_path (str): Absolute or relative path to the image file to upload.
        title (str, optional): Title for the uploaded image on Imgur.
        description (str, optional): Description for the image.
        privacy (str, optional): Privacy setting for the image on Imgur.
        mcp_config_file_path (str, optional): Path to the `mcp_config.json` file.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the upload.
            On success, typically includes:
            { "success": True, "url": "...", "imgur_id": "...", "delete_hash": "...", ... }
            On failure:
            { "success": False, "error": "...", "timestamp": "..." }
    """
    timestamp = _get_utc_timestamp()

    if not os.path.exists(image_path):
        logger.error(f"Image file not found at: {image_path}")
        return {"success": False, "error": f"Image file not found: {image_path}", "timestamp": timestamp}

    imgur_mcp_config = _load_mcp_config_imgur(mcp_config_file_path)
    if not imgur_mcp_config:
        return {"success": False, "error": "Failed to load Imgur MCP configuration.", "timestamp": timestamp}

    tool_params = {
        "image_path": os.path.abspath(image_path), # MCP might need absolute path
        "title": title,
        "description": description,
        "privacy": privacy
    }

    upload_result, error_msg = await _call_mcp_imgur_tool(
        imgur_mcp_config=imgur_mcp_config,
        tool_name="upload_image", # Standardized tool name for Imgur upload via MCP
        tool_input_params=tool_params
    )

    if error_msg: # If _call_mcp_imgur_tool returned an error message
        return {"success": False, "error": error_msg, "timestamp": timestamp}

    if upload_result and isinstance(upload_result, dict) and upload_result.get("url"): # Basic check for success from MCP
        return {
            "success": True,
            "url": upload_result.get("url"), # Imgur direct link
            "imgur_id": upload_result.get("id"),
            "delete_hash": upload_result.get("delete_hash"),
            "title": title, # Return what was intended
            "description": description,
            "privacy": privacy,
            "timestamp": timestamp,
            "source": "pipedream_mcp_imgur", # Indicate source
            "mcp_response": upload_result # Include raw MCP response if needed
        }
    else:
        # If MCP call didn't error but response is not as expected
        err = f"Imgur MCP upload_image tool returned unexpected or incomplete data: {str(upload_result)[:200]}"
        logger.error(err)
        return {"success": False, "error": err, "raw_mcp_output": upload_result, "timestamp": timestamp}

# Example Usage (requires mcp_config.json and a test image)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Create a dummy mcp_config.json for testing ---
    # This config should point to a real or mock MCP script.
    # For this example, we'll assume a mock script `mock_imgur_mcp.py` exists.
    mock_mcp_script_name = "mock_imgur_mcp.py" # Needs to be executable and in PATH or specified with full path

    # Check if python3 is available for the mock script
    python_executable = "python3"
    try:
        subprocess.run([python_executable, "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        python_executable = "python" # Fallback to 'python'
        try:
            subprocess.run([python_executable, "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"Python executable ('python3' or 'python') not found. Cannot run mock MCP script for tests.")
            python_executable = None


    if python_executable:
        dummy_mcp_config_content = {
            "mcpServers": {
                "imgur": {
                    # If mock_imgur_mcp.py is in the same directory and executable:
                    # "command": f"./{mock_mcp_script_name}",
                    # Or, if it's a Python script that needs an interpreter:
                    "command": python_executable,
                    "args": [mock_mcp_script_name] # Script name as first arg to python interpreter
                }
                # Potentially other MCP server configs here
            }
        }
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_mcp_config_path = os.path.join(current_dir, "test_mcp_config.json")

        with open(test_mcp_config_path, "w") as f:
            json.dump(dummy_mcp_config_content, f, indent=2)
        print(f"Created dummy MCP config: {test_mcp_config_path}")

        # --- Create a dummy mock_imgur_mcp.py script ---
        mock_script_content = f"""#!/usr/bin/env {python_executable}
import json
import sys
import argparse
import os
import time

def upload_image(params):
    # Simulate Imgur upload
    img_path = params.get("image_path", "unknown.jpg")
    if not os.path.exists(img_path):
        return {{"error": "Mock MCP: Image not found at " + img_path, "success": False}}

    # Simulate some processing time
    time.sleep(0.1)

    # Generate a fake Imgur response
    fake_id = "mock" + os.path.basename(img_path).split('.')[0]
    return {{
        "id": fake_id,
        "delete_hash": "del_" + fake_id,
        "url": f"https://i.imgur.com/{fake_id}.png",
        "link": f"https://imgur.com/{fake_id}",
        "success": True,
        "status": 200
    }}

def main():
    parser = argparse.ArgumentParser(description="Mock Imgur MCP Tool")
    parser.add_argument("--tool", required=True, help="Tool name to execute")
    parser.add_argument("--input", required=True, help="JSON string of input parameters")
    args = parser.parse_args()

    try:
        params = json.loads(args.input)
    except json.JSONDecodeError:
        print(json.dumps({{"error": "Mock MCP: Invalid JSON input", "success": False}}), file=sys.stderr)
        sys.exit(1)

    if args.tool == "upload_image":
        result = upload_image(params)
    else:
        result = {{"error": f"Mock MCP: Unknown tool '{{args.tool}}'", "success": False}}

    # MCPs should output JSON to stdout
    print(json.dumps(result))

if __name__ == "__main__":
    main()
"""
        mock_script_path = os.path.join(current_dir, mock_mcp_script_name)
        with open(mock_script_path, "w") as f:
            f.write(mock_script_content)
        os.chmod(mock_script_path, 0o755) # Make it executable
        print(f"Created mock MCP script: {mock_script_path} (and made it executable)")


        # --- Create a dummy image for testing ---
        dummy_image_content = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;" # Tiny valid GIF
        test_image_path = os.path.join(current_dir, "test_upload_image.gif")
        with open(test_image_path, "wb") as f:
            f.write(dummy_image_content)
        print(f"Created dummy image for upload: {test_image_path}")

        async def run_upload_test():
            print("\n--- Test Case: Upload image via (mocked) Pipedream MCP ---")
            upload_response = await upload_image_via_pipedream_mcp(
                image_path=test_image_path,
                title="Test GIF Upload",
                description="A tiny GIF uploaded via mock MCP.",
                privacy="hidden",
                mcp_config_file_path=test_mcp_config_path # Use the test config
            )
            print("Upload Response:")
            print(json.dumps(upload_response, indent=2))

            assert upload_response.get("success") is True
            assert "url" in upload_response
            assert "mocktest_upload_image" in upload_response.get("imgur_id", "")
            print("Mock upload test PASSED.")

        asyncio.run(run_upload_test())

        # --- Clean up dummy files ---
        print("\nCleaning up dummy files...")
        if os.path.exists(test_mcp_config_path): os.remove(test_mcp_config_path)
        if os.path.exists(mock_script_path): os.remove(mock_script_path)
        if os.path.exists(test_image_path): os.remove(test_image_path)
        print("Cleanup complete.")
    else:
        print("Python executable not found, skipping Pipedream MCP upload test.")


    print("\nNote: This snippet assumes an external MCP script handles actual Imgur API interaction.")
    print("The `mcp_config.json` file must correctly point to this executable script.")
    print("The example above creates a mock MCP script for local testing.")
