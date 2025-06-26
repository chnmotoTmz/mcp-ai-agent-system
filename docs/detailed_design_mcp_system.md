## 詳細設計：`main.py` から辿る処理の流れ

本システムの中心的な処理は、`main.py` で起動されるFlaskアプリケーションによって駆動されます。ここでは、`main.py` から始まり、LINEからのWebhook受信、Geminiによるコンテンツ処理、そしてはてなブログへの投稿に至るまでの主要な処理フローを詳細に追っていきます。

**1. アプリケーションの初期化 (`main.py`)**

*   **エントリーポイント**: `if __name__ == '__main__':` ブロックが実行の起点です。
*   **`create_app()` 関数**:
    *   Flaskアプリケーションインスタンス (`app`) を作成します。
    *   `app.config.from_object(Config)` により、`src/config.py` に定義された設定値（APIキー、データベース接続情報、LINEチャネル情報など）をアプリケーションにロードします。環境変数 (`.env`経由) からも設定が読み込まれるため、柔軟な設定管理が可能です。
    *   `db.init_app(app)` により、Flask-SQLAlchemyのデータベースインスタンスをアプリケーションに紐付けます。
    *   `register_routes(app)` を呼び出し、APIエンドポイントを登録します。これは `src/routes/__init__.py` 内で定義されています。
    *   `with app.app_context(): init_db()` により、データベースのテーブル作成など初期化処理を実行します。
*   **サーバー起動**: `app.run()` により、Flask開発サーバーが指定されたホストとポート（デフォルト `0.0.0.0:8084`）で起動し、リクエスト待機状態に入ります。ロギングも `logging.basicConfig` で設定され、デバッグモードは環境変数 `FLASK_ENV` に基づいて制御されます。

**2. ルーティング定義 (`src/routes/__init__.py`)**

`register_routes(app)` 関数が呼び出されると、以下の主要なブループリントが登録されます。

*   **`webhook_bp`**: `src/routes/webhook_enhanced.py` で定義されたブループリント。`/api/webhook` というURLプレフィックスで登録されます。LINEからのWebhook通知はこのブループリント内のエンドポイントで処理されます。
*   **`api_bp`**: `src/routes/api.py` で定義。一般的なAPIエンドポイント（記事取得など）がここに配置されると推測されます。
*   **`health_bp`**: `src/routes/health.py` で定義。システムの死活監視用エンドポイント。
*   ルートエンドポイント (`@app.route('/')`) や基本的なエラーハンドラもここで定義されています。

**3. LINE Webhook処理 (`src/routes/webhook_enhanced.py`)**

本システムのコア機能であるLINEからのメッセージ処理は、主にこのファイルで実装されています。

*   **エンドポイント**: `@webhook_bp.route('/line', methods=['POST'])` がLINE PlatformからのWebhookリクエストを受け付けます。
*   **初期化**: `LineBotApi`, `WebhookHandler` のインスタンス化、および `LineService`, `GeminiService`, `HatenaService` のインスタンス化が行われます。これらはそれぞれLINE API、Gemini API、はてなブログAPIとのやり取りを担当するサービスクラスです。
*   **署名検証**: LINE Platformから送信されるリクエストの正当性を検証するため、`X-Line-Signature` ヘッダーとリクエストボディを用いて署名を検証します。（現状の実装では、デバッグ目的で一時的にこの検証がスキップされている箇所があります）。
*   **イベントのパースとディスパッチ**: Webhookリクエストボディ（JSON形式）をパースし、含まれるイベント（例：メッセージイベント）を抽出します。現在は署名検証ハンドラ (`handler.handle(body, signature)`) を直接使わず、手動でイベントをループ処理し、`process_message_event_with_batch(event_data)` 関数を呼び出しています。

**4. メッセージイベント処理とバッチ化 (`process_message_event_with_batch` 関数)**

この関数が、個々のLINEメッセージイベントに対する初期処理とバッチ化のロジックを担います。

*   **メッセージ種別判定**: イベントデータからメッセージのID、ユーザーID、メッセージタイプ（テキスト、画像、動画など）を取得します。
*   **データベースへの初期保存**:
    *   受信したメッセージの基本情報（LINEメッセージID, ユーザーID, タイプ, タイムスタンプなど）を `Message` テーブルに保存します。
    *   **テキストメッセージの場合**: テキスト内容を `content` フィールドに保存します。
    *   **画像メッセージの場合**:
        1.  `line_bot_api.get_message_content()` で画像データを取得し、ローカルの `uploads` ディレクトリに保存します。
        2.  保存した画像パスを `gemini_service.analyze_image()` に渡し、Gemini APIを利用して画像の内容をテキストで説明させます（【1回目Gemini】）。この解析結果が `analyzed_text` となります。
        3.  `src/mcp_servers/imgur_server_fastmcp.py` の `upload_image` 関数を利用し、画像をImgurにアップロードします。成功すればImgurのURLが得られます。
        4.  `analyzed_text` と画像のローカルパス、Imgur URLを `Message` テーブルに保存します。
    *   **動画メッセージの場合**: 同様に動画コンテンツを保存し、そのパスを記録します。
