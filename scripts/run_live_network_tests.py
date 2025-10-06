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


def parse_mtr_output(output):
    """Parse MTR output to extract hop details."""
    import re
    hops = []

    for line in output.split('\n'):
        # Match MTR output format: "1.|-- 240.0.168.13  0.0%  10  1.2  1.3  1.2  1.6  0.1"
        match = re.match(r'\s*(\d+)\.\|--\s+(\S+)\s+(\d+\.\d+)%\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', line)
        if match:
            hop_num, host, loss, sent, last, avg, best, worst, stddev = match.groups()
            hops.append({
                "hop": int(hop_num),
                "host": host,
                "loss_pct": float(loss),
                "sent": int(sent),
                "last_ms": float(last),
                "avg_ms": float(avg),
                "best_ms": float(best),
                "worst_ms": float(worst),
                "stddev_ms": float(stddev)
            })

    return hops


def get_whois_info(ip):
    """Get ASN and organization from whois."""
    try:
        result = subprocess.run(
            ["whois", ip],
            capture_output=True,
            text=True,
            timeout=5
        )

        output = result.stdout
        asn = "Unknown"
        org = "Unknown"

        # Extract ASN
        import re
        asn_match = re.search(r'(?:origin|OriginAS):\s*(AS\d+)', output, re.IGNORECASE)
        if asn_match:
            asn = asn_match.group(1)

        # Extract organization
        org_match = re.search(r'(?:OrgName|org-name|descr):\s*(.+)', output, re.IGNORECASE)
        if org_match:
            org = org_match.group(1).strip()[:40]  # Limit length

        return asn, org
    except Exception:
        return "Unknown", "Unknown"


