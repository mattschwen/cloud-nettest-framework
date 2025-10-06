#!/usr/bin/env python3
"""
Demonstrate layered network correlation (L3→L4→L7).

Shows how network layer issues affect transport and application performance.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cnf.registry import load_registry
from cnf.tests.comprehensive import comprehensive_target_test
from cnf.formatter import NetworkTestFormatter
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box


async def main():
    """Run layered correlation demo."""
    console = Console()
    formatter = NetworkTestFormatter(console)

    # Display intro
    intro = Panel(
        Text.from_markup(
            "[bold cyan]LAYERED NETWORK CORRELATION DEMO[/bold cyan]\n\n"
            "This demonstration shows how we correlate network diagnostics across layers:\n\n"
            "[yellow]Layer 3 (Network)[/yellow] - ICMP ping and MTR path analysis\n"
            "[yellow]Layer 4 (Transport)[/yellow] - TCP session quality and packet capture\n"
            "[yellow]Layer 7 (Application)[/yellow] - HTTP timing breakdown\n\n"
            "[green]Plus cross-layer correlations:[/green]\n"
            "• How network path affects TCP performance\n"
            "• Which TCP events occur during which HTTP phase\n"
            "• Where retransmissions impact application timing"
        ),
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(1, 2)
    )
    console.print(intro)
    console.print()

    # Load registry and select probe
    registry = load_registry()

    # Use us-west-1 → Oracle San Jose (optimal route)
    probe = None
    for host in registry.hosts:
        if "us-west-1" in host.region.lower():
            probe = host
            break

    if not probe:
        console.print("[red]❌ No us-west-1 probe found in registry[/red]")
        return 1

    console.print(f"[cyan]📡 Testing from:[/cyan] {probe.hostname} ({probe.public_ip})")
    console.print(f"[cyan]🎯 Target:[/cyan] Oracle San Jose Object Storage")
    console.print()

    # Target configuration
    target_config = {
        "ip": "134.70.124.2",
        "url": "https://objectstorage.us-sanjose-1.oraclecloud.com",
        "name": "Oracle San Jose"
    }

    console.print("[yellow]⏳ Running comprehensive diagnostics...[/yellow]")
    console.print("[dim]This includes: ICMP ping, MTR path trace, HTTP timing, TCP packet capture[/dim]")
    console.print()

    # Run comprehensive test
    result = await comprehensive_target_test(
        host=probe,
        target_ip=target_config["ip"],
        target_url=target_config["url"],
        target_name=target_config["name"],
        ping_count=20,
        http_samples=5,
        mtr_cycles=15,
        capture_packets=True,
        max_capture_packets=2000
    )

    if result["status"] != "success":
        console.print(f"[red]❌ Test failed: {result.get('error', 'Unknown error')}[/red]")
        return 1

    # Display individual test results first
    console.print()
    console.rule("[bold bright_yellow]📊 INDIVIDUAL TEST RESULTS[/bold bright_yellow]", style="bright_yellow")
    console.print()

    # Ping results
    ping = result["tests"].get("ping", {})
    if ping.get("success"):
        formatter.print_latency_results("us-west-1", ping)

    # MTR results
    mtr = result["tests"].get("mtr", {})
    if mtr.get("status") == "success":
        formatter.print_mtr_results("us-west-1", "California → San Jose", mtr)

    # HTTP results
    http = result["tests"].get("http", {})
    if http.get("status") == "success":
        formatter.print_http_timing_results("us-west-1", http)

    # Packet analysis
    packet_analysis = result.get("packet_analysis")
    if packet_analysis and packet_analysis.get("status") == "success":
        formatter.print_packet_analysis(packet_analysis)

    # Now display the layered correlation - THE MAIN EVENT!
    console.print()
    console.rule("[bold bright_cyan]🔬 LAYERED CORRELATION ANALYSIS[/bold bright_cyan]", style="bright_cyan")
    console.print()

    layered = result.get("layered_analysis")
    if layered:
        formatter.print_layered_analysis(layered, "us-west-1 → Oracle San Jose")
    else:
        console.print("[yellow]⚠️  No layered analysis available[/yellow]")

    # Display TCP-to-HTTP phase correlation if available
    tcp_http_corr = result.get("tcp_http_correlation")
    if tcp_http_corr and tcp_http_corr.get("status") == "success":
        console.print()
        console.rule("[bold bright_magenta]🔗 TCP-TO-HTTP PHASE CORRELATION[/bold bright_magenta]", style="bright_magenta")
        console.print()

        from rich.table import Table

        phase_table = Table(title="TCP Events During HTTP Phases", box=box.ROUNDED)
        phase_table.add_column("HTTP Phase", style="cyan", width=20)
        phase_table.add_column("Duration", justify="right", style="white", width=12)
        phase_table.add_column("TCP Events", justify="right", style="yellow", width=12)
        phase_table.add_column("Retransmissions", justify="right", style="red", width=16)
        phase_table.add_column("Retrans Rate", justify="right", style="orange3", width=14)

        phases = tcp_http_corr.get("phases", {})
        for phase_name, phase_data in phases.items():
            duration = phase_data.get("duration_ms", 0)
            event_count = phase_data.get("event_count", 0)
            retrans = phase_data.get("retransmissions", 0)
            retrans_rate = phase_data.get("retransmission_rate", 0)

            # Color code retransmission rate
            if retrans_rate > 5:
                rate_style = "bold red"
            elif retrans_rate > 1:
                rate_style = "yellow"
            else:
                rate_style = "green"

            phase_table.add_row(
                phase_name.replace("_", " ").title(),
                f"{duration:.2f}ms",
                str(event_count),
                str(retrans),
                Text(f"{retrans_rate:.2f}%", style=rate_style)
            )

        console.print(phase_table)
        console.print()

        total_bytes = tcp_http_corr.get("total_bytes", 0)
        console.print(f"[dim]Total bytes captured: {total_bytes:,}[/dim]")

    # Display MTR-to-TCP correlation if available
    mtr_tcp_corr = result.get("mtr_tcp_correlation")
    if mtr_tcp_corr and mtr_tcp_corr.get("status") == "success":
        console.print()
        console.rule("[bold bright_green]🗺️  MTR-TO-TCP CORRELATION[/bold bright_green]", style="bright_green")
        console.print()

        predicted_rtt = mtr_tcp_corr.get("mtr_predicted_rtt", 0)
        actual_rtt = mtr_tcp_corr.get("tcp_actual_rtt", 0)
        variance_ms = mtr_tcp_corr.get("variance_ms", 0)
        variance_pct = mtr_tcp_corr.get("variance_percentage", 0)

        corr_text = Text()
        corr_text.append("MTR Predicted RTT: ", style="cyan")
        corr_text.append(f"{predicted_rtt:.2f}ms\n", style="white")
        corr_text.append("TCP Actual RTT: ", style="cyan")
        corr_text.append(f"{actual_rtt:.2f}ms\n", style="white")
        corr_text.append("Variance: ", style="cyan")

        if abs(variance_pct) < 10:
            var_style = "green"
            var_emoji = "✅"
        elif abs(variance_pct) < 25:
            var_style = "yellow"
            var_emoji = "⚠️"
        else:
            var_style = "red"
            var_emoji = "❌"

        corr_text.append(f"{var_emoji} {variance_ms:+.2f}ms ({variance_pct:+.1f}%)", style=var_style)

        corr_panel = Panel(corr_text, title="Path Latency vs TCP Handshake", border_style="bright_green")
        console.print(corr_panel)

        # Show contributing hops
        contributing = mtr_tcp_corr.get("contributing_hops", [])
        if contributing:
            console.print()
            console.print("[yellow]Hops contributing significant latency:[/yellow]")
            for hop in contributing:
                console.print(
                    f"  • Hop {hop['hop_number']}: {hop['ip']} - "
                    f"{hop['latency_ms']:.2f}ms "
                    f"({hop['loss_pct']:.1f}% loss)"
                )

    # Final summary
    console.print()
    console.rule("[bold bright_white]✨ SUMMARY[/bold bright_white]", style="bright_white")
    console.print()

    summary_panel = Panel(
        Text.from_markup(
            "[bold bright_cyan]What We Learned:[/bold bright_cyan]\n\n"
            "[green]✓[/green] We captured packets during all tests (ping, MTR, HTTP)\n"
            "[green]✓[/green] We analyzed TCP behavior at L4 (retransmissions, window sizes)\n"
            "[green]✓[/green] We correlated TCP events to HTTP timing phases (DNS, TLS, TTFB, download)\n"
            "[green]✓[/green] We compared MTR path latency to actual TCP handshake time\n"
            "[green]✓[/green] We generated quality grades for each network layer\n"
            "[green]✓[/green] We identified cross-layer correlations and insights\n\n"
            "[bold bright_yellow]This gives a complete picture from L3 → L4 → L7![/bold bright_yellow]"
        ),
        border_style="bright_white",
        box=box.DOUBLE,
        padding=(1, 2)
    )
    console.print(summary_panel)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
