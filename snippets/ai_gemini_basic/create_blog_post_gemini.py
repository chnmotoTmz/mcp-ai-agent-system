import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import json # For parsing if the response is a JSON string

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

# Default prompt template for creating a blog post
DEFAULT_CREATE_BLOG_PROMPT_TEMPLATE = """
以下の内容をもとに、魅力的なブログ記事を作成してください。

内容:
{content_text}
{title_hint_text}
要求事項:
- 読みやすく、興味深い記事にしてください
- 適切なタイトルを付けてください{title_hint_instruction}
- 記事の要約も含めてください
- 関連するタグを提案してください（既存タグ: {existing_tags_text}）
- 関連する情報がある場合は、HTMLリンク（<a href="URL">テキスト</a>）を含めてください
- 本文はHTML形式で記述してください（<p>、<br>、<strong>タグなど使用可能）

以下の形式でJSONオブジェクトとして回答してください (```json ... ``` で囲むこと):
{{
  "title": "[記事タイトル]",
  "summary": "[記事の要約]",
  "tags": ["[タグ1]", "[タグ2]", "[タグ3]"],
  "body": "[HTML形式の記事本文]"
}}
"""

def _parse_gemini_response_for_blog_post(response_text: str) -> Dict[str, Any]:
    """
    Parses the text response from Gemini, expecting a specific structure,
    or a JSON object, to extract blog post components.

    Args:
        response_text (str): The raw text response from the Gemini API.

    Returns:
        Dict[str, Any]: A dictionary containing 'title', 'summary', 'tags' (list), and 'body'.
                        Returns default values or the raw text as body if parsing fails.
    """
    response_text = response_text.strip()

    # Attempt to parse as JSON first (if wrapped in ```json ... ```)
    if response_text.startswith("```json"):
        try:
            json_str = response_text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(json_str)
            # Validate expected keys
            parsed = {
                "title": str(data.get("title", "生成されたタイトル (JSON)")),
                "summary": str(data.get("summary", "")),
                "tags": [str(tag) for tag in data.get("tags", []) if isinstance(data.get("tags"), list) and tag],
                "body": str(data.get("body", "")),
            }
            if not parsed["summary"] and parsed["body"]:
                parsed["summary"] = parsed["body"][:150] + "..." if len(parsed["body"]) > 150 else parsed["body"]
            if not parsed["tags"]:
                 parsed["tags"] = ["AI生成"]
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Gemini response: {e}. Falling back to text parsing.")
        except Exception as e: # Catch other potential errors during JSON processing
            logger.warning(f"Error processing JSON response: {e}. Falling back to text parsing.")


    # Fallback to text-based parsing (original logic)
    lines = response_text.split('\n')
    parsed_data: Dict[str, Any] = {
        "title": "",
        "summary": "",
        "tags": [],
        "body": "" # Changed from 'content' to 'body' for consistency
    }
    current_section = None

    for line in lines:
        line_stripped = line.strip()
        if line_stripped.lower().startswith('タイトル:'):
            parsed_data["title"] = line_stripped.split(':', 1)[1].strip()
            current_section = None
        elif line_stripped.lower().startswith('要約:'):
            parsed_data["summary"] = line_stripped.split(':', 1)[1].strip()
            current_section = None
        elif line_stripped.lower().startswith('タグ:'):
            tags_str = line_stripped.split(':', 1)[1].strip()
            parsed_data["tags"] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            current_section = None
        elif line_stripped.lower().startswith('本文:'):
            current_section = 'body'
            # If there's text after "本文:", capture it
            body_start_text = line_stripped.split(':', 1)[1].strip()
            if body_start_text:
                 parsed_data["body"] += body_start_text + "\n"
        elif current_section == 'body':
            parsed_data["body"] += line + "\n" # Preserve original line breaks for body
        elif not parsed_data["title"] and not any(kw in line_stripped.lower() for kw in ['要約:', 'タグ:', '本文:']):
            # If title is not yet found and no other keyword, assume this line is the title
            if not parsed_data["title"]: # Check again to assign only once
                 parsed_data["title"] = line_stripped

    # Post-processing and defaults for text parsing
    parsed_data["body"] = parsed_data["body"].strip()
    if not parsed_data["title"]:
        parsed_data["title"] = "生成された記事"
    if not parsed_data["summary"] and parsed_data["body"]:
        parsed_data["summary"] = parsed_data["body"][:150] + "..." if len(parsed_data["body"]) > 150 else parsed_data["body"]
    if not parsed_data["tags"]:
        parsed_data["tags"] = ["AI生成", "ブログ"]

    return parsed_data


