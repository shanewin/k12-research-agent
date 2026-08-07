"""
Contact email discovery.

District staff emails are almost always published somewhere public (staff
directories, board packets, school newsletters) even when the district site
itself renders them as images or hides them behind scripts. This module:

  1. Harvests real published addresses on the district's own domain
  2. Matches them directly to the contacts we've already identified
  3. Infers the district's naming convention from those confirmed matches
  4. Generates addresses for the remaining contacts from that convention
  5. Confirms the domain can actually receive mail (MX lookup)

Every address is labelled with how it was obtained, so a rep knows which
ones are confirmed and which are inferred.
"""

import logging
import re
import subprocess
from collections import Counter
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Shared inboxes are not people — never assign these to a contact
ROLE_PREFIXES = {
    "info", "contact", "webmaster", "admin", "support", "help", "office",
    "district", "hr", "jobs", "careers", "media", "press", "news", "privacy",
    "studentservices", "disability", "enrollment", "registrar", "transportation",
    "nutrition", "facilities", "purchasing", "noreply", "no-reply", "donotreply",
}

PATTERNS = [
    ("{first}.{last}", lambda f, l: f"{f}.{l}"),
    ("{first}_{last}", lambda f, l: f"{f}_{l}"),
    ("{first}{last}", lambda f, l: f"{f}{l}"),
    ("{first_initial}{last}", lambda f, l: f"{f[0]}{l}"),
    ("{first_initial}.{last}", lambda f, l: f"{f[0]}.{l}"),
    ("{first_initial}_{last}", lambda f, l: f"{f[0]}_{l}"),
    ("{last}{first_initial}", lambda f, l: f"{l}{f[0]}"),
    ("{last}.{first}", lambda f, l: f"{l}.{f}"),
    ("{last}_{first}", lambda f, l: f"{l}_{f}"),
]


def _clean_name(name: str) -> List[str]:
    """Split a display name into lowercase word tokens, dropping honorifics."""
    n = re.sub(r"\b(dr|mr|mrs|ms|prof|jr|sr|ii|iii|phd|ed\.?d)\b\.?", " ", (name or "").lower())
    return [t for t in re.split(r"[^a-z]+", n) if len(t) > 1]


def _is_role_address(local: str) -> bool:
    return local.lower().replace(".", "").replace("_", "") in ROLE_PREFIXES


def domain_accepts_mail(domain: str) -> bool:
    """MX lookup via dig — confirms the domain can receive mail at all."""
    try:
        out = subprocess.run(["dig", "+short", "MX", domain], capture_output=True,
                             text=True, timeout=10).stdout.strip()
        return bool(out)
    except Exception:
        return True  # don't discard addresses just because dig is unavailable


def harvest_domain_emails(domain: str, tavily) -> List[str]:
    """Find published email addresses on a district's domain via search."""
    found = set()
    queries = [
        f'"@{domain}" email staff directory',
        f'"@{domain}" superintendent OR director OR principal contact',
    ]
    for q in queries:
        try:
            res = tavily.search(q, search_depth="advanced", max_results=8)
        except Exception as e:
            logger.warning(f"Email harvest search failed: {e}")
            continue
        for r in (res or {}).get("results", []):
            blob = f"{r.get('content', '')} {r.get('raw_content', '') or ''} {r.get('url', '')}"
            for e in EMAIL_RE.findall(blob):
                if e.lower().endswith(f"@{domain.lower()}"):
                    found.add(e)
    logger.info(f"Harvested {len(found)} published addresses on {domain}")
    return sorted(found)


