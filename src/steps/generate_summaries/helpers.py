from typing import cast

import openai
from loguru import logger

from src.configs.settings import Settings


def rough_token_count(text: str) -> int:
    """
    Estimate the number of tokens in the given text.

    This function uses a rough heuristic of approximately
    1 token per 0.75 words to estimate token count.

    Args:
        text: The input text string to estimate tokens for.

    Returns:
        An integer representing the estimated number of tokens.
    """

    return int(len(text.split()) / 0.75)  #  ≈1 token per 0.75 words


def split_into_chunks(text: str, max_tokens: int = 100_000) -> list[str]:
    """
    Split a large text into smaller chunks each within max token limit.

    This helps to ensure that each chunk can be processed within
    token limits of language models.

    Args:
        text: The input text to split into chunks.
        max_tokens: The maximum tokens allowed per chunk.

    Returns:
        A list of string chunks, each approximately within the max_tokens limit.
    """
    token_count = rough_token_count(text)
    if token_count <= max_tokens:
        return [text]

    words = text.split()
    chunk_len = int(len(words) * max_tokens / token_count)
    return [" ".join(words[i : i + chunk_len]) for i in range(0, len(words), chunk_len)]


def openai_chat(
    system_msg: str,
    user_msg: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1_500,
    temperature: float = 0.3,
) -> str | None:
    """
    Send a chat completion request to the OpenAI API with error handling.

    Args:
        system_msg: The system prompt to guide the model's behavior.
        user_msg: The user message content for the model to respond to.
        model: The OpenAI model name to use (default "gpt-4o-mini").
        max_tokens: Maximum tokens for the completion.
        temperature: Sampling temperature for response creativity.

    Returns:
        The content of the completion response as a string, or None on error.
    """
    client = openai.OpenAI(api_key=Settings().openai_api_key)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return cast(str, resp.choices[0].message.content)
    except Exception as err:
        logger.error(f"OpenAI error: {err}")
        return None


def summarize_content(content: str, team: str, prompt_template: str, max_tokens: int) -> str | None:
    """
    Summarize content about a team, handling large text by chunking.

    If content is small enough, it is summarized directly.
    For larger content, it is split into chunks, each summarized,
    and then the partial summaries are combined into a final summary.

    Args:
        content: The textual content to summarize.
        team: The name of the team for context in the prompt.
        prompt_template: A string template prompt for summarization with placeholders for team and content.
        max_tokens: The max tokens allowed for each summary completion.

    Returns:
        A string summary of the content, or None if summarization fails.
    """
    if not content.strip():
        logger.warning(f"No content to summarize for team {team}")
        return None

    chunks = split_into_chunks(content)
    if len(chunks) == 1:
        return openai_chat(
            system_msg="You are an expert sports journalist.",
            user_msg=prompt_template.format(team=team, content=chunks[0]),
            max_tokens=max_tokens,
        )

    # Multi-chunk: summarize each, then combine
    partials: list[str] = []
    for idx, chunk in enumerate(chunks, 1):
        logger.info(f"  ↳ Summarizing chunk {idx}/{len(chunks)} for {team}")
        summary = openai_chat(
            system_msg="You condense football Wikipedia sections.",
            user_msg=f"Summarize the following part about {team}:\n\n{chunk}",
            max_tokens=max_tokens,
        )
        if summary:
            partials.append(summary)

    combined = "\n\n".join(partials)
    return openai_chat(
        system_msg="You compile football summaries.",
        user_msg="Combine the following parts into a cohesive summary:\n\n" + combined,
        max_tokens=max_tokens,
    )
