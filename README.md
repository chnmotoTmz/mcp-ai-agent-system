# 🤖 MCP AI Agent System

**2025年最先端マルチエージェント・オーケストレーション**システム

LINE → Gemini → はてなブログ 自動化システム

## 🚀 特徴

### 🔥 2025年トレンド完全対応
- ✅ **Model Context Protocol (MCP)** 標準準拠
- ✅ **LangGraph** マルチエージェント・ワークフロー  
- ✅ **FastMCP** 最新実装
- ✅ **Agent-to-Agent** 通信プロトコル準備済み

### 🎯 システム概要
```
🤖 MCP AI Agent System
├── 🔧 MCP Servers (FastMCP)
│   ├── LINE MCP Server (メッセージ受信・送信)
│   ├── Gemini MCP Server (AI コンテンツ生成)
│   └── Hatena MCP Server (ブログ投稿)
├── 🧠 AI Agent Core (LangGraph)
│   ├── メッセージ分析ノード
│   ├── タスクルーティングノード
│   ├── コンテンツ生成ノード
│   ├── 記事投稿ノード
│   └── 通知ノード
└── 🌐 Flask API
    ├── LINE Webhook受信
    ├── AIエージェントテスト
    └── ヘルスチェック
```

## Project Structure Overview

This project contains two main application entry points:

1.  **Main Application (`main.py`)**:
    *   This is the primary Flask application for the LINE to Hatena blog automation.
    *   It handles incoming LINE webhooks using an enhanced batch processing system (`src/routes/webhook_enhanced.py`). This system collects messages (text, images, videos), processes them in batches per user, uses Gemini for content analysis and generation, integrates with Imgur for image hosting, and posts articles to Hatena.
    *   It exposes REST APIs for accessing articles, messages, and other functionalities (`src/routes/api.py`).
    *   Database interaction (SQLAlchemy with `src.database.py`) is central to this application for storing messages, articles, and batch processing states.

2.  **LangGraph Application (`langgraph_main.py`)**:
    *   This is a separate Flask application dedicated to showcasing an alternative processing pipeline using LangGraph agents.
    *   It handles LINE webhooks via `src/routes/langgraph_routes.py` and processes messages using a more complex, stateful agent defined in `src/langgraph_agents/`.
    *   This system is geared towards more advanced, multi-step agentic workflows and leverages the LangGraph library.

The choice of which application to run depends on the desired processing model. The `main.py` application provides a robust batch-oriented system, while `langgraph_main.py` offers a more flexible agent-based approach.

## 🛠 セットアップ

### 1. 環境準備
```bash
git clone https://github.com/chnmotoTmz/mcp-ai-agent-system.git
cd line-gemini-hatena-integration
chmod +x setup_mcp.sh
./setup_mcp.sh
```

### 2. 環境変数設定
```bash
cp .env.example .env
# .envファイルを編集して必要な環境変数を設定
```

### 3. システム起動
```bash
python3 start_mcp_system.py
```

## 🧪 テスト方法

### AIエージェントテスト
```bash
curl -X POST http://localhost:8084/api/webhook/test \
  -H 'Content-Type: application/json' \
  -d '{"message": "AIエージェントのテストです", "user_id": "test_user"}'
```

### システム状態確認
```bash
curl http://localhost:8084/status
```

## 📋 必要な環境変数

```env
# LINE Bot設定
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# Gemini API設定
GEMINI_API_KEY=your_gemini_api_key

# はてなブログ設定
HATENA_USER_ID=your_hatena_user_id
HATENA_BLOG_ID=your_hatena_blog_id
HATENA_API_KEY=your_hatena_api_key

# その他
SECRET_KEY=your_secret_key
PORT=8084
```

## 🏗 アーキテクチャ

### MCP Servers
- **LINE MCP Server** (`src/mcp_servers/line_server_fastmcp.py`)
  - LINEメッセージの送受信
  - ユーザーコンテキスト管理
  - メッセージ履歴取得

- **Gemini MCP Server** (`src/mcp_servers/gemini_server_fastmcp.py`)
  - AIコンテンツ生成
  - 画像分析
  - ブログ記事作成

- **Hatena MCP Server** (`src/mcp_servers/hatena_server_fastmcp.py`)
  - はてなブログ記事投稿
  - 記事管理
  - ブログ統計取得

### AI/Agent Components

The system employs AI for content generation and processing in two main ways:

1.  **Primary Application (`main.py`)**:
    *   The LINE message processing workflow in `src/routes/webhook_enhanced.py` directly utilizes `src/services/gemini_service.py` for:
        *   Analyzing images and generating textual descriptions.
        *   Generating blog content based on collected user messages (text and image analyses).
        *   Generating article titles.
    *   This approach is service-oriented, with direct calls to the Gemini service for specific AI tasks within the batch processing flow.

2.  **LangGraph Application (`langgraph_main.py`)**:
    *   This application uses a dedicated LangGraph agent defined in `src/langgraph_agents/agent.py`.
    *   This agent orchestrates a more complex, stateful workflow involving multiple steps (nodes in the graph) which can include calls to MCP servers (like Gemini, Hatena, etc.) for various AI and publishing tasks.
    *   This architecture is designed for building sophisticated, multi-actor AI systems.

## 🔧 開発・拡張

### 新しいMCPサーバーの追加

1. **サーバー作成**
```python
from mcp.server.fastmcp import FastMCP

new_mcp = FastMCP("New Service")

@new_mcp.tool()
async def new_tool(param: str) -> dict:
    """新しいツールの実装"""
    return {"result": f"処理結果: {param}"}
```

2. **エージェントへの統合**
```python
# ContentCreationAgentのMCPクライアント設定に追加
"new_service": {
    "command": "python",
    "args": ["/path/to/new_server.py"],
    "transport": "stdio"
}
```

### 新しいエージェントの追加

新しい専門エージェントを作成し、Agent-to-Agent通信でコラボレーション可能：

```python
class SpecializedAgent:
    """専門エージェント"""
    
    async def collaborate_with(self, other_agent):
        """他のエージェントとの協調処理"""
        pass
```

## 📈 ロードマップ

### Phase 2: 追加MCPサーバー
- [ ] NotebookLM MCP Server (ドキュメント解析)
- [ ] Whisper MCP Server (音声文字起こし)
- [ ] YouTube MCP Server (動画作成・投稿)
- [ ] Analytics MCP Server (分析・レポート)

### Phase 3: マルチエージェント強化
- [ ] Agent-to-Agent (A2A) プロトコル実装
- [ ] エージェント・マーケットプレイス
- [ ] 動的エージェント生成
- [ ] 学習・進化機能

## 🤝 コントリビューション

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

## 🙏 謝辞

- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic
- [LangGraph](https://langchain-ai.github.io/langgraph/) - LangChain AI
- [FastMCP](https://github.com/jlowin/fastmcp) - Marvin AI

---

**🎯 2025年マルチエージェント時代の標準システム**

Made with ❤️ for the AI Agent Revolution