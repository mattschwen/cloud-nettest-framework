"""Rich-formatted output for Cloud NetTest Framework."""

from typing import Any, Dict, List, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.text import Text
from rich.box import ROUNDED, HEAVY, DOUBLE


console = Console()


class PerformanceGrader:
    """Grade network performance with visual indicators."""

    @staticmethod
    def grade_latency(latency_ms: float, distance: str = "regional") -> tuple[str, str, str]:
        """
        Grade latency performance.

        Returns: (grade, emoji, color)
        """
        if distance == "same-region":
            if latency_ms < 2:
                return "A+", "🥇", "bright_green"
            elif latency_ms < 5:
                return "A", "🥈", "green"
            elif latency_ms < 15:
                return "B", "🥉", "yellow"
            elif latency_ms < 30:
                return "C", "⚠️", "orange3"
            else:
                return "D", "❌", "red"

        elif distance == "cross-country":
            if latency_ms < 50:
                return "A+", "🥇", "bright_green"
            elif latency_ms < 70:
                return "A", "🥈", "green"
            elif latency_ms < 100:
                return "B", "🥉", "yellow"
            elif latency_ms < 150:
                return "C", "⚠️", "orange3"
            else:
                return "D", "❌", "red"

        else:  # regional
            if latency_ms < 20:
                return "A+", "🥇", "bright_green"
            elif latency_ms < 40:
                return "A", "🥈", "green"
            elif latency_ms < 70:
                return "B", "🥉", "yellow"
            elif latency_ms < 100:
                return "C", "⚠️", "orange3"
            else:
                return "D", "❌", "red"

    @staticmethod
    def grade_packet_loss(loss_pct: float) -> tuple[str, str]:
        """Grade packet loss. Returns (emoji, color)"""
        if loss_pct == 0:
            return "✅", "bright_green"
        elif loss_pct < 1:
            return "⚠️", "yellow"
        elif loss_pct < 5:
            return "🔶", "orange3"
        else:
            return "❌", "red"

    @staticmethod
    def grade_jitter(stddev_ms: float) -> tuple[str, str]:
        """Grade jitter/stddev. Returns (emoji, color)"""
        if stddev_ms < 1:
            return "✅", "bright_green"
        elif stddev_ms < 5:
            return "⚠️", "yellow"
        else:
            return "❌", "red"


