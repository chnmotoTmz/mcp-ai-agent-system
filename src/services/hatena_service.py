"""
Hatena Blog Service
はてなブログへの記事投稿・管理を担当
"""

import os
import logging
import requests
import hashlib
import random
import base64
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom
from typing import Dict, Optional

from src.config import Config

logger = logging.getLogger(__name__)

class HatenaService:
    def __init__(self):
        self.hatena_id = Config.HATENA_ID
        self.blog_id = Config.HATENA_BLOG_ID
        self.api_key = Config.HATENA_API_KEY
        self.base_url = f"https://blog.hatena.ne.jp/{self.hatena_id}/{self.blog_id}/atom"
    
    def post_article(self, title: str, content: str) -> Optional[str]:
        """シンプルな記事投稿（互換性のため）"""
        try:
            result = self.publish_article(
                title=title,
                content=content,
                tags=['AI生成', 'LINE Bot'],
                category='',
                draft=False
            )
            
            if result and result.get('url'):
                return result['url']
            else:
                logger.error("記事投稿に失敗しました")
                return None
                
        except Exception as e:
            logger.error(f"記事投稿エラー: {e}")
            return None
    
    def publish_article(self, title: str, content: str, tags: list = None, category: str = "", draft: bool = False, content_type: str = "text/x-markdown") -> Optional[Dict]:
        """記事をはてなブログに投稿（MCP対応）
        
        Args:
            title: 記事タイトル
            content: 記事内容
            tags: タグリスト
            category: カテゴリ
            draft: 下書きフラグ
            content_type: コンテンツタイプ ("text/x-markdown", "text/html", "text/x-hatena-syntax")
        
        Returns:
            dict: 投稿結果
        """
        try:
            if tags is None:
                tags = []
            
            # カテゴリをタグに追加
            if category:
                tags.append(category)
            
            # AtomPub形式のXMLを作成
            entry_xml = self._create_entry_xml(
                title=title,
                content=content,
                summary='',  # 簡略要約は空で始める
                tags=tags,
                draft=draft,
                content_type=content_type
            )
            
            # はてなブログAPIに投稿
            response = self._post_to_hatena(entry_xml)
            
            if response and response.status_code == 201:
                # 投稿成功時のレスポンス解析
                result = self._parse_response(response.text)
                
                # MCP用の結果形式で返す
                return {
                    'id': result.get('entry_id', ''),
                    'url': result.get('url', ''),
                    'title': title,
                    'content': content[:100] + '...' if len(content) > 100 else content,
                    'tags': tags,
                    'category': category,
                    'draft': draft,
                    'status': 'published' if not draft else 'draft'
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}" if response else "No response"
                logger.error(f"はてなブログ投稿失敗: {error_msg}")
                raise Exception(f"Publication failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"はてなブログ投稿エラー: {e}")
            raise
    
    def update_article(self, entry_id: str, title: str = None, content: str = None, tags: list = None, category: str = None, content_type: str = "text/x-markdown") -> Optional[Dict]:
        """既存記事の更新（MCP対応）
        
        Args:
            entry_id: 記事ID
            title: 新しいタイトル
            content: 新しい内容
            tags: 新しいタグリスト
            category: 新しいカテゴリ
        
        Returns:
            dict: 更新結果
        """
        try:
            # 既存記事を取得（必要に応じて）
            # ここでは簡易実装として、新しい値で更新
            
            if tags is None:
                tags = []
            
            if category:
                tags.append(category)
            
            # 更新用XMLを作成
            entry_xml = self._create_entry_xml(
                title=title or "Updated Article",
                content=content or "Updated content",
                summary='',
                tags=tags,
                draft=False,
                content_type=content_type
            )
            
            # entry_idから数値部分を抽出
            if entry_id.startswith('tag:'):
                # tag:blog.hatena.ne.jp,2013:blog-motochan1969-26006613719565821-6802418398470039740
                # から最後の数値部分を抽出
                numeric_id = entry_id.split('-')[-1]
            else:
                numeric_id = entry_id
            
            # 更新API呼び出し
            update_url = f"{self.base_url}/entry/{numeric_id}"
            response = self._put_to_hatena(update_url, entry_xml)
            
            if response and response.status_code == 200:
                result = self._parse_response(response.text)
                logger.info(f"はてなブログ更新成功: {result.get('url')}")
                return {
                    'id': entry_id,
                    'url': result.get('url', ''),
                    'title': title,
                    'content': content[:100] + '...' if content and len(content) > 100 else content,
                    'tags': tags,
                    'category': category,
                    'status': 'updated'
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}" if response else "No response"
                logger.error(f"はてなブログ更新失敗: {error_msg}")
                raise Exception(f"Update failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"はてなブログ更新エラー: {e}")
            raise
    
    def get_article(self, entry_id: str) -> Optional[Dict]:
        """記事を取得（MCP対応）
        
        Args:
            entry_id: 記事ID
        
        Returns:
            dict: 記事情報
        """
        try:
            get_url = f"{self.base_url}/entry/{entry_id}"
            response = self._get_from_hatena(get_url)
            
            if response and response.status_code == 200:
                result = self._parse_response(response.text)
                return {
                    'id': entry_id,
                    'url': result.get('url', ''),
                    'status': 'found'
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}" if response else "No response"
                logger.error(f"記事取得失敗: {error_msg}")
                raise Exception(f"Get article failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"記事取得エラー: {e}")
            raise
    
    def delete_article(self, entry_id: str) -> bool:
        """記事の削除"""
        try:
            delete_url = f"{self.base_url}/entry/{entry_id}"
            response = self._delete_from_hatena(delete_url)
            
            if response and response.status_code == 200:
                logger.info(f"はてなブログ削除成功: {entry_id}")
                return True
            else:
                logger.error(f"はてなブログ削除失敗: {response.status_code if response else 'No response'}")
                return False
                
        except Exception as e:
            logger.error(f"はてなブログ削除エラー: {e}")
            return False
    
    def get_articles(self) -> Optional[Dict]:
        """記事一覧の取得"""
        try:
            response = self._get_from_hatena(self.base_url + "/entry")
            
            if response and response.status_code == 200:
                # AtomフィードをパースしてPython辞書に変換
                articles = self._parse_feed(response.text)
                return articles
            else:
                logger.error(f"記事一覧取得失敗: {response.status_code if response else 'No response'}")
                return None
                
        except Exception as e:
            logger.error(f"記事一覧取得エラー: {e}")
            return None
    
    def _clean_content(self, title: str, content: str) -> str:
        """本文からタイトルの重複を除去（改良版）"""
        import re
        
        cleaned_content = content.strip()
        
        # titleが空の場合はそのまま返す
        if not title:
            return cleaned_content
        
        # 正規化されたタイトル（空白や改行を統一）
        normalized_title = re.sub(r'\s+', ' ', title.strip())
        escaped_title = re.escape(normalized_title)
        
        # パターン1: HTMLタグで囲まれたタイトル（より包括的に）
        html_patterns = [
            # ヘッダータグ（属性や改行含む）
            f"<h[1-6][^>]*>\\s*{escaped_title}\\s*</h[1-6]>",
            # 強調タグ（単独）
            f"<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>",
            # パラグラフ内の強調（完全なpタグ）
            f"<p[^>]*>\\s*<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>\\s*</p>",
            # divタグ
            f"<div[^>]*>\\s*{escaped_title}\\s*</div>",
            # タイトルタグ
            f"<title[^>]*>\\s*{escaped_title}\\s*</title>",
            # 単独のpタグ
            f"<p[^>]*>\\s*{escaped_title}\\s*</p>",
        ]
        
        for pattern in html_patterns:
            before_count = len(re.findall(pattern, cleaned_content, flags=re.IGNORECASE | re.DOTALL))
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
            after_count = len(re.findall(pattern, cleaned_content, flags=re.IGNORECASE | re.DOTALL))
            
            # パラグラフ内強調の場合、空のpタグが残る可能性があるので削除
            if before_count > after_count and 'p[^>]*' in pattern:
                cleaned_content = re.sub(r'<p[^>]*>\s*</p>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
        
        # 空のHTMLタグを削除
        cleaned_content = re.sub(r'<p[^>]*>\s*</p>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
        cleaned_content = re.sub(r'<div[^>]*>\s*</div>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
        
        # パターン2: 【】や「」で囲まれたタイトル（行の先頭または全体）
        bracket_patterns = [
            f"【\\s*{escaped_title}\\s*】",
            f"「\\s*{escaped_title}\\s*」", 
            f"『\\s*{escaped_title}\\s*』",
            f"\\[\\s*{escaped_title}\\s*\\]",
            f"\\(\\s*{escaped_title}\\s*\\)",
        ]
        
        for pattern in bracket_patterns:
            # 行の先頭にある場合
            cleaned_content = re.sub(f"^\\s*{pattern}\\s*$", '', cleaned_content, flags=re.MULTILINE)
            # 文章の先頭にある場合
            cleaned_content = re.sub(f"^{pattern}\\s*", '', cleaned_content, flags=re.DOTALL)
        
        # パターン3: プレーンテキストでのタイトル除去（複数行対応）
        lines = cleaned_content.split('\n')
        new_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            # 完全一致
            if line_stripped == normalized_title:
                continue
            # タイトル + 句読点
            if re.match(f"^{escaped_title}[。、.,：:!?！？]\\s*$", line_stripped):
                continue
            # 先頭にタイトルがある行
            if re.match(f"^{escaped_title}\\s*$", line_stripped):
                continue
            new_lines.append(line)
        
        cleaned_content = '\n'.join(new_lines)
        
        # パターン4: 本文の先頭にタイトルがある場合（より厳密に）
        # 先頭のタイトル（前後に改行や空白、句読点がある場合）
        cleaned_content = re.sub(f"^\\s*{escaped_title}\\s*[。、.,：:!?！？]?\\s*\\n?", '', cleaned_content, flags=re.DOTALL)
        
        # パターン5: マークダウン形式のタイトル
        markdown_patterns = [
            f"^#+\\s*{escaped_title}\\s*$",  # # タイトル
            f"^{escaped_title}\\s*\\n[=-]+\\s*$",  # アンダーライン形式
        ]
        
        for pattern in markdown_patterns:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE)
        
        # パターン6: 改行を含むタイトルの対応
        if '\n' in title:
            # 改行を含むタイトルの場合は、改行も考慮して削除
            title_lines = title.strip().split('\n')
            for i, title_line in enumerate(title_lines):
                if title_line.strip():
                    escaped_line = re.escape(title_line.strip())
                    cleaned_content = re.sub(f"^\\s*{escaped_line}\\s*$", '', cleaned_content, flags=re.MULTILINE)
        
        # 先頭と末尾の空行・空白を削除
        cleaned_content = cleaned_content.strip()
        
        # 連続する改行を2つまでに制限
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        # 最終チェック: まだタイトルが残っている場合の最後の削除
        lines = cleaned_content.split('\n')
        while lines and lines[0].strip() == normalized_title:
            lines.pop(0)
        cleaned_content = '\n'.join(lines).strip()
        
        return cleaned_content

    def _create_entry_xml(self, title: str, content: str, summary: str = "", tags: list = None, draft: bool = False, content_type: str = "text/x-markdown") -> str:
        """AtomPub形式のエントリXMLを作成"""
        if tags is None:
            tags = []
        
        # XMLのルート要素を作成
        entry = ET.Element('entry', {
            'xmlns': 'http://www.w3.org/2005/Atom',
            'xmlns:app': 'http://www.w3.org/2007/app'
        })
        
        # タイトル
        title_elem = ET.SubElement(entry, 'title')
        title_elem.text = title
        
        # 本文 - タイトルの重複を除去
        content_elem = ET.SubElement(entry, 'content', {'type': content_type})
        
        # マークダウンの場合はタイトル重複除去を適用、HTMLの場合はそのまま
        if content_type == "text/x-markdown":
            cleaned_content = self._clean_content(title, content)
        else:
            cleaned_content = content
            
        content_elem.text = cleaned_content
        
        # 要約（もしあれば）
        if summary:
            summary_elem = ET.SubElement(entry, 'summary')
            summary_elem.text = summary
        
        # タグ
        for tag in tags:
            category_elem = ET.SubElement(entry, 'category', {'term': tag})
        
        # 公開設定（下書きフラグを考慮）
        app_control = ET.SubElement(entry, 'app:control')
        app_draft = ET.SubElement(app_control, 'app:draft')
        app_draft.text = 'yes' if draft else 'no'
        
        # XMLを整形して文字列として返す
        rough_string = ET.tostring(entry, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _create_wsse_header(self) -> str:
        """WSSE認証ヘッダーを作成"""
        nonce = hashlib.sha1(str(random.random()).encode()).digest()
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        password_digest = hashlib.sha1(nonce + now.encode() + self.api_key.encode()).digest()
        
        return f'UsernameToken Username="{self.hatena_id}", PasswordDigest="{base64.b64encode(password_digest).decode()}", Nonce="{base64.b64encode(nonce).decode()}", Created="{now}"'
    
    def _get_headers(self) -> Dict[str, str]:
        """リクエストヘッダーを取得"""
        return {
            'Content-Type': 'application/xml',
            'X-WSSE': self._create_wsse_header()
        }
    
    def _post_to_hatena(self, xml_data: str) -> Optional[requests.Response]:
        """はてなAPIにPOST"""
        try:
            url = self.base_url + "/entry"
            headers = self._get_headers()
            
            logger.info(f"はてなブログAPIにPOST中: {url}")
            logger.info(f"ヘッダー: {headers}")
            logger.info(f"XMLデータ（最初の500文字）: {xml_data[:500]}")
            
            response = requests.post(url, data=xml_data.encode('utf-8'), headers=headers, timeout=30)
            
            logger.info(f"はてなAPI レスポンス: {response.status_code}")
            logger.info(f"レスポンスヘッダー: {dict(response.headers)}")
            logger.info(f"レスポンス本文: {response.text[:500]}")
            
            return response
            
        except requests.exceptions.Timeout:
            logger.error("はてなAPI POST タイムアウト")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"はてなAPI POST 接続エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"はてなAPI POST エラー: {e}")
            return None
    
    def _put_to_hatena(self, url: str, xml_data: str) -> Optional[requests.Response]:
        """はてなAPIにPUT"""
        try:
            headers = self._get_headers()
            response = requests.put(url, data=xml_data.encode('utf-8'), headers=headers)
            return response
            
        except Exception as e:
            logger.error(f"はてなAPI PUT エラー: {e}")
            return None
    
    def _delete_from_hatena(self, url: str) -> Optional[requests.Response]:
        """はてなAPIにDELETE"""
        try:
            headers = self._get_headers()
            response = requests.delete(url, headers=headers)
            return response
            
        except Exception as e:
            logger.error(f"はてなAPI DELETE エラー: {e}")
            return None
    
    def _get_from_hatena(self, url: str) -> Optional[requests.Response]:
        """はてなAPIからGET"""
        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers)
            return response
            
        except Exception as e:
            logger.error(f"はてなAPI GET エラー: {e}")
            return None
    
    def _parse_response(self, response_xml: str) -> Dict:
        """はてなAPIのレスポンスXMLを解析"""
        try:
            root = ET.fromstring(response_xml)
            
            # 名前空間を定義
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'app': 'http://www.w3.org/2007/app'
            }
            
            # エントリID取得
            entry_id = ""
            id_elem = root.find('atom:id', namespaces)
            if id_elem is not None:
                # URLからエントリIDを抽出
                entry_id = id_elem.text.split('/')[-1]
            
            # 記事URLを取得
            url = ""
            link_elem = root.find('atom:link[@rel="alternate"]', namespaces)
            if link_elem is not None:
                url = link_elem.get('href', '')
            
            return {
                'entry_id': entry_id,
                'url': url,
                'xml': response_xml
            }
            
        except Exception as e:
            logger.error(f"レスポンス解析エラー: {e}")
            return {}
    
    def _parse_feed(self, feed_xml: str) -> Dict:
        """Atomフィードを解析"""
        try:
            root = ET.fromstring(feed_xml)
            
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom'
            }
            
            articles = []
            
            for entry in root.findall('atom:entry', namespaces):
                article = {}
                
                # タイトル
                title_elem = entry.find('atom:title', namespaces)
                if title_elem is not None:
                    article['title'] = title_elem.text
                
                # ID
                id_elem = entry.find('atom:id', namespaces)
                if id_elem is not None:
                    article['id'] = id_elem.text.split('/')[-1]
                
                # URL
                link_elem = entry.find('atom:link[@rel="alternate"]', namespaces)
                if link_elem is not None:
                    article['url'] = link_elem.get('href')
                
                # 更新日時
                updated_elem = entry.find('atom:updated', namespaces)
                if updated_elem is not None:
                    article['updated'] = updated_elem.text
                
                articles.append(article)
            
            return {
                'articles': articles,
                'total': len(articles)
            }
            
        except Exception as e:
            logger.error(f"フィード解析エラー: {e}")
            return {'articles': [], 'total': 0}