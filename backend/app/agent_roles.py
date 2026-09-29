"""Role routing + adversarial loop + lawyer-meeting brief (D11)."""
import json

from app import llm
from app.research_tools import juportal_search, justel_search


def route_role(instruction: str) -> str:
    t = instruction.lower()
    if any(k in t for k in ("research", "jurisprud", "legislation", "wet", "article", "ecli", "precedent", "cassatie")):
        return "research"
    if any(k in t for k in ("attack", "opposing", "weakness", "counterarg", "adversar", "risico", "risks")):
        return "adversarial"
    if any(k in t for k in ("draft", "brief", "letter", "email", "schrijf", "write to")):
        return "drafting"
    if any(k in t for k in ("timeline", "chronolog", "chronology", "dates", "when did")):
        return "timeline"
    if any(k in t for k in ("evidence", "bewijs", "source", "gap", "missing")):
        return "evidence"
    return "case_manager"


ADVERSARIAL_ATTACK = """You represent the OPPOSING party in this Belgian dispute.
Given the case context, produce a list of weaknesses in my client's position. For EACH weakness:
- the specific attack
- which piece of evidence contradicts it (citation [DOC:id:page]) or a legal hook (statute or case)
- what evidence is missing that the opposing side would need
Format: numbered list, strictly these sections per item: Attack / Counter-evidence / Missing evidence / Confidence."""


ADVERSARIAL_DEFEND = """Now defend MY case. For each attack listed below, produce:
- the response our side would make
- which evidence supports the response ([DOC:id:page])
- if the attack survives, explicitly say "survives — needs lawyer strategy"
Attacks:\n"""


LAWYER_BRIEF = """Produce a lawyer-meeting brief in exactly these 12 sections:
1. What happened
2. What is disputed
3. Evidence supporting our position
4. Evidence supporting the opposing position
5. Applicable legislation
6. Relevant Belgian judgments
7. Arguments available
8. Weak points
9. Questions for the lawyer
10. Procedural deadlines
11. Recommended documents to obtain
12. Draft instructions for the lawyer
Every factual claim ends with a citation [DOC:id:page]. If a section is empty, say "—" and list under Open questions."""


def role_context(query: str, case_id: str) -> dict:
    """Which tools the role uses."""
    return {
        "research": {"jurisprudence": juportal_search(query), "legislation": justel_search(query)},
    }.get(query, {})


def build_prompt(role: str, base_context: dict, instruction: str) -> str:
    ctx = json.dumps(base_context, indent=2)
    if role == "adversarial":
        attack = llm.complete(ADVERSARIAL_ATTACK + f"\n\nCase context:\n{ctx}", system="You are litigating for the opposing party.")
        defense = llm.complete(ADVERSARIAL_DEFEND + attack + f"\n\nCase context:\n{ctx}", system="You are defending your own client.")
        return f"ADVERSARIAL ANALYSIS\n\n=== ATTACK ===\n{answer_or_exc(attack)}\n\n=== DEFENSE ===\n{answer_or_exc(defense)}"
    if role == "drafting":
        return llm.complete(LAWYER_BRIEF + f"\n\nCase context:\n{ctx}\n\nTask: {instruction}", system="You are Legal OS's drafting agent.")
    return llm.complete(f"Case context:\n{ctx}\n\nTask: {instruction}", system=SYSTEM_FALLBACK)


SYSTEM_FALLBACK = """You are the LitigationOS case agent. Use ONLY the provided case data. Output sections: Answer / Sources / Confidence / Open questions / Proposed next actions."""


def answer_or_exc(s: str) -> str:
    return s if s else "(llm returned empty)"