*   **バッチへの追加 (`add_message_to_batch` 関数)**:
    *   処理されたメッセージデータ（テキスト内容や画像解析結果を含む）を、ユーザーIDごとに管理されるグローバル変数 `user_message_buffer` にリストとして追加します。
    *   `threading.Timer` を使用して、`BATCH_INTERVAL`（デフォルト2分）後に `process_user_batch(user_id)` 関数を実行するタイマーをセットします。同じユーザーから連続してメッセージが来た場合、既存のタイマーはキャンセルされ、新しいタイマーがセットされるため、最後のメッセージから一定時間後にバッチ処理が開始される仕組みです。

**5. バッチ処理実行 (`process_user_batch` 関数)**

タイマーによって呼び出されるこの関数が、蓄積されたメッセージ群をまとめて処理し、ブログ記事を生成・投稿します。Flaskのアプリケーションコンテキスト内で実行されるよう工夫されています。

*   **メッセージの集約**: `user_message_buffer` から該当ユーザーのメッセージ群を取り出します。
*   **コンテンツ統合 (`create_integrated_content_fixed` 関数)**:
    *   バッチ内の全メッセージ（テキストメッセージの本文、画像メッセージのGemini解析結果、動画メッセージの情報）を一つのテキストにまとめます。
    *   この統合されたテキストをプロンプトとして `gemini_service.generate_content()` に渡し、ブログ記事本文を生成させます（【2回目Gemini】）。
*   **タイトル生成 (`generate_article_title` 関数)**: バッチ内のメッセージ内容（主に最初のテキストメッセージ）を基に、記事のタイトルを生成します。画像や動画の有無に応じて「（画像付き）」などの接尾辞が付加されます。
*   **画像URLの挿入 (`insert_imgur_urls_to_content` 関数)**: 生成されたブログ記事本文に対し、バッチ内の画像メッセージに対応するImgurのURLをHTMLの `<img>` タグとして記事の末尾などに挿入します。
*   **はてなブログへの投稿**: `hatena_service.post_article()` を呼び出し、生成されたタイトルと最終的な記事コンテンツ（画像URL挿入済み）をはてなブログに投稿します。
*   **結果通知と記録**:
    *   投稿が成功すれば、その旨と記事URLを `line_service.send_message()` を使ってユーザーのLINEに通知します。
    *   投稿された記事のタイトル、内容、はてなブログURLなどを `Article` テーブルに保存します。この際、元となった `Message` レコードのID群も関連付けて記録されます。
    *   処理済みの `Message` レコードに `processed = True` のマークを付けます。
    *   エラーが発生した場合は、その旨をユーザーに通知します。

**エラーハンドリングとロギング**

*   `main.py` で設定された `logging` により、処理の各段階で情報、警告、エラーがログに出力されます。特に `webhook_enhanced.py` では詳細なログ出力が見られます。
*   Flaskの標準的なエラーハンドラ (`@app.errorhandler`) が `src/routes/__init__.py` で定義されており、404や500エラー発生時にはJSON形式でエラーメッセージを返します。
*   各処理関数内でも `try-except` ブロックによる個別エラーハンドリングが行われ、エラー発生時にはログ出力や、場合によってはユーザーへの通知が試みられます。

この一連の流れにより、「LINEでの手軽な入力 → Geminiによる高度なコンテンツ生成 → はてなブログへの自動投稿」という本システムのコア機能が実現されています。バッチ処理の導入により、連続的な入力に対応しつつ、APIの効率的な利用や、ある程度まとまった内容でのブログ投稿が意図されていると考えられます。

**6. LangGraphエージェントによる処理フロー (`src/routes/langgraph_routes.py`, `src/langgraph_agents/`)**

本システムは、`src/routes/webhook_enhanced.py` で実装されているバッチ処理型のLINEメッセージ処理フローに加え、より高度で状態管理に基づいたエージェント処理フローを `src/langgraph_agents/` ディレクトリと `src/routes/langgraph_routes.py` を通じて提供しています。このフローは、LangGraphライブラリを活用し、ブログ記事生成の一連のステップをグラフとして定義・実行するものです。