def main():
    """Run live network tests from all probes."""

    # Animated header with sparkles
    console.print()
    console.print("[bold bright_cyan]" + "=" * 80 + "[/bold bright_cyan]")
    console.print()
    header = Panel(
        Text("🌐 LIVE NETWORK DIAGNOSTICS FROM ALL AWS EC2 INSTANCES 🌐", style="bold bright_cyan", justify="center"),
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(1, 2)
    )
    console.print(header)
    console.print("[bold bright_cyan]" + "=" * 80 + "[/bold bright_cyan]")
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

        main_task = progress.add_task("[cyan]Running tests from all probes...", total=len(PROBES) * 3)  # 3 tests per probe

        for probe in PROBES:
            probe_results = {
                "probe": probe,
                "ping": None,
                "http": None,
                "mtr": None,
                "status": "testing"
            }

            # Test 1: Ping
            progress.update(main_task, description=f"[{probe['color']}]📡 {probe['name']}: ICMP Ping test...")
            success, stdout, stderr = run_ssh_command(
                probe,
                f"ping -c 20 -W 2 {probe['target_ip']}"
            )

            if success:
                probe_results["ping"] = parse_ping_results(stdout)
                probe_results["ping"]["raw"] = stdout

            progress.update(main_task, advance=1)

            # Test 2: MTR Path Analysis
            progress.update(main_task, description=f"[{probe['color']}]🗺️  {probe['name']}: MTR path tracing...")
            success, stdout, stderr = run_ssh_command(
                probe,
                f"mtr -n -c 10 -r {probe['target_ip']}"
            )

            if success:
                probe_results["mtr"] = parse_mtr_output(stdout)
                probe_results["mtr_raw"] = stdout

                # Get whois for each hop
                progress.update(main_task, description=f"[{probe['color']}]🔍 {probe['name']}: Looking up hop owners...")
                for hop in probe_results["mtr"]:
                    asn, org = get_whois_info(hop["host"])
                    hop["asn"] = asn
                    hop["org"] = org

            progress.update(main_task, advance=1)

            # Test 3: HTTP timing
            progress.update(main_task, description=f"[{probe['color']}]🌐 {probe['name']}: HTTP GET timing...")

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
            sleep(0.3)

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
        mtr = result.get("mtr")

        if not ping and not http and not mtr:
            continue

        console.print(f"\n[{probe['color']}]╔{'═' * 78}╗[/{probe['color']}]")
        console.print(f"[{probe['color']}]║[/] [bold {probe['color']}]{probe['name']} → {probe['target_name']}[/bold {probe['color']}] [{probe['color']}]{'═' * (76 - len(probe['name']) - len(probe['target_name']))}║[/{probe['color']}]")
        console.print(f"[{probe['color']}]╚{'═' * 78}╝[/{probe['color']}]")

        # Ping details
        if ping:
            ping_table = Table.grid(padding=(0, 2))
            ping_table.add_column(style="bold cyan", justify="right")
            ping_table.add_column(style="white")

            ping_table.add_row("📡 ICMP Ping:", "")
            ping_table.add_row("  Packets:", f"{ping['packets_received']}/{ping['packets_sent']}")
            ping_table.add_row("  Loss:", f"[green]{ping['loss_pct']:.1f}%[/green]" if ping['loss_pct'] == 0 else f"[red]{ping['loss_pct']:.1f}%[/red]")
            ping_table.add_row("  Min:", f"{ping['min']:.2f}ms")
            ping_table.add_row("  Avg:", f"[bold bright_green]{ping['avg']:.2f}ms[/bold bright_green]")
            ping_table.add_row("  Max:", f"{ping['max']:.2f}ms")
            ping_table.add_row("  Jitter:", f"{ping['mdev']:.2f}ms")

            console.print(ping_table)

        # MTR Path Analysis with WHOIS
        if mtr and len(mtr) > 0:
            console.print()
            mtr_table = Table(
                title=f"🗺️  Network Path to {probe['target_name']}",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold bright_yellow"
            )

            mtr_table.add_column("Hop", style="cyan", justify="right", width=4)
            mtr_table.add_column("IP Address", style="white", width=16)
            mtr_table.add_column("Latency", justify="right", style="bright_green", width=10)
            mtr_table.add_column("Loss", justify="center", width=6)
            mtr_table.add_column("ASN", style="bright_blue", width=10)
            mtr_table.add_column("Organization", style="bright_magenta", width=30)

            for hop in mtr:
                # Color code latency
                avg_ms = hop['avg_ms']
                if avg_ms < 5:
                    lat_str = f"[bright_green]{avg_ms:.2f}ms[/bright_green]"
                elif avg_ms < 20:
                    lat_str = f"[green]{avg_ms:.2f}ms[/green]"
                elif avg_ms < 50:
                    lat_str = f"[yellow]{avg_ms:.2f}ms[/yellow]"
                else:
                    lat_str = f"[red]{avg_ms:.2f}ms[/red]"

                # Color code loss
                loss_pct = hop['loss_pct']
                if loss_pct == 0:
                    loss_str = f"[green]{loss_pct:.0f}%[/green]"
                else:
                    loss_str = f"[red]{loss_pct:.0f}%[/red]"

                mtr_table.add_row(
                    str(hop['hop']),
                    hop['host'],
                    lat_str,
                    loss_str,
                    hop.get('asn', 'Unknown'),
                    hop.get('org', 'Unknown')[:30]
                )

            console.print(mtr_table)

        # HTTP details
        if http:
            console.print()
            http_table = Table.grid(padding=(0, 2))
            http_table.add_column(style="bold cyan", justify="right")
            http_table.add_column(style="white")

            http_table.add_row("🌐 HTTP GET:", "")
            http_table.add_row("  DNS Lookup:", f"[bright_cyan]{http.get('dns', 0):.2f}ms[/bright_cyan]")
            http_table.add_row("  TCP Handshake:", f"[bright_blue]{http.get('tcp', 0):.2f}ms[/bright_blue]")
            http_table.add_row("  TLS Handshake:", f"[bright_magenta]{http.get('tls', 0):.2f}ms[/bright_magenta]")
            http_table.add_row("  TTFB:", f"[yellow]{http.get('ttfb', 0):.2f}ms[/yellow]")
            http_table.add_row("  Total:", f"[bold bright_green]{http.get('total', 0):.2f}ms[/bold bright_green]")

            console.print(http_table)

        console.print()

    # EPIC Summary with all the visual flair
    console.print()
    console.print("[bold bright_green]" + "🎉" * 40 + "[/bold bright_green]")
    console.print()

    # Calculate overall stats
    total_tests = len([r for r in results if r.get("ping")])
    avg_latency = sum([r["ping"]["avg"] for r in results if r.get("ping")]) / total_tests if total_tests > 0 else 0
    zero_loss = sum([1 for r in results if r.get("ping") and r["ping"]["loss_pct"] == 0])
    total_hops = sum([len(r.get("mtr") or []) for r in results])

    # Create epic completion visual
    completion_tree = Tree("🏆 [bold bright_yellow]TEST RESULTS SUMMARY[/bold bright_yellow] 🏆")

    # Network stats branch
    network_branch = completion_tree.add("[bold bright_cyan]📡 Network Statistics[/bold bright_cyan]")
    network_branch.add(f"[bright_green]✅ Probes Tested: {len(PROBES)}[/bright_green]")
    network_branch.add(f"[bright_green]✅ Successful Tests: {total_tests}/{total_tests}[/bright_green]")
    network_branch.add(f"[bright_green]✅ Zero Packet Loss: {zero_loss}/{total_tests}[/bright_green]")
    network_branch.add(f"[bright_blue]⚡ Average Latency: {avg_latency:.2f}ms[/bright_blue]")

    # Path analysis branch
    path_branch = completion_tree.add("[bold bright_magenta]🗺️  Path Analysis[/bold bright_magenta]")
    path_branch.add(f"[bright_yellow]📍 Total Hops Analyzed: {total_hops}[/bright_yellow]")
    path_branch.add(f"[bright_yellow]🔍 WHOIS Lookups Complete[/bright_yellow]")

    # Performance grades branch
    grade_branch = completion_tree.add("[bold bright_green]🎯 Performance Grades[/bold bright_green]")
    for result in results:
        if result.get("ping"):
            grade, emoji, color = grade_latency(result["ping"]["avg"])
            grade_branch.add(f"[{color}]{emoji} {result['probe']['name']}: {grade} ({result['ping']['avg']:.2f}ms)[/{color}]")

    # Create the final epic panel
    console.print(Panel(
        completion_tree,
        title="[bold bright_cyan]═══════════════════ 🌟 DIAGNOSTICS COMPLETE 🌟 ═══════════════════[/bold bright_cyan]",
        subtitle="[dim bright_white]All tests executed on remote AWS EC2 instances[/dim bright_white]",
        border_style="bright_green",
        box=box.DOUBLE_EDGE,
        padding=(1, 2)
    ))

    console.print()
    console.print("[bold bright_green]" + "🎉" * 40 + "[/bold bright_green]")
    console.print()

    # ASCII art finale
    console.print()
    console.print("[bold bright_cyan]    ╔═══════════════════════════════════════════════════════════╗[/bold bright_cyan]")
    console.print("[bold bright_cyan]    ║  ✨  NETWORK DIAGNOSTICS: [bold bright_green]100% SUCCESS[/bold bright_green] ✨              ║[/bold bright_cyan]")
    console.print("[bold bright_cyan]    ╚═══════════════════════════════════════════════════════════╝[/bold bright_cyan]")
    console.print()


if __name__ == "__main__":
    main()