class NetworkTestFormatter:
    """Beautiful formatted output for network test results."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.grader = PerformanceGrader()

    def print_header(self, title: str, subtitle: Optional[str] = None):
        """Print a beautiful header."""
        text = Text(title, style="bold cyan")
        if subtitle:
            text.append(f"\n{subtitle}", style="dim")

        panel = Panel(
            text,
            box=DOUBLE,
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)

    def print_test_plan_info(self, plan: Dict[str, Any], probes: List[Any]):
        """Print test plan information in a beautiful format."""
        # Create info table
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="bold cyan", justify="right")
        info_table.add_column(style="white")

        info_table.add_row("Test Plan:", plan.get("name", "unnamed"))
        info_table.add_row("Description:", plan.get("description", "N/A"))
        info_table.add_row("Version:", str(plan.get("version", "1.0")))
        info_table.add_row("Probes:", f"{len(probes)} active")
        info_table.add_row("Timestamp:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        panel = Panel(
            info_table,
            title="[bold]📋 Test Configuration[/bold]",
            border_style="blue",
            box=ROUNDED
        )
        self.console.print(panel)

    def print_probe_list(self, probes: List[Any]):
        """Print beautiful probe list."""
        table = Table(
            title="🔍 Selected Probe Hosts",
            box=HEAVY,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Provider", style="green")
        table.add_column("Region", style="yellow")
        table.add_column("Public IP", style="blue")
        table.add_column("Status", style="bright_green", justify="center")

        for probe in probes:
            status_emoji = "✅" if probe.status == "active" else "⚪"
            table.add_row(
                probe.id,
                probe.provider.upper(),
                probe.region,
                probe.public_ip or "N/A",
                f"{status_emoji} {probe.status}"
            )

        self.console.print(table)

    def print_latency_results(
        self,
        probe_id: str,
        probe_location: str,
        results: List[Dict[str, Any]]
    ):
        """Print beautiful latency test results."""
        table = Table(
            title=f"📡 Latency Results: {probe_id} ({probe_location})",
            box=ROUNDED,
            show_header=True,
            header_style="bold bright_cyan"
        )

        table.add_column("Target", style="cyan", no_wrap=True)
        table.add_column("Packets", justify="center", style="white")
        table.add_column("Loss", justify="center", style="white")
        table.add_column("Min", justify="right", style="bright_blue")
        table.add_column("Avg", justify="right", style="bold bright_green")
        table.add_column("Max", justify="right", style="bright_blue")
        table.add_column("Jitter", justify="right", style="yellow")
        table.add_column("Grade", justify="center", style="bold")

        for result in results:
            # Extract metrics
            target = result.get("name", result.get("host", "unknown"))
            packets = result.get("packets_received", 0)
            total = result.get("packets_sent", packets)
            loss_pct = result.get("packet_loss_pct", 0.0)
            min_ms = result.get("min_ms", 0.0)
            avg_ms = result.get("avg_ms", 0.0)
            max_ms = result.get("max_ms", 0.0)
            stddev_ms = result.get("stddev_ms", 0.0)

            # Determine distance category
            distance = "regional"
            if avg_ms < 2:
                distance = "same-region"
            elif avg_ms > 50:
                distance = "cross-country"

            # Grade performance
            grade, grade_emoji, grade_color = self.grader.grade_latency(avg_ms, distance)
            loss_emoji, loss_color = self.grader.grade_packet_loss(loss_pct)
            jitter_emoji, jitter_color = self.grader.grade_jitter(stddev_ms)

            # Format values with colors
            packets_str = f"{packets}/{total}"
            loss_str = f"[{loss_color}]{loss_pct:.1f}% {loss_emoji}[/{loss_color}]"
            min_str = f"{min_ms:.2f}ms"
            avg_str = f"[bold]{avg_ms:.2f}ms[/bold]"
            max_str = f"{max_ms:.2f}ms"
            jitter_str = f"[{jitter_color}]{stddev_ms:.2f}ms {jitter_emoji}[/{jitter_color}]"
            grade_str = f"[{grade_color}]{grade} {grade_emoji}[/{grade_color}]"

            # Add special indicator for problem IPs
            if "problem" in target.lower() or "134.70.16.1" in target:
                target = f"⚠️  {target}"

            table.add_row(
                target,
                packets_str,
                loss_str,
                min_str,
                avg_str,
                max_str,
                jitter_str,
                grade_str
            )

        self.console.print(table)

    def print_dns_results(
        self,
        probe_id: str,
        results: List[Dict[str, Any]]
    ):
        """Print beautiful DNS resolution results."""
        table = Table(
            title=f"🌐 DNS Resolution: {probe_id}",
            box=ROUNDED,
            show_header=True,
            header_style="bold bright_magenta"
        )

        table.add_column("Hostname", style="cyan", no_wrap=True)
        table.add_column("Record Type", justify="center", style="yellow")
        table.add_column("Resolved IPs", style="bright_green")
        table.add_column("Status", justify="center", style="white")

        for result in results:
            hostname = result.get("name", "unknown")
            qtype = result.get("qtype", "A")
            ips = result.get("resolved_ips", [])
            status = result.get("status", "unknown")

            # Format IPs
            if ips:
                ip_str = ", ".join(ips[:3])  # Show first 3
                if len(ips) > 3:
                    ip_str += f" [dim](+{len(ips)-3} more)[/dim]"
                status_str = "[bright_green]✅ Success[/bright_green]"
            else:
                ip_str = "[dim]No records[/dim]"
                status_str = "[red]❌ Failed[/red]"

            table.add_row(hostname, qtype, ip_str, status_str)

        self.console.print(table)

    def print_summary_statistics(self, stats: Dict[str, Any]):
        """Print beautiful summary statistics."""
        # Create summary panels
        layout = Layout()

        # Overall health panel
        health = stats.get("overall_health", "UNKNOWN")
        health_emoji = {"EXCELLENT": "🟢", "GOOD": "🟡", "FAIR": "🟠", "POOR": "🔴"}.get(health, "⚪")

        health_text = Text(f"{health_emoji} {health}", style="bold", justify="center")
        health_panel = Panel(
            health_text,
            title="Overall Health",
            border_style="green" if health == "EXCELLENT" else "yellow",
            box=HEAVY
        )

        # Stats table
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="bold cyan", justify="right")
        stats_table.add_column(style="white")

        stats_table.add_row("Total Tests:", str(stats.get("total_tests", 0)))
        stats_table.add_row("Successful:", f"[green]{stats.get('successful_tests', 0)}[/green]")
        stats_table.add_row("Failed:", f"[red]{stats.get('failed_tests', 0)}[/red]")
        stats_table.add_row("Packet Loss:", f"{stats.get('avg_packet_loss', 0):.2f}%")
        stats_table.add_row("Avg Latency:", f"{stats.get('avg_latency', 0):.2f}ms")
        stats_table.add_row("Avg Jitter:", f"{stats.get('avg_jitter', 0):.2f}ms")

        stats_panel = Panel(
            stats_table,
            title="📊 Test Statistics",
            border_style="blue",
            box=ROUNDED
        )

        self.console.print(health_panel)
        self.console.print(stats_panel)

    def print_champions(self, champions: Dict[str, Any]):
        """Print performance champions."""
        tree = Tree("🏆 [bold yellow]Performance Champions[/bold yellow]")

        if "best_overall" in champions:
            best = champions["best_overall"]
            tree.add(f"🥇 Best Overall: [bright_green]{best['route']} ({best['latency']:.2f}ms)[/bright_green]")

        if "best_regional" in champions:
            best = champions["best_regional"]
            tree.add(f"🥈 Best Regional: [green]{best['route']} ({best['latency']:.2f}ms)[/green]")

        if "best_cross_country" in champions:
            best = champions["best_cross_country"]
            tree.add(f"🥉 Best Cross-Country: [yellow]{best['route']} ({best['latency']:.2f}ms)[/yellow]")

        panel = Panel(tree, border_style="yellow", box=HEAVY)
        self.console.print(panel)

    def print_problem_ip_status(self, ip: str, status: Dict[str, Any]):
        """Print problem IP monitoring status."""
        current_latency = status.get("current_latency", 0)
        historical_latency = status.get("historical_latency", 0)
        improvement = status.get("improvement_pct", 0)

        if improvement > 50:
            status_emoji = "✅"
            status_color = "bright_green"
            status_text = "RESOLVED"
        elif improvement > 0:
            status_emoji = "⚠️"
            status_color = "yellow"
            status_text = "IMPROVED"
        else:
            status_emoji = "❌"
            status_color = "red"
            status_text = "ISSUE"

        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="bold cyan", justify="right")
        info_table.add_column(style="white")

        info_table.add_row("IP Address:", f"[bold]{ip}[/bold]")
        info_table.add_row("Historical:", f"[red]{historical_latency:.2f}ms[/red]")
        info_table.add_row("Current:", f"[{status_color}]{current_latency:.2f}ms[/{status_color}]")
        info_table.add_row("Improvement:", f"[{status_color}]{improvement:.1f}%[/{status_color}]")
        info_table.add_row("Status:", f"[{status_color}]{status_emoji} {status_text}[/{status_color}]")

        panel = Panel(
            info_table,
            title="🔍 Problem IP Monitor: 134.70.16.1",
            border_style=status_color,
            box=HEAVY
        )

        self.console.print(panel)

    def create_progress_bar(self, total: int, description: str = "Testing") -> Progress:
        """Create a beautiful progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="bright_green", finished_style="green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        )

    def print_error(self, message: str, details: Optional[str] = None):
        """Print error message."""
        text = Text(f"❌ {message}", style="bold red")
        if details:
            text.append(f"\n\n{details}", style="dim red")

        panel = Panel(text, title="Error", border_style="red", box=HEAVY)
        self.console.print(panel)

    def print_success(self, message: str):
        """Print success message."""
        text = Text(f"✅ {message}", style="bold green")
        panel = Panel(text, border_style="green", box=ROUNDED)
        self.console.print(panel)

    def print_mtr_results(
        self,
        probe_id: str,
        probe_location: str,
        results: List[Dict[str, Any]]
    ):
        """Print beautiful MTR (traceroute) results."""
        for result in results:
            target = result.get("name", result.get("target", "unknown"))
            status = result.get("status", "unknown")

            if status != "success" or not result.get("hops"):
                continue

            table = Table(
                title=f"🗺️  MTR Path Analysis: {probe_id} → {target}",
                box=ROUNDED,
                show_header=True,
                header_style="bold bright_cyan"
            )

            table.add_column("Hop", style="cyan", justify="right", width=4)
            table.add_column("Host", style="white", no_wrap=True)
            table.add_column("Loss", justify="center", width=7)
            table.add_column("Sent", justify="center", width=5)
            table.add_column("Avg", justify="right", width=8)
            table.add_column("Best", justify="right", width=8)
            table.add_column("Worst", justify="right", width=8)
            table.add_column("StDev", justify="right", width=7)

            for hop in result.get("hops", []):
                hop_num = str(hop.get("hop", "?"))
                host = hop.get("host", "???")
                loss_pct = hop.get("loss_pct", 0.0)
                sent = hop.get("packets_sent", 0)
                avg_ms = hop.get("avg_ms", 0.0)
                best_ms = hop.get("best_ms", 0.0)
                worst_ms = hop.get("worst_ms", 0.0)
                stddev_ms = hop.get("stddev_ms", 0.0)

                # Color code loss
                if loss_pct == 0:
                    loss_str = f"[green]{loss_pct:.1f}%[/green]"
                elif loss_pct < 5:
                    loss_str = f"[yellow]{loss_pct:.1f}%[/yellow]"
                else:
                    loss_str = f"[red]{loss_pct:.1f}%[/red]"

                # Highlight high latency hops
                if avg_ms > 100:
                    avg_str = f"[red]{avg_ms:.2f}ms[/red]"
                elif avg_ms > 50:
                    avg_str = f"[yellow]{avg_ms:.2f}ms[/yellow]"
                else:
                    avg_str = f"[green]{avg_ms:.2f}ms[/green]"

                table.add_row(
                    hop_num,
                    host[:40],  # Truncate long hostnames
                    loss_str,
                    str(sent),
                    avg_str,
                    f"{best_ms:.2f}ms",
                    f"{worst_ms:.2f}ms",
                    f"{stddev_ms:.2f}ms"
                )

            self.console.print(table)

            # Show summary if available
            summary = result.get("summary", {})
            if summary:
                self._print_mtr_summary(summary)

    def _print_mtr_summary(self, summary: Dict[str, Any]):
        """Print MTR summary panel."""
        path_quality = summary.get("path_quality", "unknown")
        quality_color = {
            "excellent": "bright_green",
            "good": "green",
            "acceptable": "yellow",
            "fair": "orange3",
            "unstable": "red",
            "poor": "red"
        }.get(path_quality, "white")

        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="bold cyan", justify="right")
        info_table.add_column(style="white")

        final_hop = summary.get("final_hop", {})
        info_table.add_row("Total Hops:", str(summary.get("total_hops", 0)))
        info_table.add_row("Path Quality:", f"[{quality_color}]{path_quality.upper()}[/{quality_color}]")
        info_table.add_row("Final Latency:", f"{final_hop.get('avg_ms', 0):.2f}ms")
        info_table.add_row("Final Loss:", f"{final_hop.get('loss_pct', 0):.1f}%")

        problematic = summary.get("problematic_hops", [])
        if problematic:
            issues_text = "\n".join([
                f"Hop {h['hop']}: {h['issue']}" for h in problematic[:3]
            ])
            info_table.add_row("Issues:", f"[yellow]{issues_text}[/yellow]")

        panel = Panel(
            info_table,
            title="📊 Path Summary",
            border_style=quality_color,
            box=ROUNDED
        )
        self.console.print(panel)

    def print_http_timing_results(
        self,
        probe_id: str,
        results: List[Dict[str, Any]]
    ):
        """Print detailed HTTP timing breakdown."""
        for result in results:
            if result.get("status") != "success":
                continue

            stats = result.get("statistics", {})
            if not stats:
                continue

            url = result.get("url", "unknown")

            table = Table(
                title=f"🌐 HTTP Timing Breakdown: {url}",
                box=ROUNDED,
                show_header=True,
                header_style="bold bright_magenta"
            )

            table.add_column("Phase", style="cyan")
            table.add_column("Min", justify="right", style="bright_blue")
            table.add_column("Avg", justify="right", style="bold bright_green")
            table.add_column("Max", justify="right", style="bright_blue")
            table.add_column("Median", justify="right", style="yellow")

            phases = [
                ("DNS Lookup", stats.get("dns_lookup", {})),
                ("TCP Handshake", stats.get("tcp_handshake", {})),
                ("TLS Handshake", stats.get("tls_handshake", {})),
                ("Server Processing", stats.get("server_processing", {})),
                ("Content Download", stats.get("content_download", {})),
                ("Total Time", stats.get("total_time", {}))
            ]

            for phase_name, phase_stats in phases:
                if not phase_stats or phase_stats.get("avg", 0) == 0:
                    continue

                table.add_row(
                    phase_name,
                    f"{phase_stats.get('min', 0):.2f}ms",
                    f"{phase_stats.get('avg', 0):.2f}ms",
                    f"{phase_stats.get('max', 0):.2f}ms",
                    f"{phase_stats.get('median', 0):.2f}ms"
                )

            self.console.print(table)

            # Additional info
            info_grid = Table.grid(padding=(0, 2))
            info_grid.add_column(style="bold cyan", justify="right")
            info_grid.add_column(style="white")

            info_grid.add_row("Status Code:", f"[green]{stats.get('status_code', 'N/A')}[/green]")
            info_grid.add_row("Content Size:", f"{stats.get('content_size_kb', 0):.2f} KB")
            info_grid.add_row("Transfer Speed:", f"{stats.get('transfer_speed_mbps', {}).get('avg', 0):.2f} Mbps")
            info_grid.add_row("Remote IP:", stats.get('remote_ip', 'unknown'))
            info_grid.add_row("Success Rate:", f"{stats.get('success_rate', 0) * 100:.1f}%")

            panel = Panel(info_grid, title="📈 Transfer Details", border_style="blue", box=ROUNDED)
            self.console.print(panel)

    def print_packet_analysis(self, analysis: Dict[str, Any]):
        """Print packet capture analysis results."""
        if not analysis or analysis.get("status") != "success":
            return

        # TCP Connection Analysis
        tcp_analysis = analysis.get("tcp_analysis", {})
        if tcp_analysis:
            tcp_table = Table.grid(padding=(0, 2))
            tcp_table.add_column(style="bold cyan", justify="right")
            tcp_table.add_column(style="white")

            tcp_table.add_row("Connection Attempts:", str(tcp_analysis.get("connection_attempts", 0)))
            tcp_table.add_row("Successful:", f"[green]{tcp_analysis.get('successful_connections', 0)}[/green]")
            tcp_table.add_row("Success Rate:", f"{tcp_analysis.get('connection_success_rate', 0):.1f}%")
            tcp_table.add_row("Graceful Closes:", str(tcp_analysis.get("graceful_closes", 0)))
            tcp_table.add_row("Forced Closes (RST):", f"[yellow]{tcp_analysis.get('forced_closes', 0)}[/yellow]")

            panel = Panel(tcp_table, title="🔌 TCP Connection Analysis", border_style="cyan", box=ROUNDED)
            self.console.print(panel)

        # Connection Quality
        quality_metrics = analysis.get("connection_metrics", {})
        if quality_metrics:
            quality_table = Table.grid(padding=(0, 2))
            quality_table.add_column(style="bold cyan", justify="right")
            quality_table.add_column(style="white")

            retrans = quality_metrics.get("retransmissions", 0)
            retrans_rate = quality_metrics.get("retransmission_rate", 0)
            quality_score = quality_metrics.get("quality_score", "unknown")

            # Color code based on severity
            if retrans_rate > 5:
                retrans_str = f"[red]{retrans} ({retrans_rate:.2f}%)[/red]"
            elif retrans_rate > 1:
                retrans_str = f"[yellow]{retrans} ({retrans_rate:.2f}%)[/yellow]"
            else:
                retrans_str = f"[green]{retrans} ({retrans_rate:.2f}%)[/green]"

            quality_table.add_row("Total Packets:", str(quality_metrics.get("total_packets", 0)))
            quality_table.add_row("Retransmissions:", retrans_str)
            quality_table.add_row("Duplicate ACKs:", str(quality_metrics.get("duplicate_acks", 0)))
            quality_table.add_row("Out-of-Order:", str(quality_metrics.get("out_of_order", 0)))
            quality_table.add_row("SACK Events:", str(quality_metrics.get("sack_events", 0)))
            quality_table.add_row("Quality Score:", f"[bold]{quality_score.upper()}[/bold]")

            quality_color = {
                "excellent": "green",
                "good": "green",
                "fair": "yellow",
                "poor": "red"
            }.get(quality_score, "white")

            panel = Panel(quality_table, title="📊 Connection Quality", border_style=quality_color, box=ROUNDED)
            self.console.print(panel)

        # Issues Detected
        issues = analysis.get("issues_detected", [])
        if issues:
            self._print_packet_issues(issues)

    def _print_packet_issues(self, issues: List[Dict[str, Any]]):
        """Print detected packet-level issues."""
        tree = Tree("⚠️  [bold yellow]Issues Detected[/bold yellow]")

        for issue in issues:
            severity = issue.get("severity", "unknown")
            description = issue.get("description", "Unknown issue")
            recommendation = issue.get("recommendation", "")

            severity_emoji = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢"
            }.get(severity, "⚪")

            severity_color = {
                "high": "red",
                "medium": "yellow",
                "low": "green"
            }.get(severity, "white")

            issue_text = f"[{severity_color}]{severity_emoji} {description}[/{severity_color}]"
            branch = tree.add(issue_text)
            if recommendation:
                branch.add(f"[dim]→ {recommendation}[/dim]")

        panel = Panel(tree, border_style="yellow", box=HEAVY)
        self.console.print(panel)

    def print_comprehensive_summary(self, result: Dict[str, Any]):
        """Print comprehensive test summary combining all diagnostics."""
        combined = result.get("combined_metrics", {})
        if not combined:
            return

        # Overall health panel
        health = combined.get("overall_health", "unknown")
        health_emoji = {
            "excellent": "🟢",
            "good": "🟡",
            "fair": "🟠",
            "poor": "🔴"
        }.get(health, "⚪")

        health_color = {
            "excellent": "bright_green",
            "good": "green",
            "fair": "yellow",
            "poor": "red"
        }.get(health, "white")

        health_text = Text(f"{health_emoji} {health.upper()}", style=f"bold {health_color}", justify="center")
        health_panel = Panel(health_text, title="Overall Health", border_style=health_color, box=HEAVY)
        self.console.print(health_panel)

        # Quality metrics
        metrics_table = Table.grid(padding=(0, 2))
        metrics_table.add_column(style="bold cyan", justify="right")
        metrics_table.add_column(style="white")

        metrics_table.add_row("Latency Quality:", f"[bold]{combined.get('latency_quality', 'unknown').upper()}[/bold]")
        metrics_table.add_row("Path Quality:", f"[bold]{combined.get('path_quality', 'unknown').upper()}[/bold]")
        metrics_table.add_row("Connection Quality:", f"[bold]{combined.get('connection_quality', 'unknown').upper()}[/bold]")

        panel = Panel(metrics_table, title="📊 Quality Metrics", border_style="blue", box=ROUNDED)
        self.console.print(panel)

        # Issues summary
        issues = combined.get("issues", [])
        if issues:
            self._print_comprehensive_issues(issues)

    def _print_comprehensive_issues(self, issues: List[Dict[str, Any]]):
        """Print comprehensive issues summary."""
        high = [i for i in issues if i.get("severity") == "high"]
        medium = [i for i in issues if i.get("severity") == "medium"]
        low = [i for i in issues if i.get("severity") == "low"]

        summary_text = Text()
        if high:
            summary_text.append(f"🔴 {len(high)} High  ", style="bold red")
        if medium:
            summary_text.append(f"🟡 {len(medium)} Medium  ", style="bold yellow")
        if low:
            summary_text.append(f"🟢 {len(low)} Low", style="bold green")

        panel = Panel(summary_text, title=f"⚠️  Issues Summary ({len(issues)} total)", border_style="yellow", box=ROUNDED)
        self.console.print(panel)

    def print_layered_analysis(self, analysis: Dict[str, Any], probe_id: str = "unknown"):
        """
        Print comprehensive layered network analysis (L3→L4→L7).

        Shows correlation between:
        - Layer 3 (ICMP, MTR path)
        - Layer 4 (TCP session)
        - Layer 7 (HTTP performance)
        """
        self.console.print()
        self.console.rule(f"[bold cyan]📊 LAYERED NETWORK ANALYSIS - {probe_id}[/bold cyan]", style="cyan")
        self.console.print()

        # Overall grade display
        grade = analysis.get("overall_grade", "?")
        grade_color = {
            "A+": "bright_green",
            "A": "green",
            "B": "yellow",
            "C": "orange3",
            "D": "red",
            "F": "red"
        }.get(grade, "white")

        grade_panel = Panel(
            Text(f"Overall Network Grade: {grade}", style=f"bold {grade_color}", justify="center"),
            border_style=grade_color,
            box=HEAVY
        )
        self.console.print(grade_panel)
        self.console.print()

        # Layer breakdown table
        layer_table = Table(title="🌐 Network Stack Analysis", box=ROUNDED, show_header=True, header_style="bold bright_yellow")
        layer_table.add_column("Layer", style="cyan", width=8)
        layer_table.add_column("Component", style="white", width=20)
        layer_table.add_column("Quality", justify="center", width=12)
        layer_table.add_column("Key Metrics", style="dim", width=40)

        # L3 Data
        l3 = analysis.get("layer3", {})
        l3_quality = l3.get("quality", "unknown")
        l3_color = {"excellent": "bright_green", "good": "green", "degraded": "red"}.get(l3_quality, "white")

        icmp = l3.get("icmp_latency", {})
        l3_metrics = f"Latency: {icmp.get('avg_ms', '?')}ms avg, {icmp.get('jitter_ms', '?')}ms jitter, {icmp.get('packet_loss_pct', '?')}% loss"

        path = l3.get("path_analysis", {})
        if path:
            l3_metrics += f"\nPath: {path.get('hop_count', '?')} hops, Quality: {path.get('path_quality', '?')}"

        layer_table.add_row(
            "L3",
            "Network/ICMP",
            Text(l3_quality.upper(), style=l3_color),
            l3_metrics
        )

        # L4 Data
        l4 = analysis.get("layer4", {})
        l4_quality = l4.get("quality", "unknown")
        l4_color = {"excellent": "bright_green", "good": "green", "degraded": "red"}.get(l4_quality, "white")

        tcp_qual = l4.get("tcp_quality", {})
        conn_metrics = l4.get("connection_metrics", {})

        l4_metrics = f"Score: {tcp_qual.get('quality_score', '?')}, Retrans: {tcp_qual.get('retransmission_rate', '?')}%"
        l4_metrics += f"\nPackets: {conn_metrics.get('total_packets', '?')}, DupACK: {conn_metrics.get('duplicate_acks', '?')}, OOO: {conn_metrics.get('out_of_order', '?')}"

        layer_table.add_row(
            "L4",
            "Transport/TCP",
            Text(l4_quality.upper(), style=l4_color),
            l4_metrics
        )

        # L7 Data
        l7 = analysis.get("layer7", {})
        l7_quality = l7.get("quality", "unknown")
        l7_color = {"excellent": "bright_green", "good": "green", "degraded": "red"}.get(l7_quality, "white")

        http_perf = l7.get("http_performance", {})
        phase_breakdown = l7.get("phase_breakdown", {})

        l7_metrics = f"Total: {http_perf.get('total_time_ms', '?')}ms"
        if phase_breakdown:
            l7_metrics += f"\nBreakdown: TCP {phase_breakdown.get('tcp_pct', '?')}%, TLS {phase_breakdown.get('tls_pct', '?')}%, Server {phase_breakdown.get('server_pct', '?')}%, DL {phase_breakdown.get('download_pct', '?')}%"

        layer_table.add_row(
            "L7",
            "Application/HTTP",
            Text(l7_quality.upper(), style=l7_color),
            l7_metrics
        )

        self.console.print(layer_table)
        self.console.print()

        # Cross-layer correlations
        correlations = analysis.get("correlations", {})
        if correlations:
            corr_tree = Tree("🔗 [bold bright_magenta]Cross-Layer Correlations[/bold bright_magenta]")

            # L3→L4
            l3_l4 = correlations.get("l3_l4", {})
            if l3_l4:
                l3_l4_branch = corr_tree.add("[cyan]L3 → L4 (Path affects TCP)[/cyan]")
                l3_l4_branch.add(f"[dim]{l3_l4.get('finding', 'No correlation data')}[/dim]")

            # L4→L7
            l4_l7 = correlations.get("l4_l7", {})
            if l4_l7:
                l4_l7_branch = corr_tree.add("[yellow]L4 → L7 (TCP affects HTTP)[/yellow]")

                # Show retransmissions by HTTP phase
                retrans_by_phase = l4_l7.get("retransmissions_by_phase", {})
                if retrans_by_phase:
                    phase_branch = l4_l7_branch.add("Retransmissions per HTTP phase:")
                    for phase, count in retrans_by_phase.items():
                        if count > 0:
                            phase_branch.add(f"[red]{phase}: {count} retransmissions[/red]")

                # Show window evolution
                window_evolution = l4_l7.get("window_evolution", [])
                if window_evolution:
                    l4_l7_branch.add(f"[dim]Window size tracked across {len(window_evolution)} events[/dim]")

                total_bytes = l4_l7.get("total_bytes", 0)
                if total_bytes:
                    l4_l7_branch.add(f"[dim]Total bytes transferred: {total_bytes:,}[/dim]")

            # End-to-end
            e2e = correlations.get("end_to_end", {})
            if e2e:
                e2e_branch = corr_tree.add("[bright_green]End-to-End Summary[/bright_green]")
                e2e_branch.add(f"[dim]{e2e.get('summary', 'No summary available')}[/dim]")

            self.console.print(corr_tree)
            self.console.print()

        # Insights
        insights = analysis.get("insights", [])
        if insights:
            self.console.print()
            insights_panel = Panel(
                Text("💡 Network Insights", style="bold bright_yellow", justify="center"),
                border_style="bright_yellow",
                box=DOUBLE
            )
            self.console.print(insights_panel)

            for insight in insights:
                severity = insight.get("severity", "info")
                layers = insight.get("layers", "")
                message = insight.get("message", "")

                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "ℹ️")
                severity_color = {"high": "red", "medium": "yellow", "low": "green"}.get(severity, "white")

                insight_text = Text()
                insight_text.append(f"{severity_emoji} ", style=severity_color)
                insight_text.append(f"[{layers}] ", style="cyan")
                insight_text.append(message, style=severity_color)

                self.console.print(insight_text)

            self.console.print()


# Global formatter instance
formatter = NetworkTestFormatter()
