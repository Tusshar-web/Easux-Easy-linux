"""
Token classifier and shell buffer parser.
Follows the token classification priority specified in the PRD.
"""

import os
from pathlib import Path
from typing import List, Optional
from ai_terminal.models import TokenType, ParsedBuffer


KNOWN_COMMANDS = {"git", "npm", "pip", "pip3", "docker", "make", "cargo", "go", "kubectl"}


def parse_shell_buffer(buffer: str, cursor: Optional[int] = None) -> ParsedBuffer:
    """
    Parses a shell command buffer up to the cursor position and classifies the active token.
    Token classification order:
    1. Quoted or escaped token
    2. Path-like token
    3. First command token
    4. Known-command subcommand
    5. Option
    6. Positional argument
    """
    if cursor is None or cursor > len(buffer):
        cursor = len(buffer)
    active_text = buffer[:cursor]

    # Tokenize while keeping track of quoting
    tokens: List[str] = []
    in_single = False
    in_double = False
    escaped = False
    current_token: List[str] = []

    for char in active_text:
        if escaped:
            current_token.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            current_token.append(char)
            continue

        if char == "'" and not in_double:
            in_single = not in_single
            current_token.append(char)
            continue

        if char == '"' and not in_single:
            in_double = not in_double
            current_token.append(char)
            continue

        if char.isspace() and not in_single and not in_double:
            if current_token:
                tokens.append("".join(current_token))
                current_token = []
        else:
            current_token.append(char)

    trailing_space = (len(active_text) > 0 and active_text[-1].isspace() and not in_single and not in_double)

    if current_token:
        tokens.append("".join(current_token))
        active_token = tokens[-1]
        active_index = len(tokens) - 1
    elif trailing_space:
        # Buffer ends in a space, so active token is empty (user is starting a new token)
        active_token = ""
        active_index = len(tokens)
    else:
        active_token = ""
        active_index = 0

    command_name = tokens[0] if len(tokens) > 0 else None
    subcommand = tokens[1] if len(tokens) > 1 and not tokens[1].startswith("-") else None

    # Classify token
    token_type = _classify_token(
        token=active_token,
        token_index=active_index,
        command_name=command_name,
        is_quoted=(in_single or in_double or escaped),
    )

    return ParsedBuffer(
        raw_buffer=buffer,
        cursor_pos=cursor,
        tokens=tokens,
        active_token_index=active_index,
        active_token=active_token,
        token_type=token_type,
        prefix=active_token,
        command_name=command_name,
        subcommand=subcommand,
    )


def _classify_token(
    token: str,
    token_index: int,
    command_name: Optional[str],
    is_quoted: bool
) -> TokenType:
    # 1. Quoted or escaped token
    if is_quoted or token.startswith(('"', "'")) or "\\" in token:
        return TokenType.QUOTED_OR_ESCAPED

    # 2. Path-like token
    if token.startswith(("./", "../", "/", "~")) or "/" in token:
        return TokenType.PATH_LIKE

    # 3. First command token
    if token_index == 0:
        return TokenType.FIRST_COMMAND

    # 4. Known-command subcommand (token_index == 1 for commands like git, npm, pip, docker, make)
    if token_index == 1 and command_name in KNOWN_COMMANDS and not token.startswith("-"):
        return TokenType.KNOWN_SUBCOMMAND

    # 5. Option (starts with - or --)
    if token.startswith("-"):
        return TokenType.OPTION

    # 6. Positional argument
    return TokenType.POSITIONAL
