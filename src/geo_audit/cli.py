"""CLI interface for geo-audit."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from . import __version__
from .models import Severity, AuditResult
from .auditor import audit_url


console = Console()


def severity_style(severity: Severity) -> str:
    """Get Rich style for severity level."""
    return {
        Severity.PASS: "green",
        Severity.INFO: "blue",
        Severity.WARNING: "yellow",
        Severity.ERROR: "red",
    }.get(severity, "white")


def severity_icon(severity: Severity) -> str:
    """Get icon for severity level."""
    return {
        Severity.PASS: "✓",
        Severity.INFO: "ℹ",
        Severity.WARNING: "⚠",
        Severity.ERROR: "✗",
    }.get(severity, "•")


def score_color(score: int) -> str:
    """Get color for a score value."""
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    elif score >= 40:
        return "orange1"
    else:
        return "red"


def print_score_bar(score: int, width: int = 20) -> Text:
    """Create a visual score bar."""
    filled = int((score / 100) * width)
    empty = width - filled
    color = score_color(score)
    
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * empty, style="dim")
    bar.append(f" {score}/100", style=f"bold {color}")
    return bar


def print_result(result: AuditResult, verbose: bool = False) -> None:
    """Print audit result to console."""
    
    if result.error:
        console.print(f"\n[red]Error:[/red] {result.error}")
        return
    
    # Header
    console.print()
    console.print(Panel(
        f"[bold]{result.final_url}[/bold]\n"
        f"[dim]Fetched in {result.fetch_time_ms}ms[/dim]",
        title="🔍 GEO Audit",
        border_style="blue"
    ))
    
    # Overall score
    console.print()
    score = result.total_score
    console.print(f"  GEO Score: ", end="")
    console.print(print_score_bar(score, width=25))
    console.print()
    
    # Check results table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Check", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Status")
    
    for check in result.checks:
        pct = int((check.score / check.max_score) * 100) if check.max_score > 0 else 0
        status_parts = []
        
        errors = sum(1 for f in check.findings if f.severity == Severity.ERROR)
        warnings = sum(1 for f in check.findings if f.severity == Severity.WARNING)
        
        if errors > 0:
            status_parts.append(f"[red]{errors} error{'s' if errors > 1 else ''}[/red]")
        if warnings > 0:
            status_parts.append(f"[yellow]{warnings} warning{'s' if warnings > 1 else ''}[/yellow]")
        if not errors and not warnings:
            status_parts.append("[green]OK[/green]")
        
        table.add_row(
            check.name,
            f"[{score_color(pct)}]{check.score}/{check.max_score}[/]",
            ", ".join(status_parts)
        )
    
    console.print(table)
    
    # Findings (verbose mode shows all, otherwise just errors/warnings)
    if verbose:
        console.print("\n[bold]All Findings:[/bold]\n")
        for check in result.checks:
            for finding in check.findings:
                icon = severity_icon(finding.severity)
                style = severity_style(finding.severity)
                console.print(f"  [{style}]{icon}[/] {finding.message}")
                if finding.details:
                    console.print(f"    [dim]{finding.details}[/dim]")
                if finding.fix_hint:
                    console.print(f"    [cyan]→ {finding.fix_hint}[/cyan]")
    else:
        # Show just issues
        issues = []
        for check in result.checks:
            for finding in check.findings:
                if finding.severity in (Severity.ERROR, Severity.WARNING):
                    issues.append(finding)
        
        if issues:
            console.print("\n[bold]Issues Found:[/bold]\n")
            for finding in issues:
                icon = severity_icon(finding.severity)
                style = severity_style(finding.severity)
                console.print(f"  [{style}]{icon}[/] {finding.message}")
                if finding.fix_hint:
                    console.print(f"    [cyan]→ {finding.fix_hint}[/cyan]")
    
    # Quick wins
    quick_wins = result.quick_wins
    if quick_wins:
        console.print("\n[bold]🎯 Top Quick Wins:[/bold]\n")
        for i, finding in enumerate(quick_wins[:3], 1):
            console.print(f"  {i}. [bold]{finding.message}[/bold]")
            if finding.fix_hint:
                console.print(f"     [cyan]{finding.fix_hint}[/cyan]")
            console.print()
    
    # Footer
    console.print("[dim]─" * 50 + "[/dim]")
    console.print(f"[dim]geo-audit v{__version__} • https://github.com/huiren/geo-audit[/dim]")
    console.print()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__)
@click.argument("url", required=False)
@click.option("-v", "--verbose", is_flag=True, help="Show all findings, not just issues")
@click.option("-t", "--timeout", default=30.0, help="Request timeout in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def main(ctx, url: str | None, verbose: bool, timeout: float, json_output: bool):
    """GEO Audit - Instant Generative Engine Optimization audit.
    
    Run an audit:
    
        geo-audit example.com
        
    Show all findings:
    
        geo-audit example.com --verbose
    """
    if ctx.invoked_subcommand is None:
        if url:
            with console.status(f"[bold blue]Scanning {url}...[/bold blue]"):
                result = audit_url(url, timeout=timeout)
            
            if json_output:
                import json
                # Convert to dict for JSON output
                output = {
                    "url": result.url,
                    "final_url": result.final_url,
                    "score": result.total_score,
                    "fetch_time_ms": result.fetch_time_ms,
                    "error": result.error,
                    "checks": [
                        {
                            "name": c.name,
                            "score": c.score,
                            "max_score": c.max_score,
                            "findings": [
                                {
                                    "check": f.check,
                                    "message": f.message,
                                    "severity": f.severity.value,
                                    "details": f.details,
                                    "fix_hint": f.fix_hint,
                                    "impact": f.impact,
                                }
                                for f in c.findings
                            ]
                        }
                        for c in result.checks
                    ]
                }
                click.echo(json.dumps(output, indent=2))
            else:
                print_result(result, verbose=verbose)
        else:
            click.echo(ctx.get_help())


@main.command()
def version():
    """Show version information."""
    console.print(f"geo-audit v{__version__}")


if __name__ == "__main__":
    main()
