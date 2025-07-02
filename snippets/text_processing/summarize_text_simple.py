def summarize_text_simple(text: str, length_threshold: int = 50, short_text_prefix: str = "短文: ", long_text_prefix: str = "長文: ", ellipsis: str = "...") -> str:
    """
    Creates a very simple summary of a given text.
    If the text is shorter than or equal to the length_threshold,
    it's prefixed with short_text_prefix.
    Otherwise, it's truncated to the length_threshold, prefixed with
    long_text_prefix, and an ellipsis is appended.

    Args:
        text (str): The input text to summarize.
        length_threshold (int, optional): The character length to differentiate
                                          between short and long text. Defaults to 50.
        short_text_prefix (str, optional): Prefix for texts considered short.
                                           Defaults to "短文: ".
        long_text_prefix (str, optional): Prefix for texts considered long and truncated.
                                          Defaults to "長文: ".
        ellipsis (str, optional): Suffix for truncated long texts.
                                  Defaults to "...".

    Returns:
        str: The simple summarized text.
    """
    if not isinstance(text, str):
        # Or raise TypeError("Input text must be a string")
        return f"{long_text_prefix}無効な入力{ellipsis}"

    if len(text) <= length_threshold:
        return f"{short_text_prefix}{text}"
    else:
        return f"{long_text_prefix}{text[:length_threshold]}{ellipsis}"

# Example Usage for testing
if __name__ == "__main__":
    test_cases = [
        ("This is a short text.", "短文: This is a short text."),
        ("This is a very long text that definitely exceeds the fifty character limit by a significant margin.", "長文: This is a very long text that definitely exceeds t..."),
        ("", "短文: "), # Empty string
        ("Exactly fifty characters long text exactly fifty ch", "短文: Exactly fifty characters long text exactly fifty ch"), # Exactly 50 chars
        ("Fifty one characters long text exactly fifty one char", "長文: Fifty one characters long text exactly fifty one c..."), # 51 chars
        (None, "長文: 無効な入力..."), # Non-string input
        (12345, "長文: 無効な入力..."), # Non-string input
    ]

    for i, (original, expected) in enumerate(test_cases):
        print(f"--- Test Case {i+1} ---")
        print(f"Original: '{original}'")
        summary = summarize_text_simple(original)
        print(f"Summary : '{summary}'")
        print(f"Expected: '{expected}'")
        assert summary == expected, f"Test Case {i+1} Failed!\nExpected: '{expected}'\nGot: '{summary}'"
        print(f"Test Case {i+1} Passed!")
        print("-----------------------\n")

    # Test with different threshold and prefixes
    print("--- Custom Parameters Test ---")
    custom_text = "This is a test for custom parameters."
    custom_summary = summarize_text_simple(
        custom_text,
        length_threshold=20,
        short_text_prefix="S: ",
        long_text_prefix="L: ",
        ellipsis=" END"
    )
    expected_custom = "L: This is a test for c END"
    print(f"Original: '{custom_text}'")
    print(f"Summary : '{custom_summary}'")
    print(f"Expected: '{expected_custom}'")
    assert custom_summary == expected_custom, "Custom Parameters Test Failed!"
    print("Custom Parameters Test Passed!")
    print("----------------------------\n")
