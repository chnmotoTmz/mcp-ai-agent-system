import logging
import json # For robust JSON parsing
from typing import Dict, Any, List # Added List for tags

logger = logging.getLogger(__name__)

def parse_gemini_article_response(
    response_text: str,
    expected_keys: List[str] = None, # e.g., ["title", "summary", "tags", "body"]
    default_title: str = "生成された記事",
    default_summary_from_body_length: int = 150,
    default_tags: List[str] = None
) -> Dict[str, Any]:
    """
    Parses a text response from the Gemini API, expecting specific structured
    data for an article (e.g., title, summary, tags, body/content).
    It prioritizes parsing a JSON object if the response is formatted as such
    (e.g., within ```json ... ```). Otherwise, it falls back to a line-by-line
    text parsing based on keywords.

    Args:
        response_text (str): The raw text response from the Gemini API.
        expected_keys (List[str], optional): A list of keys expected in the output dict.
            If None, defaults to ["title", "summary", "tags", "body"].
            This primarily influences the structure of the fallback dictionary.
        default_title (str, optional): Title to use if parsing fails to find one.
        default_summary_from_body_length (int, optional): If summary is missing but body exists,
            truncate body to this length for a summary. Set to 0 to disable.
        default_tags (List[str], optional): Default tags if none are found.
            If None, defaults to ["AI生成", "記事"].

    Returns:
        Dict[str, Any]: A dictionary containing the parsed article components.
                        Keys will match `expected_keys`. If parsing a specific field fails,
                        it will attempt to provide a default or empty value.
    """
    if expected_keys is None:
        expected_keys = ["title", "summary", "tags", "body"] # 'body' is preferred over 'content'
    if default_tags is None:
        default_tags = ["AI生成", "記事"]

    cleaned_response_text = response_text.strip()
    parsed_data: Dict[str, Any] = {key: "" for key in expected_keys} # Initialize with empty strings
    if "tags" in parsed_data:
        parsed_data["tags"] = []


    # 1. Attempt to parse as JSON if ```json ... ``` block is present
    if cleaned_response_text.startswith("```json"):
        try:
            # Extract content within ```json ... ```
            json_str_match = cleaned_response_text.split("```json", 1)
            if len(json_str_match) > 1:
                json_content = json_str_match[1].rsplit("```", 1)[0].strip()
                data = json.loads(json_content)

                # Map known fields, allowing for variations like 'content' vs 'body'
                parsed_data["title"] = str(data.get("title", data.get("記事タイトル", "")))
                parsed_data["summary"] = str(data.get("summary", data.get("要約", "")))
                parsed_data["body"] = str(data.get("body", data.get("content", data.get("本文", ""))))

                tags_data = data.get("tags", data.get("タグ", []))
                if isinstance(tags_data, list):
                    parsed_data["tags"] = [str(tag).strip() for tag in tags_data if str(tag).strip()]
                elif isinstance(tags_data, str): # Handle comma-separated string for tags
                    parsed_data["tags"] = [tag.strip() for tag in tags_data.split(',') if tag.strip()]

                logger.info(f"Successfully parsed JSON response. Title: {parsed_data.get('title', '')[:50]}")
                # Apply defaults if fields are still empty after JSON parsing
                return _apply_defaults_to_parsed_data(parsed_data, default_title, default_summary_from_body_length, default_tags)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}. Falling back to text-based parsing.")
        except Exception as e: # Catch other potential errors during JSON processing
            logger.warning(f"Error processing supposed JSON response: {e}. Falling back to text-based parsing.")

    # 2. Fallback to text-based parsing (keyword-driven)
    lines = cleaned_response_text.split('\n')
    current_section_key: Optional[str] = None # Stores the key for multi-line content (e.g., "body")

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped: # Skip empty lines for keyword matching
            if current_section_key == "body": # Preserve empty lines within body
                 parsed_data[current_section_key] += "\n"
            continue

        # Try to match keywords case-insensitively
        if line_stripped.lower().startswith('タイトル:') or line_stripped.lower().startswith('title:'):
            parsed_data["title"] = line_stripped.split(':', 1)[1].strip()
            current_section_key = None
        elif line_stripped.lower().startswith('要約:') or line_stripped.lower().startswith('summary:'):
            parsed_data["summary"] = line_stripped.split(':', 1)[1].strip()
            current_section_key = None
        elif line_stripped.lower().startswith('タグ:') or line_stripped.lower().startswith('tags:'):
            tags_str = line_stripped.split(':', 1)[1].strip()
            parsed_data["tags"] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            current_section_key = None
        elif line_stripped.lower().startswith('本文:') or line_stripped.lower().startswith('body:') or line_stripped.lower().startswith('content:'):
            current_section_key = "body" # Standardize to 'body'
            # Capture text on the same line as the keyword
            body_start_text = line_stripped.split(':', 1)[1].strip()
            if body_start_text:
                parsed_data["body"] += body_start_text + "\n"
        elif current_section_key == "body":
            parsed_data["body"] += line + "\n" # Add line to current section (body)
        elif not parsed_data.get("title") and not any(kw_token in line_stripped.lower() for kw_token in [':', '要約', 'タグ', '本文', 'summary', 'tags', 'body', 'content']):
            # If no keywords matched yet and no colon (indicating other fields), assume it's the title.
            # This is a heuristic for responses that might just start with the title.
            parsed_data["title"] = line_stripped
            current_section_key = None # Reset section after assuming title

    # Clean up the accumulated body text
    if "body" in parsed_data:
        parsed_data["body"] = parsed_data["body"].strip()

    return _apply_defaults_to_parsed_data(parsed_data, default_title, default_summary_from_body_length, default_tags)

