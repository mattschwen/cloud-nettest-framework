"""Network throughput testing using iperf3."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient


async def iperf3_test_remote(
    host: Host,
    server: str,
    port: int = 5201,
    duration: int = 10,
    reverse: bool = False,
    udp: bool = False,
    parallel: int = 1,
) -> Dict[str, Any]:
    """Run iperf3 throughput test from remote probe host."""
    result = {
        "server": server,
        "port": port,
        "success": False,
        "throughput_mbps": None,
        "protocol": "UDP" if udp else "TCP",
        "direction": "download" if reverse else "upload",
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Check if iperf3 is available
            check_code, _, _ = await ssh.execute("which iperf3", timeout=5)
            if check_code != 0:
                result["error"] = "iperf3 not installed on probe"
                return result
            
            # Build iperf3 command
            cmd_parts = [
                "iperf3",
                "-c", server,
                "-p", str(port),
                "-t", str(duration),
                "-J",  # JSON output
            ]
            
            if reverse:
                cmd_parts.append("-R")
            if udp:
                cmd_parts.append("-u")
            if parallel > 1:
                cmd_parts.extend(["-P", str(parallel)])
            
            cmd = " ".join(cmd_parts)
            
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=duration + 30)
            
            if returncode == 0 and stdout:
                try:
                    # Parse JSON output
                    data = json.loads(stdout)
                    
                    # Extract throughput
                    if "end" in data and "sum_received" in data["end"]:
                        throughput_bps = data["end"]["sum_received"]["bits_per_second"]
                        result["throughput_mbps"] = throughput_bps / 1_000_000
                        result["success"] = True
                        
                        # Additional stats
                        result["retransmits"] = data["end"].get("sum_sent", {}).get("retransmits", 0)
                        result["bytes_transferred"] = data["end"]["sum_received"].get("bytes", 0)
                    
                except json.JSONDecodeError:
                    result["error"] = "Failed to parse iperf3 JSON output"
            else:
                result["error"] = stderr or "iperf3 test failed"
                
    except Exception as e:
        result["error"] = f"iperf3 test failed: {e}"
    
    return result


async def run_throughput_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run throughput tests for all targets from a probe host."""
    results = []
    
    for target in targets:
        server = target.get("iperf_server")
        
        if not server:
            # Skip if no iperf server specified
            results.append({
                "name": target.get("name", "throughput_test"),
                "success": False,
                "error": "No iperf server specified",
            })
            continue
        
        port = target.get("port", 5201)
        duration = target.get("duration_s", 10)
        reverse = target.get("reverse", False)
        udp = target.get("udp", False)
        parallel = target.get("parallel", 1)
        
        result = await iperf3_test_remote(
            host, server, port, duration, reverse, udp, parallel
        )
        
        result["name"] = target.get("name", f"iperf3_{server}")
        results.append(result)
    
    return results
