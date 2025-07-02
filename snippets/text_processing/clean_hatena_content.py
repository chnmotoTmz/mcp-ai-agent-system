import re

def clean_hatena_content(title: str, content: str) -> str:
    """
    Removes duplicate titles from the beginning of Hatena blog content.
    This function is designed to clean up content before posting, especially
    if the title might be automatically prepended to the content body by
    some generation tools.

    Args:
        title (str): The title of the blog post.
        content (str): The raw content of the blog post.

    Returns:
        str: Content with the leading title removed, if found.
             Otherwise, returns the original content, stripped of leading/trailing whitespace.
    """
    cleaned_content = content.strip()

    # If title is empty, nothing to clean based on title
    if not title:
        return cleaned_content

    # Normalize the title: strip, replace multiple spaces with one
    normalized_title = re.sub(r'\s+', ' ', title.strip())
    # Escape the title for use in regex (handles special characters in title)
    escaped_title = re.escape(normalized_title)

    # --- Patterns to remove ---

    # 1. HTML-style titles: <h1>Title</h1>, <p><strong>Title</strong></p>, etc.
    #    More comprehensive to handle attributes and potential spaces.
    html_patterns = [
        # Header tags (h1-h6)
        f"<h[1-6][^>]*>\\s*{escaped_title}\\s*</h[1-6]>",
        # Strong/bold/em/italic tags (alone)
        f"<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>",
        # Paragraph containing only a strong/bold/em/italic title
        f"<p[^>]*>\\s*<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>\\s*</p>",
        # Div tags containing only the title
        f"<div[^>]*>\\s*{escaped_title}\\s*</div>",
        # Actual <title> HTML tag (less common in blog content body but possible)
        f"<title[^>]*>\\s*{escaped_title}\\s*</title>",
        # Paragraph containing only the title
        f"<p[^>]*>\\s*{escaped_title}\\s*</p>",
    ]

    for pattern in html_patterns:
        # Using re.IGNORECASE and re.DOTALL to make matching more robust
        # Store original length to see if a change was made by re.sub
        # Check how many times pattern is found
        found_occurrences = len(re.findall(pattern, cleaned_content, flags=re.IGNORECASE | re.DOTALL))
        if found_occurrences > 0:
            cleaned_content = re.sub(pattern, '', cleaned_content, count=found_occurrences, flags=re.IGNORECASE | re.DOTALL)
            # If a <p> tag pattern was removed, it might leave empty <p></p> tags. Clean them.
            if 'p[^>]*' in pattern: # Heuristic: if pattern involved <p>
                 cleaned_content = re.sub(r'<p[^>]*>\s*</p>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)


    # Clean up potentially empty HTML tags that might be left after substitution
    cleaned_content = re.sub(r'<p[^>]*>\s*</p>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
    cleaned_content = re.sub(r'<div[^>]*>\s*</div>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)


    # 2. Bracketed titles: 【Title】, 「Title」, etc., at the very beginning of a line or the content.
    bracket_patterns = [
        f"【\\s*{escaped_title}\\s*】",
        f"「\\s*{escaped_title}\\s*」",
        f"『\\s*{escaped_title}\\s*』",
        f"\\[\\s*{escaped_title}\\s*\\]", # Square brackets
        f"\\(\\s*{escaped_title}\\s*\\)", # Parentheses
    ]
    for pattern in bracket_patterns:
        # If the pattern is at the very start of the content string
        cleaned_content = re.sub(f"^\\s*{pattern}\\s*", '', cleaned_content, count=1, flags=re.DOTALL)
        # If the pattern is at the start of any line (after cleaning previous matches)
        cleaned_content = re.sub(f"^\\s*{pattern}\\s*$", '', cleaned_content, flags=re.MULTILINE)


    # 3. Plain text title at the beginning of lines or the content.
    #    Split content into lines to handle titles that might be on their own line.
    lines = cleaned_content.split('\n')
    new_lines = []
    title_removed_from_start = False

    for i, line in enumerate(lines):
        stripped_line = line.strip()
        # Check if the line exactly matches the normalized title
        if stripped_line == normalized_title:
            if i == 0: # Only remove if it's the first line or part of a multi-line title start
                title_removed_from_start = True
            continue # Skip this line
        # Check if the line starts with the title followed by common punctuation
        if re.match(f"^{escaped_title}[。、.,：:!?！？]?\\s*$", stripped_line, flags=re.IGNORECASE):
            if i == 0:
                title_removed_from_start = True
            continue
        new_lines.append(line)
    cleaned_content = '\n'.join(new_lines)


    # 4. Title at the very beginning of the (potentially modified) content string,
    #    possibly followed by punctuation and/or newlines.
    #    This is a more aggressive check for the start of the entire content.
    cleaned_content = re.sub(f"^\\s*{escaped_title}\\s*[。、.,：:!?！？]?\\s*\\n?", '', cleaned_content, count=1, flags=re.DOTALL | re.IGNORECASE)


    # 5. Markdown-style titles: # Title, ## Title, or Title\n====
    markdown_patterns = [
        f"^#+\\s+{escaped_title}\\s*$",       # e.g., # Title
        f"^{escaped_title}\\s*\\n[=-]+\\s*$", # e.g., Title \n === or Title \n ---
    ]
    for pattern in markdown_patterns:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE | re.IGNORECASE)


    # 6. Handle titles that might themselves contain newlines (less common but possible).
    if '\n' in normalized_title:
        # This is tricky; for simplicity, if the title has newlines, we'll try to match
        # the first line of the title at the beginning of the content.
        first_line_of_title = re.escape(normalized_title.split('\n')[0].strip())
        cleaned_content = re.sub(f"^\\s*{first_line_of_title}\\s*\\n?", '', cleaned_content, count=1, flags=re.IGNORECASE)


    # Final cleanup: strip leading/trailing whitespace and reduce multiple newlines.
    cleaned_content = cleaned_content.strip()
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content) # Reduce 3+ newlines to 2

    # One last check: if the very first line of the remaining content IS the title, remove it.
    # This can happen if previous removals were partial or left newlines.
    lines = cleaned_content.split('\n')
    if lines and lines[0].strip() == normalized_title:
        lines.pop(0)
        cleaned_content = '\n'.join(lines).strip()

    return cleaned_content

# Example Usage for testing
if __name__ == "__main__":
    test_cases = [
        ("Simple Title", "Simple Title\nThis is the content.", "This is the content."),
        ("HTML Title H1", "<h1>HTML Title H1</h1><p>Content starts here.</p>", "<p>Content starts here.</p>"),
        ("HTML Title P Strong", "<p><strong>HTML Title P Strong</strong></p>Content here.", "Content here."),
        ("Bracket Title", "【Bracket Title】\nActual content.", "Actual content."),
        ("Markdown Title", "# Markdown Title\nContent body.", "Content body."),
        ("Title with Punctuation", "Title with Punctuation.\nContent.", "Content."),
        ("No Title in Content", "Just Content", "This is just the content without the title.", "This is just the content without the title."),
        ("Empty Content", "Empty Content Title", "", ""),
        ("Empty Title", "", "Some content here.", "Some content here."),
        ("Title with Spaces", "  Title with Spaces  ", "  Title with Spaces  \nContent.", "Content."),
        ("Multi-line Title", "Line1\nLine2", "Line1\nLine2\nThe actual content.", "The actual content."),
        ("Complex HTML", "<div class='title'><h2>  Complex HTML  </h2></div><p>  Complex HTML  </p>The story begins.", "The story begins."),
        ("Title in Brackets Mid-Sentence", "A Title", "This is [A Title] not at the start.", "This is [A Title] not at the start."),
        ("Title with special regex characters", "Title with (Parentheses) and [Brackets]", "Title with (Parentheses) and [Brackets]\nContent body.", "Content body."),
        ("Title at very start, no newline", "Title At Start", "Title At StartContent without newline.", "Content without newline."),
        ("Title with leading/trailing spaces in definition", " Spaced Title ", " Spaced Title \nAnd content", "And content"),
        ("HTML title with attributes", "<h1 class=\"foo\">Attr Title</h1>Content", "Content"),
        ("Plain text title with multiple spaces", "Plain  Text   Title", "Plain  Text   Title\nContent", "Content"),
        ("<p>タグ内の<strong>タグ", "<p><strong>タグ内の<strong>タグ</strong></p>本文です。", "本文です。"),
        ("タグとテキストの組み合わせタイトル", "<strong>タグとテキストの組み合わせタイトル</strong> 通常テキスト", "<strong>タグとテキストの組み合わせタイトル</strong> 通常テキスト\nこれが本文", "これが本文"),
        ("タイトル重複なし", "ユニークなタイトル", "これは本文で、タイトルは含まれていません。", "これは本文で、タイトルは含まれていません。"),
        ("HTMLタイトルと本文の間にスペース", "<h1>HTMLスペースタイトル</h1>   <p>本文</p>", "<p>本文</p>"),
        ("Markdownアンダーライン形式", "Markdownアンダーライン\n----\n本文です。", "本文です。")
    ]

    for i, (title, content, expected) in enumerate(test_cases):
        print(f"--- Test Case {i+1} ---")
        print(f"Title: '{title}'")
        print(f"Original Content:\n'''\n{content}\n'''")
        cleaned = clean_hatena_content(title, content)
        print(f"Cleaned Content:\n'''\n{cleaned}\n'''")
        print(f"Expected Content:\n'''\n{expected}\n'''")
        assert cleaned == expected, f"Test Case {i+1} Failed!\nExpected:\n{expected}\nGot:\n{cleaned}"
        print(f"Test Case {i+1} Passed!")
        print("-----------------------\n")
