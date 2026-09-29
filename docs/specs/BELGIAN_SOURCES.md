# BELGIAN_SOURCES.md — Belgian Legal Sources (Appendix D)

Version 1.0. Why this file exists: mainstream legal AI (Harvey, CoCounsel, Lexis+, vLex) is US/UK-optimized. Belgian law needs Belgian primary sources. **Citation verification is a critical control** — legal AI can produce plausible but wrong citations.

## Sources

| Source | What it covers | Access in v1 | Notes |
|---|---|---|---|
| **JuPortal** | Belgian jurisprudence: Constitutional Court, Court of Cassation, Courts of Appeal, labour courts, courts of first instance, company courts | Public web search; store URL + ECLI + exact passage | Coverage outside Court of Cassation is **selective** — say so in output |
| **Justel** | Belgian legislation (Belgian State Gazette / Belgisch Staatsblad) | Public web; store consolidated version URL + article | Always cite exact article + in-force date |
| **Lex.be** | Aggregated Belgian legislation + jurisprudence (incl. State Gazette, Juridat) | Public web as secondary route | Cross-check against JuPortal/Justel |
| **EUR-Lex** | EU law where relevant | Public web; CELEX identifier | Only when EU dimension exists |
| **Jura / Strada lex / LexNow** | Commercial commentary + broader case law | Out of scope v1 (subscription) | UHasselt warns their coverage differs and none is complete — do not assume completeness |
| **e-Deposit** | Electronic court filing | **Manual-only in v1** | Agent prepares bundle, human files |

## Citation format — every legal citation record contains
Court · Date · Case number · **ECLI** · Source (JuPortal/Justel/Lex.be) · URL · Exact passage · Why relevant · Verification status (VERIFIED / UNVERIFIABLE / MISMATCH).

Example: `Cass. 14 november 2019, ECLI:BE:CASS:2019:ARR.2019112804.…, passage "…", relevance: burden of proof for rental damage`.

## Verification procedure (drives D12)
1. Resolver re-fetches `url` (or local copy) and locates `exact_passage`.
2. Passage found & matches → VERIFIED. Source found but passage differs → MISMATCH. Source unreachable/unresolvable → UNVERIFIABLE (rendered as such; cannot be APPROVED).

## Product note
Docuralis (Belgian legal AI over JuPortal/Justel/EUR-Lex/BCE/ONSS working with own case files) is worth evaluating as a research complement before over-investing in our own retrieval of case law.
