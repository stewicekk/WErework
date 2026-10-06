"""Line-preserving reader/writer for Metin2 script-text files.

Covers the ``Setting.txt`` / ``MapProperty.txt`` / ``AreaProperty.txt`` /
``AreaData.txt`` / environment family: line-oriented ``key + values``
records with ``//`` comments, blank lines and (for area files) indented
positional lines.

Design rules (see docs/audit/FORMATS.md, AUDIT_CONSOLIDATED.md):

* Unknown lines are preserved **byte-identical** — never dropped,
  never re-encoded; their relative order is kept (serializers re-emit
  them after the canonical block, which is documented per writer).
* Line endings are preserved per line; the document default is detected
  from the source. Files created from scratch default to ``CRLF``,
  matching the legacy ``fopen(..., "w")`` output on Windows.
* Decoding is UTF-8 strict. undecodable bytes raise :class:`ParseError`
  with file + line instead of producing mojibake.
* Key lookup is case-sensitive exact match. Legacy loader case-folding
  lives in the absent GameLib sources (UNVERIFIED), so no folding is
  assumed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import ParseError

CRLF = b"\r\n"
LF = b"\n"

_TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\S+')
_WS_RE = re.compile(r"\s*")


def detect_newline(data: bytes) -> bytes:
    """Dominant newline of *data*; ``CRLF`` for empty/new content."""
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    if crlf == 0 and lf == 0:
        return CRLF
    return CRLF if crlf >= lf else LF


def _split_lines(data: bytes) -> list[tuple[bytes, bytes]]:
    """Split into ``(content, ending)`` pairs keeping endings."""
    out: list[tuple[bytes, bytes]] = []
    for raw in data.splitlines(keepends=True):
        if raw.endswith(b"\r\n"):
            out.append((raw[:-2], CRLF))
        elif raw.endswith(b"\n") or raw.endswith(b"\r"):
            out.append((raw[:-1], LF))
        else:
            out.append((raw, b""))
    return out


def tokenize(text: str) -> list[str]:
    """Quote-aware token split; quotes are kept (``"a b"` stays quoted).

    Use :meth:`ScriptLine.values` for the unquoted view.
    """
    return _TOKEN_RE.findall(text)


def token_spans(text: str) -> list[tuple[int, int, str]]:
    """``(start, end, token)`` spans for quote-aware tokenizing."""
    return [(m.start(), m.end(), m.group(0)) for m in _TOKEN_RE.finditer(text)]


def _strip_quotes(token: str) -> str:
    if len(token) >= 2 and token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    return token


@dataclass
class ScriptLine:
    """One source line: raw bytes + decoded text + token view."""

    raw: bytes
    ending: bytes
    text: str
    number: int = 0

    @property
    def is_blank(self) -> bool:
        return self.text.strip() == ""

    @property
    def is_comment(self) -> bool:
        return self.text.lstrip().startswith("//")

    @property
    def indent(self) -> str:
        m = _WS_RE.match(self.text)
        return m.group(0) if m else ""

    @property
    def is_indented(self) -> bool:
        return not self.is_blank and not self.is_comment and len(self.indent) > 0

    @property
    def kind(self) -> str:
        if self.is_blank:
            return "blank"
        if self.is_comment:
            return "comment"
        if self.is_indented:
            return "indented"
        return "kv"

    @property
    def tokens(self) -> list[str]:
        if self.kind == "blank":
            return []
        return tokenize(self.text.strip())

    @property
    def key(self) -> str | None:
        toks = self.tokens
        if self.kind == "comment" or not toks:
            return None
        return _strip_quotes(toks[0])

    @property
    def values(self) -> list[str]:
        toks = self.tokens
        if self.kind == "comment" or len(toks) < 2:
            return []
        return [_strip_quotes(t) for t in toks[1:]]

    def with_values(self, new_values: list[str]) -> "ScriptLine":
        """Return a copy with value tokens replaced.

        The line head (indentation + key + original gap up to the first
        value) is preserved; the replacement values are joined with a
        single space. Used for in-place edits of files whose exact
        column layout is owned by legacy (e.g. environment scripts).
        """
        spans = token_spans(self.text.strip())
        if not spans:
            raise ValueError("cannot set values on a blank/comment line")
        head_end_in_stripped = spans[0][1]
        leading = self.text[: len(self.text) - len(self.text.lstrip())]
        head = leading + self.text.lstrip()[:head_end_in_stripped]
        new_text = head + (" " + " ".join(new_values) if new_values else "")
        return ScriptLine(
            raw=new_text.encode("utf-8"), ending=self.ending, text=new_text, number=self.number
        )


@dataclass
class ScriptDocument:
    """An ordered, line-preserving view of a script-text file."""

    lines: list[ScriptLine] = field(default_factory=list)
    newline: bytes = CRLF
    source: str = "<memory>"

    # -- loading ------------------------------------------------------
    @classmethod
    def from_bytes(cls, data: bytes, source: str = "<memory>") -> "ScriptDocument":
        doc = cls(newline=detect_newline(data), source=source)
        for i, (content, ending) in enumerate(_split_lines(data), start=1):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ParseError(source, f"line is not valid UTF-8: {exc}", i) from exc
            doc.lines.append(ScriptLine(raw=content, ending=ending, text=text, number=i))
        return doc

    @classmethod
    def from_text(cls, text: str, source: str = "<memory>") -> "ScriptDocument":
        return cls.from_bytes(text.encode("utf-8"), source)

    @classmethod
    def load(cls, path: str) -> "ScriptDocument":
        with open(path, "rb") as fh:
            return cls.from_bytes(fh.read(), source=path)

    # -- key access (column-0 records only) ----------------------------
    def _kv_lines(self, include_indented: bool = False):
        for line in self.lines:
            if line.kind == "kv" or (include_indented and line.kind == "indented"):
                yield line

    def get_first(self, key: str, include_indented: bool = False) -> list[str] | None:
        for line in self._kv_lines(include_indented):
            if line.key == key:
                return line.values
        return None

    def get_all(self, key: str, include_indented: bool = False) -> list[list[str]]:
        return [line.values for line in self._kv_lines(include_indented) if line.key == key]

    def require_first(self, key: str, include_indented: bool = False) -> list[str]:
        values = self.get_first(key, include_indented)
        if values is None:
            raise ParseError(self.source, f"required key {key!r} is missing")
        return values

    def set_first(
        self, key: str, values: list[str], include_indented: bool = False, append: bool = True
    ) -> bool:
        """Replace the first matching record's values in place.

        Returns True when an existing record was updated. When no record
        exists and *append* is set, a new ``key + values`` line (single
        spaces) is appended; otherwise returns False.
        """
        for i, line in enumerate(self.lines):
            if (line.kind == "kv" or (include_indented and line.kind == "indented")) and line.key == key:
                self.lines[i] = line.with_values(values)
                return True
        if append:
            text = key + (" " + " ".join(values) if values else "")
            self.lines.append(
                ScriptLine(raw=text.encode("utf-8"), ending=self.newline, text=text)
            )
        return False

    def unknown_lines(self, known_keys: set[str], include_indented: bool = False) -> list[ScriptLine]:
        """Lines that are not blank and not a known key — preserved verbatim."""
        out = []
        for line in self.lines:
            if line.kind in ("kv", "indented"):
                if line.kind == "kv" or include_indented:
                    if line.key not in known_keys:
                        out.append(line)
            elif line.kind == "comment":
                out.append(line)
        return out

    # -- serializing --------------------------------------------------
    def to_bytes(self) -> bytes:
        return b"".join(line.raw + line.ending for line in self.lines)

    def save(self, path: str) -> None:
        with open(path, "wb") as fh:
            fh.write(self.to_bytes())
