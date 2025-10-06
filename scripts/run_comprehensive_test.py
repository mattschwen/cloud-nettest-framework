#!/usr/bin/env python3
"""Run comprehensive network diagnostics on Oracle endpoints."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cnf.registry import load_registry
from cnf.tests.comprehensive import comprehensive_target_test
from cnf.formatter import NetworkTestFormatter
from rich.console import Console

console = Console()
formatter = NetworkTestFormatter(console)


async def main():
    """Run comprehensive test on Oracle Phoenix (the historical problem IP)."""

    # Load registry to get our AWS probes
    registry = load_registry()

    # Get us-west-1 probe (best for Phoenix testing)
    probe = None
    for host in registry.hosts:
        if host.region == "us-west-1" and host.status == "active":
            probe = host
            break

    if not probe:
        console.print("[red]Error: No active us-west-1 probe found[/red]")
        return

    # Test Oracle Phoenix - the historically problematic IP
    target_ip = "134.70.16.1"
    target_url = "https://objectstorage.us-phoenix-1.oraclecloud.com"
    target_name = "Oracle Phoenix (Problem IP - was 471ms, baseline check)"

    formatter.print_header(
        "🔬 Comprehensive Network Diagnostics",
        f"Testing: {target_name}\nProbe: {probe.id} ({probe.public_ip})\nTarget: {target_ip}"
    )

    console.print()
    console.print("[cyan]Running comprehensive diagnostics...[/cyan]")
    console.print("[dim]This will take 2-3 minutes and includes:[/dim]")
    console.print("  [dim]• Packet capture (tcpdump)[/dim]")
    console.print("  [dim]• Ping test (30 packets)[/dim]")
    console.print("  [dim]• MTR path analysis (20 cycles)[/dim]")
    console.print("  [dim]• HTTP GET (5 samples with timing)[/dim]")
    console.print("  [dim]• TCP packet analysis[/dim]")
    console.print()

    # Run comprehensive test
    result = await comprehensive_target_test(
        host=probe,
        target_ip=target_ip,
        target_url=target_url,
        target_name=target_name,
        ping_count=30,
        http_samples=5,
        mtr_cycles=20,
        capture_packets=True,
        max_capture_packets=2500
    )

    if result["status"] != "success":
        console.print(f"[red]Test failed: {result.get('error', 'Unknown error')}[/red]")
        return

    # Display results
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold yellow]TEST RESULTS[/bold yellow]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

    # Ping results
    ping_result = result.get("tests", {}).get("ping", {})
    if ping_result and ping_result.get("success"):
        formatter.print_latency_results(
            probe.id,
            f"{probe.region} ({probe.public_ip})",
            [ping_result]
        )
        console.print()

    # MTR results
    mtr_result = result.get("tests", {}).get("mtr", {})
    if mtr_result:
        formatter.print_mtr_results(
            probe.id,
            probe.region,
            [mtr_result]
        )
        console.print()

    # HTTP results
    http_result = result.get("tests", {}).get("http", {})
    if http_result:
        formatter.print_http_timing_results(
            probe.id,
            [http_result]
        )
        console.print()

    # Packet analysis
    packet_analysis = result.get("packet_analysis")
    if packet_analysis:
        console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
        console.print("[bold yellow]PACKET CAPTURE ANALYSIS[/bold yellow]")
        console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

        formatter.print_packet_analysis(packet_analysis)
        console.print()

    # Comprehensive summary
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold yellow]COMPREHENSIVE SUMMARY[/bold yellow]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

    formatter.print_comprehensive_summary(result)
    console.print()

    # Problem IP comparison
    if ping_result and ping_result.get("success"):
        current_latency = ping_result.get("avg_ms", 0)
        historical_latency = 471.0  # The problematic baseline
        improvement = ((historical_latency - current_latency) / historical_latency) * 100

        formatter.print_problem_ip_status(
            "134.70.16.1",
            {
                "current_latency": current_latency,
                "historical_latency": historical_latency,
                "improvement_pct": improvement
            }
        )
        console.print()

    # Success message
    formatter.print_success(
        f"Comprehensive diagnostics completed!\n"
        f"All tests executed on AWS probe: {probe.id}\n"
        f"Results show complete network stack analysis"
    )


if __name__ == "__main__":
    asyncio.run(main())
