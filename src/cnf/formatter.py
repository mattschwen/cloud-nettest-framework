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


# Global formatter instance
formatter = NetworkTestFormatter()
