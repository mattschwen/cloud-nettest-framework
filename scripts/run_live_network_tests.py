#!/usr/bin/env python3
"""Run LIVE network diagnostics from ALL 3 AWS EC2 instances."""

import subprocess
import sys
from pathlib import Path
from time import sleep

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.tree import Tree

console = Console()

# EC2 instances configuration
PROBES = [
    {
        "name": "us-east-1 (Virginia)",
        "instance": "i-08b98d43fd53b67e4",
        "ip": "54.87.147.228",
        "key": "~/.ssh/oracle-test-key",
        "user": "ec2-user",
        "target_ip": "134.70.24.1",
        "target_name": "Oracle Ashburn",
        "color": "bright_cyan"
    },
    {
        "name": "us-west-1 (California)",
        "instance": "i-035a2165f45edc09c",
        "ip": "3.101.64.113",
        "key": "~/.ssh/network-testing-key-west.pem",
        "user": "ubuntu",
        "target_ip": "134.70.124.2",
        "target_name": "Oracle San Jose",
        "color": "bright_green"
    },
    {
        "name": "us-east-2 (Ohio)",
        "instance": "i-0dfc6bdd6a24ca82e",
        "ip": "18.222.238.187",
        "key": "~/.ssh/network-testing-key-east2.pem",
        "user": "ubuntu",
        "target_ip": "134.70.24.1",
        "target_name": "Oracle Ashburn",
        "color": "bright_yellow"
    }
]


def run_ssh_command(probe, command):
    """Execute command via SSH on probe."""
    ssh_cmd = [
        "ssh",
        "-i", probe["key"],
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        f"{probe['user']}@{probe['ip']}",
        command
    ]

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def parse_ping_results(output):
    """Parse ping output for stats."""
    import re

    stats = {
        "packets_sent": 0,
        "packets_received": 0,
        "loss_pct": 100.0,
        "min": 0.0,
        "avg": 0.0,
        "max": 0.0,
        "mdev": 0.0
    }

    # Parse transmitted/received
    match = re.search(r'(\d+) packets transmitted, (\d+).*received', output)
    if match:
        stats["packets_sent"] = int(match.group(1))
        stats["packets_received"] = int(match.group(2))
        if stats["packets_sent"] > 0:
            stats["loss_pct"] = ((stats["packets_sent"] - stats["packets_received"]) / stats["packets_sent"]) * 100

    # Parse rtt
    match = re.search(r'rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', output)
    if match:
        stats["min"] = float(match.group(1))
        stats["avg"] = float(match.group(2))
        stats["max"] = float(match.group(3))
        stats["mdev"] = float(match.group(4))

    return stats


def grade_latency(latency_ms):
    """Grade latency performance."""
    if latency_ms < 2:
        return "A+", "🥇", "bright_green"
    elif latency_ms < 20:
        return "A", "🥈", "green"
    elif latency_ms < 50:
        return "B", "🥉", "yellow"
    elif latency_ms < 100:
        return "C", "⚠️", "orange3"
    else:
        return "D", "❌", "red"


