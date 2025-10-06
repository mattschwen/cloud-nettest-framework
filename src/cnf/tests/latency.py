"""ICMP ping and TCP latency tests."""

import asyncio
import re
from typing import Any, Dict, List, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient
from cnf.utils import Timer


def parse_ping_output(output: str) -> Dict[str, Any]:
    """Parse ping command output to extract statistics."""
    stats = {
        "packets_sent": 0,
        "packets_received": 0,
        "packet_loss_pct": 100.0,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "stddev_ms": None,
    }
    
    # Parse transmitted/received
    match = re.search(r'(\d+) packets transmitted, (\d+).*received', output)
    if match:
        stats["packets_sent"] = int(match.group(1))
        stats["packets_received"] = int(match.group(2))
        if stats["packets_sent"] > 0:
            stats["packet_loss_pct"] = ((stats["packets_sent"] - stats["packets_received"]) / stats["packets_sent"]) * 100
    
    # Parse rtt statistics (min/avg/max/stddev)
    match = re.search(r'rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', output)
    if match:
        stats["min_ms"] = float(match.group(1))
        stats["avg_ms"] = float(match.group(2))
        stats["max_ms"] = float(match.group(3))
        stats["stddev_ms"] = float(match.group(4))
    
    return stats


async def ping_test_remote(host: Host, target: str, count: int = 4, timeout: int = 10) -> Dict[str, Any]:
    """Run ICMP ping test from remote probe host."""
    result = {
        "target": target,
        "test_type": "icmp_ping",
        "success": False,
        "stats": None,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            cmd = f"ping -c {count} -W {timeout} {target}"
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=timeout + 5)
            
            if returncode == 0 or "packets transmitted" in stdout:
                result["success"] = True
                result["stats"] = parse_ping_output(stdout)
            else:
                result["error"] = stderr or "Ping failed"
                
    except Exception as e:
        result["error"] = f"Remote ping failed: {e}"
    
    return result


async def tcp_ping_remote(host: Host, target: str, port: int = 443, count: int = 4) -> Dict[str, Any]:
    """Run TCP connection timing test from remote probe host."""
    result = {
        "target": target,
        "port": port,
        "test_type": "tcp_connect",
        "success": False,
        "connect_times_ms": [],
        "avg_ms": None,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            connect_times = []
            
            for i in range(count):
                # Use nc (netcat) or bash TCP device for timing
                cmd = f"timeout 5 bash -c 'time echo > /dev/tcp/{target}/{port}' 2>&1 || true"
                returncode, stdout, stderr = await ssh.execute(cmd, timeout=10)
                
                # Parse time output (real time)
                time_match = re.search(r'real\s+0m([\d.]+)s', stdout + stderr)
                if time_match:
                    connect_time_ms = float(time_match.group(1)) * 1000
                    connect_times.append(connect_time_ms)
                
                await asyncio.sleep(0.2)  # Small delay between attempts
            
            if connect_times:
                result["success"] = True
                result["connect_times_ms"] = connect_times
                result["avg_ms"] = sum(connect_times) / len(connect_times)
            else:
                result["error"] = "No successful connections"
                
    except Exception as e:
        result["error"] = f"TCP ping failed: {e}"
    
    return result


async def run_latency_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run latency tests for all targets from a probe host."""
    results = []
    
    for target_config in targets:
        target = target_config.get("host")
        mode = target_config.get("mode", "icmp")
        count = target_config.get("count", 10)
        fallback_port = target_config.get("fallback_tcp_port")
        alert_threshold = target_config.get("alert_threshold")
        
        if mode == "icmp":
            # Try ICMP first
            result = await ping_test_remote(host, target, count=count)
            
            # Fallback to TCP if ICMP fails and fallback port specified
            if not result["success"] and fallback_port:
                tcp_result = await tcp_ping_remote(host, target, port=fallback_port, count=count)
                if tcp_result["success"]:
                    result = tcp_result
        
        elif mode == "tcp":
            port = target_config.get("port", 443)
            result = await tcp_ping_remote(host, target, port=port, count=count)
        
        else:
            result = {
                "target": target,
                "error": f"Unknown mode: {mode}",
                "success": False,
            }
        
        # Check alert threshold
        if alert_threshold and result.get("stats", {}).get("avg_ms"):
            if result["stats"]["avg_ms"] > alert_threshold:
                result["alert"] = f"Latency {result['stats']['avg_ms']:.1f}ms exceeds threshold {alert_threshold}ms"
        
        result["name"] = target_config.get("name", target)
        results.append(result)
    
    return results


async def ping_test(target: str, count: int = 4) -> Dict[str, Any]:
    """Simple local ping test (for CLI smoke tests)."""
    result = {
        "target": target,
        "success": False,
        "error": None,
    }
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await proc.communicate()
        output = stdout.decode()
        
        if proc.returncode == 0 or "packets transmitted" in output:
            result["success"] = True
            result["stats"] = parse_ping_output(output)
        else:
            result["error"] = stderr.decode() or "Ping failed"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result
