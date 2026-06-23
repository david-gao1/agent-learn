def compact_messages(messages: list[str], keep_last: int = 3) -> list[str]:
    """Summarize older context while preserving recent working memory."""
    if keep_last < 1:
        raise ValueError("keep_last must be at least 1")
    if len(messages) <= keep_last:
        return messages

    older = messages[:-keep_last]
    recent = messages[-keep_last:]
    summary = "Summary of earlier context: " + " ".join(older)
    return [summary, *recent]
