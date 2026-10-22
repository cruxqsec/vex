from collections.abc import Iterable
from dataclasses import dataclass

from vex_cli.models.pydantic import FlowSummary, Scope

SEARCH_FIELDS: dict[str, str] = {
    "host": "host",
    "method": "method",
    "path": "path",
    "query": "query",
    "status": "status_code",
    "mime": "mime",
    "title": "http_title",
    "ext": "file_extension",
    "cookie": "cookie",
}


@dataclass(frozen=True)
class SearchTerm:
    """A normalized substring and its optional search-field prefix."""

    prefix: str | None
    value: str


def parse_search_query(text: str) -> tuple[SearchTerm, ...]:
    """Validate every whitespace-delimited token, splitting its first colon only."""
    terms = []
    for token in text.split():
        if ":" not in token:
            terms.append(SearchTerm(None, token.casefold()))
            continue
        prefix, value = token.split(":", 1)
        prefix = prefix.casefold()
        if prefix not in SEARCH_FIELDS:
            raise ValueError(f"Invalid search token {token!r}: unknown prefix {prefix!r}")
        if not value:
            raise ValueError(f"Invalid search token {token!r}: empty value")
        terms.append(SearchTerm(prefix, value.casefold()))
    return tuple(terms)


def matches_scope(summary: FlowSummary, scope: Scope | None) -> bool:
    """Match exact hosts, with deny entries overriding the optional allow list."""
    if scope is None:
        return True
    if summary.host in scope.deny_endpoints:
        return False
    return not scope.allow_endpoints or summary.host in scope.allow_endpoints


def matches_search(summary: FlowSummary, search_terms: tuple[SearchTerm, ...]) -> bool:
    """Require every term to match; unprefixed terms may match any search field."""
    for term in search_terms:
        fields = (
            SEARCH_FIELDS.values()
            if term.prefix is None
            else (SEARCH_FIELDS[term.prefix],)
        )
        if not any(
            value is not None and term.value in str(value).casefold()
            for value in (getattr(summary, field) for field in fields)
        ):
            return False
    return True


def filter_summaries(
    summaries: Iterable[FlowSummary],
    scope: Scope | None,
    search_terms: tuple[SearchTerm, ...],
) -> list[FlowSummary]:
    """Apply scope before search without sorting or modifying the summaries."""
    return [
        summary
        for summary in summaries
        if matches_scope(summary, scope) and matches_search(summary, search_terms)
    ]
