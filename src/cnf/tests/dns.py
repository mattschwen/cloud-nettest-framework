"""DNS resolution and timing tests."""

import asyncio
import time
from typing import Any, Dict, List

import dns.asyncresolver
import dns.resolver
from dns.exception import DNSException

from cnf.registry import Host
from cnf.ssh import SSHClient
from cnf.utils import Timer


async def dns_query_local(hostname: str, qtype: str = "A", timeout: int = 5) -> Dict[str, Any]:
    """Perform DNS query from local machine."""
    result = {
        "hostname": hostname,
        "qtype": qtype,
        "success": False,
        "query_time_ms": None,
        "answers": [],
        "error": None,
    }
    
    try:
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        
        with Timer() as timer:
            answers = await resolver.resolve(hostname, qtype)
        
        result["success"] = True
        result["query_time_ms"] = timer.elapsed_ms
        result["answers"] = [str(rdata) for rdata in answers]
        
    except DNSException as e:
        result["error"] = f"DNS error: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
    
    return result


async def dns_query_remote(host: Host, hostname: str, qtype: str = "A", timeout: int = 5) -> Dict[str, Any]:
    """Perform DNS query from remote probe host."""
    result = {
        "hostname": hostname,
        "qtype": qtype,
        "success": False,
        "query_time_ms": None,
        "answers": [],
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Use dig for DNS query with timing
            cmd = f"dig +short +time={timeout} {hostname} {qtype}"
            
            with Timer() as timer:
                returncode, stdout, stderr = await ssh.execute(cmd, timeout=timeout + 2)
            
            if returncode == 0 and stdout.strip():
                result["success"] = True
                result["query_time_ms"] = timer.elapsed_ms
                result["answers"] = [line.strip() for line in stdout.strip().split("\n") if line.strip()]
            else:
                result["error"] = stderr or "No response"
                
    except Exception as e:
        result["error"] = f"Remote query failed: {e}"
    
    return result


async def run_dns_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run DNS tests for all targets from a probe host."""
    results = []
    
    for target in targets:
        hostname = target.get("name")
        qtype = target.get("qtype", "A")
        attempts = target.get("attempts", 1)
        timeout = target.get("timeout_s", 5)
        
        test_results = {
            "target": hostname,
            "qtype": qtype,
            "attempts": [],
            "avg_query_time_ms": None,
            "success_rate": 0.0,
        }
        
        # Run multiple attempts
        for i in range(attempts):
            attempt_result = await dns_query_remote(host, hostname, qtype, timeout)
            test_results["attempts"].append(attempt_result)
            await asyncio.sleep(0.1)  # Small delay between attempts
        
        # Calculate statistics
        successful = [a for a in test_results["attempts"] if a["success"]]
        test_results["success_rate"] = len(successful) / attempts if attempts > 0 else 0.0
        
        if successful:
            query_times = [a["query_time_ms"] for a in successful if a["query_time_ms"]]
            if query_times:
                test_results["avg_query_time_ms"] = sum(query_times) / len(query_times)
        
        results.append(test_results)
    
    return results
