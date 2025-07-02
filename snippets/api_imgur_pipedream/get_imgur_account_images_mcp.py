import asyncio
import logging
import os
import json
from typing import Dict, Any, Optional, List, Tuple # Added List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_MCP_CONFIG_PATH_IMGUR_GET = "mcp_config.json"

# --- Helper Functions (similar to upload_image_pipedream_mcp.py) ---
def _load_mcp_config_imgur_for_get(config_path: str = DEFAULT_MCP_CONFIG_PATH_IMGUR_GET) -> Optional[Dict[str, Any]]:
    """Loads the Imgur-specific section from the MCP configuration file."""
    try:
        abs_config_path = os.path.abspath(config_path)
        if not os.path.exists(abs_config_path):
            logger.error(f"MCP config not found for get_account_images: {abs_config_path}")
            return None
        with open(abs_config_path, 'r') as f:
            full_config = json.load(f)
        imgur_config = full_config.get("mcpServers", {}).get("imgur")
        if not imgur_config:
            logger.error("'imgur' config not found in MCP config for get_account_images.")
            return None
        return imgur_config
    except Exception as e:
        logger.error(f"Error loading MCP config for get_account_images: {e}", exc_info=True)
        return None

def _get_utc_timestamp_for_get() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

async def _call_mcp_imgur_tool_for_get(
    imgur_mcp_config: Dict[str, Any],
    tool_name: str,
    tool_input_params: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Helper function to call a generic tool via the Imgur MCP."""
    # This is identical to _call_mcp_imgur_tool in the upload snippet.
    # In a library, this would be a shared utility.
    cmd = imgur_mcp_config.get("command")
    base_args = imgur_mcp_config.get("args", [])
    if not cmd: return None, "Imgur MCP 'command' not defined."
    full_command_args = [str(cmd)] + [str(arg) for arg in base_args] + ["--tool", tool_name, "--input", json.dumps(tool_input_params)]
    logger.info(f"Executing Imgur MCP (get_account_images): {' '.join(full_command_args)}")
    try:
        process = await asyncio.create_subprocess_exec(*full_command_args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            try: return json.loads(stdout.decode('utf-8')), None
            except json.JSONDecodeError as e: return None, f"Failed to parse JSON from MCP '{tool_name}': {e}. Output: {stdout.decode('utf-8')[:200]}"
        else: return None, f"MCP tool '{tool_name}' failed. Code: {process.returncode}. Error: {stderr.decode('utf-8').strip() if stderr else 'Unknown'}"
    except FileNotFoundError: return None, f"MCP command '{cmd}' not found."
    except Exception as e: return None, f"Unexpected error executing MCP tool '{tool_name}': {e}"
# --- End of Helper Functions ---

async def get_imgur_account_images_mcp(
    limit: int = 10,
    page: int = 0, # Imgur API often uses page numbers (0-indexed or 1-indexed depending on endpoint)
    mcp_config_file_path: str = DEFAULT_MCP_CONFIG_PATH_IMGUR_GET
) -> Dict[str, Any]:
    """
    Retrieves a list of images from the configured Imgur account via an MCP script.

    Args:
        limit (int, optional): The number of images to return per page. Defaults to 10.
                               (Actual Imgur API default might be 50 or 60).
        page (int, optional): The page number to retrieve. Defaults to 0.
        mcp_config_file_path (str, optional): Path to the `mcp_config.json` file.

    Returns:
        Dict[str, Any]: A dictionary containing the result.
            On success, typically:
            { "success": True, "data": [list_of_image_objects], "page_info": {...}, "timestamp": "..." }
            Each image object in "data" would contain details like id, link, title, etc.
            On failure:
            { "success": False, "error": "...", "timestamp": "..." }
    """
    timestamp = _get_utc_timestamp_for_get()
    imgur_mcp_config = _load_mcp_config_imgur_for_get(mcp_config_file_path)

    if not imgur_mcp_config:
        return {"success": False, "error": "Failed to load Imgur MCP configuration for get_account_images.", "timestamp": timestamp}

    tool_params = {
        "limit": limit,
        "page": page
        # The MCP script for "get_account_images" would translate these to actual Imgur API params.
    }

    # The actual tool name in MCP config for fetching account images.
    # This might be 'get_account_images', 'list_images', etc.
    # For this snippet, we'll assume "get_account_images" is the standardized tool name.
    mcp_tool_name = "get_account_images"

    api_result, error_msg = await _call_mcp_imgur_tool_for_get(
        imgur_mcp_config=imgur_mcp_config,
        tool_name=mcp_tool_name,
        tool_input_params=tool_params
    )

    if error_msg:
        return {"success": False, "error": error_msg, "timestamp": timestamp}

    # Assuming the MCP script returns a structure like Imgur API's image list response
    # which usually has a "data" field containing the list of images.
    if api_result and isinstance(api_result, dict) and "data" in api_result and isinstance(api_result["data"], list):
        # You might want to include pagination info if the MCP provides it
        page_info = {
            "current_page": page,
            "items_per_page": limit,
            "returned_items": len(api_result["data"]),
            # The MCP could potentially return total_items, total_pages if it fetches that meta.
        }
        return {
            "success": True,
            "data": api_result["data"], # List of image objects from Imgur
            "page_info": page_info,
            "timestamp": timestamp,
            "source": "pipedream_mcp_imgur"
        }
    else:
        err = f"Imgur MCP tool '{mcp_tool_name}' returned unexpected or incomplete data: {str(api_result)[:200]}"
        logger.error(err)
        return {"success": False, "error": err, "raw_mcp_output": api_result, "timestamp": timestamp}

# Example Usage (requires mcp_config.json and a mock MCP script)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Setup mock environment (similar to upload_image_pipedream_mcp.py) ---
    mock_mcp_script_name_get = "mock_imgur_mcp_for_get.py"
    python_executable_get = "python3" # Assume python3
    try: subprocess.run([python_executable_get, "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError): python_executable_get = "python" # Fallback
    try: subprocess.run([python_executable_get, "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError): python_executable_get = None

    if python_executable_get:
        current_dir_get = os.path.dirname(os.path.abspath(__file__))
        test_mcp_config_path_get = os.path.join(current_dir_get, "test_mcp_config_get.json")
        mock_script_path_get = os.path.join(current_dir_get, mock_mcp_script_name_get)

        dummy_mcp_config_content_get = {
            "mcpServers": {"imgur": {"command": python_executable_get, "args": [mock_script_path_get]}}
        }
        with open(test_mcp_config_path_get, "w") as f: json.dump(dummy_mcp_config_content_get, f, indent=2)

        mock_script_content_get = f"""#!/usr/bin/env {python_executable_get}
import json, sys, argparse, time, random

def get_account_images(params):
    limit = params.get("limit", 5)
    page = params.get("page", 0) # Mock pagination

    # Simulate a list of Imgur image objects
    images = []
    for i in range(limit):
        img_id = f"mockImg{{page*limit + i + 1:03d}}"
        images.append({{
            "id": img_id, "title": f"Mock Image {{page*limit + i + 1}}", "description": "A mock image.",
            "datetime": int(time.time()) - random.randint(0, 360000), "type": "image/jpeg",
            "animated": False, "width": 640, "height": 480, "size": random.randint(10000, 500000),
            "views": random.randint(0, 1000), "link": f"https://i.imgur.com/{img_id}.jpg",
            "deletehash": f"del_{img_id}"
        }})
    # Simulate that there might be more pages if page is 0
    has_more = page == 0
    return {{"data": images, "success": True, "status": 200, "has_more": has_more}}

def main():
    parser = argparse.ArgumentParser(description="Mock Imgur MCP Tool (for get_account_images)")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try: params = json.loads(args.input)
    except json.JSONDecodeError:
        print(json.dumps({{"error": "Mock MCP: Invalid JSON input", "success": False}}), file=sys.stderr); sys.exit(1)
    if args.tool == "get_account_images": result = get_account_images(params)
    else: result = {{"error": f"Mock MCP: Unknown tool '{{args.tool}}'", "success": False}}
    print(json.dumps(result))

if __name__ == "__main__": main()
"""
        with open(mock_script_path_get, "w") as f: f.write(mock_script_content_get)
        os.chmod(mock_script_path_get, 0o755)
        print(f"Created dummy MCP config and script for get_account_images test.")

        async def run_get_images_test():
            print("\n--- Test Case: Get account images via (mocked) Pipedream MCP ---")
            response = await get_imgur_account_images_mcp(
                limit=3,
                page=0,
                mcp_config_file_path=test_mcp_config_path_get
            )
            print("Get Account Images Response:")
            print(json.dumps(response, indent=2, ensure_ascii=False))

            assert response.get("success") is True
            assert "data" in response and isinstance(response["data"], list)
            assert len(response["data"]) == 3
            assert response["data"][0]["title"] == "Mock Image 1"
            print("Mock get_account_images test PASSED.")

        asyncio.run(run_get_images_test())

        print("\nCleaning up dummy files for get_account_images test...")
        if os.path.exists(test_mcp_config_path_get): os.remove(test_mcp_config_path_get)
        if os.path.exists(mock_script_path_get): os.remove(mock_script_path_get)
        print("Cleanup complete.")
    else:
        print("Python executable not found, skipping Pipedream MCP get_account_images test.")

    print("\nNote: This snippet assumes an MCP script implements 'get_account_images' tool.")
