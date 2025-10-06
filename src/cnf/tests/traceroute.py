"""Traceroute and MTR network path analysis."""

import asyncio
import re
from typing import Any, Dict, List

from cnf.registry import Host
from cnf.ssh import SSHClient


async def traceroute_remote(host: Host, target: str, max_hops: int = 30, mode: str = "icmp", port: int = 443) -> Dict[str, Any]:
    """Run traceroute from remote probe host."""
    result = {
        "target": target,
        "mode": mode,
        "success": False,
        "hops": [],
        "total_hops": 0,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Construct traceroute command based on mode
            if mode == "tcp":
                cmd = f"traceroute -T -p {port} -m {max_hops} -w 5 {target} 2>&1"
            elif mode == "udp":
                cmd = f"traceroute -U -m {max_hops} -w 5 {target} 2>&1"
            else:  # icmp
                cmd = f"traceroute -I -m {max_hops} -w 5 {target} 2>&1"
            
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=max_hops * 5 + 10)
            
            if stdout:
                result["success"] = True
                
                # Parse traceroute output
                lines = stdout.strip().split('\n')
                for line in lines[1:]:  # Skip first line (header)
                    hop_match = re.match(r'\s*(\d+)\s+(.+)', line)
                    if hop_match:
                        hop_num = int(hop_match.group(1))
                        hop_data = hop_match.group(2).strip()
                        
                        hop_info = {
                            "hop": hop_num,
                            "raw": hop_data,
                        }
                        
                        # Try to parse IP and latency
                        ip_match = re.search(r'\(?([\d.]+)\)?', hop_data)
                        if ip_match:
                            hop_info["ip"] = ip_match.group(1)
                        
                        # Parse latencies (ms)
                        latencies = re.findall(r'([\d.]+)\s*ms', hop_data)
                        if latencies:
                            hop_info["latencies_ms"] = [float(l) for l in latencies]
                            hop_info["avg_latency_ms"] = sum(hop_info["latencies_ms"]) / len(hop_info["latencies_ms"])
                        
                        result["hops"].append(hop_info)
                
                result["total_hops"] = len(result["hops"])
            else:
                result["error"] = stderr or "No output"
                
    except Exception as e:
        result["error"] = f"Traceroute failed: {e}"
    
    return result


async def mtr_remote(host: Host, target: str, count: int = 10, timeout: int = 60) -> Dict[str, Any]:
    """Run MTR (My TraceRoute) from remote probe host."""
    result = {
        "target": target,
        "success": False,
        "hops": [],
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Run MTR in report mode with JSON output if available
            cmd = f"mtr -r -c {count} -w {target} 2>&1"
            
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=timeout)
            
            if stdout and "HOST:" in stdout:
                result["success"] = True
                result["raw_output"] = stdout
                
                # Parse MTR output (basic parsing)
                lines = stdout.strip().split('\n')
                for line in lines:
                    if line.strip().startswith(('HOST:', 'Start:')):
                        continue
                    
                    # Parse MTR line format
                    parts = line.split()
                    if len(parts) >= 7:
                        try:
                            hop_info = {
                                "hop": int(parts[0].rstrip('.')),
                                "host": parts[1],
                                "loss_pct": float(parts[2].rstrip('%')),
                                "sent": int(parts[3]),
                                "last_ms": float(parts[4]),
                                "avg_ms": float(parts[5]),
                                "best_ms": float(parts[6]),
                                "worst_ms": float(parts[7]) if len(parts) > 7 else None,
                                "stddev_ms": float(parts[8]) if len(parts) > 8 else None,
                            }
                            result["hops"].append(hop_info)
                        except (ValueError, IndexError):
                            continue
            else:
                result["error"] = "MTR not available or failed"
                
    except Exception as e:
        result["error"] = f"MTR failed: {e}"
    
    return result


async def run_traceroute_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run traceroute/MTR tests for all targets from a probe host."""
    results = []
    
    for target in targets:
        target_host = target.get("host")
        max_hops = target.get("max_hops", 30)
        mode = target.get("mode", "icmp")
        port = target.get("port", 443)
        use_mtr = target.get("use_mtr", False)
        
        if use_mtr:
            result = await mtr_remote(host, target_host, count=target.get("count", 10))
        else:
            result = await traceroute_remote(host, target_host, max_hops, mode, port)
        
        result["name"] = target.get("name", target_host)
        results.append(result)
    
    return results
