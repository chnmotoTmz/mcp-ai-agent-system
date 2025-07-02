# Snippet Guide

Welcome to the detailed guide for the Code Snippets Collection. This document provides
in-depth explanations, usage examples, and important notes for each snippet.

## Table of Contents

1.  [Text Processing (`text_processing/`)](#1-text-processing-text_processing)
    *   [generate_blog_article_fixed.py](#generate_blog_article_fixedpy)
    *   [clean_hatena_content.py](#clean_hatena_contentpy)
    *   [summarize_text_simple.py](#summarize_text_simplepy)
2.  [AI - Gemini Basic (`ai_gemini_basic/`)](#2-ai---gemini-basic-ai_gemini_basic)
    *   [generate_content_gemini.py](#generate_content_geminipy)
    *   [analyze_image_for_blog_gemini.py](#analyze_image_for_blog_geminipy)
    *   ... (other snippets will be added here)
... (other categories will be added here)

---

## 1. Text Processing (`text_processing/`)

This category includes utilities for manipulating, cleaning, and generating text content.

### `generate_blog_article_fixed.py`

**Purpose:** Generates and formats a blog article from input content using a specified "tool" (which is expected to be an object or function capable of content generation). It handles various response formats from the tool and includes fallback mechanisms.

**Main Function:** `async def generate_blog_article_fixed(content: Dict[str, Any], tools: List[Any]) -> Dict[str, Any]`

**Key Arguments:**
- `content` (Dict[str, Any]): A dictionary containing source material. Expected to have a `"text"` key with the main content. Can also include `"title_hint"` and `"tags"`.
- `tools` (List[Any]): A list of tool-like objects. The function searches for a tool with `name == "create_blog_post"`. This tool must have an `async def ainvoke(params: Dict[str, Any])` method.

**Returns:**
- (Dict[str, Any]): A dictionary containing the generated blog post under the `"blog_post"` key (with sub-keys like "title", "content", "tags", "category"), along with `"type": "text_blog_article"` and a `"success": True/False` flag.

**Dependencies:**
- `logging`
- `json`
- `typing` (Dict, Any, List)

**Usage Example:**
```python
import asyncio
import logging
from typing import Dict, Any, List # Ensure these are imported for the example

# Assuming generate_blog_article_fixed and MockTool are defined as in the snippet
# from snippets.text_processing.generate_blog_article_fixed import generate_blog_article_fixed, MockTool

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# MockTool definition for the example to run:
class MockTool: # Defined here for example context
    def __init__(self, name):
        self.name = name
    async def ainvoke(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # This is a mock implementation.
        logger.info(f"MockTool '{self.name}' invoked with params: {params}")
        return {
            "success": True,
            "blog_post": {
                "title": params.get("title_hint", "Generated Title from Mock"),
                "content": params.get("content", "Mock content from tool."),
                "tags": params.get("tags", ["mock", "generated"]),
                "category": "Mock Category"
            }
        }

# generate_blog_article_fixed function definition would be here if running standalone
# For this guide, we assume it's imported or available.
# async def generate_blog_article_fixed(content: Dict[str, Any], tools: List[Any]) -> Dict[str, Any]:
#     # ... (actual function implementation from the snippet)
#     # For brevity in this Markdown, we'll simulate its call below.
#     pass


async def example_generate_blog():
    mock_blog_tool = MockTool(name="create_blog_post")
    test_content = {
        "text": "This is the main content for our new blog post about exciting adventures.",
        "title_hint": "Adventures Await",
        "tags": ["adventure", "travel"]
    }

    # Simulate the call to generate_blog_article_fixed as its definition is external to this MD
    # In a real script, you would:
    # from snippets.text_processing.generate_blog_article_fixed import generate_blog_article_fixed
    # result = await generate_blog_article_fixed(test_content, [mock_blog_tool])

    # Placeholder for the actual call for demonstration purposes in this guide
    print("Simulating call to generate_blog_article_fixed (as it's not defined in this MD snippet)...")
    result = {"success": True, "blog_post": {"title": "Adventures Await (Simulated)", "content": "Simulated blog content about adventures...", "tags": ["adventure", "travel"], "category": "Travelogue"}}


    if result.get("success"):
        blog_post = result.get("blog_post", {})
        print(f"Title: {blog_post.get('title')}")
        print(f"Category: {blog_post.get('category')}")
        print(f"Tags: {blog_post.get('tags')}")
        print(f"Content Preview: {blog_post.get('content', '')[:100]}...")
    else:
        print(f"Blog generation failed: {result.get('error')}")

# To run this example:
# 1. Ensure generate_blog_article_fixed.py is in your PYTHONPATH or same directory.
# 2. Uncomment the import and the actual call to generate_blog_article_fixed within example_generate_blog.
# 3. Run: asyncio.run(example_generate_blog())
# For now, to make this MD snippet runnable in isolation if copy-pasted:
# if __name__ == "__main__":
#     asyncio.run(example_generate_blog())
```
**Notes:**
- The quality and structure of the generated blog post heavily depend on the implementation of the "tool" passed to the function. The snippet includes a `MockTool` for testing.
- The function attempts to parse JSON responses from the tool and has several fallback mechanisms for robustness.

### `clean_hatena_content.py`

**Purpose:** Removes duplicated titles from the beginning of Hatena blog content. This is useful when content generation tools might automatically prepend the title to the content body.

**Main Function:** `def clean_hatena_content(title: str, content: str) -> str`

**Key Arguments:**
- `title` (str): The title of the blog post.
- `content` (str): The raw content of the blog post (potentially containing the title at the beginning).

**Returns:**
- (str): The content string with the leading title removed if found. Otherwise, returns the original content stripped of whitespace.

**Dependencies:**
- `re` (for regular expressions)

**Usage Example:**
```python
# from snippets.text_processing.clean_hatena_content import clean_hatena_content

# title_example = "My Awesome Blog Post"
# raw_content_html_example = f"<h1>{title_example}</h1><p>This is the actual start of the content.</p>"

# Assume clean_hatena_content is available or imported:
# cleaned_html_example = clean_hatena_content(title_example, raw_content_html_example)

# print(f"Original HTML:\n{raw_content_html_example}")
# print(f"Cleaned HTML:\n{cleaned_html_example}")
# Expected: <p>This is the actual start of the content.</p>
# (Actual output depends on the clean_hatena_content function being callable here)
```
**Notes:**
- The function handles various ways a title might be duplicated: plain text, HTML headings (h1-h6), strong/p tags, bracketed titles (【】, 「」), and Markdown headings.
- It normalizes whitespace in the title for more robust matching.

### `summarize_text_simple.py`
(Details to be added in subsequent updates to this guide)

---

## 2. AI - Gemini Basic (`ai_gemini_basic/`)
These snippets provide foundational capabilities for interacting with Google's Gemini Large Language Models. They cover text generation, image analysis, video analysis, and more.

### `generate_content_gemini.py`

**Purpose:** Generates textual content (e.g., a blog article, creative writing) from a given input text using a specified Gemini model. It includes retry logic with exponential backoff for API call robustness.

**Main Function:** `def generate_content_gemini(text: str, model_name: str = "gemini-1.5-flash", ...) -> Optional[str]` (see snippet for full signature)

**Key Arguments:**
- `text` (str): The input text to generate content from.
- `model_name` (str, optional): Name of the Gemini model (e.g., "gemini-1.5-flash").
- `api_key` (Optional[str], optional): Gemini API key. If not set, environment variable `GOOGLE_API_KEY` is used.
- `max_retries` (int, optional): Maximum number of retries for API calls.
- `prompt_template` (str, optional): A string template for the prompt. Must include a `{text}` placeholder.
- `generation_config` (Optional[Dict[str, Any]], optional): Gemini generation configuration (e.g., temperature, max_output_tokens).
- `safety_settings` (Optional[Dict[str, Any]], optional): Gemini safety settings.
- `configured_model` (Optional[Any]): A pre-initialized `genai.GenerativeModel` instance.

**Returns:**
- (Optional[str]): The generated content as a string if successful, or a fallback content string (if retries fail), or `None` if critical components like the SDK are missing or API key is not configured.

**Dependencies:**
- `logging`, `time`, `os`, `typing`, `datetime`
- `google-generativeai` Python SDK (must be installed)

**Usage Example:**
```python
import os
# from snippets.ai_gemini_basic.generate_content_gemini import generate_content_gemini

# Ensure GOOGLE_API_KEY is set in your environment for the example to run,
# or pass the api_key argument to the function.
# API_KEY = os.getenv("GOOGLE_API_KEY")

# input_text_example = "Write a short story about a robot who discovers music."
# generated_story_example = generate_content_gemini(input_text_example) # Uses GOOGLE_API_KEY env var

# if generated_story_example:
#     print("\nGenerated Story:")
#     print(generated_story_example)
# else:
#     print("\nFailed to generate story. Check API key and SDK installation.")
# For this guide, simulate output:
# print("\nGenerated Story (Simulated):\nOnce upon a time, in a world of circuits and code, a robot named Bolt...")
```
**Notes:**
- Requires the `google-generativeai` Python SDK to be installed.
- An API key for Gemini must be available, either via the `api_key` argument or the `GOOGLE_API_KEY` environment variable.
- The default prompt is geared towards generating a blog post in HTML. This can be customized via the `prompt_template` argument for different generation tasks.
- Includes a `create_fallback_content` helper (defined within the snippet) to provide a basic response if the API calls repeatedly fail.

### `analyze_image_for_blog_gemini.py`
(Details to be added in subsequent updates to this guide)

---
(More sections and snippet details will be added in subsequent updates)
