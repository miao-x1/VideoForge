"""URL 输入处理器:抓取网页内容,提取纯文本。"""
from __future__ import annotations

import re

import httpx

from ..core.logging import logger
from .base import InputProcessor, InputSource, InputPayload, InputType

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()


class URLProcessor(InputProcessor):
    name = "url"

    async def process(self, source: InputSource) -> InputPayload:
        url = source.content
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "VideoForge/1.0"})
                resp.raise_for_status()
                text = _strip_html(resp.text)
                if len(text) > 2000:
                    text = text[:2000] + "..."
                return InputPayload(
                    type=InputType.URL,
                    raw_content=url,
                    processed_content=f"URL: {url}\n内容摘要: {text}",
                )
        except Exception as e:
            logger.warning("URL 抓取失败 %s: %s", url, e)
            return InputPayload(
                type=InputType.URL,
                raw_content=url,
                processed_content=f"[URL 抓取失败: {e}]",
            )
