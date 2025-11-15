"""
Regex-based detector for PII and secrets (Middleware Building Block)
--------------------------------------------------------------------
- Detects common PII (email, phone, SSN, credit card, DOB) and secrets 
  (AWS keys, GitHub tokens, Slack/Stripe keys, JWTs, DB URLs, RSA tokens, private keys, etc.)
- Provides masking and a simple decision engine: block / mask / allow
- Designed to be used standalone OR imported inside a FastAPI/Flask middleware.

Usage (CLI):
    python regex_detector.py  # runs a demo
Or import:
    from regex_detector import detect, mask_text, decide_action
"""

import re
from dataclasses import dataclass
from typing import List, Optional

# -------------------- Helper Validators --------------------


def _luhn_check(num: str) -> bool:
    """Validate a credit card number with Luhn algorithm."""
    digits = [int(d) for d in num if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = (len(digits) - 2) % 2
    for i, d in enumerate(digits[:-1]):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    checksum += digits[-1]
    return checksum % 10 == 0


def _valid_ipv4(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _valid_ssn(ssn: str) -> bool:
    """Basic US SSN validation: disallow invalid area/group/serial combos."""
    m = re.fullmatch(r"(\d{3})-(\d{2})-(\d{4})", ssn)
    if not m:
        return False
    area, group, serial = m.groups()
    if area in {"000", "666"} or "900" <= area <= "999":
        return False
    if group == "00" or serial == "0000":
        return False
    return True


# -------------------- Pattern Definition --------------------


@dataclass
class PatternSpec:
    name: str
    category: str  # e.g., "PII", "Secret", "Network"
    severity: str  # "low" | "medium" | "high" | "critical"
    regex: str
    flags: int = re.MULTILINE
    validate: Optional[str] = None


PATTERNS: List[PatternSpec] = [
    # ---- PII ----
    PatternSpec(
        name="Email Address",
        category="PII",
        severity="medium",
        regex=r"\b[a-zA-Z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    ),
    PatternSpec(
        name="US Phone Number",
        category="PII",
        severity="medium",
        regex=r"\b(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b",
    ),
    PatternSpec(
        name="US SSN",
        category="PII",
        severity="high",
        regex=r"\b\d{3}-\d{2}-\d{4}\b",
        validate="_valid_ssn",
    ),
    PatternSpec(
        name="Credit Card Number",
        category="PII",
        severity="high",
        regex=r"\b(?:\d[ -]?){13,19}\b",
        validate="_luhn_check",
    ),
    PatternSpec(
        name="Date of Birth (MM/DD/YYYY or MM-DD-YYYY)",
        category="PII",
        severity="medium",
        regex=r"\b(?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2}\b",
    ),
    PatternSpec(
        name="IPv4 Address",
        category="Network",
        severity="low",
        regex=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        validate="_valid_ipv4",
    ),
    # ---- Secrets / Credentials ----
    PatternSpec(
        name="AWS Access Key ID",
        category="Secret",
        severity="critical",
        regex=r"\bAKIA[0-9A-Z]{16}\b",
    ),
    PatternSpec(
        name="AWS Secret Access Key (context)",
        category="Secret",
        severity="critical",
        regex=r"(?i)(?:aws|aws_secret_access_key|secret_access_key)\s*[:=]\s*([A-Za-z0-9/+=]{40})",
    ),
    PatternSpec(
        name="GitHub Token",
        category="Secret",
        severity="critical",
        regex=r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,255}\b",
    ),
    PatternSpec(
        name="Slack Token",
        category="Secret",
        severity="critical",
        regex=r"\b(?:xoxb|xoxp|xapp|xoxa|xoxr)-\d{10,13}-[a-zA-Z0-9\-]{24,}\b",
    ),
    PatternSpec(
        name="Stripe Secret Key",
        category="Secret",
        severity="critical",
        regex=r"\bsk_live_[0-9a-zA-Z]{24,}\b",
    ),
    PatternSpec(
        name="Google API Key",
        category="Secret",
        severity="high",
        regex=r"\bAIza[0-9A-Za-z\-_]{35}\b",
    ),
    PatternSpec(
        name="JWT (JSON Web Token)",
        category="Secret",
        severity="high",
        regex=r"\beyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\b",
    ),
    PatternSpec(
        name="Database URL (common schemes)",
        category="Secret",
        severity="high",
        regex=r"(?i)\b(?:postgres|mysql|mongodb|mssql|oracle|redis)://[^\s'\"`]+",
    ),
    PatternSpec(
        name="Private Key Block",
        category="Secret",
        severity="critical",
        regex=r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----[\s\S]+?-----END (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----",
        flags=re.MULTILINE,
    ),
    PatternSpec(
        name="Generic Credential Assignment",
        category="Secret",
        severity="high",
        regex=r"(?i)\b(password|pwd|pass|secret|token|api[-_ ]?key)\b\s*[:=]\s*([^\s'\"`]{6,})",
    ),
    PatternSpec(
        name="RSA Token",
        category="Secret",
        severity="critical",
        regex=r"(?i)\brsa[_-]?(token|key|secret)\b\s*[:=]\s*([A-Za-z0-9+/=]{8,128})",
    ),
    PatternSpec(
        name="SSH RSA Public Key",
        category="Secret",
        severity="high",
        regex=r"ssh-(rsa|ed25519|dss)\s+[A-Za-z0-9+/=]{40,}={0,2}",
    ),
    PatternSpec(
        name="Generic Credential Assignment",
        category="Secret",
        severity="high",
        regex=r"(?i)\b(password|pwd|pass|secret|token|api[-_ ]?key)\b\s*[:=]\s*([^\s'\"`]{6,})",
    ),
    PatternSpec(
        name="RSA Token",
        category="Secret",
        severity="critical",
        regex=r"\bRSA[_-]?(TOKEN|KEY|SECRET)\b\s*[:=]\s*([A-Za-z0-9+/=]{8,128})",
    ),
    PatternSpec(
        name="SSH RSA Public Key",
        category="Secret",
        severity="high",
        regex=r"\bssh-(rsa|ed25519|dss)\s+[A-Za-z0-9+/=]{50,}\b",
    ),
    PatternSpec(
        name="OpenSSH Key Block",
        category="Secret",
        severity="critical",
        regex=r"-----BEGIN OPENSSH (?:PRIVATE|PUBLIC) KEY-----[\s\S]+?-----END OPENSSH (?:PRIVATE|PUBLIC) KEY-----",
        flags=re.MULTILINE,
    ),

    PatternSpec(
        name="International Phone Number",
        category="PII",
        severity="medium",
        regex=r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\(?\d{1,4}\)?[\s-]?)?(?:\d[\d\s-]{5,}\d)",
    ),

]

# -------------------- Validators Map --------------------
_VALIDATORS = {
    "_luhn_check": _luhn_check,
    "_valid_ipv4": _valid_ipv4,
    "_valid_ssn": _valid_ssn,
}

# -------------------- Core Detection --------------------


@dataclass
class Match:
    name: str
    category: str
    severity: str
    match: str
    start: int
    end: int


def _severity_rank(sev: str) -> int:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return order.get(sev, 0)


def detect(text: str) -> List[Match]:
    """Return all pattern matches in the given text."""
    findings: List[Match] = []
    for spec in PATTERNS:
        pattern = re.compile(spec.regex, spec.flags)
        for m in pattern.finditer(text):
            matched_text = m.group(0)
            if spec.validate:
                validator = _VALIDATORS.get(spec.validate)
                if validator:
                    cand = matched_text
                    if spec.validate == "_luhn_check":
                        cand = "".join(ch for ch in matched_text if ch.isdigit())
                    if not validator(cand):
                        continue
            findings.append(
                Match(
                    name=spec.name,
                    category=spec.category,
                    severity=spec.severity,
                    match=matched_text,
                    start=m.start(),
                    end=m.end(),
                )
            )
    findings.sort(key=lambda x: (x.start, -_severity_rank(x.severity)))
    deduped: List[Match] = []
    used_spans = set()
    for f in findings:
        span = (f.start, f.end)
        if span not in used_spans:
            used_spans.add(span)
            deduped.append(f)
    return deduped


# -------------------- Masking & Decision --------------------


def mask_text(text: str, matches: List[Match], strategy: str = "redact") -> str:
    """Mask matches in text."""
    out = text
    for f in sorted(matches, key=lambda m: m.start, reverse=True):
        replacement = f"[REDACTED:{f.name}]"
        if strategy == "partial":
            replacement = _partial_mask(f.match, f.name)
        out = out[: f.start] + replacement + out[f.end :]
    return out


def _partial_mask(value: str, name: str) -> str:
    v = value
    if name == "Email Address":
        parts = v.split("@")
        if len(parts) == 2:
            return "[REDACTED_EMAIL]@" + parts[1]
    if name == "US Phone Number":
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) >= 10:
            return "***-***-" + digits[-4:]
    if name == "Credit Card Number":
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) >= 12:
            return "[REDACTED_CC]" + ("*" * (len(digits) - 4)) + digits[-4:]
    return "[REDACTED]"


