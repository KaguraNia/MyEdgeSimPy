"""Small literature-search helper (OpenAlex / arXiv / DBLP).

There is no general web-search tool in this environment, so this script queries the
bibliographic APIs that matter for a systems/edge-computing literature review. Everything
it prints comes straight from the API response -- nothing is inferred or invented.

Usage
-----
    # Verify a specific paper by title (OpenAlex first, DBLP as fallback)
    python scripts/litsearch.py title "Live Service Migration in Mobile Edge Clouds"

    # Topic sweep
    python scripts/litsearch.py topic "service migration mobile edge computing" --limit 10

    # Preprints only
    python scripts/litsearch.py arxiv "state migration edge computing"

    # Full API payload for a query (useful when writing up related work)
    python scripts/litsearch.py topic "..." --limit 10 --json
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

USER_AGENT = "MyEdgeSimPy-litreview/0.1 (research; mailto:student@example.edu)"
MAILTO = "student@example.edu"


# --------------------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------------------
def _ssl_context() -> ssl.SSLContext:
    """Use certifi's bundle when available.

    Some hosts (dblp.org) send an incomplete certificate chain that Python's bundled
    trust store cannot resolve, while certifi's bundle can.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_SSL_CONTEXT = _ssl_context()


def _get(url: str, attempts: int = 3, timeout: int = 40) -> Any:
    """GET a URL and parse JSON, retrying on transient failures."""
    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout, context=_SSL_CONTEXT) as response:
                payload = response.read().decode("utf-8", errors="replace")
            return json.loads(payload)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed: {url}\n{last_error}")


def _reconstruct_abstract(inverted: Optional[Dict[str, List[int]]], max_chars: int = 1200) -> str:
    """OpenAlex ships abstracts as an inverted index; rebuild readable text."""
    if not inverted:
        return ""
    positions: List[tuple] = []
    for word, offsets in inverted.items():
        for offset in offsets:
            positions.append((offset, word))
    positions.sort()
    text = " ".join(word for _, word in positions)
    return text[:max_chars]


