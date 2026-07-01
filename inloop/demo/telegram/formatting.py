"""Converts the agent's Markdown replies into Telegram's HTML formatting."""

import html

from markdown_it import MarkdownIt
from markdown_it.token import Token

_md = MarkdownIt("commonmark")


def to_telegram_html(text: str) -> str:
    """Render Markdown as the subset of HTML Telegram's sendMessage understands."""
    blocks, _ = _render_blocks(_md.parse(text), 0)
    return "\n\n".join(block for block in blocks if block)


def _render_blocks(tokens: list[Token], i: int) -> tuple[list[str], int]:
    blocks = []
    while i < len(tokens):
        token = tokens[i]
        if token.nesting == -1:
            return blocks, i + 1
        block, i = _render_block(tokens, i)
        blocks.append(block)
    return blocks, i


def _render_block(tokens: list[Token], i: int) -> tuple[str, int]:
    token = tokens[i]
    match token.type:
        case "heading_open":
            return f"<b>{_render_inline(tokens[i + 1])}</b>", i + 3
        case "paragraph_open":
            return _render_inline(tokens[i + 1]), i + 3
        case "fence" | "code_block":
            lang = token.info.strip().split()[0] if token.info.strip() else ""
            language_class = f' class="language-{html.escape(lang)}"' if lang else ""
            code = html.escape(token.content.rstrip("\n"))
            return f"<pre><code{language_class}>{code}</code></pre>", i + 1
        case "hr":
            return "──────────", i + 1
        case "blockquote_open":
            inner, i = _render_blocks(tokens, i + 1)
            return f"<blockquote>{'\n'.join(inner)}</blockquote>", i
        case "bullet_list_open" | "ordered_list_open":
            return _render_list(tokens, i + 1)
        case _:
            return "", i + 1


def _render_list(tokens: list[Token], i: int) -> tuple[str, int]:
    items = []
    while tokens[i].type == "list_item_open":
        marker = f"{tokens[i].info}." if tokens[i].info else "•"
        inner, i = _render_blocks(tokens, i + 1)
        items.append(f"{marker} {'\n'.join(inner)}")
    return "\n".join(items), i + 1


def _render_inline(token: Token) -> str:
    parts = []
    for child in token.children:
        match child.type:
            case "text":
                parts.append(html.escape(child.content))
            case "code_inline":
                parts.append(f"<code>{html.escape(child.content)}</code>")
            case "strong_open":
                parts.append("<b>")
            case "strong_close":
                parts.append("</b>")
            case "em_open":
                parts.append("<i>")
            case "em_close":
                parts.append("</i>")
            case "link_open":
                href = html.escape(child.attrGet("href") or "", quote=True)
                parts.append(f'<a href="{href}">')
            case "link_close":
                parts.append("</a>")
            case "softbreak" | "hardbreak":
                parts.append("\n")
            case "image":
                parts.append(html.escape(child.content))
            case _:
                parts.append(html.escape(child.content))
    return "".join(parts)
