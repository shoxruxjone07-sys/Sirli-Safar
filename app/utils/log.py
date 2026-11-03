"""Jurnal sozlamalari: maxfiy qiymatlar (token, baza paroli) jurnalga tushmaydi."""
from __future__ import annotations

import logging
import re


class RedactFilter(logging.Filter):
    def __init__(self, secrets: list[str]):
        super().__init__()
        self.secrets = [s for s in secrets if s and len(s) >= 6]

    def _clean(self, text: str) -> str:
        for s in self.secrets:
            text = text.replace(s, "***")
        return re.sub(r"(postgres(?:ql)?://[^:/\s]+:)[^@\s]+@", r"\1***@", text)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        record.msg = self._clean(msg)
        record.args = ()
        if record.exc_info and record.exc_info[1] is not None:
            record.exc_text = self._clean(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def setup_logging(level: str, secrets: list[str]) -> None:
    logging.basicConfig(level=getattr(logging, level, logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    flt = RedactFilter(secrets)
    for handler in logging.getLogger().handlers:
        handler.addFilter(flt)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