# --------------------------------------------------------------------------------------
# OpenAlex
# --------------------------------------------------------------------------------------
def openalex(search: Optional[str] = None, title: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search OpenAlex by free text (`search`) or by title (`title`)."""
    params: Dict[str, Any] = {"per-page": max(1, min(limit, 200)), "mailto": MAILTO}
    if title:
        params["filter"] = f"title.search:{title}"
    elif search:
        params["search"] = search
    else:
        raise ValueError("either search or title is required")

    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    data = _get(url)

    results: List[Dict[str, Any]] = []
    for work in data.get("results", []):
        venue = ""
        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}
        venue = source.get("display_name") or ""
        results.append(
            {
                "openalex_id": work.get("id"),
                "doi": work.get("doi"),
                "title": work.get("title") or "",
                "year": work.get("publication_year"),
                "venue": venue,
                "type": work.get("type"),
                "cited_by": work.get("cited_by_count", 0),
                "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
                "authors": [
                    (authorship.get("author") or {}).get("display_name", "")
                    for authorship in (work.get("authorships") or [])[:6]
                ],
                "concepts": [
                    concept.get("display_name", "")
                    for concept in (work.get("concepts") or [])[:5]
                ],
            }
        )
    return results


# --------------------------------------------------------------------------------------
# arXiv
# --------------------------------------------------------------------------------------
def arxiv(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search arXiv and return the standard Atom entries as flat dictionaries."""
    url = (
        "http://export.arxiv.org/api/query?"
        + urllib.parse.urlencode(
            {"search_query": query, "start": 0, "max_results": max(1, min(limit, 100)), "sortBy": "relevance"},
            quote_via=urllib.parse.quote,
        )
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=40) as response:
        xml = response.read().decode("utf-8", errors="replace")

    import xml.etree.ElementTree as ET

    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    results: List[Dict[str, Any]] = []
    for entry in root.findall("atom:entry", namespace):
        results.append(
            {
                "arxiv_id": (entry.findtext("atom:id", "", namespace) or "").rsplit("/", 1)[-1],
                "title": " ".join((entry.findtext("atom:title", "", namespace) or "").split()),
                "published": entry.findtext("atom:published", "", namespace),
                "updated": entry.findtext("atom:updated", "", namespace),
                "summary": " ".join((entry.findtext("atom:summary", "", namespace) or "").split())[:1200],
                "authors": [
                    author.findtext("atom:name", "", namespace)
                    for author in entry.findall("atom:author", namespace)[:6]
                ],
                "categories": [
                    category.get("term", "")
                    for category in entry.findall("atom:category", namespace)
                ],
            }
        )
    return results


# --------------------------------------------------------------------------------------
# DBLP (good for exact titles / venue confirmation)
# --------------------------------------------------------------------------------------
def dblp(title: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search DBLP by title; useful to confirm the venue of a specific paper."""
    # DBLP is aggressive about rate limiting; be polite between calls.
    time.sleep(1.2)
    url = "https://dblp.org/search/publ/api?" + urllib.parse.urlencode(
        {"q": title, "format": "json", "h": max(1, min(limit, 50))}
    )
    try:
        data = _get(url, attempts=2)
    except RuntimeError:
        return []
    hits = (((data.get("result") or {}).get("hits") or {}).get("hit")) or []

    results: List[Dict[str, Any]] = []
    for hit in hits:
        info = hit.get("info") or {}
        authors = info.get("authors", {}).get("author") if isinstance(info.get("authors"), dict) else []
        if isinstance(authors, dict):
            authors = [authors]
        results.append(
            {
                "title": info.get("title", ""),
                "venue": info.get("venue", ""),
                "year": info.get("year"),
                "type": info.get("type"),
                "doi": info.get("doi"),
                "authors": [a.get("text", "") for a in (authors or [])][:8],
                "url": info.get("ee") or info.get("url"),
            }
        )
    return results


# --------------------------------------------------------------------------------------
# Crossref (fallback for venue/DOI confirmation)
# --------------------------------------------------------------------------------------
def crossref(title: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search Crossref by title."""
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
        {"query.bibliographic": title, "rows": max(1, min(limit, 20)), "mailto": MAILTO}
    )
    data = _get(url)
    items = (((data.get("message") or {}).get("items")) or [])

    results: List[Dict[str, Any]] = []
    for item in items:
        titles = item.get("title") or []
        container = item.get("container-title") or []
        issued = ((item.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        results.append(
            {
                "title": titles[0] if titles else "",
                "venue": container[0] if container else "",
                "year": issued,
                "type": item.get("type"),
                "doi": item.get("DOI"),
                "publisher": item.get("publisher"),
            }
        )
    return results


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _print_openalex(rows: List[Dict[str, Any]], show_abstract: bool) -> None:
    for row in rows:
        print(f"- {row['year']} | {row['title']}")
        print(f"    venue: {row['venue'] or 'n/a'} | type: {row['type']} | cited_by: {row['cited_by']}")
        if row["doi"]:
            print(f"    doi: {row['doi']}")
        if show_abstract and row["abstract"]:
            print(f"    abstract: {row['abstract'][:600]}...")
        print()


def main() -> int:
    # Chinese Windows consoles default to GBK, which cannot encode many author names.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("title", "verify a specific paper by title"),
        ("topic", "topic sweep over OpenAlex"),
        ("arxiv", "search arXiv preprints"),
        ("dblp", "search DBLP by title"),
        ("crossref", "search Crossref by title"),
        ("digest", "compact view over a directory of saved topic dumps"),
        ("bibtex", "emit BibTeX entries from a directory of saved paper dumps"),
    ):
        child = sub.add_parser(name, help=help_text)
        child.add_argument("query")
        child.add_argument("--limit", type=int, default=10)
        child.add_argument("--json", action="store_true", help="dump the raw parsed records")
        child.add_argument("--abstract", action="store_true", help="include abstracts")
        child.add_argument("--out", help="write the parsed records to this JSON file")
        child.add_argument("--authors", action="store_true", help="include author lists (digest)")
        child.add_argument("--doi", action="store_true", help="include DOIs (digest)")

    args = parser.parse_args()

    if args.command == "title":
        rows = openalex(title=args.query, limit=args.limit)
        print(f"== OpenAlex (title search): {args.query} ==")
        _print_openalex(rows, args.abstract or args.json)
        extra = crossref(args.query, limit=args.limit)
        if extra:
            print(f"== Crossref (title search): {args.query} ==")
            for row in extra:
                print(f"- {row['year']} | {row['title']} | {row['venue']} | {row['type']}")
        if args.out:
            _dump(args.out, {"query": args.query, "openalex": rows, "crossref": extra})
        return 0

    if args.command == "topic":
        rows = openalex(search=args.query, limit=args.limit)
        print(f"== OpenAlex (topic search): {args.query} ==")
        _print_openalex(rows, args.abstract or args.json)
        if args.out:
            _dump(args.out, {"query": args.query, "openalex": rows})
        return 0

    if args.command == "arxiv":
        rows = arxiv(args.query, limit=args.limit)
        print(f"== arXiv: {args.query} ==")
        for row in rows:
            print(f"- {row['published'][:10]} | {row['title']}")
            print(f"    {row['arxiv_id']} | {', '.join(row['categories'][:3])}")
            if args.abstract or args.json:
                print(f"    {row['summary'][:600]}...")
            print()
        if args.out:
            _dump(args.out, {"query": args.query, "arxiv": rows})
        return 0

    if args.command == "dblp":
        for row in dblp(args.query, limit=args.limit):
            print(f"- {row['year']} | {row['title']} | {row['venue']} | {row['type']}")
            print(f"    {row['url']}")
        if args.out:
            _dump(args.out, {"query": args.query, "dblp": dblp(args.query, limit=args.limit)})
        return 0

    if args.command == "crossref":
        rows = crossref(args.query, limit=args.limit)
        for row in rows:
            print(f"- {row['year']} | {row['title']} | {row['venue']} | {row['type']} | {row['doi']}")
        if args.out:
            _dump(args.out, {"query": args.query, "crossref": rows})
        return 0

    if args.command == "digest":
        from pathlib import Path

        directory = Path(args.query)
        top = args.limit
        for path in sorted(directory.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            works = payload.get("openalex") or payload.get("arxiv") or payload.get("crossref") or []
            print(f"### {path.stem}  |  {payload.get('query', '')}")
            for work in works[:top]:
                if "year" in work:
                    suffix = ""
                    if args.doi or args.authors:
                        parts = []
                        if args.doi and work.get("doi"):
                            parts.append(work["doi"].replace("https://doi.org/", ""))
                        if args.authors and work.get("authors"):
                            parts.append("; ".join(a for a in work["authors"] if a))
                        if parts:
                            suffix = "\n      " + " | ".join(parts)
                    print(
                        f"  {work['year']} | cites {work['cited_by']:>5} | "
                        f"{work['title'][:100]} | {(work['venue'] or '')[:42]}{suffix}"
                    )
                else:
                    print(f"  {work.get('published', '')[:10]} | {work['title'][:100]}")
            print()
        return 0

    if args.command == "bibtex":
        from pathlib import Path

        directory = Path(args.query)
        entries = []
        for path in sorted(directory.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            works = payload.get("openalex") or []
            if not works:
                continue
            work = works[0]
            key = path.stem.replace("-", "")
            venue = work.get("venue") or ""
            doi = (work.get("doi") or "").replace("https://doi.org/", "")
            authors = " and ".join(a for a in (work.get("authors") or []) if a)
            kind_is_proceedings = any(
                word in venue.lower()
                for word in ("conference", "symposium", "proceedings", "workshop", "cloud computing")
            )
            entry_type = "inproceedings" if kind_is_proceedings else "article"
            venue_field = "booktitle" if kind_is_proceedings else "journal"
            lines = [
                f"@{entry_type}{{{key},",
                f"  title = {{{work.get('title', '')}}},",
                f"  author = {{{authors}}},",
                f"  year = {{{work.get('year', '')}}},",
                f"  {venue_field} = {{{venue}}},",
            ]
            if doi:
                lines.append(f"  doi = {{{doi}}},")
            lines.append(f"  note = {{OpenAlex; cited by {work.get('cited_by', 0)}}},")
            lines.append("}")
            entries.append("\n".join(lines))

        text = "\n\n".join(entries) + "\n"
        if args.out:
            _dump_text(args.out, text)
        else:
            print(text)
        return 0

    return 1


def _dump(path: str, payload: Any) -> None:
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[wrote {target}]")


def _dump_text(path: str, text: str) -> None:
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"[wrote {target}]")


if __name__ == "__main__":
    raise SystemExit(main())
