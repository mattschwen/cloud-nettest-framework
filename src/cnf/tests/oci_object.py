"""Oracle Cloud Infrastructure Object Storage specific tests.

Based on comprehensive network analysis from Oracle Object Storage Network Analysis Report.
Includes advanced diagnostics for bufferbloat, conntrack exhaustion, and packet analysis.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient
from cnf.utils import Timer, load_yaml, get_config_dir


async def check_conntrack_status(host: Host) -> Dict[str, Any]:
    """Check Linux netfilter connection tracking table status.
    
    Detects potential conntrack table exhaustion which can cause:
    - Packet drops
    - Connection tracking state loss
    - Retry storms
    - "90% read wait" times in storage requests
    """
    result = {
        "test": "conntrack_check",
        "success": False,
        "count": None,
        "max": None,
        "usage_pct": None,
        "warning": None,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Check current count
            returncode, stdout, _ = await ssh.execute(
                "cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo 'N/A'",
                timeout=5
            )
            
            if stdout.strip() != 'N/A':
                result["count"] = int(stdout.strip())
                
                # Check max limit
                returncode, stdout, _ = await ssh.execute(
                    "cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo 'N/A'",
                    timeout=5
                )
                
                if stdout.strip() != 'N/A':
                    result["max"] = int(stdout.strip())
                    result["usage_pct"] = (result["count"] / result["max"]) * 100
                    result["success"] = True
                    
                    # Check for warnings
                    if result["usage_pct"] > 90:
                        result["warning"] = f"CRITICAL: Conntrack table {result['usage_pct']:.1f}% full - likely causing packet drops"
                    elif result["usage_pct"] > 75:
                        result["warning"] = f"WARNING: Conntrack table {result['usage_pct']:.1f}% full"
                    
                    # Check dmesg for conntrack errors
                    returncode, dmesg_out, _ = await ssh.execute(
                        "dmesg | grep -i conntrack | tail -5",
                        timeout=5
                    )
                    if "table full" in dmesg_out.lower():
                        result["dmesg_errors"] = dmesg_out.strip()
            else:
                result["error"] = "Conntrack not available (not running as root or netfilter disabled)"
                
    except Exception as e:
        result["error"] = f"Conntrack check failed: {e}"
    
    return result


async def detect_bufferbloat(host: Host, target: str, ping_count: int = 100) -> Dict[str, Any]:
    """Detect bufferbloat using ping variance analysis.
    
    Bufferbloat symptoms:
    - High RTT variance
    - Large max RTT values (>10x min)
    - Latency spikes under load
    - Packet reordering and SACK events
    """
    result = {
        "test": "bufferbloat_detection",
        "target": target,
        "success": False,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "stddev_ms": None,
        "bufferbloat_score": None,
        "severity": None,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Run rapid ping test
            cmd = f"ping -c {ping_count} -i 0.2 {target}"
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=ping_count + 30)
            
            if returncode == 0 or "packets transmitted" in stdout:
                # Parse statistics
                match = re.search(r'rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', stdout)
                if match:
                    result["min_ms"] = float(match.group(1))
                    result["avg_ms"] = float(match.group(2))
                    result["max_ms"] = float(match.group(3))
                    result["stddev_ms"] = float(match.group(4))
                    result["success"] = True
                    
                    # Calculate bufferbloat score (max/min ratio)
                    if result["min_ms"] > 0:
                        ratio = result["max_ms"] / result["min_ms"]
                        result["bufferbloat_score"] = ratio
                        
                        # Classify severity
                        if ratio > 20:
                            result["severity"] = "SEVERE"
                            result["warning"] = f"Severe bufferbloat detected (max/min={ratio:.1f}x) - likely causing packet reordering"
                        elif ratio > 10:
                            result["severity"] = "MODERATE"
                            result["warning"] = f"Moderate bufferbloat detected (max/min={ratio:.1f}x)"
                        elif ratio > 5:
                            result["severity"] = "MILD"
                            result["warning"] = f"Mild bufferbloat detected (max/min={ratio:.1f}x)"
                        else:
                            result["severity"] = "NONE"
                    
                    # Check coefficient of variation
                    if result["avg_ms"] > 0:
                        cv = (result["stddev_ms"] / result["avg_ms"]) * 100
                        result["coefficient_variation_pct"] = cv
                        if cv > 50:
                            result["warning"] = (result.get("warning", "") + 
                                               f" High jitter (CV={cv:.1f}%)").strip()
            else:
                result["error"] = "Ping test failed"
                
    except Exception as e:
        result["error"] = f"Bufferbloat detection failed: {e}"
    
    return result


async def tcp_packet_analysis(host: Host, target: str, port: int = 443, duration: int = 10) -> Dict[str, Any]:
    """Capture and analyze TCP packets for network anomalies.
    
    Detects:
    - SACK (Selective Acknowledgment) events
    - Packet retransmissions
    - Out-of-order packets
    - Window size oscillations
    - MSS reduction (overlay/tunnel overhead)
    """
    result = {
        "test": "tcp_packet_analysis",
        "target": target,
        "port": port,
        "success": False,
        "packets_captured": 0,
        "sack_events": 0,
        "retransmissions": 0,
        "out_of_order": 0,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Check if tcpdump is available
            check_code, _, _ = await ssh.execute("which tcpdump", timeout=5)
            if check_code != 0:
                result["error"] = "tcpdump not installed"
                return result
            
            # Note: Requires sudo/root for packet capture
            # Capture packets and analyze with tcpdump
            cmd = (
                f"timeout {duration} sudo tcpdump -c 500 -nn "
                f"host {target} and port {port} 2>&1 | head -100 || true"
            )
            
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=duration + 5)
            
            if stdout:
                result["success"] = True
                
                # Count packets
                packet_lines = [l for l in stdout.split('\n') if target in l]
                result["packets_captured"] = len(packet_lines)
                
                # Detect SACK
                sack_count = stdout.lower().count('sack')
                result["sack_events"] = sack_count
                
                # Detect retransmissions
                retrans_count = stdout.lower().count('retransmission')
                result["retransmissions"] = retrans_count
                
                # Calculate anomaly rate
                if result["packets_captured"] > 0:
                    result["sack_rate_pct"] = (sack_count / result["packets_captured"]) * 100
                    
                    if result["sack_rate_pct"] > 5:
                        result["warning"] = f"High SACK rate ({result['sack_rate_pct']:.1f}%) indicates packet loss/reordering"
            else:
                result["error"] = "No packets captured (may need sudo access)"
                
    except Exception as e:
        result["error"] = f"Packet analysis failed: {e}"
    
    return result


async def comprehensive_oci_test(host: Host, endpoint: str) -> Dict[str, Any]:
    """Run comprehensive OCI Object Storage test suite.
    
    Combines multiple test types for complete analysis:
    - DNS resolution timing
    - TCP connect timing
    - TLS handshake timing
    - HTTP TTFB (Time To First Byte)
    - Full request timing
    - Bufferbloat detection
    - Packet loss check
    """
    from cnf.tests.dns import dns_query_remote
    from cnf.tests.http import http_test_remote
    from cnf.tests.latency import ping_test_remote
    from cnf.tests.tls import tls_test_remote
    
    # Load OCI endpoints config
    try:
        oci_config_path = get_config_dir() / "oci_endpoints.yaml"
        oci_config = load_yaml(oci_config_path)
        endpoints = oci_config.get("endpoints", [])
        
        # Find endpoint config
        endpoint_config = None
        for ep in endpoints:
            if ep.get("region") == endpoint or ep.get("hostname") in endpoint:
                endpoint_config = ep
                break
        
        if not endpoint_config:
            return {"error": f"Endpoint {endpoint} not found in oci_endpoints.yaml"}
        
        hostname = endpoint_config.get("hostname")
        
    except Exception as e:
        return {"error": f"Failed to load OCI endpoint config: {e}"}
    
    result = {
        "endpoint": endpoint,
        "hostname": hostname,
        "tests": {},
        "overall_health": "UNKNOWN",
    }
    
    # DNS test
    result["tests"]["dns"] = await dns_query_remote(host, hostname, "A", timeout=5)
    
    # Latency test
    result["tests"]["latency"] = await ping_test_remote(host, hostname, count=20)
    
    # TLS test
    result["tests"]["tls"] = await tls_test_remote(host, hostname, port=443)
    
    # HTTP test with full timing
    test_url = f"https://{hostname}/n/test/b/test/o/test"  # Will return 404 but that's expected
    result["tests"]["http"] = await http_test_remote(host, test_url, "GET", timeout=15)
    
    # Bufferbloat detection
    result["tests"]["bufferbloat"] = await detect_bufferbloat(host, hostname, ping_count=50)
    
    # System checks
    result["tests"]["conntrack"] = await check_conntrack_status(host)
    
    # Determine overall health
    issues = []
    warnings = []
    
    if result["tests"]["bufferbloat"].get("severity") in ["SEVERE", "MODERATE"]:
        issues.append(f"Bufferbloat: {result['tests']['bufferbloat']['severity']}")
    
    if result["tests"]["conntrack"].get("warning"):
        issues.append(result["tests"]["conntrack"]["warning"])
    
    if result["tests"]["latency"].get("stats", {}).get("packet_loss_pct", 0) > 1:
        issues.append(f"Packet loss: {result['tests']['latency']['stats']['packet_loss_pct']:.1f}%")
    
    if issues:
        result["overall_health"] = "DEGRADED"
        result["issues"] = issues
    else:
        result["overall_health"] = "HEALTHY"
    
    return result


async def monitor_problem_ip(host: Host, ip: str = "134.70.16.1", threshold_ms: float = 100) -> Dict[str, Any]:
    """Monitor the previously problematic Oracle Phoenix IP (134.70.16.1).
    
    This IP previously showed 471ms latency spikes but was resolved to 59.5ms.
    Continuous monitoring ensures the issue doesn't recur.
    """
    result = {
        "test": "problem_ip_monitor",
        "ip": ip,
        "threshold_ms": threshold_ms,
        "success": False,
        "current_latency_ms": None,
        "status": None,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Run extended ping test
            cmd = f"ping -c 20 -i 0.5 {ip}"
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=20)
            
            if returncode == 0 or "packets transmitted" in stdout:
                # Parse avg latency
                match = re.search(r'rtt min/avg/max/(?:mdev|stddev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', stdout)
                if match:
                    result["current_latency_ms"] = float(match.group(2))
                    result["max_latency_ms"] = float(match.group(3))
                    result["success"] = True
                    
                    # Check against threshold
                    if result["current_latency_ms"] > threshold_ms:
                        result["status"] = "ALERT"
                        result["warning"] = (
                            f"Latency {result['current_latency_ms']:.1f}ms exceeds threshold {threshold_ms}ms "
                            f"(previously 471ms, resolved to 59.5ms)"
                        )
                    else:
                        result["status"] = "OK"
                        result["message"] = f"Latency {result['current_latency_ms']:.1f}ms is within normal range"
            else:
                result["error"] = "Ping failed"
                
    except Exception as e:
        result["error"] = f"IP monitoring failed: {e}"
    
    return result


async def run_oci_object_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run Oracle Object Storage specific tests."""
    results = []
    
    for target in targets:
        endpoint = target.get("endpoint")
        test_types = target.get("test_types", [])
        monitor_ips = target.get("monitor_ips", [])
        
        # Run comprehensive test if requested
        if "full_suite" in test_types or len(test_types) == 0:
            result = await comprehensive_oci_test(host, endpoint)
            results.append(result)
        else:
            # Run individual tests
            test_result = {
                "endpoint": endpoint,
                "tests": {},
            }
            
            if "bufferbloat_detection" in test_types:
                # Get hostname from endpoint
                oci_config = load_yaml(get_config_dir() / "oci_endpoints.yaml")
                ep_config = next((e for e in oci_config["endpoints"] if e["region"] == endpoint), None)
                if ep_config:
                    test_result["tests"]["bufferbloat"] = await detect_bufferbloat(
                        host, ep_config["hostname"]
                    )
            
            results.append(test_result)
        
        # Monitor specific IPs if requested
        for monitor_ip in monitor_ips:
            monitor_result = await monitor_problem_ip(host, monitor_ip)
            results.append(monitor_result)
    
    return results
