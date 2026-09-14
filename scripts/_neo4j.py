"""Shared bits for the graph_import* and warm_path scripts: repo paths, .env
loading, company/person-name aliasing, and company-name normalization."""

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"
COMPANY_ALIASES = REPO / "job" / "company_aliases.json"
PERSON_ALIASES = REPO / "job" / "person_aliases.json"
JOBWATCH_ENV = REPO.parent / "jobwatch" / ".env"
JOBWATCH_CONFIG = REPO.parent / "jobwatch" / "config.py"

# Every pipeline stage except the closed ones (job/pipeline.json's own
# "stages" list has the full set) - the complement of objection_report.py's
# CLOSED_STAGES, kept as its own literal here rather than importing a script
# not meant to be a library. Deliberately wider than any one script's prior
# "active" set (board.py's LIVE, job_scaffold.py's ACTIVE, and an earlier cut
# of this constant all disagreed, and all three dropped "interviewing" or
# "waiting" - the highest-priority stages to have title/company coverage for).
OPEN_STAGES = {"interviewing", "waiting", "applied", "followup",
               "considering", "outreach", "warm"}

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


def is_exact_match(matches: list[dict]) -> bool:
    """True when find_company() resolved to exactly one unambiguous match
    (score 100) - safe to use without asking a human to disambiguate. Shared
    by every script that resolves a typed/pipeline company name against the
    graph, so the definition of "exact" can't drift between them."""
    return len(matches) == 1 and matches[0]["score"] >= 100


def load_env(path: Path = ENV) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"no .env at {path}")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def load_jobwatch_config_names(*names: str) -> dict:
    """Pull top-level list/dict assignments out of jobwatch/config.py by name,
    without importing it (keeps these scripts out of JobWatch's own venv/
    deps). Used by every script here that needs to compare pipeline data
    against JobWatch's search config - one parse of the file per call,
    shared instead of each script walking the AST itself."""
    if not JOBWATCH_CONFIG.exists():
        raise FileNotFoundError(f"no config.py at {JOBWATCH_CONFIG}")
    tree = ast.parse(JOBWATCH_CONFIG.read_text(encoding="utf-8"))
    wanted = set(names)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in wanted:
                found[target.id] = ast.literal_eval(node.value)
    missing = wanted - found.keys()
    if missing:
        raise ValueError(f"{JOBWATCH_CONFIG} has no top-level assignment(s) named {sorted(missing)}")
    return found


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
