# Code Snippets Collection

This repository contains a collection of reusable Python code snippets organized by functionality.
These snippets are designed to be easily integrated into various projects.

## Directory Structure

```
snippets/
├── text_processing/
├── ai_gemini_basic/
├── ai_gemini_enhancement/
├── api_hatena/
├── api_line/
├── api_imgur_pipedream/
├── api_google_photos/
├── database_operations/
├── file_operations/
├── process_async/
└── config_management/
```

## Categories and Snippets

### 1. Text Processing (`text_processing/`)
Utilities for manipulating and generating text content.
- `generate_blog_article_fixed.py`: Generates and formats a blog article from input content and tools.
- `clean_hatena_content.py`: Removes duplicate titles from Hatena blog content.
- `summarize_text_simple.py`: Creates a simple summary of a given text based on length.

### 2. AI - Gemini Basic (`ai_gemini_basic/`)
Snippets for basic interactions with Google's Gemini AI models.
- `generate_content_gemini.py`: Generates content from text using Gemini (with retries).
- `analyze_image_for_blog_gemini.py`: Analyzes an image and generates blog post text using Gemini.
- `analyze_video_gemini.py`: Uploads and analyzes a video, then generates blog post text using Gemini.
- `analyze_multiple_media_gemini.py`: Integrates analysis of multiple media types (text, image, video) using Gemini.
- `create_blog_post_gemini.py`: Creates a structured blog post (title, summary, tags, body) from source content using Gemini.
- `generate_article_from_content_gemini.py`: Generates an article of a specified style from source content using Gemini.
- `create_integrated_article_gemini.py`: Creates an article by integrating text content with image analyses using Gemini.
- `chat_gemini.py`: Engages in a chat-like conversation with Gemini, supporting history.
- `get_model_info_gemini.py`: Retrieves information about a specified Gemini model.
- `analyze_image_gemini_enhanced.py`: Enhanced image analysis with retries, file size checks, and multiple upload methods.
- `parse_gemini_article_response.py`: Parses text or JSON responses from Gemini into a structured article dictionary.

### 3. AI - Gemini Enhancement (`ai_gemini_enhancement/`)
Snippets focused on improving or augmenting content using Gemini AI.
- `improve_text_quality_gemini.py`: Improves text quality (proofreading, flow, readability) using Gemini.
- `add_internal_links_gemini.py`: Adds internal links to HTML content based on a list of similar articles, using Gemini.
- `analyze_image_for_enhancement_gemini.py`: Analyzes an image to extract descriptive elements for content enrichment using Gemini.
- `enhance_content_with_image_analysis_gemini.py`: Enhances HTML content by integrating textual analysis of an image, using Gemini.
- `generate_content_summary_gemini.py`: Generates a concise summary of text content using Gemini.

### 4. API Integration - Hatena Blog (`api_hatena/`)
Functions for interacting with the Hatena Blog API (AtomPub).
- `publish_hatena_article.py`: Publishes a new article to Hatena Blog.
- `update_hatena_article.py`: Updates an existing article on Hatena Blog.
- `get_hatena_article.py`: Retrieves a specific article from Hatena Blog.
- `delete_hatena_article.py`: Deletes an article from Hatena Blog.
- `get_hatena_articles_list.py`: Retrieves a list of articles from Hatena Blog, supporting pagination.

### 5. API Integration - LINE (`api_line/`)
Utilities for interacting with LINE Messaging API.
- `send_line_message.py`: Sends messages (text, etc.) to a LINE user.
- `download_line_content.py`: Downloads content (images, video, audio) from a LINE message.

### 6. API Integration - Imgur via Pipedream MCP (`api_imgur_pipedream/`)
Snippets for interacting with Imgur, assuming an MCP (Media Control Proxy) script.
- `upload_image_pipedream_mcp.py`: Uploads an image to Imgur via an MCP script.
- `get_imgur_account_images_mcp.py`: Retrieves a list of account images from Imgur via an MCP script.
- `health_check_imgur_mcp.py`: Performs a health check of the Imgur service via an MCP script.

### 7. API Integration - Google Photos (`api_google_photos/`)
Functions for interacting with the Google Photos Library API.
- `upload_google_photos_image.py`: Uploads an image to Google Photos library.

### 8. Database Operations (SQLAlchemy) (`database_operations/`)
SQLAlchemy-based database interaction snippets.
- `save_line_message_sqlalchemy.py`: Saves a LINE-like message structure to a database, checking for duplicates.
- `get_user_messages_sqlalchemy.py`: Retrieves messages for a specific user, with limit and ordering.
- `get_unprocessed_messages_sqlalchemy.py`: Retrieves messages marked as unprocessed, with limit and ordering.

### 9. File Operations (`file_operations/`)
Utilities for file handling.
- `get_file_extension_from_content_type.py`: Determines a file extension from a content type or MIME type string.

### 10. Process & Async Operations (`process_async/`)
Snippets for asynchronous operations and subprocess management.
- `run_async_subprocess.py`: Runs an external command asynchronously, capturing output and handling errors.

### 11. Configuration Management (`config_management/`)
Utilities for loading and managing configurations.
- `load_json_config.py`: Loads configuration from a JSON file with error handling and optional creation.

## How to Use

Each snippet is designed to be relatively self-contained or clearly define its dependencies (like specific SDKs or API keys). Refer to the individual `.py` files for detailed usage instructions, arguments, and examples within their `if __name__ == "__main__":` blocks.

For more detailed explanations and advanced use cases, please refer to the Snippet Guide documentation (link to be added in `docs/snippet_guide.md`).
