"""Data models for GEO audit results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity level for audit findings."""
    PASS = "pass"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Finding:
    """A single audit finding."""
    check: str
    message: str
    severity: Severity
    details: Optional[str] = None
    fix_hint: Optional[str] = None
    impact: int = 1  # 1-10 scale for prioritization


@dataclass
class CheckResult:
    """Result of a single check category."""
    name: str
    score: int  # 0-100
    max_score: int
    findings: list[Finding] = field(default_factory=list)
    
    @property
    def passed(self) -> bool:
        return self.score == self.max_score


@dataclass
class AuditResult:
    """Complete audit result for a URL."""
    url: str
    final_url: str  # After redirects
    checks: list[CheckResult] = field(default_factory=list)
    fetch_time_ms: int = 0
    error: Optional[str] = None
    
    @property
    def total_score(self) -> int:
        if not self.checks:
            return 0
        total = sum(c.score for c in self.checks)
        max_total = sum(c.max_score for c in self.checks)
        return int((total / max_total) * 100) if max_total > 0 else 0
    
    @property
    def quick_wins(self) -> list[Finding]:
        """Get top findings sorted by impact that can be fixed."""
        all_findings = []
        for check in self.checks:
            for finding in check.findings:
                if finding.severity in (Severity.ERROR, Severity.WARNING) and finding.fix_hint:
                    all_findings.append(finding)
        return sorted(all_findings, key=lambda f: f.impact, reverse=True)[:5]