*   **エントリーポイント (`src/routes/langgraph_routes.py`)**:
    *   `@langgraph_bp.route('/webhook', methods=['POST'])` が、LINE PlatformからのWebhookリクエストを `/api/langgraph/webhook` エンドポイントで受け付けます。これは、前述の `/api/webhook/line` とは別のエンドポイントであり、LangGraphエージェント処理専用の入り口となります。
    *   署名検証後、`handle_webhook_async` 関数が非同期に呼び出され、受信したイベント（メッセージイベントなど）をパースします。
    *   メッセージイベントの場合、`process_message_event` 関数が呼び出され、メッセージタイプ（テキスト、画像、動画、音声）に応じて初期処理（メディアファイルのダウンロードなど）が行われます。
    *   その後、`process_line_message_async` 関数（実体は `src/langgraph_agents/agent.py` 内）を通じて、`BlogGenerationAgent` のメイン処理が開始されます。

*   **`BlogGenerationAgent` によるグラフ処理 (`src/langgraph_agents/agent.py`)**:
    *   `BlogGenerationAgent` は、ブログ生成の全プロセスを管理するステートフルなエージェントです。`_build_graph()` メソッドで処理の各ステップ（ノード）とそれらの遷移関係（エッジ）が定義されたLangGraphグラフを構築します。
    *   **状態管理 (`AgentState`)**: 処理の進行状況や各ステップで生成されたデータ（LINEメッセージ情報、Gemini分析結果、生成記事、エラー情報など）は `AgentState` オブジェクトに集約されて管理され、ノード間で引き継がれます。
    *   **主要ノードと処理概要 (`BlogGenerationNodes` クラス - `src/langgraph_agents/nodes.py`)**:
        1.  **`receive_line_message`**: 受信したLINEメッセージ情報（タイプ、内容、ファイルパスなど）を検証し、`AgentState` に初期設定します。
        2.  **`analyze_with_gemini`**: `AgentState` 内のメッセージに基づき、Gemini APIを呼び出して内容分析を行います。テキストの場合は記事の骨子やタグを生成し、画像の場合は画像内容の分析とそれに基づく記事ネタの提案を行います。結果は `AgentState` の `gemini_analysis` に保存されます。
        3.  **`generate_article`**: `gemini_analysis` の結果とユーザー設定（スタイルなど）を基に、再度Gemini APIを呼び出してブログ記事の本文を本格的に生成します。結果は `AgentState` の `gemini_analysis.content` などに格納されます。
        4.  **`upload_images_if_needed`**: メッセージが画像で、まだImgurにアップロードされていなければ、Imgur APIを呼び出して画像をアップロードし、そのURLを `AgentState` の `imgur_uploads` に記録します。記事本文にも画像URLが追記されることがあります。
        5.  **`publish_to_hatena`**: `AgentState` 内の生成済み記事タイトル、本文、タグなどを用いて、はてなブログAPIを呼び出し、記事を投稿（または下書き保存）します。投稿結果（URLなど）は `AgentState` の `hatena_post` に保存されます。
        6.  **`notify_user`**: 処理結果（成功時はブログURL、失敗時はエラー概要）をLINE API経由でユーザーに通知します。
        7.  **`handle_error`**: 各ノード処理後にエラーが検知された場合に呼び出されます。`AgentState` のリトライ回数に基づき、処理をリトライするか、諦めてエラーとして終了するかを決定します。エラー情報はユーザーにも通知されます。
    *   **グラフの実行**: `process_line_message_async` が呼び出されると、一意のセッションIDが生成され、初期状態がLangGraphに投入されます。グラフは定義されたノードとエッジに従って非同期に実行 (`graph.astream`) され、各ステップの完了ごとに状態が更新されます。最終的な処理結果（成功/失敗、ブログURL、エラー情報など）が返されます。

*   **既存バッチ処理フローとの関連**:
    *   `src/routes/webhook_enhanced.py` で定義されているバッチ処理フローと、このLangGraphエージェント処理フローは、現時点では異なるLINE Webhookエンドポイント（`/api/webhook/line` と `/api/langgraph/webhook`）を持つため、並行して存在し、用途に応じて使い分けられるか、あるいは一方が他方を将来的に置き換えることを想定して開発されている可能性があります。
    *   LangGraphエージェントは、より複雑な状態遷移や条件分岐、エラーハンドリング、リトライロジックを洗練された形で実装しており、個々のメッセージに対してよりインタラクティブで詳細なフィードバックを提供する能力を持っています。一方、バッチ処理フローは、複数のメッセージをまとめて処理することに特化しています。
    *   どちらのフローが主として利用されるか、またはどのように統合・連携されていくかは、システムの運用方針や今後の開発ロードマップに依存すると考えられます。

このLangGraphベースのアーキテクチャは、処理の各段階を明確に分離し、状態管理とエラーリカバリを強化することで、より堅牢で高度なAI連携アプリケーションの構築を可能にしています。
