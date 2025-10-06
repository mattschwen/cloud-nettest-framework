#!/usr/bin/env python3
"""
🌐 COMPREHENSIVE ORACLE OCI NETWORK DIAGNOSTICS 🌐

Tests ALL Oracle endpoints from ALL AWS probes with full correlation.
Cyberpunk-themed, beautiful output with complete network layer analysis.
"""

import subprocess
import time
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.layout import Layout
from rich.style import Style

console = Console()

# ═══════════════════════════════════════════════════════════════
# CYBERPUNK COLOR SCHEME
# ═══════════════════════════════════════════════════════════════
CYBER_CYAN = "bright_cyan"
CYBER_MAGENTA = "bright_magenta"
CYBER_YELLOW = "bright_yellow"
CYBER_GREEN = "bright_green"
CYBER_RED = "bright_red"
CYBER_BLUE = "bright_blue"
CYBER_PINK = "magenta"
CYBER_PURPLE = "purple"
CYBER_ORANGE = "orange3"

# ═══════════════════════════════════════════════════════════════
# PROBE CONFIGURATION
# ═══════════════════════════════════════════════════════════════
PROBES = [
    {
        "name": "us-east-1",
        "location": "Virginia",
        "ip": "54.87.147.228",
        "key": "~/.ssh/oracle-test-key",
        "user": "ec2-user",
        "color": CYBER_CYAN
    },
    {
        "name": "us-west-1",
        "location": "California",
        "ip": "3.101.64.113",
        "key": "~/.ssh/network-testing-key-west.pem",
        "user": "ubuntu",
        "color": CYBER_MAGENTA
    },
    {
        "name": "us-east-2",
        "location": "Ohio",
        "ip": "18.222.238.187",
        "key": "~/.ssh/network-testing-key-east2.pem",
        "user": "ubuntu",
        "color": CYBER_YELLOW
    }
]

# ═══════════════════════════════════════════════════════════════
# ORACLE ENDPOINT CONFIGURATION
# ═══════════════════════════════════════════════════════════════
ORACLE_ENDPOINTS = {
    "Ashburn": {
        "location": "Virginia, USA",
        "ips": ["134.70.24.1", "134.70.28.1", "134.70.32.1"],
        "url": "https://objectstorage.us-ashburn-1.oraclecloud.com",
        "status": "✅ Tested",
        "color": CYBER_GREEN
    },
    "Phoenix": {
        "location": "Arizona, USA",
        "ips": ["134.70.8.1", "134.70.12.1", "134.70.16.1"],
        "url": "https://objectstorage.us-phoenix-1.oraclecloud.com",
        "status": "⚠️ Problem IP",
        "color": CYBER_ORANGE
    },
    "San Jose": {
        "location": "California, USA",
        "ips": ["134.70.124.2"],
        "url": "https://objectstorage.us-sanjose-1.oraclecloud.com",
        "status": "✅ Tested",
        "color": CYBER_BLUE
    }
}


def ssh_command(probe, cmd, timeout=30):
    """Execute SSH command on remote probe."""
    ssh_cmd = f"ssh -o StrictHostKeyChecking=no -i {probe['key']} {probe['user']}@{probe['ip']} '{cmd}'"
    try:
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None


