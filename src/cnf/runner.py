"""Test plan runner and orchestration."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from cnf.registry import load_registry, Host
from cnf.utils import ensure_dir, get_timestamp, load_yaml, save_json

console = Console()


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
        console.print(f"[cyan]Test Plan: {self.plan.get('name', 'unnamed')}[/cyan]")
        console.print(f"[dim]{self.plan.get('description', '')}[/dim]\n")
        
        # Select probes
        probes = self.select_probes()
        console.print(f"[yellow]Selected {len(probes)} probe(s)[/yellow]")
        for probe in probes:
            console.print(f"  - {probe.id} ({probe.provider}/{probe.region})")
        
        # Run tests
        results = await self.run_tests(probes)
        
        # Save results
        await self.save_results(results)
        
        return results


async def run_test_plan(plan_file: Path, output_dir: Optional[Path] = None):
    """Load and run a test plan."""
    plan = load_yaml(plan_file)
    runner = TestRunner(plan, output_dir)
    return await runner.run()
