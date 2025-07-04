## 要件定義：誰の、どんな課題を解決するためか

「mcp-ai-agent-system」（以下、本システム）が目指す「LINEの手軽さとGeminiの賢さを融合させ、はてなブログへの情報発信を劇的に効率化・高度化する」というコンセプトを実現するためには、具体的なターゲットユーザーとそのニーズを明確にし、それに応えるための機能要件を定義する必要があります。

**ターゲットユーザー**

本システムの主なターゲットユーザーとしては、以下のような層が想定されます。

1.  **ブロガー・コンテンツクリエイター**:
    *   定期的にブログを更新したいが、ネタ出し、構成作成、執筆、推敲といった一連の作業に多くの時間を費やしている。
    *   複数のプラットフォームやツールを使い分ける手間を減らし、より執筆活動そのものに集中したい。
    *   AIの力を借りて、記事の品質向上や表現の多様化を図りたい。

2.  **情報発信に関心のある一般ユーザー**:
    *   日々の気づきや専門知識、趣味に関する情報を発信したいという思いはあるものの、ブログ作成の技術的なハードルや手間を感じて躊躇している。
    *   LINEのような日常的に使うツールから、もっと気軽に情報発信を始めたい。

3.  **技術ブロガー・開発者**:
    *   技術的な知見やTipsを記録・共有したいが、ドキュメント作成やブログ執筆の時間を十分に確保できない。
    *   コードスニペットやアイデアの断片をLINEでメモし、それを元にAIが記事の骨子を生成してくれるような支援を求めている。

**ユーザーが抱える課題（ペイン）**

これらのターゲットユーザーは、情報発信において以下のような共通の課題を抱えていると考えられます。

*   **時間的制約**: コンテンツ作成には多くの時間がかかり、他の業務や活動との両立が難しい。
*   **アイデアの枯渇・具体化の困難**: 発信したいネタが思いつかない、あるいは思いついてもそれを魅力的な記事に具体化するスキルや労力が不足している。
*   **作業の煩雑さ**: メモ、下書き、AIツールでの処理、ブログプラットフォームへの投稿といった作業が分断されており、ツール間の行き来やコピー＆ペーストが煩わしい。
*   **継続の難しさ**: 上記の課題により、情報発信を継続するモチベーションを維持するのが難しい。

**本システムが提供すべき主要機能（機能要件）**

これらの課題を解決し、ターゲットユーザーのニーズを満たすために、本システムには以下の主要な機能が求められます。

1.  **LINEからの入力受付機能**:
    *   ユーザーがLINEのメッセージとして送信したテキストや画像（将来的には音声なども考慮）を、本システムが確実に受信できること。
    *   特定のコマンドやキーワードによって、処理の種類（例：ブログ記事化、アイデアメモ、下書き依頼など）を指定できること。
    *   ユーザー認証やアカウント連携により、どのユーザーからの入力かを識別できること。

2.  **Geminiによるコンテンツ処理機能**:
    *   受け付けた入力内容（テキスト、画像等）を、指定された処理の種類に応じてGemini APIに連携し、適切なプロンプトで処理を実行できること。
    *   処理の種類としては、以下のようなものが考えられる：
        *   **記事生成**: 入力されたテーマやキーワード、メモに基づいて、ブログ記事のタイトル、導入文、本文、まとめなどを生成する。
        *   **文章リライト・校正**: 既存の文章をより洗練された表現に書き換えたり、誤字脱字を修正したりする。
        *   **アイデア拡張**: 断片的なアイデアから、関連情報や深掘りすべき点を提示する。
        *   **画像キャプション生成**: 画像の内容を説明するキャプションを生成する。
    *   Geminiの処理結果（生成されたテキスト、構造化されたデータなど）を適切に受け取り、後続の処理に渡せること。

3.  **はてなブログへの出力機能**:
    *   Geminiによって処理・生成されたコンテンツを、はてなブログのAPI等を利用して、指定されたユーザーのアカウントに記事として投稿（下書きまたは公開）できること。
    *   記事のタイトル、本文、カテゴリ、タグなどを適切に設定できること。
    *   投稿処理の成功・失敗をユーザーにフィードバックできること。

4.  **ユーザーインタラクション・フィードバック機能**:
    *   処理の開始、中間報告（必要な場合）、完了、エラー発生などをLINEを通じてユーザーに通知できること。
    *   ユーザーが処理の状況を確認したり、簡単な指示（例：投稿の承認、修正依頼）を出したりできること。

5.  **設定・管理機能（限定的でも可）**:
    *   ユーザーがLINEアカウントとはてなブログアカウントを紐付けるための基本的な設定ができること。
    *   （将来的には）Geminiの利用に関する設定（例：出力のトーン、長さなど）を調整できること。

これらの機能要件は、本システムがユーザーにとって真に価値のある「手軽で賢い情報発信基盤」となるための基礎となります。開発においては、まずコアとなるLINE-Gemini-はてなの連携フローを確立し、段階的に周辺機能や利便性を向上させていくアプローチが考えられます。