def create_blog_post_gemini(
    source_content_text: str,
    title_hint: str = "",
    existing_tags: Optional[List[str]] = None,
    category: str = "日記", # Default category
    model_name: str = "gemini-1.5-flash",
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_CREATE_BLOG_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None
) -> Optional[Dict[str, Any]]:
    """
    Creates a structured blog post (title, summary, tags, body, category, created_at)
    from source content using the Gemini API.

    Args:
        source_content_text (str): The main text content to base the blog post on.
        title_hint (str, optional): A hint for the blog post's title.
        existing_tags (Optional[List[str]], optional): A list of tags already associated
                                                       with the content. Defaults to ["AI生成", "ブログ"].
        category (str, optional): Category for the blog post. Defaults to "日記".
        model_name, api_key, prompt_template, generation_config, safety_settings, configured_model:
            Similar to other Gemini snippets for model and API configuration.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the blog post with keys
                                  'title', 'body', 'summary', 'tags' (list), 'category',
                                  and 'created_at' (ISO format string).
                                  Returns None on failure.
    """
    if existing_tags is None:
        existing_tags = ["AI生成", "ブログ"]

    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured.")
             return None
        model = genai.GenerativeModel(model_name)
    else:
        logger.error("Gemini SDK not available and no configured_model provided.")
        return None

    prompt = prompt_template.format(
        content_text=source_content_text,
        title_hint_text=f"\nタイトルのヒント: {title_hint}\n" if title_hint else "",
        title_hint_instruction=f"（{title_hint}を参考に）" if title_hint else "",
        existing_tags_text=', '.join(existing_tags)
    )

    try:
        logger.info(f"Attempting Gemini API call to create blog post (Model: {model_name})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info(f"Gemini response received. Length: {len(response.text)}")
            parsed_article_data = _parse_gemini_response_for_blog_post(response.text)

            # Merge tags: combine existing_tags with newly suggested tags, ensuring uniqueness
            final_tags = list(set(existing_tags + parsed_article_data.get("tags", [])))

            return {
                'title': parsed_article_data['title'],
                'body': parsed_article_data['body'], # Ensure key is 'body'
                'summary': parsed_article_data['summary'],
                'tags': final_tags,
                'category': category,
                'created_at': datetime.utcnow().isoformat() + "Z" # ISO 8601 format
            }
        else:
            logger.warning("Gemini API response for blog post creation was empty.")
            return None

    except Exception as e:
        logger.error(f"Gemini API error during blog post creation: {e}", exc_info=True)
        return None

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)):
        print("Skipping test: Gemini SDK not available or API key not configured.")
    else:
        sample_content = "今日はAIカンファレンスに参加しました。基調講演では最新のLLM技術とその応用例が紹介され、非常に刺激的でした。特にマルチモーダルAIのデモは圧巻で、今後の可能性を感じました。"

        print("\n--- Test Case 1: Create blog post with basic content ---")
        blog_post1 = create_blog_post_gemini(sample_content, api_key=test_api_key)
        if blog_post1:
            print("Generated Blog Post (Test 1):")
            print(f"  Title: {blog_post1['title']}")
            print(f"  Summary: {blog_post1['summary'][:100]}...")
            print(f"  Tags: {blog_post1['tags']}")
            print(f"  Body (first 100 chars): {blog_post1['body'][:100]}...")
            print(f"  Category: {blog_post1['category']}")
            print(f"  Created At: {blog_post1['created_at']}")
        else:
            print("Failed to create blog post (Test 1).")

        print("\n--- Test Case 2: Create blog post with title hint and existing tags ---")
        blog_post2 = create_blog_post_gemini(
            "午後は専門セッションで、医療分野におけるAI活用事例を学びました。診断支援や個別化治療への期待が高まります。",
            title_hint="医療AIの最前線",
            existing_tags=["カンファレンス", "技術トレンド"],
            category="テクノロジー",
            api_key=test_api_key
        )
        if blog_post2:
            print("Generated Blog Post (Test 2):")
            print(f"  Title: {blog_post2['title']}")
            print(f"  Tags: {blog_post2['tags']}") # Check if existing tags are merged
            print(f"  Category: {blog_post2['category']}")
        else:
            print("Failed to create blog post (Test 2).")

        print("\n--- Test Case 3: Model returns structured JSON (mocked) ---")
        class MockModelReturnsJson:
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                class MockResponse:
                    def __init__(self):
                        # Simulate Gemini returning JSON within backticks
                        self.text = """```json
                        {
                          "title": "Mocked JSON Title",
                          "summary": "Summary from mocked JSON.",
                          "tags": ["mock", "json_test"],
                          "body": "<p>This is the body from a <b>mocked JSON</b> response.</p>"
                        }
                        ```"""
                return MockResponse()

        mock_model_json = MockModelReturnsJson()
        blog_post3 = create_blog_post_gemini(
            "Content for JSON mock test.",
            configured_model=mock_model_json
        )
        if blog_post3:
            print("Generated Blog Post (Test 3 - JSON Mock):")
            print(f"  Title: {blog_post3['title']}")
            assert blog_post3['title'] == "Mocked JSON Title"
            assert "json_test" in blog_post3['tags']
            print("  JSON Mock Test Passed.")
        else:
            print("Failed to create blog post (Test 3 - JSON Mock).")

    print("\nNote: Live API calls to Gemini cost money and depend on network.")
