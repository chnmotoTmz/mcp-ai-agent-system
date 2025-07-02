import asyncio
import logging
import os
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_MCP_CONFIG_PATH_IMGUR_HEALTH = "mcp_config.json"

# --- Helper Functions (similar to other Imgur MCP snippets) ---
def _load_mcp_config_imgur_for_health(config_path: str = DEFAULT_MCP_CONFIG_PATH_IMGUR_HEALTH) -> Optional[Dict[str, Any]]:
    """Loads the Imgur-specific section from the MCP configuration file."""
    try:
        abs_config_path = os.path.abspath(config_path)
        if not os.path.exists(abs_config_path):
            logger.error(f"MCP config not found for health_check: {abs_config_path}")
            return None
        with open(abs_config_path, 'r') as f:
            full_config = json.load(f)
        imgur_config = full_config.get("mcpServers", {}).get("imgur")
        if not imgur_config:
            logger.error("'imgur' config not found in MCP config for health_check.")
            return None
        return imgur_config
    except Exception as e:
        logger.error(f"Error loading MCP config for health_check: {e}", exc_info=True)
        return None

def _get_utc_timestamp_for_health() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

async def _call_mcp_imgur_tool_for_health(
    imgur_mcp_config: Dict[str, Any],
    tool_name: str,
    tool_input_params: Dict[str, Any] # Usually empty for health_check
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Helper function to call a generic tool via the Imgur MCP."""
    # This is identical to _call_mcp_imgur_tool in other Imgur MCP snippets.
    cmd = imgur_mcp_config.get("command")
    base_args = imgur_mcp_config.get("args", [])
    if not cmd: return None, "Imgur MCP 'command' not defined."
    full_command_args = [str(cmd)] + [str(arg) for arg in base_args] + ["--tool", tool_name, "--input", json.dumps(tool_input_params)]
    logger.info(f"Executing Imgur MCP (health_check): {' '.join(full_command_args)}")
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

async def health_check_imgur_mcp(
    mcp_config_file_path: str = DEFAULT_MCP_CONFIG_PATH_IMGUR_HEALTH,
    health_check_tool_name: str = "health_check", # Standardized name for health check tool
    health_check_params: Optional[Dict[str, Any]] = None # Usually empty
) -> Dict[str, Any]:
    """
    Performs a health check of the Imgur service via the configured MCP script.
    This typically involves calling a specific "health_check" tool in the MCP.

    Args:
        mcp_config_file_path (str, optional): Path to the `mcp_config.json` file.
        health_check_tool_name (str, optional): The name of the health check tool
                                                defined in the MCP script.
        health_check_params (Optional[Dict[str, Any]], optional): Parameters to pass
            to the health check tool, if any. Defaults to an empty dictionary.

    Returns:
        Dict[str, Any]: A dictionary containing the health check status.
            Example success:
            { "status": "healthy", "service": "Imgur MCP", "mcp_response": {...}, "timestamp": "..." }
            Example failure:
            { "status": "error", "error": "...", "timestamp": "..." }
    """
    timestamp = _get_utc_timestamp_for_health()
    if health_check_params is None:
        health_check_params = {}

    imgur_mcp_config = _load_mcp_config_imgur_for_health(mcp_config_file_path)
    if not imgur_mcp_config:
        return {"status": "error", "error": "Failed to load Imgur MCP configuration for health check.", "timestamp": timestamp}

    mcp_response, error_msg = await _call_mcp_imgur_tool_for_health(
        imgur_mcp_config=imgur_mcp_config,
        tool_name=health_check_tool_name,
        tool_input_params=health_check_params
    )

    if error_msg:
        return {"status": "error", "error": error_msg, "service": "Imgur MCP", "timestamp": timestamp}

    # A successful health check from MCP might return specific status info.
    # We assume if _call_mcp_imgur_tool_for_health returns a dict and no error, it's healthy.
    if isinstance(mcp_response, dict):
        # The MCP's health_check tool itself should ideally return a clear status.
        # For this snippet, we'll consider a non-error response from MCP as "healthy".
        return {
            "status": "healthy", # Or mcp_response.get("status", "healthy") if MCP provides it
            "service": "Imgur MCP",
            "mcp_response": mcp_response, # The actual JSON response from the MCP health_check tool
            "timestamp": timestamp
        }
    else:
        # This case might occur if MCP returns non-JSON or unexpected format on success.
        err = f"Imgur MCP health_check tool returned unexpected data format: {str(mcp_response)[:200]}"
        logger.error(err)
        return {"status": "error", "error": err, "service": "Imgur MCP", "raw_mcp_output": mcp_response, "timestamp": timestamp}


# Example Usage (requires mcp_config.json and a mock MCP script)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Setup mock environment (similar to other Imgur MCP snippets) ---
    mock_mcp_script_name_health = "mock_imgur_mcp_for_health.py"
    python_executable_health = "python3"
    try: subprocess.run([python_executable_health, "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError): python_executable_health = "python"
    try: subprocess.run([python_executable_health, "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError): python_executable_health = None

    if python_executable_health:
        current_dir_health = os.path.dirname(os.path.abspath(__file__))
        test_mcp_config_path_health = os.path.join(current_dir_health, "test_mcp_config_health.json")
        mock_script_path_health = os.path.join(current_dir_health, mock_mcp_script_name_health)

        dummy_mcp_config_content_health = {
            "mcpServers": {"imgur": {"command": python_executable_health, "args": [mock_script_path_health]}}
        }
        with open(test_mcp_config_path_health, "w") as f: json.dump(dummy_mcp_config_content_health, f, indent=2)

        mock_script_content_health = f"""#!/usr/bin/env {python_executable_health}
import json, sys, argparse, datetime

def health_check(params):
    # Simulate a health check response
    return {{
        "status": "ok",
        "message": "Mock Imgur MCP is operational.",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dependencies": {{"imgur_api": "reachable", "database": "connected"}},
        "success": True
    }}

def main():
    parser = argparse.ArgumentParser(description="Mock Imgur MCP Tool (for health_check)")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--input", required=True) # Even if health_check takes no input via JSON
    args = parser.parse_args()
    # params = json.loads(args.input) # No specific input params for health_check usually
    if args.tool == "health_check": result = health_check(None) # Pass None as params
    else: result = {{"error": f"Mock MCP: Unknown tool '{{args.tool}}'", "success": False}}
    print(json.dumps(result))

if __name__ == "__main__": main()
"""
        with open(mock_script_path_health, "w") as f: f.write(mock_script_content_health)
        os.chmod(mock_script_path_health, 0o755)
        print(f"Created dummy MCP config and script for health_check test.")

        async def run_health_check_test():
            print("\n--- Test Case: Perform health check via (mocked) Pipedream MCP ---")
            health_status = await health_check_imgur_mcp(
                mcp_config_file_path=test_mcp_config_path_health
            )
            print("Health Check Status:")
            print(json.dumps(health_status, indent=2, ensure_ascii=False))

            assert health_status.get("status") == "healthy"
            assert health_status.get("service") == "Imgur MCP"
            assert "mcp_response" in health_status
            assert health_status["mcp_response"].get("status") == "ok"
            print("Mock health_check test PASSED.")

        asyncio.run(run_health_check_test())

        print("\nCleaning up dummy files for health_check test...")
        if os.path.exists(test_mcp_config_path_health): os.remove(test_mcp_config_path_health)
        if os.path.exists(mock_script_path_health): os.remove(mock_script_path_health)
        print("Cleanup complete.")
    else:
        print("Python executable not found, skipping Pipedream MCP health_check test.")

    print("\nNote: This snippet assumes an MCP script implements a 'health_check' tool.")