def _apply_defaults_to_parsed_data(
    parsed_data: Dict[str, Any],
    default_title: str,
    default_summary_from_body_length: int,
    default_tags: List[str]
) -> Dict[str, Any]:
    """Helper to apply default values to the parsed data dictionary."""
    if not parsed_data.get("title"):
        parsed_data["title"] = default_title

    if not parsed_data.get("summary") and parsed_data.get("body") and default_summary_from_body_length > 0:
        body_text = parsed_data["body"]
        parsed_data["summary"] = body_text[:default_summary_from_body_length] + \
                                 ("..." if len(body_text) > default_summary_from_body_length else "")

    if "tags" not in parsed_data or not parsed_data.get("tags"): # Check if tags list is empty or key missing
        parsed_data["tags"] = default_tags[:] # Use a copy

    # Ensure all expected keys are present, even if empty (except tags, which has a default list)
    for key in ["title", "summary", "body"]: # Add other expected string keys if necessary
        if key not in parsed_data or parsed_data[key] is None:
            parsed_data[key] = ""

    logger.info(f"Final parsed data (defaults applied) - Title: {str(parsed_data.get('title',''))[:50]}, Summary: {str(parsed_data.get('summary',''))[:50]}, Tags: {parsed_data.get('tags',[])}")
    return parsed_data

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_responses = [
        # Standard text format
        """タイトル: テスト記事１
要約: これはテスト記事１の要約です。
タグ: テスト,サンプル,記事
本文:
これはテスト記事１の本文です。
複数行にわたることもあります。""",
        # JSON format
        """```json
{
  "title": "JSONテスト記事",
  "summary": "JSON形式のテスト記事のサマリー。",
  "tags": ["json", "test", "gemini"],
  "body": "<p>これはJSONからパースされた<b>本文</b>です。</p>"
}
```""",
        # Only title and body
        """タイトル: シンプル記事
本文:
本文のみの記事です。要約やタグはありません。""",
        # No keywords, just text (should try to infer title, use raw as body)
        """これはタイトルになるはずのテキスト
そして、これが本文になるはずのテキスト。
改行もそのまま。""",
        # JSON with 'content' instead of 'body'
        """```json
{
  "title": "Content Key Test",
  "summary": "Testing 'content' key for body.",
  "tags": ["content_key"],
  "content": "<p>This body was under 'content' key.</p>"
}
```""",
        # Malformed JSON (should fall back to text parsing)
        """```json
{
  "title": "Malformed JSON",
  "summary": "This JSON is intentionally broken."
  "tags": ["malformed"],
  "body": "This won't be parsed as JSON."
}```""",
        # Empty response
        "",
        # Response with only tags
        "タグ: オンリータグ"
    ]

    for i, response_str in enumerate(test_responses):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Raw Response:\n'''\n{response_str}\n'''")
        parsed = parse_gemini_article_response(response_str)
        print("Parsed Output:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))

        # Basic assertions
        assert "title" in parsed
        assert "summary" in parsed
        assert "tags" in parsed and isinstance(parsed["tags"], list)
        assert "body" in parsed

        if i == 0: # Standard text
            assert parsed["title"] == "テスト記事１"
            assert "テスト" in parsed["tags"]
        if i == 1: # JSON
            assert parsed["title"] == "JSONテスト記事"
            assert "json" in parsed["tags"]
        if i == 2: # Title and body only
            assert parsed["title"] == "シンプル記事"
            assert parsed["summary"] != "" # Should be generated from body
        if i == 3: # No keywords
            assert parsed["title"] == "これはタイトルになるはずのテキスト" # First line as title
            assert parsed["body"].startswith("そして、これが本文になるはずのテキスト。")
        if i == 4: # JSON with 'content' key
            assert parsed["title"] == "Content Key Test"
            assert parsed["body"] == "<p>This body was under 'content' key.</p>"
        if i == 5: # Malformed JSON
            # Behavior depends on how text parser handles it. Likely title will be "```json" or similar
            # and body will contain the rest. This is acceptable for fallback.
            assert parsed["title"] # Should have some title
        if i == 6: # Empty response
            assert parsed["title"] == "生成された記事" # Default title
            assert parsed["tags"] == ["AI生成", "記事"]
        if i == 7: # Only tags
             assert parsed["title"] == "生成された記事"
             assert parsed["tags"] == ["オンリータグ"]


    print("\nAll test cases processed.")