def decide_action(matches: List[Match]) -> str:
    """Return 'block' if any critical; 'mask' if any high/medium; else 'allow'."""
    if any(m.severity == "critical" for m in matches):
        return "block"
    if any(_severity_rank(m.severity) >= 1 for m in matches):
        return "mask"
    return "allow"


# -------------------- Demo --------------------
def _demo():
    sample = (
        "Hi, my email is jane.doe@example.com and my phone is (215) 555-1234.\n"
        "My SSN is 123-45-6789 and my card is 4242 4242 4242 4242 exp 12/29.\n"
        "Here is my AWS key: AKIAABCDEFGHIJKLMNOP and aws_secret_access_key=abcdefghijklmnopqrstuvwxyz0123456789AB\n"
        "GitHub token: ghp_abcdefghijklmnopqrstuvwxyz012345\n"
        "RSA token: rsa_token=ZXhhbXBsZXNlY3JldA==\n"
        "RSA key: rsa_key: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6\n"
        "JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvZSIsImlhdCI6MTUxNjIzOTAyMn0.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk\n"
        "DB: postgres://user:pass@db.example.com:5432/app\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIICXQIBAAKBgQC...snip...\n-----END RSA PRIVATE KEY-----\n"
        "192.168.1.1 \n"
        "ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEArandomSSHKey"
    )
    findings = detect(sample)
    print("== Findings ==")
    for f in findings:
        print(f"- {f.name} [{f.category}/{f.severity}] ->", repr(f.match))
    action = decide_action(findings)
    print("\nDecision:", action)
    masked = mask_text(sample, findings, strategy="partial")
    print("\n== Masked Text (partial) ==\n", masked)


if __name__ == "__main__":
    _demo()