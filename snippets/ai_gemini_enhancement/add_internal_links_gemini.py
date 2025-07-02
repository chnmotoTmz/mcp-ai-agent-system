import logging
import os
from typing import Optional, Dict, Any, List

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_ADD_LINKS_PROMPT_TEMPLATE = """
以下のブログ記事に、関連する記事への内部リンクを自然な形で追加してください。
記事の最後（または文脈上適切な箇所）に「関連記事」や「こちらもおすすめ」といったセクションを設け、提供された関連記事リストへのリンクをHTML形式で挿入してください。

元記事のHTML：
```html
{article_html_content}
```

関連記事リスト (タイトルとURL)：
{similar_articles_text}

要求：
- 元記事の内容や構成を大幅に変更しないでください。主に追記の形で内部リンクセクションを追加します。
- 内部リンクは、読者にとって価値のある、文脈に沿ったものにしてください。
- リンクのアンカーテキストは、関連記事のタイトルを適切に使用してください。
- リンクの挿入箇所は、記事の最後が基本ですが、モデルが文脈上より自然と判断した場合は本文中への挿入も許可します（ただし、可読性を損なわない範囲で）。
- 元の記事の雰囲気やトーンを維持してください。

出力要求事項：
- 内部リンクが追加された、記事全体の完全なHTMLを出力してください。
- HTMLタグ（例: <p>, <br>, <a>, <ul>, <li>, <h2>）を適切に使用してください。
- マークダウン記法は使用しないでください。
"""

def add_internal_links_gemini(
    article_html_content: str,
    similar_articles: List[Dict[str, str]], # Expects list of {'title': '...', 'url': '...'}
    model_name: str = "gemini-1.5-flash",
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_ADD_LINKS_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None,
    max_links_to_add: int = 5 # Limit the number of links to suggest in the prompt
) -> Optional[str]:
    """
    Adds internal links to related articles within a given HTML blog post content using Gemini API.

    Args:
        article_html_content (str): The HTML content of the original blog post.
        similar_articles (List[Dict[str, str]]): A list of dictionaries, where each
            dictionary represents a similar article and should have 'title' and 'url' keys.
        model_name, api_key, prompt_template, generation_config, safety_settings, configured_model:
            Standard Gemini configuration arguments.
        max_links_to_add (int): Maximum number of similar articles to include in the prompt
                                to suggest links for.

    Returns:
        Optional[str]: The HTML content of the blog post with added internal links,
                       or None if the process fails.
    """
    if not article_html_content:
        logger.warning("Original article content is empty. Cannot add internal links.")
        return article_html_content # Return original if empty

    if not similar_articles:
        logger.info("No similar articles provided. Returning original content.")
        return article_html_content

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

    # Prepare the list of similar articles for the prompt
    # Limit the number of articles sent to the prompt to avoid excessive length
    limited_similar_articles = similar_articles[:max_links_to_add]
    similar_articles_text_lines = []
    for article in limited_similar_articles:
        title = article.get('title', '関連記事')
        url = article.get('url', '#') # Use '#' if URL is missing
        if url: # Only add if URL is present
            similar_articles_text_lines.append(f"- 「{title}」へのリンク: {url}")

    if not similar_articles_text_lines:
        logger.info("No valid similar articles with URLs to add. Returning original content.")
        return article_html_content

    similar_articles_text = "\n".join(similar_articles_text_lines)

    prompt = prompt_template.format(
        article_html_content=article_html_content,
        similar_articles_text=similar_articles_text
    )

    try:
        logger.info(f"Attempting Gemini API call to add internal links (Model: {model_name})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info("Internal links addition successful.")
            # The model is expected to return the full HTML with links added.
            return response.text.strip()
        else:
            logger.warning("Gemini API response for adding internal links was empty.")
            return None # Or return original_article_content as a fallback

    except Exception as e:
        logger.error(f"Gemini API error during internal link addition: {e}", exc_info=True)
        return None # Or return original_article_content

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)): # type: ignore
        print("Skipping internal links test: Gemini SDK not available or API key not configured.")
    else:
        sample_article_html = """
        <h1>My Trip to the Zoo</h1>
        <p>Today, I visited the local zoo and saw many amazing animals.
        The lions were majestic, and the monkeys were very playful.</p>
        <p>One of the highlights was the penguin enclosure. They are such fascinating birds!</p>
        <h2>Feeding Time</h2>
        <p>We also got to see the seals during their feeding time, which was a lot of fun.</p>
        """

        related_posts = [
            {"title": "Understanding Penguin Behavior", "url": "https://example.com/penguins"},
            {"title": "The Majesty of Lions: A Photo Essay", "url": "https://example.com/lions"},
            {"title": "Top 10 Playful Monkey Species", "url": "https://example.com/monkeys"},
            {"title": "A Day at the Aquarium (No URL for this one)", "url": ""}, # Test missing URL
            {"title": "Seal Conservation Efforts", "url": "https://example.com/seals"}
        ]

        print("\n--- Test Case 1: Add internal links to sample article ---")
        updated_html1 = add_internal_links_gemini(
            sample_article_html,
            related_posts,
            api_key=test_api_key
        )
        if updated_html1:
            print("Article with Internal Links (Test 1):")
            print(updated_html1)
            # Basic check: see if some URLs are present
            assert "example.com/penguins" in updated_html1 or "Understanding Penguin Behavior" in updated_html1
            assert "example.com/lions" in updated_html1 or "Majesty of Lions" in updated_html1
        else:
            print("Failed to add internal links (Test 1).")

        print("\n--- Test Case 2: No similar articles ---")
        updated_html2 = add_internal_links_gemini(sample_article_html, [], api_key=test_api_key)
        if updated_html2:
            print("Article with No Similar Articles (Test 2):")
            print(updated_html2)
            assert updated_html2.strip() == sample_article_html.strip() # Should return original
        else:
            print("Failed (unexpectedly) for no similar articles (Test 2).")

        print("\n--- Test Case 3: Simulating an API error (mocked) ---")
        class MockModelLinksFail:
            def generate_content(self, prompt, generation_config=None, safety_settings=None):
                raise Exception("Simulated API failure for link addition")

        mock_model_fail_links = MockModelLinksFail()
        updated_html_fail = add_internal_links_gemini(
            sample_article_html,
            related_posts,
            configured_model=mock_model_fail_links
        )
        print(f"Result on failure: {updated_html_fail}")
        assert updated_html_fail is None # Expecting None on error
        print("Internal links error handling test passed.")

    print("\nNote: Live API calls to Gemini cost money and depend on network.")
    print("The quality of link placement depends on the prompt and model's understanding.")
