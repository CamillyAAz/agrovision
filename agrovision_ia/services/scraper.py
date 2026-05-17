import time
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Dict

import requests

from .config import (
    SCRAPER_COOLDOWN_SECONDS,
    SCRAPER_TARGET_URL,
    SCRAPER_TIMEOUT,
    SCRAPER_USER_AGENT,
)


class WikipediaSummaryParser(HTMLParser):
    """Extract readable paragraphs from the main Wikipedia article body."""

    def __init__(self):
        super().__init__()
        self._in_main_content = False
        self._main_depth = 0
        self._in_paragraph = False
        self._skip_depth = 0
        self._current_text = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "div" and attrs_dict.get("class") == "mw-parser-output":
            self._in_main_content = True
            self._main_depth = 1
            return

        if self._in_main_content and tag == "div":
            self._main_depth += 1

        if not self._in_main_content:
            return

        if tag in {"sup", "table", "style", "script"}:
            self._skip_depth += 1

        if tag == "p" and self._skip_depth == 0:
            self._in_paragraph = True
            self._current_text = []

    def handle_endtag(self, tag):
        if not self._in_main_content:
            return

        if tag == "p" and self._in_paragraph:
            text = " ".join("".join(self._current_text).split())
            if text:
                self.paragraphs.append(text)
            self._in_paragraph = False
            self._current_text = []

        if tag in {"sup", "table", "style", "script"} and self._skip_depth > 0:
            self._skip_depth -= 1

        if tag == "div":
            self._main_depth -= 1
            if self._main_depth <= 0:
                self._in_main_content = False

    def handle_data(self, data):
        if self._in_main_content and self._in_paragraph and self._skip_depth == 0:
            self._current_text.append(data)


class AgriculturalScraper:
    """Fetch structured agricultural context from a public data source.

    The scraping layer enriches AgroVision events with public agricultural
    context. It is intentionally isolated from routes, templates and YOLO
    logic, and it uses cache/cooldown controls to avoid excessive requests.
    """

    def __init__(self):
        self._last_request_time = 0.0
        self._cache: Dict[str, Any] = {}

    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _extract_summary(self, html_text: str) -> str:
        parser = WikipediaSummaryParser()
        parser.feed(html_text)

        for paragraph in parser.paragraphs:
            if len(paragraph) > 80:
                return paragraph

        return "Nao foi possivel extrair um resumo legivel da pagina de referencia."

    def _build_response(self, status: str, insight: str, message: str = "") -> Dict[str, Any]:
        return {
            "source": SCRAPER_TARGET_URL,
            "topic": "Soja",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "insight": insight,
            "message": message,
            "request_limit": {
                "cooldown_seconds": SCRAPER_COOLDOWN_SECONDS,
                "uses_cache": status == "cached",
            },
        }

    def _should_use_cache(self) -> bool:
        return bool(
            self._cache
            and time.time() - self._last_request_time < SCRAPER_COOLDOWN_SECONDS
        )

    def get_latest_insight(self) -> Dict[str, Any]:
        if self._should_use_cache():
            cached = dict(self._cache)
            cached["status"] = "cached"
            cached["request_limit"] = {
                "cooldown_seconds": SCRAPER_COOLDOWN_SECONDS,
                "uses_cache": True,
            }
            return cached

        try:
            response = requests.get(
                SCRAPER_TARGET_URL,
                headers=self._headers(),
                timeout=SCRAPER_TIMEOUT,
            )
            response.raise_for_status()
            summary = self._extract_summary(response.text)
            result = self._build_response("ok", summary)
        except requests.RequestException as exc:
            print(f"Scraper request failed: {exc}")
            result = self._build_response(
                "error",
                "Dados nao disponiveis no momento.",
                message="A fonte publica nao respondeu dentro do esperado.",
            )
        except Exception as exc:
            print(f"Scraper processing failed: {exc}")
            result = self._build_response(
                "error",
                "Falha ao processar os dados de scraping.",
                message="Nao foi possivel organizar os dados coletados.",
            )

        self._cache = result
        self._last_request_time = time.time()
        return result


agricultural_scraper = AgriculturalScraper()