def main():
    """Run live network tests from all probes."""

    # Header
    console.print()
    header = Panel(
        Text("🌐 LIVE NETWORK DIAGNOSTICS FROM ALL AWS EC2 INSTANCES", style="bold bright_cyan", justify="center"),
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(1, 2)
    )
    console.print(header)
    console.print()

    # Show probe inventory
    probe_tree = Tree("📍 [bold]Testing Probes[/bold]")
    for probe in PROBES:
        branch = probe_tree.add(f"[{probe['color']}]{probe['name']}[/{probe['color']}]")
        branch.add(f"Instance: {probe['instance']}")
        branch.add(f"IP: {probe['ip']}")
        branch.add(f"Target: {probe['target_name']} ({probe['target_ip']})")

    console.print(Panel(probe_tree, border_style="blue", box=box.ROUNDED))
    console.print()

    # Results storage
    results = []

    # Run tests with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        main_task = progress.add_task("[cyan]Running tests from all probes...", total=len(PROBES))

        for probe in PROBES:
            progress.update(main_task, description=f"[{probe['color']}]Testing from {probe['name']}...")

            probe_results = {
                "probe": probe,
                "ping": None,
                "http": None,
                "status": "testing"
            }

            # Test 1: Ping
            progress.update(main_task, description=f"[{probe['color']}]{probe['name']}: Running ping test...")
            success, stdout, stderr = run_ssh_command(
                probe,
                f"ping -c 20 -W 2 {probe['target_ip']}"
            )

            if success:
                probe_results["ping"] = parse_ping_results(stdout)
                probe_results["ping"]["raw"] = stdout

            # Test 2: HTTP timing
            progress.update(main_task, description=f"[{probe['color']}]{probe['name']}: Running HTTP test...")

            if "us-ashburn" in probe["target_name"].lower():
                url = "https://objectstorage.us-ashburn-1.oraclecloud.com"
            else:
                url = "https://objectstorage.us-sanjose-1.oraclecloud.com"

            success, stdout, stderr = run_ssh_command(
                probe,
                f'curl -w "DNS:%{{time_namelookup}}|TCP:%{{time_connect}}|TLS:%{{time_appconnect}}|TTFB:%{{time_starttransfer}}|Total:%{{time_total}}\\n" -o /dev/null -s {url}'
            )

            if success and stdout:
                probe_results["http"] = {}
                for part in stdout.strip().split('|'):
                    if ':' in part:
                        key, val = part.split(':')
                        probe_results["http"][key.lower()] = float(val) * 1000  # Convert to ms

            probe_results["status"] = "complete"
            results.append(probe_results)

            progress.update(main_task, advance=1)
            sleep(0.5)

    console.print()

    # Display results
    console.print("[bold bright_cyan]═══════════════════════════════════════════════════════════════[/bold bright_cyan]")
    console.print("[bold bright_yellow]                         TEST RESULTS                          [/bold bright_yellow]")
    console.print("[bold bright_cyan]═══════════════════════════════════════════════════════════════[/bold bright_cyan]")
    console.print()

    # Create results table
    results_table = Table(
        title="🎯 Network Performance Summary",
        box=box.HEAVY,
        show_header=True,
        header_style="bold bright_magenta"
    )

    results_table.add_column("Probe", style="cyan", no_wrap=True)
    results_table.add_column("Target", style="white")
    results_table.add_column("Latency", justify="right", style="bold bright_green")
    results_table.add_column("Loss", justify="center", style="white")
    results_table.add_column("HTTP Total", justify="right", style="bright_blue")
    results_table.add_column("Grade", justify="center", style="bold")

    for result in results:
        probe = result["probe"]
        ping = result.get("ping")
        http = result.get("http")

        # Ping stats
        if ping:
            latency = f"{ping['avg']:.2f}ms"
            loss = f"{ping['loss_pct']:.1f}%"
            loss_color = "green" if ping['loss_pct'] == 0 else "red"
            loss_str = f"[{loss_color}]{loss}[/{loss_color}]"

            grade, emoji, color = grade_latency(ping['avg'])
            grade_str = f"[{color}]{grade} {emoji}[/{color}]"
        else:
            latency = "N/A"
            loss_str = "N/A"
            grade_str = "❌"

        # HTTP stats
        if http:
            http_total = f"{http.get('total', 0):.1f}ms"
        else:
            http_total = "N/A"

        results_table.add_row(
            f"[{probe['color']}]{probe['name']}[/{probe['color']}]",
            probe['target_name'],
            latency,
            loss_str,
            http_total,
            grade_str
        )

    console.print(results_table)
    console.print()

    # Detailed breakdown for each probe
    for result in results:
        probe = result["probe"]
        ping = result.get("ping")
        http = result.get("http")

        if not ping and not http:
            continue

        console.print(f"\n[{probe['color']}]╔═══ {probe['name']} → {probe['target_name']} ═══╗[/{probe['color']}]")

        # Ping details
        if ping:
            ping_table = Table.grid(padding=(0, 2))
            ping_table.add_column(style="bold cyan", justify="right")
            ping_table.add_column(style="white")

            ping_table.add_row("📡 ICMP Ping:", "")
            ping_table.add_row("  Packets:", f"{ping['packets_received']}/{ping['packets_sent']}")
            ping_table.add_row("  Loss:", f"{ping['loss_pct']:.1f}%")
            ping_table.add_row("  Min:", f"{ping['min']:.2f}ms")
            ping_table.add_row("  Avg:", f"[bold bright_green]{ping['avg']:.2f}ms[/bold bright_green]")
            ping_table.add_row("  Max:", f"{ping['max']:.2f}ms")
            ping_table.add_row("  Jitter:", f"{ping['mdev']:.2f}ms")

            console.print(ping_table)

        # HTTP details
        if http:
            console.print()
            http_table = Table.grid(padding=(0, 2))
            http_table.add_column(style="bold cyan", justify="right")
            http_table.add_column(style="white")

            http_table.add_row("🌐 HTTP GET:", "")
            http_table.add_row("  DNS Lookup:", f"{http.get('dns', 0):.2f}ms")
            http_table.add_row("  TCP Handshake:", f"{http.get('tcp', 0):.2f}ms")
            http_table.add_row("  TLS Handshake:", f"{http.get('tls', 0):.2f}ms")
            http_table.add_row("  TTFB:", f"{http.get('ttfb', 0):.2f}ms")
            http_table.add_row("  Total:", f"[bold bright_blue]{http.get('total', 0):.2f}ms[/bold bright_blue]")

            console.print(http_table)

        console.print(f"[{probe['color']}]╚{'═' * 50}╝[/{probe['color']}]")

    # Summary
    console.print()
    console.print("[bold bright_cyan]═══════════════════════════════════════════════════════════════[/bold bright_cyan]")
    console.print()

    # Calculate overall stats
    total_tests = len([r for r in results if r.get("ping")])
    avg_latency = sum([r["ping"]["avg"] for r in results if r.get("ping")]) / total_tests if total_tests > 0 else 0
    zero_loss = sum([1 for r in results if r.get("ping") and r["ping"]["loss_pct"] == 0])

    summary_panel = Panel(
        f"[bold bright_green]✅ TESTS COMPLETE![/bold bright_green]\n\n"
        f"Probes Tested: [bold]{len(PROBES)}[/bold]\n"
        f"Successful Tests: [bold bright_green]{total_tests}[/bold bright_green]\n"
        f"Zero Packet Loss: [bold bright_green]{zero_loss}/{total_tests}[/bold bright_green]\n"
        f"Avg Latency: [bold bright_blue]{avg_latency:.2f}ms[/bold bright_blue]\n\n"
        f"[dim]All tests executed on remote AWS EC2 instances[/dim]",
        title="📊 Summary",
        border_style="bright_green",
        box=box.DOUBLE,
        padding=(1, 2)
    )

    console.print(summary_panel)
    console.print()


if __name__ == "__main__":
    main()
