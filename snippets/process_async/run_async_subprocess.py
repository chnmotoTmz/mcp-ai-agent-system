import asyncio
import logging
from typing import List, Tuple, Optional, Union, Dict, Any # Added Dict, Any
import json # For parsing JSON output

logger = logging.getLogger(__name__)

async def run_async_subprocess(
    command_and_args: List[str],
    input_data: Optional[Union[str, bytes]] = None, # Data to be sent to stdin
    timeout_seconds: Optional[float] = None, # Timeout for the subprocess.communicate()
    cwd: Optional[str] = None, # Current working directory for the subprocess
    env: Optional[Dict[str, str]] = None, # Environment variables for the subprocess
    expected_stdout_type: str = "text" # "text", "json", "bytes"
) -> Tuple[Optional[Any], Optional[str], Optional[int]]:
    """
    Runs an external command asynchronously, captures its stdout and stderr,
    and handles potential timeouts and errors.

    Args:
        command_and_args (List[str]): The command and its arguments as a list of strings.
                                      The first element is the command, subsequent are args.
        input_data (Optional[Union[str, bytes]], optional): Data to be sent to the
            subprocess's stdin. If str, it will be utf-8 encoded. Defaults to None.
        timeout_seconds (Optional[float], optional): Timeout for waiting for the
            subprocess to complete. Defaults to None (no timeout).
        cwd (Optional[str], optional): Current working directory for the subprocess.
        env (Optional[Dict[str, str]], optional): Environment variables.
        expected_stdout_type (str, optional): How to interpret stdout.
            "text": decodes as UTF-8 string.
            "json": decodes as UTF-8 then parses as JSON.
            "bytes": returns raw bytes.
            Defaults to "text".

    Returns:
        Tuple[Optional[Any], Optional[str], Optional[int]]: A tuple containing:
            - stdout_content (Optional[Any]): Processed stdout content (str, dict, or bytes
                                             based on expected_stdout_type), or None on error/timeout.
            - stderr_content (Optional[str]): Decoded stderr string, or None if no error output.
            - return_code (Optional[int]): The process's return code, or None on timeout/startup error.
    """
    if not command_and_args:
        logger.error("No command provided to run_async_subprocess.")
        return None, "No command provided.", None

    cmd_str_for_logging = ' '.join(command_and_args) # For logging
    logger.info(f"Running async subprocess: {cmd_str_for_logging}")

    # Prepare stdin pipe if input_data is provided
    stdin_pipe = asyncio.subprocess.PIPE if input_data is not None else None

    # Encode input_data if it's a string
    input_bytes: Optional[bytes] = None
    if isinstance(input_data, str):
        input_bytes = input_data.encode('utf-8')
    elif isinstance(input_data, bytes):
        input_bytes = input_data

    try:
        process = await asyncio.create_subprocess_exec(
            *command_and_args,
            stdin=stdin_pipe,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(input=input_bytes),
            timeout=timeout_seconds
        )

        return_code = process.returncode
        stderr_content = stderr_bytes.decode('utf-8', errors='replace').strip() if stderr_bytes else None

        if return_code == 0:
            logger.info(f"Subprocess '{cmd_str_for_logging}' completed successfully (RC: {return_code}).")
            if expected_stdout_type == "json":
                try:
                    stdout_content = json.loads(stdout_bytes.decode('utf-8', errors='replace'))
                except json.JSONDecodeError as e:
                    err_msg = f"Failed to parse JSON from stdout: {e}. Raw: {stdout_bytes.decode('utf-8', errors='replace')[:200]}"
                    logger.error(err_msg)
                    return None, err_msg, return_code # Return code indicates success, but parsing failed
            elif expected_stdout_type == "bytes":
                stdout_content = stdout_bytes
            else: # Default to "text"
                stdout_content = stdout_bytes.decode('utf-8', errors='replace')
            return stdout_content, stderr_content, return_code
        else:
            err_msg = f"Subprocess '{cmd_str_for_logging}' failed with return code {return_code}."
            if stderr_content:
                err_msg += f" Stderr: {stderr_content}"
            logger.error(err_msg)
            # Still return stdout if any, as it might contain useful error info from some tools
            stdout_for_error = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else None
            return stdout_for_error, stderr_content, return_code

    except asyncio.TimeoutError:
        logger.error(f"Subprocess '{cmd_str_for_logging}' timed out after {timeout_seconds} seconds.")
        if process.returncode is None: # Process might still be running, try to kill it
            try: process.kill()
            except ProcessLookupError: pass # Already terminated
            except Exception as kill_e: logger.error(f"Error trying to kill timed-out process: {kill_e}")
        return None, "Process timed out.", None
    except FileNotFoundError:
        logger.error(f"Command not found: {command_and_args[0]}. Please ensure it's installed and in PATH.")
        return None, f"Command not found: {command_and_args[0]}", None
    except Exception as e:
        logger.error(f"Unexpected error running subprocess '{cmd_str_for_logging}': {e}", exc_info=True)
        return None, str(e), None


# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async def main_tests():
        print("\n--- Test Case 1: Simple echo (text output) ---")
        cmd1 = ["echo", "Hello, async world!"]
        stdout1, stderr1, rc1 = await run_async_subprocess(cmd1)
        print(f"Stdout: '{stdout1.strip() if stdout1 else None}', Stderr: {stderr1}, RC: {rc1}")
        assert rc1 == 0 and stdout1 and "Hello, async world!" in stdout1

        print("\n--- Test Case 2: Python script for JSON output ---")
        # Create a temporary python script
        py_script_content = "import json; print(json.dumps({'key': 'value', 'number': 123}));"
        py_script_path = "temp_test_script.py"
        with open(py_script_path, "w") as f: f.write(py_script_content)

        # Try to find python3, then python
        python_exe = "python3"
        try: subprocess.run([python_exe, "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError) : python_exe = "python"
        try: subprocess.run([python_exe, "--version"], check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError) : python_exe = None

        if python_exe:
            cmd2 = [python_exe, py_script_path]
            stdout2, stderr2, rc2 = await run_async_subprocess(cmd2, expected_stdout_type="json")
            print(f"Stdout (JSON): {stdout2}, Stderr: {stderr2}, RC: {rc2}")
            assert rc2 == 0 and isinstance(stdout2, dict) and stdout2.get("key") == "value"
            os.remove(py_script_path) # Clean up
        else:
            print("Python executable not found, skipping JSON output test.")


        print("\n--- Test Case 3: Command fails (stderr and non-zero RC) ---")
        # Using 'ls' with a non-existent file to generate an error
        # This behavior can be OS-dependent. On Linux/macOS, ls to non-existent file prints to stderr and non-zero RC.
        # On Windows, 'dir' might behave differently.
        # For cross-platform, a dedicated script that exits with error might be better.
        cmd3_fail_script = "temp_fail_script.py"
        if python_exe:
            with open(cmd3_fail_script, "w") as f: f.write("import sys; sys.stderr.write('This is a test error\\n'); sys.exit(1);")
            cmd3 = [python_exe, cmd3_fail_script]
            stdout3, stderr3, rc3 = await run_async_subprocess(cmd3)
            print(f"Stdout: {stdout3}, Stderr: '{stderr3.strip() if stderr3 else None}', RC: {rc3}")
            assert rc3 == 1 and stderr3 and "This is a test error" in stderr3
            os.remove(cmd3_fail_script)
        else:
            print("Python executable not found, skipping command failure test with script.")


        print("\n--- Test Case 4: Command with stdin ---")
        if python_exe:
            # Script that reads stdin and prints it to stdout
            stdin_script_content = "import sys; data = sys.stdin.read(); print(f'Script read: {{data.strip()}}');"
            stdin_script_path = "temp_stdin_script.py"
            with open(stdin_script_path, "w") as f: f.write(stdin_script_content)
            cmd4 = [python_exe, stdin_script_path]
            input_text = "Text to send to stdin"
            stdout4, stderr4, rc4 = await run_async_subprocess(cmd4, input_data=input_text)
            print(f"Stdout: '{stdout4.strip() if stdout4 else None}', Stderr: {stderr4}, RC: {rc4}")
            assert rc4 == 0 and stdout4 and f"Script read: {input_text}" in stdout4
            os.remove(stdin_script_path)
        else:
            print("Python executable not found, skipping stdin test.")


        print("\n--- Test Case 5: Timeout ---")
        # Use a command that sleeps longer than the timeout
        # `sleep` command is common on Linux/macOS. For Windows, `timeout /t` or ping.
        # For a more reliable cross-platform test, a python script that sleeps.
        if python_exe:
            sleep_script_content = "import time; time.sleep(2);" # Sleeps for 2 seconds
            sleep_script_path = "temp_sleep_script.py"
            with open(sleep_script_path, "w") as f: f.write(sleep_script_content)
            cmd5 = [python_exe, sleep_script_path]
            stdout5, stderr5, rc5 = await run_async_subprocess(cmd5, timeout_seconds=0.1) # Timeout 0.1s
            print(f"Stdout (Timeout): {stdout5}, Stderr: '{stderr5}', RC: {rc5}")
            assert rc5 is None and stderr5 == "Process timed out." # Expect None RC and specific error
            os.remove(sleep_script_path)
        else:
            print("Python executable not found, skipping timeout test.")

        print("\n--- Test Case 6: Command not found ---")
        cmd6 = ["nonexistentcommand123xyz"]
        stdout6, stderr6, rc6 = await run_async_subprocess(cmd6)
        print(f"Stdout: {stdout6}, Stderr: '{stderr6}', RC: {rc6}")
        assert rc6 is None and stderr6 and "Command not found" in stderr6


        print("\nAll async subprocess tests completed (or skipped if Python not found).")

    # Need to import subprocess for the setup part of the test for python executable check
    import subprocess
    asyncio.run(main_tests())
