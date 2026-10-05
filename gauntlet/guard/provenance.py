"""Provenance tags: every payment parameter records where its value came from."""
from __future__ import annotations

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Source(str, Enum):
    USER = "user"            # typed by the delegating user / in the signed mandate
    TRUSTED = "trusted"      # our own systems: allowlist, payee history, config
    UNTRUSTED = "untrusted"  # web pages, invoices, vendor messages, tool outputs


class Tagged(BaseModel, Generic[T]):
    value: T
    source: Source
    origin: str = ""  # e.g. "invoice:INV2-XXXX" or "page:https://..."

    @property
    def untrusted(self) -> bool:
        return self.source == Source.UNTRUSTED
