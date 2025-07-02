import logging
import os
from typing import Optional, Dict, Any

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
except ImportError:
    genai = None # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_PROMPT_TEMPLATE = """
以下の記事の簡潔な要約を作成してください。

記事全文：
```text
{full_content_text}
```

要約の要求事項：
- {target_sentences_or_lines}程度の長さで、記事の最も重要なポイントを捉えてください。
- 読者が記事全体を読むかどうかを判断するのに役立つような、興味を引く表現を心がけてください。
- 要約は、記事の主要なトピックや結論を明確に示してください。
- 出力は要約文のみとしてください。余計な前置きや定型句（「この要約は～」など）は不要です。
"""

def generate_content_summary_gemini(
    full_content_text: str,
    target_sentences_or_lines: str = "3～4文", # Descriptive target length for the prompt
    model_name: str = "gemini-1.5-flash", # Models good at summarization
    api_key: Optional[str] = None,
    prompt_template: str = DEFAULT_SUMMARY_PROMPT_TEMPLATE,
    generation_config: Optional[Dict[str, Any]] = None,
    safety_settings: Optional[Dict[str, Any]] = None,
    configured_model = None
) -> Optional[str]:
    """
    Generates a concise summary of the given text content using the Gemini API.

    Args:
        full_content_text (str): The full text content to be summarized.
        target_sentences_or_lines (str, optional): A descriptive target length for the summary
            (e.g., "2-3 sentences", "about 50 words", "3 key bullet points"). This is
            used directly in the prompt. Defaults to "3～4文".
        model_name, api_key, prompt_template, generation_config, safety_settings, configured_model:
            Standard Gemini configuration arguments.

    Returns:
        Optional[str]: The generated summary text if successful, None otherwise.
    """
    if not full_content_text.strip():
        logger.warning("Content for summary is empty or whitespace only.")
        return "" # Return empty string for empty input

    if configured_model:
        model = configured_model
    elif genai:
        if api_key:
            genai.configure(api_key=api_key)
        elif not os.getenv('GOOGLE_API_KEY') and not genai.API_KEY:
             logger.error("Gemini API key not provided and genai not configured for summary.")
             return None
        model = genai.GenerativeModel(model_name)
    else:
        logger.error("Gemini SDK not available and no configured_model provided for summary.")
        return None

    prompt = prompt_template.format(
        full_content_text=full_content_text,
        target_sentences_or_lines=target_sentences_or_lines
    )

    try:
        logger.info(f"Attempting Gemini API call for content summary (Model: {model_name})")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.text and response.text.strip():
            logger.info("Content summary generation successful.")
            return response.text.strip()
        else:
            logger.warning("Gemini API response for content summary was empty.")
            return None

    except Exception as e:
        logger.error(f"Gemini API error during content summary generation: {e}", exc_info=True)
        return None

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_api_key = os.getenv("GOOGLE_API_KEY")

    if not genai or (not configured_model and not test_api_key and (genai and not genai.API_KEY)): # type: ignore
        print("Skipping summary generation test: Gemini SDK not available or API key not configured.")
    else:
        sample_long_article = """
        人工知能（AI）は、近年目覚ましい発展を遂げ、私たちの日常生活やビジネスのあり方を根本から変えつつあります。
        特に、大規模言語モデル（LLM）の登場は、自然言語処理技術の新たな地平を切り開きました。
        LLMは、人間が書いたかのような自然な文章を生成したり、複雑な質問に的確に答えたり、さらにはプログラムコードを記述したりするなど、
        従来では考えられなかった高度なタスクをこなすことができます。これにより、チャットボット、コンテンツ作成支援、翻訳、
        要約、情報検索など、多岐にわたる分野での応用が進んでいます。

        しかし、AI技術の急速な進化は、倫理的な課題や社会的な影響も伴います。
        例えば、フェイクニュースの生成、著作権の問題、雇用への影響、AIによる意思決定の透明性や公平性など、
        慎重な検討と対策が求められる課題が山積しています。これらの課題に対応するためには、技術開発者、政策立案者、
        そして社会全体での議論と協力が不可欠です。AIの恩恵を最大限に享受しつつ、
        そのリスクを適切に管理していくためのルール作りやガイドラインの整備が急がれています。
        AIと人間が共存し、より良い未来を築くためには、技術的な進歩だけでなく、
        倫理観や社会的責任に基づいた開発と利用が求められているのです。
        """

        print("\n--- Test Case 1: Generate summary with default target length ---")
        summary1 = generate_content_summary_gemini(sample_long_article, api_key=test_api_key)
        if summary1:
            print("Generated Summary (Default Target):")
            print(summary1)
        else:
            print("Failed to generate summary (Test 1).")

        print("\n--- Test Case 2: Generate summary with a custom target length description ---")
        summary2 = generate_content_summary_gemini(
            sample_long_article,
            target_sentences_or_lines="1～2文の非常に短い要点",
            api_key=test_api_key
        )
        if summary2:
            print("\nGenerated Summary (Custom Target '1～2文'):")
            print(summary2)
        else:
            print("Failed to generate summary with custom target (Test 2).")

        print("\n--- Test Case 3: Summarize very short content ---")
        short_content = "猫が窓辺で日向ぼっこをしている。とても平和だ。"
        summary3 = generate_content_summary_gemini(short_content, api_key=test_api_key)
        if summary3:
            print("\nGenerated Summary (Short Content):")
            print(summary3)
            # For very short content, the summary might be very similar or slightly rephrased
        else:
            print("Failed to generate summary for short content (Test 3).")

        print("\n--- Test Case 4: Summarize empty content ---")
        summary4 = generate_content_summary_gemini("", api_key=test_api_key)
        print(f"\nGenerated Summary (Empty Content): '{summary4}'")
        assert summary4 == "" # Expecting empty string for empty input

    print("\nNote: Live API calls to Gemini cost money and depend on network.")
    print("The quality of the summary depends on the prompt and the model's capabilities.")
