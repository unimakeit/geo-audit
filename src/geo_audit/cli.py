"""CLI interface for geo-audit."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from . import __version__
from .models import Severity, AuditResult
from .auditor import audit_url, normalize_url, DEFAULT_HEADERS


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
    console.print(f"[dim]geo-audit v{__version__} • https://github.com/unimakeit/geo-audit[/dim]")
    console.print()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__)
def cli(ctx):
    """GEO Audit - Instant Generative Engine Optimization audit.
    
    \b
    Quick start:
        geo-audit scan example.com
        geo-audit fix example.com
    
    \b
    Commands:
        scan    Audit a URL for GEO optimization
        fix     Generate llms.txt and JSON-LD schema
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("url")
@click.option("-v", "--verbose", is_flag=True, help="Show all findings, not just issues")
@click.option("-t", "--timeout", default=30.0, help="Request timeout in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def scan(url: str, verbose: bool, timeout: float, json_output: bool):
    """Audit a URL for GEO optimization.
    
    \b
    Examples:
        geo-audit scan stripe.com
        geo-audit scan example.com --verbose
        geo-audit scan example.com --json
    """
    with console.status(f"[bold blue]Scanning {url}...[/bold blue]"):
        result = audit_url(url, timeout=timeout)
    
    if json_output:
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


@cli.command()
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory (default: current dir)")
@click.option("--llms-txt/--no-llms-txt", default=True, help="Generate llms.txt")
@click.option("--schema/--no-schema", default=True, help="Generate JSON-LD schema")
@click.option("--schema-type", type=click.Choice(["Organization", "WebSite", "FAQPage", "all"]), 
              default="all", help="Schema type to generate")
@click.option("--print-only", is_flag=True, help="Print to stdout instead of saving files")
@click.option("-t", "--timeout", default=30.0, help="Request timeout in seconds")
def fix(url: str, output: str | None, llms_txt: bool, schema: bool, schema_type: str, 
        print_only: bool, timeout: float):
    """Generate GEO optimization files for a URL.
    
    \b
    Examples:
        geo-audit fix example.com
        geo-audit fix example.com --print-only
        geo-audit fix example.com -o ./output
        geo-audit fix example.com --schema-type Organization
    """
    import httpx
    from bs4 import BeautifulSoup
    
    from .generators import generate_llms_txt, generate_schema
    from .generators.schema import generate_all_schemas, schema_to_html
    
    url = normalize_url(url)
    
    with console.status(f"[bold blue]Fetching {url}...[/bold blue]"):
        try:
            with httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                final_url = str(response.url)
        except Exception as e:
            console.print(f"[red]Error fetching URL:[/red] {e}")
            return
    
    parsed = urlparse(final_url)
    domain = parsed.netloc.replace("www.", "")
    
    console.print()
    console.print(Panel(
        f"[bold]{final_url}[/bold]",
        title="🔧 GEO Fix",
        border_style="green"
    ))
    
    # Prepare output directory
    if not print_only:
        output_dir = Path(output) if output else Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)
    
    generated_files = []
    
    # Generate llms.txt
    if llms_txt:
        llms_content = generate_llms_txt(soup, final_url)
        
        if print_only:
            console.print("\n[bold cyan]━━━ llms.txt ━━━[/bold cyan]\n")
            console.print(llms_content)
        else:
            llms_path = output_dir / "llms.txt"
            llms_path.write_text(llms_content)
            generated_files.append(("llms.txt", llms_path))
            console.print(f"\n[green]✓[/green] Generated [cyan]llms.txt[/cyan]")
    
    # Generate schema
    if schema:
        if schema_type == "all":
            schemas = generate_all_schemas(soup, final_url)
        else:
            schemas = [generate_schema(soup, final_url, schema_type)]
        
        for s in schemas:
            s_type = s.get("@type", "Schema")
            
            if print_only:
                console.print(f"\n[bold cyan]━━━ {s_type} Schema (JSON-LD) ━━━[/bold cyan]\n")
                console.print(json.dumps(s, indent=2))
                console.print(f"\n[bold cyan]━━━ HTML Embed ━━━[/bold cyan]\n")
                console.print(schema_to_html(s))
            else:
                # Save JSON
                json_filename = f"schema-{s_type.lower()}.json"
                json_path = output_dir / json_filename
                json_path.write_text(json.dumps(s, indent=2))
                generated_files.append((json_filename, json_path))
                
                # Save HTML snippet
                html_filename = f"schema-{s_type.lower()}.html"
                html_path = output_dir / html_filename
                html_path.write_text(schema_to_html(s))
                generated_files.append((html_filename, html_path))
                
                console.print(f"[green]✓[/green] Generated [cyan]{json_filename}[/cyan] + [cyan]{html_filename}[/cyan]")
    
    if not print_only and generated_files:
        console.print(f"\n[bold]Files saved to:[/bold] {output_dir.absolute()}")
        console.print()
        
        # Show next steps
        console.print("[bold]📋 Next Steps:[/bold]\n")
        console.print("  1. Review and customize the generated files")
        console.print("  2. Upload [cyan]llms.txt[/cyan] to your site root (e.g., example.com/llms.txt)")
        console.print("  3. Add the schema HTML to your page's [cyan]<head>[/cyan] section")
        console.print("  4. Re-run [cyan]geo-audit scan[/cyan] to verify your score improved")
        console.print()
    
    # Footer
    console.print("[dim]─" * 50 + "[/dim]")
    console.print(f"[dim]geo-audit v{__version__}[/dim]")
    console.print()


