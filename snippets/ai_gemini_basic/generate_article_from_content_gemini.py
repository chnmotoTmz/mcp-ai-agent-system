import logging
import os
from typing import Optional, Dict, Any, List # Added List for type hinting
import json # For parsing if the response is a JSON string

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

# Default prompt template, adaptable for different styles
DEFAULT_ARTICLE_PROMPT_TEMPLATE = """
以下の内容をもとに、{style_description}を作成してください。

内容:
{content_text}

要求事項:
- {style_description}のスタイルで書いてください
- 読みやすく、魅力的な文章にしてください
- 適切なタイトルを付けてください
- 記事の要約も含めてください
- 関連するタグを3-5個提案してください
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

# Re-using the parser from create_blog_post_gemini as it's very similar
def _parse_gemini_response_for_article(response_text: str) -> Dict[str, Any]:
    """
    Parses the text response from Gemini, expecting a specific structure,
    or a JSON object, to extract article components.
    (Adapted from _parse_gemini_response_for_blog_post)
    """
    response_text = response_text.strip()

    if response_text.startswith("```json"):
        try:
            json_str = response_text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(json_str)
            parsed = {
                "title": str(data.get("title", "生成されたタイトル (JSON)")),
                "summary": str(data.get("summary", "")),
                "tags": [str(tag) for tag in data.get("tags", []) if isinstance(data.get("tags"), list) and tag],
                "body": str(data.get("body", "")), # Expect 'body' for content
            }
            if not parsed["summary"] and parsed["body"]: # Auto-generate summary if missing
                parsed["summary"] = parsed["body"][:150] + "..." if len(parsed["body"]) > 150 else parsed["body"]
            if not parsed["tags"]: # Default tags if missing
                 parsed["tags"] = ["AI生成記事"]
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Gemini response for article: {e}. Falling back to text parsing.")
        except Exception as e:
            logger.warning(f"Error processing JSON response for article: {e}. Falling back to text parsing.")

    # Fallback to text-based parsing
    lines = response_text.split('\n')
    parsed_data: Dict[str, Any] = {"title": "", "summary": "", "tags": [], "body": ""}
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
            body_start_text = line_stripped.split(':', 1)[1].strip()
            if body_start_text:
                 parsed_data["body"] += body_start_text + "\n"
        elif current_section == 'body':
            parsed_data["body"] += line + "\n"
        elif not parsed_data["title"] and not any(kw in line_stripped.lower() for kw in ['要約:', 'タグ:', '本文:']):
            if not parsed_data["title"]:
                 parsed_data["title"] = line_stripped

    parsed_data["body"] = parsed_data["body"].strip()
    if not parsed_data["title"]:
        parsed_data["title"] = "生成された記事"
    if not parsed_data["summary"] and parsed_data["body"]:
        parsed_data["summary"] = parsed_data["body"][:150] + "..." if len(parsed_data["body"]) > 150 else parsed_data["body"]
    if not parsed_data["tags"]:
        parsed_data["tags"] = ["AI生成", "記事"]

    return parsed_data


def generate_article_from_content_gemini(
    source_content_text: str,
    style: str = "blog", # e.g., "blog", "news", "casual", "formal"
    style_descriptions: Optional[Dict[str, str]] = None, # To map style codes to descriptions
    model_name: str = "gemini-1.5-flash",
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_ARTICLE_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None
) -> Optional[Dict[str, Any]]:
    """
    Generates a styled article (title, summary, tags, body, style) from source content
    using the Gemini API.

    Args:
        source_content_text (str): The main text content for the article.
        style (str, optional): The desired style of the article (e.g., "blog", "news").
                               Defaults to "blog".
        style_descriptions (Optional[Dict[str, str]], optional): A dictionary mapping
            style codes (like "blog") to descriptive phrases (like "親しみやすいブログ記事")
            for use in the prompt. If None, uses a default set.
        model_name, api_key, prompt_template, generation_config, safety_settings, configured_model:
            Similar to other Gemini snippets.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representing the article with keys
                                  'title', 'body', 'summary', 'tags' (list), and 'style'.
                                  Returns None on failure.
    """
    if style_descriptions is None:
        style_descriptions = {
            'blog': '親しみやすいブログ記事',
            'news': '客観的で事実に基づいたニュース記事風',
            'casual': 'カジュアルでフレンドリーな文章',
            'formal': 'フォーマルで専門的な記事',
            'technical': '技術的な詳細を含む解説記事',
            'story': '物語風のナラティブな記事'
        }

    selected_style_description = style_descriptions.get(style, style_descriptions['blog']) # Default to blog style

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
        style_description=selected_style_description,
        content_text=source_content_text
    )

    try:
        logger.info(f"Attempting Gemini API call for article generation (Style: {style}, Model: {model_name})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info(f"Gemini response received. Length: {len(response.text)}")
            parsed_article_data = _parse_gemini_response_for_article(response.text)

            # Add the requested style to the output dictionary
            parsed_article_data['style'] = style

            return parsed_article_data
        else:
            logger.warning(f"Gemini API response for article generation (style: {style}) was empty.")
            return None

    except Exception as e:
        logger.error(f"Gemini API error during article generation (style: {style}): {e}", exc_info=True)
        return None

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)):
        print("Skipping test: Gemini SDK not available or API key not configured.")
    else:
        sample_content_tech = "量子コンピューティングは、特定の問題に対して従来のコンピュータよりも指数関数的に高速な計算を可能にする技術です。量子ビット（qubit）の重ね合わせとエンタングルメントの原理を利用します。"

        print("\n--- Test Case 1: Generate 'technical' style article ---")
        article1 = generate_article_from_content_gemini(
            sample_content_tech,
            style="technical",
            api_key=test_api_key
        )
        if article1:
            print("Generated Article (Test 1 - Technical):")
            print(f"  Title: {article1['title']}")
            print(f"  Summary: {article1['summary'][:100]}...")
            print(f"  Tags: {article1['tags']}")
            print(f"  Body (first 100 chars): {article1['body'][:100]}...")
            print(f"  Style: {article1['style']}")
            assert article1['style'] == "technical"
        else:
            print("Failed to generate article (Test 1 - Technical).")

        sample_content_event = "週末に地元のフードフェスティバルに行った。たくさんの屋台が出ていて、美味しいものをいっぱい食べた。特にタコスが最高だった！"
        print("\n--- Test Case 2: Generate 'casual' style article ---")
        article2 = generate_article_from_content_gemini(
            sample_content_event,
            style="casual",
            api_key=test_api_key
        )
        if article2:
            print("Generated Article (Test 2 - Casual):")
            print(f"  Title: {article2['title']}")
            print(f"  Style: {article2['style']}")
            assert article2['style'] == "casual"
        else:
            print("Failed to generate article (Test 2 - Casual).")

        print("\n--- Test Case 3: Generate 'news' style article with JSON mock ---")
        class MockModelReturnsNewsJson:
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                class MockResponse:
                    def __init__(self):
                        self.text = """```json
                        {
                          "title": "Local Library Announces Summer Reading Program",
                          "summary": "The town's library has unveiled its annual summer reading challenge aimed at encouraging children and adults alike to read more during the summer break.",
                          "tags": ["community", "library", "summer program", "reading"],
                          "body": "<p>The Anytown Public Library today announced the launch of its much-anticipated Summer Reading Program, themed 'Adventures in Books'. The program, running from June 1st to August 31st, aims to foster a love for reading across all age groups within the community.</p><p>Librarian Ms. Emily Carter stated, 'We're thrilled to offer a diverse range of activities and incentives this year. Our goal is to show that reading can be a fun and engaging adventure for everyone.' Participants can sign up online or at the library front desk.</p>"
                        }
                        ```"""
                return MockResponse()

        mock_model_news = MockModelReturnsNewsJson()
        article3 = generate_article_from_content_gemini(
            "Details about the library's summer reading program.",
            style="news",
            configured_model=mock_model_news
        )
        if article3:
            print("Generated Article (Test 3 - News Mock):")
            print(f"  Title: {article3['title']}")
            assert "library" in article3['title'].lower()
            assert "news" == article3['style']
            print("  News Mock Test Passed.")
        else:
            print("Failed to generate article (Test 3 - News Mock).")


    print("\nNote: Live API calls to Gemini cost money and depend on network.")
