"""Test plan runner and orchestration."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from cnf.registry import load_registry, Host
from cnf.utils import ensure_dir, get_timestamp, load_yaml, save_json
from cnf.formatter import NetworkTestFormatter

console = Console()
formatter = NetworkTestFormatter(console)


class TestRunner:
    """Orchestrates test execution across probe hosts."""
    
    def __init__(self, test_plan: Dict[str, Any], output_dir: Optional[Path] = None):
        self.plan = test_plan
        self.output_dir = output_dir or Path(f"runs/{get_timestamp('filename')}")
        self.results = []
        self.registry = load_registry()
    
    def select_probes(self) -> List[Host]:
        """Select probe hosts based on test plan criteria."""
        probe_config = self.plan.get("probes", {})
        include = probe_config.get("include", [])
        
        selected = []
        for criteria in include:
            provider = criteria.get("provider")
            regions = criteria.get("regions", [])
            status = criteria.get("status", "active")
            
            for host in self.registry.hosts:
                if provider and host.provider != provider:
                    continue
                if regions and host.region not in regions:
                    continue
                if status and host.status != status:
                    continue
                
                if host not in selected:
                    selected.append(host)
        
        # Apply limit if specified
        limit = probe_config.get("limit")
        if limit:
            selected = selected[:limit]
        
        return selected
    
    async def run_tests(self, probes: List[Host]) -> List[Dict[str, Any]]:
        """Execute all tests from the test plan."""
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running tests...", total=len(probes))
            
            for probe in probes:
                console.print(f"\n[yellow]Testing from probe: {probe.id}[/yellow]")
                
                # Run different test types
                test_results = {
                    "probe_id": probe.id,
                    "provider": probe.provider,
                    "region": probe.region,
                    "timestamp": get_timestamp(),
                    "tests": {},
                }
                
                # DNS tests
                if "dns" in self.plan.get("targets", {}):
                    from cnf.tests.dns import run_dns_tests
                    test_results["tests"]["dns"] = await run_dns_tests(
                        probe, self.plan["targets"]["dns"]
                    )
                
                # Latency tests
                if "latency" in self.plan.get("targets", {}):
                    from cnf.tests.latency import run_latency_tests
                    test_results["tests"]["latency"] = await run_latency_tests(
                        probe, self.plan["targets"]["latency"]
                    )
                
                # HTTP tests
                if "http" in self.plan.get("targets", {}):
                    from cnf.tests.http import run_http_tests
                    test_results["tests"]["http"] = await run_http_tests(
                        probe, self.plan["targets"]["http"]
                    )
                
                # TLS tests
                if "tls" in self.plan.get("targets", {}):
                    from cnf.tests.tls import run_tls_tests
                    test_results["tests"]["tls"] = await run_tls_tests(
                        probe, self.plan["targets"]["tls"]
                    )
                
                results.append(test_results)
                progress.update(task, advance=1)
        
        return results
    
    async def save_results(self, results: List[Dict[str, Any]]):
        """Save test results to output directory."""
        ensure_dir(self.output_dir)
        
        # Save raw results
        raw_file = self.output_dir / "raw_results.json"
        save_json({"results": results, "plan": self.plan}, raw_file)
        
        console.print(f"\n[green]Results saved to: {self.output_dir}[/green]")
    
    async def run(self):
        """Execute the full test run."""
        # Beautiful header
        formatter.print_header(
            "Cloud NetTest Framework - Test Execution",
            f"Running: {self.plan.get('name', 'unnamed')}"
        )

        # Select probes
        probes = self.select_probes()

        # Show test plan info
        formatter.print_test_plan_info(self.plan, probes)
        console.print()

        # Show probe list
        formatter.print_probe_list(probes)
        console.print()

        # Run tests with progress
        results = await self.run_tests(probes)

        # Display results
        self._display_results(results)

        # Save results
        await self.save_results(results)

        return results

    def _display_results(self, results: List[Dict[str, Any]]):
        """Display test results in beautiful format."""
        for result in results:
            probe_id = result.get("probe_id", "unknown")
            probe_region = result.get("region", "unknown")
            tests = result.get("tests", {})

            # DNS results
            if "dns" in tests:
                formatter.print_dns_results(probe_id, tests["dns"])
                console.print()

            # Latency results
            if "latency" in tests:
                formatter.print_latency_results(
                    probe_id,
                    probe_region,
                    tests["latency"]
                )
                console.print()

        # Calculate and show summary
        self._display_summary(results)

    def _display_summary(self, results: List[Dict[str, Any]]):
        """Display summary statistics."""
        total_tests = 0
        successful_tests = 0
        failed_tests = 0
        total_latency = 0.0
        latency_count = 0

        for result in results:
            tests = result.get("tests", {})

            # Count latency tests
            if "latency" in tests:
                for lat_test in tests["latency"]:
                    total_tests += 1
                    if lat_test.get("packet_loss_pct", 100) < 100:
                        successful_tests += 1
                        total_latency += lat_test.get("avg_ms", 0)
                        latency_count += 1
                    else:
                        failed_tests += 1

            # Count DNS tests
            if "dns" in tests:
                for dns_test in tests["dns"]:
                    total_tests += 1
                    if dns_test.get("resolved_ips"):
                        successful_tests += 1
                    else:
                        failed_tests += 1

        avg_latency = total_latency / latency_count if latency_count > 0 else 0

        # Determine health
        if failed_tests == 0 and avg_latency < 50:
            health = "EXCELLENT"
        elif failed_tests == 0 and avg_latency < 100:
            health = "GOOD"
        elif failed_tests < total_tests * 0.1:
            health = "FAIR"
        else:
            health = "POOR"

        stats = {
            "overall_health": health,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "avg_packet_loss": 0.0,
            "avg_latency": avg_latency,
            "avg_jitter": 0.0
        }

        formatter.print_summary_statistics(stats)
        console.print()


async def run_test_plan(plan_file: Path, output_dir: Optional[Path] = None):
    """Load and run a test plan."""
    plan = load_yaml(plan_file)
    runner = TestRunner(plan, output_dir)
    return await runner.run()