@cli.command()
@click.argument("brand")
@click.option("--industry", "-i", help="Industry for context (e.g., 'cloud hosting', 'AI tools')")
@click.option("--product", "-p", help="Specific product name to test")
@click.option("--provider", "-P", multiple=True, 
              type=click.Choice(["openai", "anthropic", "google", "perplexity"]),
              help="Specific provider(s) to test (default: all configured)")
@click.option("--verbose", "-v", is_flag=True, help="Show full responses")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def test(brand: str, industry: str | None, product: str | None, 
         provider: tuple[str, ...], verbose: bool, json_output: bool):
    """Test if LLMs know about your brand.
    
    \b
    Examples:
        geo-audit test "Stripe"
        geo-audit test "Vercel" --industry "cloud hosting"
        geo-audit test "Anthropic" --product "Claude"
        geo-audit test "OpenAI" --provider openai --provider google
    
    \b
    Required API keys (set as environment variables):
        OPENAI_API_KEY     - For ChatGPT
        ANTHROPIC_API_KEY  - For Claude  
        GOOGLE_API_KEY     - For Gemini
        PERPLEXITY_API_KEY - For Perplexity
    """
    from .tester import test_brand_visibility
    from .tester.providers import (
        get_configured_providers, get_all_providers,
        OpenAIProvider, AnthropicProvider, GoogleProvider, PerplexityProvider
    )
    
    # Get providers
    if provider:
        provider_map = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "google": GoogleProvider(),
            "perplexity": PerplexityProvider(),
        }
        providers = [provider_map[p] for p in provider]
    else:
        providers = get_configured_providers()
    
    if not providers:
        all_providers = get_all_providers()
        console.print("\n[yellow]⚠ No LLM providers configured![/yellow]\n")
        console.print("Set at least one API key:\n")
        for p in all_providers:
            key_name = f"{p.name.upper()}_API_KEY"
            if p.name == "Google":
                key_name = "GOOGLE_API_KEY or GEMINI_API_KEY"
            console.print(f"  export {key_name}=your-key-here")
        console.print()
        return
    
    # Show what we're testing
    console.print()
    console.print(Panel(
        f"[bold]{brand}[/bold]" + 
        (f"\n[dim]Industry: {industry}[/dim]" if industry else "") +
        (f"\n[dim]Product: {product}[/dim]" if product else ""),
        title="🧪 LLM Visibility Test",
        border_style="magenta"
    ))
    
    console.print(f"\n[dim]Testing with: {', '.join(p.name for p in providers)}[/dim]\n")
    
    # Run tests
    with console.status("[bold magenta]Querying LLMs...[/bold magenta]"):
        result = test_brand_visibility(
            brand=brand,
            industry=industry,
            product=product,
            providers=providers,
            parallel=True
        )
    
    if json_output:
        output = {
            "brand": result.brand,
            "industry": result.industry,
            "overall_visibility": round(result.overall_visibility, 1),
            "providers_tested": result.providers_tested,
            "results": [
                {
                    "provider": r.provider,
                    "model": r.model,
                    "mention_rate": round(r.mention_rate, 1),
                    "avg_latency_ms": r.avg_latency_ms,
                    "responses": [
                        {
                            "prompt": resp.prompt,
                            "mentions_brand": resp.mentions_brand,
                            "mention_context": resp.mention_context,
                            "error": resp.error,
                        }
                        for resp in r.responses
                    ]
                }
                for r in result.llm_results
            ]
        }
        click.echo(json.dumps(output, indent=2))
        return
    
    # Show overall visibility score
    visibility = result.overall_visibility
    vis_color = score_color(int(visibility))
    
    console.print(f"  Overall Visibility: ", end="")
    console.print(print_score_bar(int(visibility), width=25))
    console.print()
    
    # Results table
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="dim")
    table.add_column("Mention Rate", justify="right")
    table.add_column("Latency", justify="right")
    table.add_column("Status")
    
    for llm_result in result.llm_results:
        if llm_result.error_count == len(llm_result.responses):
            # All errors
            status = f"[red]{llm_result.responses[0].error if llm_result.responses else 'No responses'}[/red]"
            table.add_row(
                llm_result.provider,
                llm_result.model,
                "-",
                "-",
                status
            )
        else:
            rate = llm_result.mention_rate
            rate_color = "green" if rate >= 60 else "yellow" if rate >= 30 else "red"
            mentions = sum(1 for r in llm_result.responses if r.mentions_brand)
            total = len(llm_result.responses)
            
            table.add_row(
                llm_result.provider,
                llm_result.model,
                f"[{rate_color}]{rate:.0f}%[/] ({mentions}/{total})",
                f"{llm_result.avg_latency_ms}ms",
                "[green]OK[/green]"
            )
    
    console.print(table)
    
    # Show mention contexts
    console.print("\n[bold]Mentions Found:[/bold]\n")
    
    any_mentions = False
    for llm_result in result.llm_results:
        for resp in llm_result.responses:
            if resp.mentions_brand and resp.mention_context:
                any_mentions = True
                console.print(f"  [cyan]{llm_result.provider}[/cyan] → [dim]{resp.prompt[:50]}...[/dim]")
                console.print(f"    [green]\"{resp.mention_context}\"[/green]")
                console.print()
    
    if not any_mentions:
        console.print("  [yellow]No direct brand mentions found in LLM responses.[/yellow]")
        console.print("  [dim]This may indicate low brand visibility in AI systems.[/dim]")
        console.print()
    
    # Verbose: show full responses
    if verbose:
        console.print("\n[bold]Full Responses:[/bold]\n")
        for llm_result in result.llm_results:
            console.print(f"[bold cyan]━━━ {llm_result.provider} ({llm_result.model}) ━━━[/bold cyan]\n")
            for resp in llm_result.responses:
                if resp.error:
                    console.print(f"[red]Error: {resp.error}[/red]\n")
                else:
                    console.print(f"[dim]Q: {resp.prompt}[/dim]\n")
                    console.print(resp.response[:500] + ("..." if len(resp.response) > 500 else ""))
                    mention_icon = "✓" if resp.mentions_brand else "✗"
                    mention_color = "green" if resp.mentions_brand else "red"
                    console.print(f"\n[{mention_color}]{mention_icon} Mentions {brand}[/]")
                    console.print()
    
    # Recommendations
    if result.overall_visibility < 50:
        console.print("[bold]💡 Recommendations:[/bold]\n")
        console.print("  1. Run [cyan]geo-audit fix[/cyan] to generate llms.txt and schema")
        console.print("  2. Ensure your brand has a Wikipedia page or strong web presence")
        console.print("  3. Get mentioned in authoritative sources LLMs are trained on")
        console.print("  4. Use structured data to help LLMs understand your brand")
        console.print()
    
    # Footer
    console.print("[dim]─" * 50 + "[/dim]")
    console.print(f"[dim]geo-audit v{__version__}[/dim]")
    console.print()


# Convenience: allow `geo-audit URL` as shortcut for `geo-audit scan URL`
def main():
    """Entry point that handles both `geo-audit URL` and `geo-audit scan URL`."""
    args = sys.argv[1:]
    
    # If first arg looks like a URL (not a command), insert 'scan'
    if args and not args[0].startswith('-') and args[0] not in ['scan', 'fix', 'test', 'version', '--help', '--version']:
        # Check if it looks like a URL/domain
        if '.' in args[0] or args[0] == 'localhost':
            sys.argv.insert(1, 'scan')
    
    cli()


if __name__ == "__main__":
    main()
