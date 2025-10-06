"""Command-line interface for Cloud NetTest Framework."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="cnf",
    help="Cloud NetTest Framework - Multi-cloud network testing for OCI Object Storage",
    add_completion=False,
)

console = Console()

# Registry subcommands
registry_app = typer.Typer(help="Host registry management")
app.add_typer(registry_app, name="registry")

# Test subcommands
test_app = typer.Typer(help="Network test execution")
app.add_typer(test_app, name="test")

# Report subcommands
report_app = typer.Typer(help="Test result reporting")
app.add_typer(report_app, name="report")


@app.command()
def version():
    """Show version information."""
    from cnf import __version__, __description__
    console.print(f"[bold cyan]Cloud NetTest Framework[/bold cyan] v{__version__}")
    console.print(__description__)


@registry_app.command("list")
def registry_list(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """List all registered probe hosts."""
    from cnf.registry import load_registry
    
    registry = load_registry()
    hosts = registry.hosts
    
    # Apply filters
    if provider:
        hosts = [h for h in hosts if h.provider == provider]
    if status:
        hosts = [h for h in hosts if h.status == status]
    
    table = Table(title="Registered Probe Hosts")
    table.add_column("ID", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Region", style="yellow")
    table.add_column("Public IP", style="blue")
    table.add_column("Status", style="magenta")
    
    for host in hosts:
        table.add_row(
            host.id,
            host.provider,
            host.region,
            host.public_ip or "N/A",
            host.status or "unknown"
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(hosts)} hosts[/dim]")


@registry_app.command("discover")
def registry_discover(
    providers: str = typer.Option("aws", "--providers", "-p", help="Comma-separated providers"),
    ssh_user: str = typer.Option("ubuntu", "--ssh-user", help="SSH username"),
    ssh_key: Path = typer.Option("~/.ssh/id_rsa", "--ssh-key", help="SSH private key path"),
    save: Optional[Path] = typer.Option(None, "--save", help="Save to inventory file"),
):
    """Discover and register probe hosts via SSH."""
    console.print("[yellow]Discovery functionality coming soon...[/yellow]")
    console.print(f"Providers: {providers}")
    console.print(f"SSH User: {ssh_user}")
    console.print(f"SSH Key: {ssh_key}")


@test_app.command("run")
def test_run(
    plan: Path = typer.Option(..., "--plan", "-p", help="Test plan YAML file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run without executing"),
):
    """Run network tests from a test plan."""
    from cnf.runner import run_test_plan
    
    if not plan.exists():
        console.print(f"[red]Error: Test plan not found: {plan}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Loading test plan: {plan}[/cyan]")
    
    if dry_run:
        console.print("[yellow]Dry run mode - no tests will be executed[/yellow]")
        return
    
    # Run async test plan
    try:
        asyncio.run(run_test_plan(plan, output))
    except Exception as e:
        console.print(f"[red]Error running tests: {e}[/red]")
        raise typer.Exit(1)


@test_app.command("smoke")
def test_smoke(
    host_id: Optional[str] = typer.Option(None, "--host", "-h", help="Specific host ID"),
    target: str = typer.Option("8.8.8.8", "--target", "-t", help="Test target"),
):
    """Run quick smoke tests against a target."""
    from cnf.registry import load_registry
    from cnf.tests.latency import ping_test
    
    console.print(f"[cyan]Running smoke test to {target}[/cyan]")
    
    registry = load_registry()
    hosts = [h for h in registry.hosts if h.id == host_id] if host_id else registry.hosts
    
    if not hosts:
        console.print("[red]No hosts found[/red]")
        raise typer.Exit(1)
    
    for host in hosts:
        console.print(f"\n[yellow]Testing from {host.id} ({host.public_ip})[/yellow]")
        # Simple local ping test (would normally SSH to probe)
        console.print("[dim]Smoke test functionality coming soon...[/dim]")


@report_app.command("summarize")
def report_summarize(
    run_dir: Path = typer.Argument(..., help="Run directory to summarize"),
    to: str = typer.Option("md", "--to", help="Output format (md,csv,json)"),
):
    """Generate summary report from test run."""
    if not run_dir.exists():
        console.print(f"[red]Error: Run directory not found: {run_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Summarizing results from: {run_dir}[/cyan]")
    console.print(f"[yellow]Report generation functionality coming soon...[/yellow]")


@report_app.command("view")
def report_view(
    run_dir: Optional[Path] = typer.Argument(None, help="Run directory to view (optional - shows live results if not provided)"),
):
    """View test results with beautiful formatting."""
    from cnf.formatter import NetworkTestFormatter
    from cnf.utils import load_json
    import sys
    import subprocess

    formatter = NetworkTestFormatter(console)

    if not run_dir:
        # Show live test results
        console.print("[cyan]Displaying live test results...[/cyan]\n")
        script_path = Path(__file__).parent.parent.parent / "scripts" / "view_results.py"
        subprocess.run([
            sys.executable,
            str(script_path)
        ])
        return

    if not run_dir.exists():
        console.print(f"[red]Error: Run directory not found: {run_dir}[/red]")
        raise typer.Exit(1)

    # Load results
    raw_results_file = run_dir / "raw_results.json"
    if not raw_results_file.exists():
        console.print(f"[red]Error: Results file not found: {raw_results_file}[/red]")
        raise typer.Exit(1)

    data = load_json(raw_results_file)
    results = data.get("results", [])
    plan = data.get("plan", {})

    # Display with beautiful formatting
    formatter.print_header(
        "Cloud NetTest Framework - Test Results",
        f"Results from: {run_dir.name}"
    )

    # Show results for each probe
    for result in results:
        probe_id = result.get("probe_id", "unknown")
        probe_region = result.get("region", "unknown")
        tests = result.get("tests", {})

        if "dns" in tests:
            formatter.print_dns_results(probe_id, tests["dns"])
            console.print()

        if "latency" in tests:
            formatter.print_latency_results(probe_id, probe_region, tests["latency"])
            console.print()

    console.print("[green]✅ Results displayed successfully[/green]")


if __name__ == "__main__":
    app()
