"""Belgian legal-source adapters (D11 Research tool, hardened in D12).

Live, free, public:
- JuPortal: ECLI resolution `https://juportal.be/content/<ECLI>`
- Justel: keyword search via ejustice.just.fgov.be legacy `rech.pl` form -> `rech_res.pl`
  (unofficial; we parse result links to stable ELI article URLs); article text via
  ELI coordinate URL `https://www.ejustice.just.fgov.be/eli/{type}/{yyyy}/{mm}/{dd}/{numac}/justel`
- EUR-Lex: CELEX resolution `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:<celex>`

All functions degrade gracefully to `None`/[] on network failure — the caller
(the Research Agent) treats that as UNVERIFIABLE, which is the correct signal.
"""
from __future__ import annotations
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "LitigationOS/0.1 (legal research; free public sources)"}
TIMEOUT = 12


def _get(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception:
        return None


# ---------------- JuPortal ----------------

def juportal_get_by_ecli(ecli: str) -> dict | None:
    """Fetch a judgment's page. Returns {url, ecli, title?} or None."""
    if not re.match(r"^ECLI:BE:[A-Z0-9]+:\d{4}:[A-Z0-9.]+$", ecli):
        return None
    url = f"https://juportal.be/content/{ecli}"
    html = _get(url)
    if not html or "Page not found" in html:
        return None
    return {"source": "juportal", "ecli": ecli, "url": url}


def juportal_search(query: str, limit: int = 5) -> list[dict]:
    """Best-effort ECLI discovery via site search; returns list of citation stubs to verify later.
    JuPortal has no public query API; we return lookup URLs + empty (verified later by D12)."""
    # Using Juportal content endpoint requires known ECLI; for keyword search we return a
    # reference to the UI the user/agent can open. The D12 verifier then resolves the chosen ECLI.
    q = urllib.parse.quote(query)
    return [{
        "source": "juportal",
        "search_url": f"https://juportal.be/moteur/formulaire?type=juportal&texte={q}",
        "note": "open this to pick the exact ECLI to cite; verifier resolves https://juportal.be/content/<ECLI>",
    }][:limit]


# ---------------- Justel ----------------

_JUST_RES = "https://www.ejustice.just.fgov.be/cgi_loi/rech_res.pl"
_ELI_RE = re.compile(r'https://www\.ejustice\.just\.fgov\.be/eli/[a-z0-9]+/\d{4}/\d{2}/\d{2}/\d+/justel', re.I)


def justel_search(query: str, language: str = "nl", limit: int = 5) -> list[dict]:
    """Keyword search consolidated Belgian legislation via the public form. Returns ELI URLs."""
    body = urllib.parse.urlencode({
        "language": language, "dt": "LOI", "text1": query, "chercher": "t",
        ("nl" if language == "nl" else "fr"): "1", "trier": "promulgation", "numero1": "1",
    }).encode("iso-8859-1")
    try:
        req = urllib.request.Request(_JUST_RES, data=body, headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
        raw = urllib.request.urlopen(req, timeout=TIMEOUT).read()
        html = raw.decode("iso-8859-1", errors="replace")
    except Exception:
        return []
    results: list[dict] = []
    for m in _ELI_RE.finditer(html):
        eli = m.group(0)
        if not any(r["eli"] == eli for r in results):
            results.append({"source": "justel", "eli": eli, "url": eli})
        if len(results) >= limit:
            break
    return results


def justel_get_text(eli_url: str) -> str | None:
    html = _get(eli_url)
    return html


# ---------------- EUR-Lex ----------------

def eurlex_get_by_celex(celex: str) -> dict | None:
    url = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{urllib.parse.quote(celex)}"
    html = _get(url)
    return {"source": "eurlex", "celex": celex, "url": url} if html else None


TOOLS_INFO = {
    "search_jurisprudence": "JuPortal ECLI discovery (returns search URL to pick exact ECLI)",
    "get_legal_source": "Resolve ECLI/ELI/CELEX -> {source, url} for verification",
    "search_legislation": "Justel keyword search -> ELI article URLs",
}