def infer_pattern(emails: List[str], contacts: List[dict]) -> Optional[str]:
    """Infer the district's naming convention by matching published addresses
    to people we know, falling back to the shape of the local parts."""
    votes = Counter()

    # Strongest evidence: an address that matches a known person's name
    for c in contacts:
        tokens = _clean_name(c.get("name", ""))
        if len(tokens) < 2:
            continue
        first, last = tokens[0], tokens[-1]
        for e in emails:
            local = e.split("@")[0].lower()
            for template, build in PATTERNS:
                if local == build(first, last):
                    votes[template] += 3

    # Weaker evidence: separator shape across all harvested addresses
    if not votes:
        for e in emails:
            local = e.split("@")[0].lower()
            if _is_role_address(local):
                continue
            if re.fullmatch(r"[a-z]+\.[a-z]+", local):
                votes["{first}.{last}"] += 1
            elif re.fullmatch(r"[a-z]+_[a-z]+", local):
                votes["{first}_{last}"] += 1
            elif re.fullmatch(r"[a-z]\.[a-z]+", local):
                votes["{first_initial}.{last}"] += 1
            elif re.fullmatch(r"[a-z][a-z]+", local) and len(local) > 6:
                votes["{first_initial}{last}"] += 1

    if not votes:
        return None
    best, count = votes.most_common(1)[0]
    logger.info(f"Inferred email pattern {best} (score {count})")
    return best


def _build(template: str, first: str, last: str) -> str:
    for name, fn in PATTERNS:
        if name == template:
            return fn(first, last)
    return f"{first}.{last}"


def find_emails(contacts: List, district_domain: str, tavily) -> Dict[str, int]:
    """Fill in `.email` on Contact objects. Returns per-method counts.

    Sets each contact's source suffix so reps can tell confirmed addresses
    from inferred ones.
    """
    stats = {"published": 0, "pattern": 0, "none": 0}
    if not district_domain or not contacts:
        return stats

    domain = urlparse(district_domain).netloc or district_domain
    domain = domain.replace("www.", "").strip("/")
    if not domain:
        return stats

    emails = harvest_domain_emails(domain, tavily)
    people_emails = [e for e in emails if not _is_role_address(e.split("@")[0])]
    pattern = infer_pattern(people_emails, [{"name": getattr(c, "name", "")} for c in contacts])
    mx_ok = domain_accepts_mail(domain)

    lower_map = {e.lower(): e for e in people_emails}

    for c in contacts:
        if getattr(c, "email", None):
            continue
        tokens = _clean_name(getattr(c, "name", ""))
        if len(tokens) < 2:
            stats["none"] += 1
            continue
        last = tokens[-1]
        # People often go by a middle/preferred name ("Mao Misty Her"), so try
        # every non-surname token as the candidate first name.
        first_options = tokens[:-1]
        first = first_options[0]

        # 1) Direct match against a published address
        hit = None
        for cand_first in first_options:
            for tmpl, build in PATTERNS:
                cand = f"{build(cand_first, last)}@{domain}".lower()
                if cand in lower_map:
                    hit = lower_map[cand]
                    break
            if hit:
                break
        if not hit:
            # Token-exact fallback: the surname must be a whole token in the
            # local part, and a first token must match a name or its initial.
            # (Substring matching wrongly paired "Mao ... Her" with "Mala.Her".)
            for e in people_emails:
                local = e.split("@")[0].lower()
                parts = [p for p in re.split(r"[._\-]", local) if p]
                if last not in parts:
                    continue
                others = [p for p in parts if p != last]
                if any(o == f or (len(o) == 1 and o == f[0]) for o in others for f in first_options):
                    hit = e
                    break
        if hit:
            c.email = hit
            c.source = f"{getattr(c, 'source', '')} · email: published".strip(" ·")
            stats["published"] += 1
            continue

        # 2) Generate from the district's convention
        if pattern and mx_ok:
            c.email = f"{_build(pattern, first, last)}@{domain}"
            c.source = f"{getattr(c, 'source', '')} · email: inferred pattern".strip(" ·")
            stats["pattern"] += 1
        else:
            stats["none"] += 1

    logger.info(f"Email discovery on {domain}: {stats}")
    return stats
