"""
LangGraph 統合エージェント実装
LINE→Gemini→Hatena フローを管理するメインエージェント
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState, ProcessingStage, MessageType
from .nodes import BlogGenerationNodes

logger = logging.getLogger(__name__)

class BlogGenerationAgent:
    """ブログ生成統合エージェント"""
    
    def __init__(self):
        self.nodes = BlogGenerationNodes()
        self.graph = None
        self.checkpointer = MemorySaver()
        self._build_graph()
    
    def _build_graph(self):
        """LangGraph フロー構築"""
        logger.info("LangGraph フロー構築開始")
        
        # グラフ初期化
        workflow = StateGraph(AgentState)
        
        # ノード追加
        workflow.add_node("receive_message", self.nodes.receive_line_message)
        workflow.add_node("analyze_content", self.nodes.analyze_with_gemini)
        workflow.add_node("generate_article", self.nodes.generate_article)
        workflow.add_node("upload_images", self.nodes.upload_images_if_needed)
        workflow.add_node("publish_blog", self.nodes.publish_to_hatena)
        workflow.add_node("notify_user", self.nodes.notify_user)
        workflow.add_node("handle_error", self.nodes.handle_error)
        
        # エントリーポイント設定
        workflow.set_entry_point("receive_message")
        
        # フロー定義
        workflow.add_edge("receive_message", "analyze_content")
        workflow.add_edge("analyze_content", "generate_article")
        workflow.add_edge("generate_article", "upload_images")
        workflow.add_edge("upload_images", "publish_blog")
        workflow.add_edge("publish_blog", "notify_user")
        workflow.add_edge("notify_user", END)
        
        # 条件付きエッジ（エラーハンドリング）
        workflow.add_conditional_edges(
            "receive_message",
            self._should_continue_or_error,
            {
                "continue": "analyze_content",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "analyze_content",
            self._should_continue_or_error,
            {
                "continue": "generate_article",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_article",
            self._should_continue_or_error,
            {
                "continue": "upload_images",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "upload_images",
            self._should_continue_or_error,
            {
                "continue": "publish_blog",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "publish_blog",
            self._should_continue_or_error,
            {
                "continue": "notify_user",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_error",
            self._should_retry_or_end,
            {
                "retry": "receive_message",
                "end": END
            }
        )
        
        # グラフをコンパイル
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        
        logger.info("LangGraph フロー構築完了")
    
    def _should_continue_or_error(self, state: AgentState) -> str:
        """正常継続かエラーハンドリングかを判定"""
        # 最新のエラーをチェック
        if state.errors:
            latest_error = state.errors[-1]
            # 現在のステージでエラーが発生している場合
            if latest_error.stage == state.stage:
                return "error"
        
        return "continue"
    
    def _should_retry_or_end(self, state: AgentState) -> str:
        """リトライするか終了するかを判定"""
        if state.stage == ProcessingStage.FAILED:
            return "end"
        elif state.can_retry():
            return "retry"
        else:
            return "end"
    
    async def process_line_message(self, message_id: str, user_id: str, 
                                 message_type: str, content: str = None, 
                                 file_path: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """LINE メッセージを処理してブログ記事を生成・投稿"""
        session_id = str(uuid.uuid4())
        
        try:
            logger.info(f"新しいセッション開始: {session_id} - ユーザー: {user_id}")
            
            # 初期状態を作成
            initial_state = AgentState(
                session_id=session_id,
                user_id=user_id,
                config=config or {}
            )
            
            # LINE メッセージ情報を設定
            initial_state.set_line_message(
                message_id=message_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                file_path=file_path
            )
            
            # グラフ実行
            logger.info(f"フロー実行開始: {session_id}")
            
            final_state = None
            async for state_update in self.graph.astream(
                initial_state,
                config={"configurable": {"thread_id": session_id}}
            ):
                # 各ステップの進捗をログ出力
                for node_name, updated_state in state_update.items():
                    logger.info(f"ノード '{node_name}' 完了: ステージ={updated_state.stage.value}")
                    final_state = updated_state
            
            # 最終結果を返す
            if final_state:
                result = {
                    "success": final_state.stage == ProcessingStage.COMPLETED,
                    "session_id": session_id,
                    "stage": final_state.stage.value,
                    "processing_time": final_state.processing_time,
                    "summary": final_state.get_summary()
                }
                
                if final_state.hatena_post and final_state.hatena_post.success:
                    result["blog_post"] = {
                        "title": final_state.hatena_post.title,
                        "url": final_state.hatena_post.url,
                        "tags": final_state.hatena_post.tags
                    }
                
                if final_state.errors:
                    result["errors"] = [
                        {
                            "stage": error.stage.value,
                            "type": error.error_type,
                            "message": error.error_message
                        }
                        for error in final_state.errors
                    ]
                
                logger.info(f"フロー完了: {session_id} - 成功: {result['success']}")
                return result
            else:
                raise Exception("フロー実行で最終状態が取得できませんでした")
        
        except Exception as e:
            logger.error(f"フロー実行エラー: {session_id} - {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "stage": "failed"
            }
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション状態を取得"""
        try:
            # checkpointer から状態を取得
            checkpoint = await self.checkpointer.aget(
                config={"configurable": {"thread_id": session_id}}
            )
            
            if checkpoint and checkpoint.channel_values:
                state = checkpoint.channel_values.get("__start__")
                if isinstance(state, AgentState):
                    return state.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"セッション状態取得エラー: {session_id} - {e}")
            return None
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """アクティブなセッション一覧を取得"""
        try:
            # checkpointer からすべてのセッションを取得
            sessions = []
            
            # MemorySaver の内部状態にアクセス（実装依存）
            if hasattr(self.checkpointer, 'storage'):
                for thread_id, checkpoint in self.checkpointer.storage.items():
                    if checkpoint and checkpoint.channel_values:
                        state = checkpoint.channel_values.get("__start__")
                        if isinstance(state, AgentState):
                            sessions.append({
                                "session_id": thread_id,
                                "user_id": state.user_id,
                                "stage": state.stage.value,
                                "created_at": state.created_at.isoformat(),
                                "updated_at": state.updated_at.isoformat()
                            })
            
            return sessions
            
        except Exception as e:
            logger.error(f"アクティブセッション取得エラー: {e}")
            return []
    
    async def cancel_session(self, session_id: str) -> bool:
        """セッションをキャンセル"""
        try:
            # checkpointer から状態を削除
            if hasattr(self.checkpointer, 'storage'):
                if session_id in self.checkpointer.storage:
                    del self.checkpointer.storage[session_id]
                    logger.info(f"セッションキャンセル: {session_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"セッションキャンセルエラー: {session_id} - {e}")
            return False
    
    def get_graph_visualization(self) -> str:
        """グラフ構造の可視化（Mermaid形式）"""
        return """
graph TD
    A[receive_message] --> B[analyze_content]
    B --> C[generate_article]
    C --> D[upload_images]
    D --> E[publish_blog]
    E --> F[notify_user]
    F --> G[END]
    
    A --> H[handle_error]
    B --> H
    C --> H
    D --> H
    E --> H
    
    H --> A
    H --> G
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#e0f2f1
    style H fill:#ffebee
"""

# シングルトンインスタンス
_agent_instance = None

def get_blog_agent() -> BlogGenerationAgent:
    """ブログ生成エージェントのシングルトンインスタンスを取得"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BlogGenerationAgent()
    return _agent_instance

async def process_line_message_async(message_id: str, user_id: str, 
                                   message_type: str, content: str = None,
                                   file_path: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """LINE メッセージ処理の非同期エントリーポイント"""
    agent = get_blog_agent()
    return await agent.process_line_message(
        message_id=message_id,
        user_id=user_id,
        message_type=message_type,
        content=content,
        file_path=file_path,
        config=config
    )