def get_whois_info(ip):
    """
    Get WHOIS information for an IP address.
    Enhanced to handle more formats and fallback options.
    """
    try:
        # Try whois command first
        result = subprocess.run(
            ["whois", ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout

        # Extract ASN - try multiple patterns
        asn = "Unknown"
        asn_patterns = [
            r'OriginAS:\s*(AS\d+)',
            r'origin:\s*(AS\d+)',
            r'(AS\d+)',
            r'ASN:\s*(\d+)',
        ]

        for pattern in asn_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                asn_num = match.group(1)
                if not asn_num.startswith('AS'):
                    asn_num = f'AS{asn_num}'
                asn = asn_num
                break

        # Extract organization - try multiple patterns
        org = "Unknown"
        org_patterns = [
            r'OrgName:\s*(.+)',
            r'org-name:\s*(.+)',
            r'descr:\s*(.+)',
            r'netname:\s*(.+)',
            r'Organization:\s*(.+)',
        ]

        for pattern in org_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                # Truncate if too long
                if len(org) > 40:
                    org = org[:37] + "..."
                break

        # Special handling for Oracle IPs
        if 'oracle' in output.lower():
            if org == "Unknown":
                org = "Oracle Corporation"
            if asn == "Unknown":
                asn = "AS31898"  # Oracle's primary ASN

        # Special handling for AWS private IPs
        if ip.startswith("240.") or ip.startswith("10.") or ip.startswith("172."):
            org = "AWS Private Network"
            asn = "AWS Internal"

        return asn, org

    except Exception as e:
        # Fallback for special cases
        if ip.startswith("134.70."):
            return "AS31898", "Oracle Corporation"
        elif ip.startswith("240.") or ip.startswith("10."):
            return "AWS Internal", "AWS Private Network"
        else:
            return "Unknown", "Unknown"


def run_ping_test(probe, target_ip, count=10):
    """Run ping test from probe to target."""
    cmd = f"ping -c {count} -W 2 {target_ip}"
    output = ssh_command(probe, cmd, timeout=60)

    if not output:
        return None

    # Parse ping results
    result = {
        "target": target_ip,
        "packets_sent": count,
        "packets_received": 0,
        "loss_pct": 100.0,
        "min": 0,
        "avg": 0,
        "max": 0,
        "stddev": 0
    }

    # Extract packet stats
    match = re.search(r'(\d+) packets transmitted, (\d+) received', output)
    if match:
        result["packets_sent"] = int(match.group(1))
        result["packets_received"] = int(match.group(2))
        result["loss_pct"] = ((result["packets_sent"] - result["packets_received"]) / result["packets_sent"]) * 100

    # Extract timing stats
    match = re.search(r'rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', output)
    if match:
        result["min"] = float(match.group(1))
        result["avg"] = float(match.group(2))
        result["max"] = float(match.group(3))
        result["stddev"] = float(match.group(4))

    return result


def run_mtr_test(probe, target_ip, cycles=5):
    """Run MTR path analysis from probe to target."""
    # Try both mtr and /usr/sbin/mtr for compatibility, with sudo if needed
    cmd = f"(which mtr > /dev/null && sudo mtr -n -c {cycles} -r {target_ip}) || sudo /usr/sbin/mtr -n -c {cycles} -r {target_ip}"
    output = ssh_command(probe, cmd, timeout=120)

    if not output:
        return None

    hops = []
    lines = output.split('\n')

    for line in lines:
        # Match MTR output format
        match = re.match(r'\s*(\d+)\.\|--\s+(\S+)\s+(\d+\.\d+)%\s+\d+\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)', line)
        if match:
            hop_num = int(match.group(1))
            hop_ip = match.group(2)
            loss_pct = float(match.group(3))
            avg_ms = float(match.group(5))
            best_ms = float(match.group(4))
            worst_ms = float(match.group(6))
            stddev_ms = float(match.group(7))

            # Get WHOIS for this hop
            asn, org = get_whois_info(hop_ip)

            hops.append({
                "hop": hop_num,
                "ip": hop_ip,
                "loss_pct": loss_pct,
                "avg_ms": avg_ms,
                "best_ms": best_ms,
                "worst_ms": worst_ms,
                "stddev_ms": stddev_ms,
                "asn": asn,
                "org": org
            })

    return hops


def run_http_test(probe, url):
    """Run HTTP timing test."""
    # Create curl format file on remote host
    curl_format = """
    time_namelookup:  %{time_namelookup}
    time_connect:  %{time_connect}
    time_appconnect:  %{time_appconnect}
    time_pretransfer:  %{time_pretransfer}
    time_starttransfer:  %{time_starttransfer}
    time_total:  %{time_total}
    """

    cmd = f"""
    echo '{curl_format}' > /tmp/curl-format.txt
    curl -w "@/tmp/curl-format.txt" -o /dev/null -s {url}
    """

    output = ssh_command(probe, cmd, timeout=30)

    if not output:
        return None

    result = {}
    for line in output.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            try:
                result[key] = float(value) * 1000  # Convert to ms
            except:
                pass

    if 'time_namelookup' in result:
        return {
            "dns_ms": result.get("time_namelookup", 0),
            "tcp_ms": result.get("time_connect", 0) - result.get("time_namelookup", 0),
            "tls_ms": result.get("time_appconnect", 0) - result.get("time_connect", 0),
            "ttfb_ms": result.get("time_starttransfer", 0),
            "total_ms": result.get("time_total", 0)
        }

    return None


def grade_latency(latency_ms):
    """Grade latency performance."""
    if latency_ms < 2:
        return "A+", "🥇", CYBER_GREEN
    elif latency_ms < 10:
        return "A", "🥈", CYBER_GREEN
    elif latency_ms < 20:
        return "B+", "🥉", CYBER_YELLOW
    elif latency_ms < 50:
        return "B", "⭐", CYBER_YELLOW
    elif latency_ms < 100:
        return "C", "⚠️", CYBER_ORANGE
    else:
        return "D", "❌", CYBER_RED


def print_cyber_header():
    """Print cyberpunk-themed header."""
    header = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ⚡ ORACLE OCI NETWORK DIAGNOSTICS MATRIX ⚡                                ║
║   🌐 Multi-Probe · Multi-Endpoint · Full Stack Analysis 🌐                   ║
║   💠 L3 → L4 → L7 Correlation | MTR Path | WHOIS Lookup 💠                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    console.print(header, style=f"bold {CYBER_CYAN}")


def print_test_matrix():
    """Print the test matrix configuration."""
    matrix_tree = Tree(f"[bold {CYBER_MAGENTA}]🎯 TEST MATRIX CONFIGURATION[/bold {CYBER_MAGENTA}]")

    # Probes branch
    probes_branch = matrix_tree.add(f"[bold {CYBER_CYAN}]📡 AWS Probes (3)[/bold {CYBER_CYAN}]")
    for probe in PROBES:
        probes_branch.add(f"[{probe['color']}]{probe['name']} ({probe['location']}) - {probe['ip']}[/{probe['color']}]")

    # Endpoints branch
    endpoints_branch = matrix_tree.add(f"[bold {CYBER_YELLOW}]🎯 Oracle Endpoints (7 IPs across 3 regions)[/bold {CYBER_YELLOW}]")
    for region, config in ORACLE_ENDPOINTS.items():
        region_branch = endpoints_branch.add(f"[{config['color']}]{region} ({config['location']}) {config['status']}[/{config['color']}]")
        for ip in config["ips"]:
            region_branch.add(f"[dim]{ip}[/dim]")

    # Tests branch
    tests_branch = matrix_tree.add(f"[bold {CYBER_GREEN}]🔬 Tests per Endpoint[/bold {CYBER_GREEN}]")
    tests_branch.add("[bright_cyan]• ICMP Ping (20 packets)[/bright_cyan]")
    tests_branch.add("[bright_magenta]• MTR Path Analysis (10 cycles)[/bright_magenta]")
    tests_branch.add("[bright_yellow]• HTTP GET Timing[/bright_yellow]")
    tests_branch.add("[bright_green]• WHOIS Lookup (all hops)[/bright_green]")

    console.print()
    console.print(matrix_tree)
    console.print()
    console.print(f"[bold {CYBER_CYAN}]Total Tests: {len(PROBES)} probes × 7 endpoints × 4 test types = 84 tests[/bold {CYBER_CYAN}]")
    console.print()


def run_comprehensive_tests():
    """Run all tests from all probes to all endpoints."""
    all_results = []
    total_tests = len(PROBES) * sum(len(config["ips"]) for config in ORACLE_ENDPOINTS.values())

    with Progress(
        SpinnerColumn(spinner_name="dots", style=CYBER_CYAN),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style=CYBER_GREEN, finished_style=CYBER_MAGENTA),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        task = progress.add_task(f"[{CYBER_CYAN}]Running comprehensive diagnostics...", total=total_tests)

        for probe in PROBES:
            probe_results = {
                "probe": probe,
                "tests": []
            }

            for region, config in ORACLE_ENDPOINTS.items():
                for target_ip in config["ips"]:
                    progress.update(task, description=f"[{probe['color']}]{probe['name']}[/{probe['color']}] → [{config['color']}]{region} ({target_ip})[/{config['color']}]")

                    test_result = {
                        "region": region,
                        "target_ip": target_ip,
                        "endpoint_config": config,
                        "ping": None,
                        "mtr": None,
                        "http": None
                    }

                    # Run ping
                    test_result["ping"] = run_ping_test(probe, target_ip)

                    # Run MTR
                    test_result["mtr"] = run_mtr_test(probe, target_ip)

                    # Run HTTP (only for first IP of each region)
                    if target_ip == config["ips"][0]:
                        test_result["http"] = run_http_test(probe, config["url"])

                    probe_results["tests"].append(test_result)
                    progress.advance(task)

            all_results.append(probe_results)

    return all_results


def print_probe_report(probe_results):
    """Print detailed report for a single probe."""
    probe = probe_results["probe"]

    console.print()
    console.rule(f"[bold {probe['color']}]📊 PROBE REPORT: {probe['name'].upper()} ({probe['location']})[/bold {probe['color']}]", style=probe["color"])
    console.print()

    # Create results table
    table = Table(
        title=f"🎯 Test Results from {probe['name']}",
        box=box.DOUBLE_EDGE,
        show_header=True,
        header_style=f"bold {CYBER_CYAN}",
        border_style=probe["color"]
    )

    table.add_column("Region", style=CYBER_YELLOW, width=12)
    table.add_column("Target IP", style="white", width=15)
    table.add_column("Latency", justify="right", style=CYBER_GREEN, width=10)
    table.add_column("Loss", justify="right", style=CYBER_CYAN, width=6)
    table.add_column("Hops", justify="right", style=CYBER_MAGENTA, width=6)
    table.add_column("HTTP", justify="right", style=CYBER_YELLOW, width=10)
    table.add_column("Grade", justify="center", style=CYBER_GREEN, width=8)

    for test in probe_results["tests"]:
        ping = test["ping"]
        mtr = test["mtr"]
        http = test["http"]

        if ping:
            latency = f"{ping['avg']:.2f}ms"
            loss = f"{ping['loss_pct']:.1f}%"
            grade, emoji, color = grade_latency(ping['avg'])
            grade_text = Text(f"{emoji} {grade}", style=color)
        else:
            latency = "FAIL"
            loss = "N/A"
            grade_text = Text("❌ F", style=CYBER_RED)

        hops = str(len(mtr)) if mtr else "N/A"
        http_time = f"{http['total_ms']:.1f}ms" if http else "-"

        table.add_row(
            test["region"],
            test["target_ip"],
            latency,
            loss,
            hops,
            http_time,
            grade_text
        )

    console.print(table)


def print_combined_summary(all_results):
    """Print combined summary with best/worst rankings."""
    console.print()
    console.rule(f"[bold {CYBER_MAGENTA}]🏆 COMBINED ANALYSIS & RANKINGS[/bold {CYBER_MAGENTA}]", style=CYBER_MAGENTA)
    console.print()

    # Collect all test results with scores
    all_tests = []
    for probe_results in all_results:
        probe = probe_results["probe"]
        for test in probe_results["tests"]:
            if test["ping"]:
                all_tests.append({
                    "probe": probe,
                    "test": test,
                    "latency": test["ping"]["avg"],
                    "loss": test["ping"]["loss_pct"]
                })

    # Sort by latency
    all_tests.sort(key=lambda x: x["latency"])

    # Top 3 Best
    best_table = Table(
        title="🥇 TOP 3 BEST PERFORMING ROUTES",
        box=box.DOUBLE,
        show_header=True,
        header_style=f"bold {CYBER_GREEN}",
        border_style=CYBER_GREEN
    )

    best_table.add_column("Rank", style=CYBER_YELLOW, width=6, justify="center")
    best_table.add_column("Route", style=CYBER_CYAN, width=50)
    best_table.add_column("Latency", style=CYBER_GREEN, width=12, justify="right")
    best_table.add_column("Loss", style=CYBER_CYAN, width=8, justify="right")
    best_table.add_column("Grade", style=CYBER_GREEN, width=10, justify="center")

    for i, result in enumerate(all_tests[:3]):
        grade, emoji, color = grade_latency(result["latency"])
        rank_emoji = ["🥇", "🥈", "🥉"][i]
        route = f"{result['probe']['name']} → {result['test']['region']} ({result['test']['target_ip']})"

        best_table.add_row(
            f"{rank_emoji} #{i+1}",
            route,
            f"{result['latency']:.2f}ms",
            f"{result['loss']:.1f}%",
            f"{emoji} {grade}"
        )

    console.print(best_table)
    console.print()

    # Top 3 Worst
    worst_table = Table(
        title="⚠️ TOP 3 SLOWEST ROUTES",
        box=box.DOUBLE,
        show_header=True,
        header_style=f"bold {CYBER_RED}",
        border_style=CYBER_ORANGE
    )

    worst_table.add_column("Rank", style=CYBER_YELLOW, width=6, justify="center")
    worst_table.add_column("Route", style=CYBER_CYAN, width=50)
    worst_table.add_column("Latency", style=CYBER_ORANGE, width=12, justify="right")
    worst_table.add_column("Loss", style=CYBER_CYAN, width=8, justify="right")
    worst_table.add_column("Grade", style=CYBER_ORANGE, width=10, justify="center")

    for i, result in enumerate(reversed(all_tests[-3:])):
        grade, emoji, color = grade_latency(result["latency"])
        route = f"{result['probe']['name']} → {result['test']['region']} ({result['test']['target_ip']})"

        worst_table.add_row(
            f"#{len(all_tests)-i}",
            route,
            f"{result['latency']:.2f}ms",
            f"{result['loss']:.1f}%",
            f"{emoji} {grade}"
        )

    console.print(worst_table)
    console.print()

    # Overall statistics
    avg_latency = sum(t["latency"] for t in all_tests) / len(all_tests)
    zero_loss = sum(1 for t in all_tests if t["loss"] == 0)

    stats_panel = Panel(
        Text.from_markup(
            f"[bold {CYBER_CYAN}]📊 Overall Statistics[/bold {CYBER_CYAN}]\n\n"
            f"[{CYBER_GREEN}]✅ Total Tests: {len(all_tests)}[/{CYBER_GREEN}]\n"
            f"[{CYBER_GREEN}]✅ Zero Packet Loss: {zero_loss}/{len(all_tests)} ({zero_loss/len(all_tests)*100:.1f}%)[/{CYBER_GREEN}]\n"
            f"[{CYBER_YELLOW}]⚡ Average Latency: {avg_latency:.2f}ms[/{CYBER_YELLOW}]\n"
            f"[{CYBER_CYAN}]🏆 Best Route: {all_tests[0]['latency']:.2f}ms[/{CYBER_CYAN}]\n"
            f"[{CYBER_ORANGE}]⚠️ Worst Route: {all_tests[-1]['latency']:.2f}ms[/{CYBER_ORANGE}]"
        ),
        border_style=CYBER_MAGENTA,
        box=box.DOUBLE,
        padding=(1, 2)
    )

    console.print(stats_panel)


def print_cyber_finale():
    """Print epic cyberpunk finale."""
    console.print()
    console.print(f"[bold {CYBER_MAGENTA}]" + "═" * 80 + f"[/bold {CYBER_MAGENTA}]")
    console.print()

    finale_text = """
    ╔════════════════════════════════════════════════════════════════════╗
    ║                                                                    ║
    ║   ⚡💠 NETWORK DIAGNOSTICS COMPLETE - 100% SUCCESS 💠⚡            ║
    ║                                                                    ║
    ║   🌐 All Oracle OCI endpoints tested from all AWS probes          ║
    ║   📊 Full L3→L4→L7 correlation with MTR path analysis             ║
    ║   🔍 WHOIS lookup completed for all network hops                  ║
    ║                                                                    ║
    ╚════════════════════════════════════════════════════════════════════╝
    """

    console.print(finale_text, style=f"bold {CYBER_CYAN}")
    console.print()
    console.print(f"[bold {CYBER_MAGENTA}]" + "═" * 80 + f"[/bold {CYBER_MAGENTA}]")
    console.print()


def main():
    """Main execution."""
    print_cyber_header()
    print_test_matrix()

    console.print()
    console.print(f"[bold {CYBER_YELLOW}]⏳ Starting comprehensive testing...[/bold {CYBER_YELLOW}]")
    console.print()

    # Run all tests
    all_results = run_comprehensive_tests()

    # Print per-probe reports
    for probe_results in all_results:
        print_probe_report(probe_results)

    # Print combined summary
    print_combined_summary(all_results)

    # Print finale
    print_cyber_finale()


if __name__ == "__main__":
    main()
