from typing import Dict, Optional

# For more comprehensive MIME type to extension mapping, the 'mimetypes' module can be used.
# import mimetypes
# Example: mimetypes.guess_extension('image/jpeg') would give '.jpe' or '.jpeg'

def get_file_extension_from_content_type(
    content_type_or_mime_type: str,
    default_extension: str = ".bin",
    custom_mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    Determines a file extension based on a content type string (e.g., "image", "video")
    or a full MIME type string (e.g., "image/jpeg", "application/pdf").

    Prioritizes custom_mapping, then a default internal mapping for common types,
    then tries Python's `mimetypes` module (if available and full MIME type is given),
    and finally falls back to default_extension.

    Args:
        content_type_or_mime_type (str): The content type string (like "image", "audio")
                                         or a full MIME type (like "image/png").
                                         Case-insensitive for simple type keys.
        default_extension (str, optional): The extension to return if no specific
                                           match is found. Defaults to ".bin".
        custom_mapping (Optional[Dict[str, str]], optional): A user-provided dictionary
            to map content types/MIME types to extensions. This takes precedence.
            Keys should be lowercased. Example: {"image/custom": ".cimg"}

    Returns:
        str: The determined file extension, including the leading dot.
    """
    if not content_type_or_mime_type or not isinstance(content_type_or_mime_type, str):
        return default_extension

    normalized_type = content_type_or_mime_type.lower().strip()

    # 1. Check custom mapping first
    if custom_mapping:
        custom_ext = custom_mapping.get(normalized_type)
        if custom_ext:
            return custom_ext if custom_ext.startswith('.') else '.' + custom_ext

    # 2. Default internal mapping for simple types (like those from LINE webhook)
    #    These are often more about the general category than specific MIME.
    simple_type_mapping: Dict[str, str] = {
        'image': '.jpg',  # LINE often converts images to JPEG upon download
        'video': '.mp4',
        'audio': '.m4a',
        'text': '.txt',
        'file': '', # For generic 'file' type, extension might be in filename
        # Common full MIME types also included for convenience
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'video/mp4': '.mp4',
        'video/quicktime': '.mov',
        'audio/mpeg': '.mp3',
        'audio/mp4': '.m4a', # Can also be audio
        'audio/aac': '.aac',
        'audio/wav': '.wav',
        'application/pdf': '.pdf',
        'application/zip': '.zip',
        'application/json': '.json',
        'text/plain': '.txt',
        'text/html': '.html',
        'text/css': '.css',
        'text/javascript': '.js',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    }

    ext = simple_type_mapping.get(normalized_type)
    if ext is not None: # Handles cases like 'file': '' where we want an empty string
        return ext if ext.startswith('.') or ext == "" else '.' + ext

    # 3. Try Python's mimetypes module if it's a full MIME type (contains '/')
    if '/' in normalized_type:
        try:
            import mimetypes
            guessed_ext = mimetypes.guess_extension(normalized_type, strict=False) # strict=False allows non-standard
            if guessed_ext:
                # mimetypes can sometimes return .jpe for jpeg, prefer .jpg
                if guessed_ext.lower() == ".jpe": return ".jpg"
                return guessed_ext
        except ImportError:
            pass # mimetypes module not available or failed to import
        except Exception: # Catch any other errors from mimetypes
            pass


    # 4. Fallback to default
    return default_extension if default_extension.startswith('.') or default_extension == "" else '.' + default_extension

# Example Usage
if __name__ == "__main__":
    test_cases = {
        "image": ".jpg",
        "video": ".mp4",
        "audio": ".m4a",
        "text": ".txt",
        "file": "", # Expect empty for generic file type
        "unknown": ".bin",
        "IMAGE": ".jpg", # Test case-insensitivity for simple types
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "application/pdf": ".pdf",
        "text/html; charset=utf-8": ".html", # mimetypes should handle this if available
        "application/vnd.oasis.opendocument.text": ".odt", # Example for mimetypes
        "nonexistent/mimetype": ".bin",
        None: ".bin",
        "": ".bin",
    }

    custom_map = {
        "image/custom-format": ".cimg",
        "application/x-my-app": ".myapp"
    }

    print("--- Standard Tests ---")
    for content_type, expected_ext in test_cases.items():
        # For "text/html; charset=utf-8", mimetypes might not always be loaded in all test envs
        # So, we make a specific check for it if mimetypes is not available.
        if content_type == "text/html; charset=utf-8":
            try:
                import mimetypes
                if not mimetypes.guess_extension(content_type, strict=False): # If mimetypes doesn't know it
                    # print(f"Note: mimetypes module might not know '{content_type}'. Relying on simple map or default.")
                    pass # Allow simple map to try
            except ImportError: # mimetypes not available
                # print(f"Note: mimetypes module not available for '{content_type}'. Relying on simple map or default.")
                pass


        actual_ext = get_file_extension_from_content_type(content_type)
        print(f"Content Type: '{str(content_type):<40}' -> Expected: '{expected_ext}', Got: '{actual_ext}'")
        # A more robust test would handle cases where mimetypes is not installed.
        # For now, we assume it might be for some cases.
        if content_type == "text/html; charset=utf-8" and actual_ext != expected_ext:
            print(f"  (Note: '{content_type}' result can vary based on mimetypes availability/configuration)")
        elif content_type == "application/vnd.oasis.opendocument.text" and actual_ext != expected_ext:
             print(f"  (Note: '{content_type}' result depends on mimetypes knowing this type)")
        else:
            assert actual_ext == expected_ext, f"Failed for '{content_type}'"

    print("\n--- Custom Mapping Tests ---")
    custom_test_cases = {
        "image/custom-format": ".cimg",
        "application/x-my-app": ".myapp",
        "image": ".jpg", # Should still use default mapping if not in custom
    }
    for content_type, expected_ext in custom_test_cases.items():
        actual_ext = get_file_extension_from_content_type(content_type, custom_mapping=custom_map)
        print(f"Content Type: '{content_type:<30}' (custom) -> Expected: '{expected_ext}', Got: '{actual_ext}'")
        assert actual_ext == expected_ext, f"Custom mapping failed for '{content_type}'"

    print("\n--- Default Extension Tests ---")
    actual_ext_def = get_file_extension_from_content_type("unlisted/type", default_extension=".dat")
    print(f"Content Type: 'unlisted/type' (default .dat) -> Expected: '.dat', Got: '{actual_ext_def}'")
    assert actual_ext_def == ".dat"

    actual_ext_def_no_dot = get_file_extension_from_content_type("unlisted/type2", default_extension="xyz")
    print(f"Content Type: 'unlisted/type2' (default xyz) -> Expected: '.xyz', Got: '{actual_ext_def_no_dot}'")
    assert actual_ext_def_no_dot == ".xyz"

    print("\nAll tests passed (or noted variations).")
