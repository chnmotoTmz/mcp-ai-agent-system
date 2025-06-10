"""
Blog Article Generation Fix
データ構造解析の修正版
"""

import json
import logging

logger = logging.getLogger(__name__)

async def generate_blog_article_fixed(content, tools):
    """
    修正版ブログ記事生成
    データ構造の問題を解決
    """
    try:
        # ブログ生成ツールを検索
        generate_tool = None
        for tool in tools:
            if tool.name == "create_blog_post":
                generate_tool = tool
                break
        
        if not generate_tool:
            logger.warning("Blog generation tool not found, using fallback")
            # フォールバック: 元のテキストをそのまま記事として使用
            text_content = content.get("text", "")
            return {
                "type": "text_blog_article",
                "blog_post": {
                    "title": "AI生成記事",
                    "content": text_content if text_content else "コンテンツの生成に失敗しました。",
                    "tags": ["ブログ", "AI生成"],
                    "category": "日記"
                },
                "success": True
            }
        
        # ブログ投稿を生成
        text_content = content.get("text", "")
        logger.info(f"Generating blog from text: {text_content[:100]}...")
        
        blog_result = await generate_tool.ainvoke({
            "content": text_content,
            "title_hint": "",
            "tags": ["ブログ", "AI生成"]
        })
        
        logger.info(f"Blog generation result type: {type(blog_result)}")
        
        # JSON文字列の場合はパース
        if isinstance(blog_result, str):
            try:
                blog_result = json.loads(blog_result)
                logger.info("Successfully parsed JSON response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                # フォールバック: 直接文字列として使用
                return {
                    "type": "text_blog_article",
                    "blog_post": {
                        "title": "AI生成記事",
                        "content": blog_result,
                        "tags": ["ブログ", "AI生成"],
                        "category": "日記"
                    },
                    "success": True
                }
        
        # データ検証と抽出
        if not isinstance(blog_result, dict):
            logger.error(f"Unexpected blog_result type: {type(blog_result)}")
            return {"error": "Invalid blog result format", "success": False}
        
        if not blog_result.get("success", True):
            error_msg = blog_result.get("error", "Unknown error")
            logger.error(f"Blog generation failed: {error_msg}")
            return {"error": error_msg, "success": False}
        
        # blog_postデータを抽出
        blog_post_raw = blog_result.get("blog_post", {})
        
        # blog_postがdictの場合の処理
        if isinstance(blog_post_raw, dict):
            # 直接使用できる形式
            title = blog_post_raw.get("title", "AI生成記事")
            content_text = blog_post_raw.get("content", "")
            tags = blog_post_raw.get("tags", ["ブログ", "AI生成"])
            category = blog_post_raw.get("category", "日記")
            
            # contentが空の場合、titleから本文を抽出してみる
            if not content_text or content_text == "記事内容の生成に失敗しました。":
                # titleに本文が含まれている可能性をチェック
                if "本文:" in title:
                    parts = title.split("本文:", 1)
                    if len(parts) == 2:
                        # タイトルと本文を分離
                        actual_title = parts[0].split("要約:")[0].strip()
                        content_text = parts[1].strip()
                        
                        # タグを抽出
                        if "タグ:" in title:
                            tag_section = title.split("タグ:")[1].split("本文:")[0]
                            extracted_tags = [tag.strip() for tag in tag_section.split(",") if tag.strip()]
                            if extracted_tags:
                                tags = extracted_tags
                        
                        title = actual_title
                        logger.info(f"Extracted from title - Title: {title[:50]}, Content: {content_text[:100]}")
            
            # 型変換と検証
            title = str(title) if title else "AI生成記事"
            content_text = str(content_text) if content_text else ""
            if isinstance(tags, str):
                tags = [tags]
            elif not isinstance(tags, list):
                tags = ["ブログ", "AI生成"]
            category = str(category) if category else "日記"
            
            blog_post_clean = {
                "title": title,
                "content": content_text,
                "tags": tags,
                "category": category
            }
        else:
            # blog_postが文字列や他の形式の場合
            logger.warning(f"blog_post is not dict: {type(blog_post_raw)}")
            blog_post_clean = {
                "title": "AI生成記事",
                "content": str(blog_post_raw) if blog_post_raw else "コンテンツの生成に失敗しました。",
                "tags": ["ブログ", "AI生成"],
                "category": "日記"
            }
        
        # 最終検証
        if not blog_post_clean.get("content") or blog_post_clean["content"] == "記事内容の生成に失敗しました。":
            logger.warning("Content is empty or failed, using original text")
            blog_post_clean["content"] = text_content if text_content else "内容の生成に問題が発生しました。"
        
        # 型の最終確認
        for key, value in blog_post_clean.items():
            if key == "tags" and not isinstance(value, list):
                blog_post_clean[key] = [str(value)] if value else ["ブログ", "AI生成"]
            elif key != "tags" and not isinstance(value, str):
                blog_post_clean[key] = str(value)
        
        logger.info(f"Final blog post: title='{blog_post_clean['title']}', content_length={len(blog_post_clean['content'])}, tags={blog_post_clean['tags']}")
        
        return {
            "type": "text_blog_article", 
            "blog_post": blog_post_clean,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Blog article generation failed: {e}")
        import traceback
        traceback.print_exc()
        # 完全フォールバック
        text_content = content.get("text", "") if isinstance(content, dict) else str(content)
        return {
            "type": "text_blog_article",
            "blog_post": {
                "title": "AI生成記事",
                "content": text_content if text_content else "内容の生成に問題が発生しました。",
                "tags": ["ブログ", "AI生成"],
                "category": "日記"
            },
            "success": True
        }
