"""Check content structure for GEO optimization."""

import re
from collections import Counter

from bs4 import BeautifulSoup, Tag

from ..models import CheckResult, Finding, Severity


def check_content_structure(soup: BeautifulSoup, url: str) -> CheckResult:
    """Check content structure for LLM-friendliness.
    
    LLMs prefer:
    - Clear heading hierarchy
    - Lists (bulleted/numbered)
    - Tables for data
    - Short paragraphs
    - FAQ sections
    """
    findings: list[Finding] = []
    score = 0
    max_score = 20
    
    # Remove script, style, nav, footer, header for content analysis
    content_soup = BeautifulSoup(str(soup), "lxml")
    for tag in content_soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    
    # Check heading structure
    headings = {f"h{i}": content_soup.find_all(f"h{i}") for i in range(1, 7)}
    h1_count = len(headings["h1"])
    total_headings = sum(len(h) for h in headings.values())
    
    if h1_count == 0:
        findings.append(Finding(
            check="content_structure",
            message="No H1 heading found",
            severity=Severity.ERROR,
            details="H1 is the primary page topic signal for LLMs",
            fix_hint="Add one clear H1 heading that describes the page",
            impact=7
        ))
    elif h1_count > 1:
        findings.append(Finding(
            check="content_structure",
            message=f"Multiple H1 headings ({h1_count})",
            severity=Severity.WARNING,
            details="Multiple H1s can confuse LLMs about page topic",
            fix_hint="Use only one H1, use H2+ for subsections",
            impact=4
        ))
        score += 2
    else:
        score += 4
        findings.append(Finding(
            check="content_structure",
            message="Single H1 heading ✓",
            severity=Severity.PASS
        ))
    
    if total_headings >= 3:
        score += 2
        findings.append(Finding(
            check="content_structure",
            message=f"Good heading structure ({total_headings} headings)",
            severity=Severity.PASS
        ))
    elif total_headings > 0:
        findings.append(Finding(
            check="content_structure",
            message=f"Minimal heading structure ({total_headings} headings)",
            severity=Severity.INFO,
            details="More headings help LLMs understand content hierarchy",
            fix_hint="Break content into sections with H2/H3 headings",
            impact=3
        ))
    
    # Check for lists
    lists = content_soup.find_all(["ul", "ol"])
    list_items = content_soup.find_all("li")
    
    if len(lists) >= 2 and len(list_items) >= 5:
        score += 4
        findings.append(Finding(
            check="content_structure",
            message=f"Good list usage ({len(lists)} lists, {len(list_items)} items)",
            severity=Severity.PASS,
            details="LLMs favor structured lists for extraction"
        ))
    elif len(lists) >= 1:
        score += 2
        findings.append(Finding(
            check="content_structure",
            message=f"Some list usage ({len(lists)} lists)",
            severity=Severity.INFO,
            details="Lists make content easier for LLMs to quote",
            fix_hint="Convert appropriate content to bullet/numbered lists",
            impact=3
        ))
    else:
        findings.append(Finding(
            check="content_structure",
            message="No lists found",
            severity=Severity.INFO,
            details="Lists are LLM-friendly and easy to quote",
            fix_hint="Add bulleted lists for features, steps, or key points",
            impact=4
        ))
    
    # Check for tables
    tables = content_soup.find_all("table")
    if tables:
        # Check if tables have headers
        tables_with_headers = sum(1 for t in tables if t.find("th"))
        if tables_with_headers == len(tables):
            score += 3
            findings.append(Finding(
                check="content_structure",
                message=f"Tables with headers found ({len(tables)})",
                severity=Severity.PASS,
                details="Well-structured tables are easy for LLMs to parse"
            ))
        else:
            score += 1
            findings.append(Finding(
                check="content_structure",
                message="Tables found but some lack headers",
                severity=Severity.INFO,
                fix_hint="Add <th> header cells to tables",
                impact=2
            ))
    
    # Check for FAQ-like content
    faq_patterns = ["faq", "frequently asked", "questions", "q&a"]
    page_text = content_soup.get_text().lower()
    headings_text = " ".join(h.get_text().lower() for hs in headings.values() for h in hs)
    
    has_faq = any(p in headings_text for p in faq_patterns)
    if has_faq:
        score += 3
        findings.append(Finding(
            check="content_structure",
            message="FAQ section detected",
            severity=Severity.PASS,
            details="FAQs are highly quotable by LLMs"
        ))
    else:
        findings.append(Finding(
            check="content_structure",
            message="No FAQ section found",
            severity=Severity.INFO,
            details="FAQ sections are frequently cited by LLMs",
            fix_hint="Consider adding an FAQ section with common questions",
            impact=4
        ))
    
    # Check paragraph length (LLMs prefer shorter, clearer paragraphs)
    paragraphs = content_soup.find_all("p")
    if paragraphs:
        lengths = [len(p.get_text(strip=True).split()) for p in paragraphs]
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        long_paras = sum(1 for l in lengths if l > 100)
        
        if avg_length < 60 and long_paras == 0:
            score += 4
            findings.append(Finding(
                check="content_structure",
                message=f"Good paragraph length (avg {avg_length:.0f} words)",
                severity=Severity.PASS
            ))
        elif long_paras > 0:
            findings.append(Finding(
                check="content_structure",
                message=f"{long_paras} long paragraphs (>100 words)",
                severity=Severity.INFO,
                details="Long paragraphs are harder for LLMs to quote",
                fix_hint="Break long paragraphs into smaller chunks",
                impact=3
            ))
            score += 2
    
    return CheckResult(
        name="Content Structure",
        score=score,
        max_score=max_score,
        findings=findings
    )
