"""Shared bits for the graph_import* and warm_path scripts: repo paths, .env
loading, company/person-name aliasing, and company-name normalization."""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
COMPANY_ALIASES = REPO / "job" / "company_aliases.json"
PERSON_ALIASES = REPO / "job" / "person_aliases.json"

_SUFFIXES = re.compile(
    r"\b(inc|llc|ltd|corp|corporation|co|company|group|holdings?|"
    r"international|technologies|technology|systems?)\b\.?",
    re.IGNORECASE,
)


def normalize(name: str) -> str:
    """Case/punctuation/legal-suffix-insensitive form of a company name, for
    matching "Google Cloud" to "Google" or a typo'd variant to its match."""
    n = name.lower()
    n = _SUFFIXES.sub("", n)
    n = re.sub(r"[.,&]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def find_company(session, query: str, threshold: int = 85) -> list[dict]:
    """Resolve a typed company name against every Company node in the graph.

    Exact case-insensitive match returns immediately as a single 100-score
    hit. Otherwise every other company name is fuzzy-matched (via rapidfuzz)
    against the normalized query, so an unmerged variant ("Deloitte
    Consulting LLP") is still findable from a short typed name ("Deloitte")
    with no approved alias needed. Returns a list of {"name", "score"} dicts,
    sorted best first; empty if nothing clears the threshold.
    """
    exact = session.run(
        "MATCH (c:Company) WHERE toLower(c.name) = toLower($q) RETURN c.name AS name",
        q=query,
    ).single()
    if exact:
        return [{"name": exact["name"], "score": 100.0}]

    from rapidfuzz import fuzz

    norm_query = normalize(query)
    names = [r["name"] for r in session.run("MATCH (c:Company) RETURN c.name AS name")]
    scored = [(n, fuzz.ratio(norm_query, normalize(n))) for n in names]
    scored = [(n, s) for n, s in scored if s >= threshold]
    scored.sort(key=lambda t: -t[1])
    return [{"name": n, "score": round(s, 1)} for n, s in scored]


def load_env() -> dict:
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_aliases() -> dict:
    """alias -> canonical company name, approved via company_aliases_suggest.py."""
    return _load_json(COMPANY_ALIASES)


def load_person_aliases() -> dict:
    """alias -> canonical person name, e.g. a first-name-only pipeline mention
    resolved to the full name it turned out to match in job/pipeline.json or
    a LinkedIn export. Manually curated, not suggested — no automated fuzzy
    pass for people the way there is for companies."""
    return _load_json(PERSON_ALIASES)
