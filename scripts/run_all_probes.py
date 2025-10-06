#!/usr/bin/env python3
"""Run comprehensive diagnostics from all available probes."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cnf.registry import load_registry
from cnf.tests.comprehensive import comprehensive_target_test
from cnf.formatter import NetworkTestFormatter
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
formatter = NetworkTestFormatter(console)


async def test_from_probe(probe, target_ip, target_url, target_name):
    """Run comprehensive test from a single probe."""

    panel_title = f"Testing from: {probe.id} ({probe.region})"
    console.print(Panel(
        Text(f"Probe: {probe.public_ip}\nTarget: {target_name}\nIP: {target_ip}", style="cyan"),
        title=panel_title,
        border_style="bright_blue"
    ))
    console.print()

    result = await comprehensive_target_test(
        host=probe,
        target_ip=target_ip,
        target_url=target_url,
        target_name=target_name,
        ping_count=20,
        http_samples=5,
        mtr_cycles=15,
        capture_packets=True,
        max_capture_packets=2000
    )

    if result["status"] != "success":
        console.print(f"[red]❌ Test failed: {result.get('error', 'Unknown error')}[/red]\n")
        return result

    # Display results
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold yellow]RESULTS: {probe.region.upper()}  → {target_name}[/bold yellow]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

    # Ping
    ping_result = result.get("tests", {}).get("ping", {})
    if ping_result and ping_result.get("success"):
        formatter.print_latency_results(probe.id, f"{probe.region} ({probe.public_ip})", [ping_result])
        console.print()

    # MTR
    mtr_result = result.get("tests", {}).get("mtr", {})
    if mtr_result:
        formatter.print_mtr_results(probe.id, probe.region, [mtr_result])
        console.print()

    # HTTP
    http_result = result.get("tests", {}).get("http", {})
    if http_result:
        formatter.print_http_timing_results(probe.id, [http_result])
        console.print()

    # Packet analysis
    packet_analysis = result.get("packet_analysis")
    if packet_analysis:
        formatter.print_packet_analysis(packet_analysis)
        console.print()

    # Summary
    formatter.print_comprehensive_summary(result)
    console.print("\n")

    return result


async def main():
    """Run tests from all available probes."""

    formatter.print_header(
        "🔬 Multi-Probe Comprehensive Network Diagnostics",
        "Testing Oracle OCI endpoints from all AWS regions"
    )
    console.print()

    # Load registry
    registry = load_registry()
    active_probes = [h for h in registry.hosts if h.status == "active"]

    if not active_probes:
        console.print("[red]No active probes found![/red]")
        return

    console.print(f"[green]Found {len(active_probes)} active probe(s):[/green]")
    for probe in active_probes:
        console.print(f"  • {probe.id} - {probe.region} ({probe.public_ip})")
    console.print()

    # Test different targets from each probe
    # us-west-1 → Oracle San Jose (best performance)
    # us-east-2 → Oracle Ashburn (best performance)

    tests = [
        {
            "probe_region": "us-west-1",
            "target_ip": "134.70.124.2",
            "target_url": "https://objectstorage.us-sanjose-1.oraclecloud.com",
            "target_name": "Oracle San Jose"
        },
        {
            "probe_region": "us-east-2",
            "target_ip": "134.70.24.1",
            "target_url": "https://objectstorage.us-ashburn-1.oraclecloud.com",
            "target_name": "Oracle Ashburn"
        }
    ]

    results = []

    for test_config in tests:
        # Find probe for this test
        probe = None
        for p in active_probes:
            if p.region == test_config["probe_region"]:
                probe = p
                break

        if not probe:
            console.print(f"[yellow]Skipping test - no probe in {test_config['probe_region']}[/yellow]\n")
            continue

        # Run test
        result = await test_from_probe(
            probe,
            test_config["target_ip"],
            test_config["target_url"],
            test_config["target_name"]
        )
        results.append(result)

        # Brief pause between tests
        await asyncio.sleep(2)

    # Final summary
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold green]✅ ALL TESTS COMPLETED[/bold green]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")

    successful = sum(1 for r in results if r.get("status") == "success")
    console.print(f"Tests run: {len(results)}")
    console.print(f"Successful: [green]{successful}[/green]")
    console.print(f"Failed: [red]{len(results) - successful}[/red]")
    console.print()

    formatter.print_success(
        "Comprehensive multi-probe diagnostics complete!\n"
        "All tests executed on remote AWS EC2 instances\n"
        "Full network stack analysis with packet capture"
    )


if __name__ == "__main__":
    asyncio.run(main())
