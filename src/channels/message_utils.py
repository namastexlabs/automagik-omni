"""Utility functions for message processing across channels."""

import logging
import re
from typing import Any, Dict, List, Union


logger = logging.getLogger(__name__)


def extract_response_text(response: Union[str, Dict[str, Any]]) -> str:
    """
    Extract text content from various response formats.

    Args:
        response: Response data from message router or API

    Returns:
        Extracted text content
    """
    if isinstance(response, str):
        text: str = response
    elif isinstance(response, dict):
        # Check common response fields
        text = ""
        for field in ["message", "text", "content", "response"]:
            if field in response and response[field]:
                text = str(response[field])
                break

        # Check nested content
        if not text and "data" in response and isinstance(response["data"], dict):
            text = extract_response_text(response["data"])

        # If all else fails, convert to string
        if not text:
            text = str(response)
    else:
        # Fallback for other types
        text = str(response)

    # Fix concatenated intermediate messages from AgentOS
    # Pattern: "message[punct]Immediate uppercase" -> "message[punct]\n\nImmediate uppercase"
    # This happens when agent sends multiple tool calls with intermediate messages
    # Covers ALL punctuation: "Installing:Now" "Done.Another" "Restart!Success" "message)Next" etc.
    text = re.sub(r'([a-zà-ÿ])([\.,:;\!\?\)]+)\s*([A-ZÀ-Ÿ🎉🔧✅❌⚠️💀🚀])', r'\1\2\n\n\3', text)

    return text


def split_message_for_discord(text: str, max_length: int = 2000) -> List[str]:
    """
    Split a long message into Discord-compatible chunks.

    Discord has a 2000 character limit per message. This function intelligently
    splits messages on paragraph/sentence/word boundaries to maintain readability.

    Args:
        text: Message text to split
        max_length: Maximum length per chunk (default: 2000 for Discord)

    Returns:
        List of message chunks, each under max_length
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # First, try splitting on double newlines (paragraphs)
    paragraphs = text.split('\n\n')

    for para_idx, paragraph in enumerate(paragraphs):
        # If adding this paragraph would exceed limit, save current chunk
        test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph

        if len(test_chunk) > max_length:
            # Save current chunk if it exists
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # If paragraph itself is too long, split it further
            if len(paragraph) > max_length:
                # Try splitting on single newlines first
                lines = paragraph.split('\n')
                for line in lines:
                    test_chunk = current_chunk + ('\n' if current_chunk else '') + line

                    if len(test_chunk) > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""

                        # If line is still too long, split on sentences
                        if len(line) > max_length:
                            sentences = re.split(r'([.!?]+\s+)', line)
                            for i in range(0, len(sentences), 2):
                                sentence = sentences[i]
                                if i + 1 < len(sentences):
                                    sentence += sentences[i + 1]

                                test_chunk = current_chunk + sentence

                                if len(test_chunk) > max_length:
                                    if current_chunk:
                                        chunks.append(current_chunk.strip())

                                    # Last resort: split on words
                                    if len(sentence) > max_length:
                                        words = sentence.split(' ')
                                        temp_chunk = ""
                                        for word in words:
                                            if len(temp_chunk) + len(word) + 1 > max_length:
                                                if temp_chunk:
                                                    chunks.append(temp_chunk.strip())
                                                temp_chunk = word
                                            else:
                                                temp_chunk += (' ' if temp_chunk else '') + word
                                        current_chunk = temp_chunk
                                    else:
                                        current_chunk = sentence
                                else:
                                    current_chunk = test_chunk
                        else:
                            current_chunk = line
                    else:
                        current_chunk = test_chunk
            else:
                current_chunk = paragraph
        else:
            current_chunk = test_chunk

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    # Add continuation indicators
    if len(chunks) > 1:
        for i in range(len(chunks)):
            if i < len(chunks) - 1:
                chunks[i] = chunks[i] + f"\n\n_[{i+1}/{len(chunks)}]_"
            else:
                chunks[i] = chunks[i] + f"\n\n_[{i+1}/{len(chunks)} - Final]_"

    return chunks
