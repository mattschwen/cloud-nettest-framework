"""Comprehensive network diagnostics combining all test types."""

import asyncio
from typing import Any, Dict, List, Optional

from cnf.registry import Host
from cnf.tests.latency import ping_test
from cnf.tests.mtr import run_mtr_test
from cnf.tests.http import comprehensive_http_get
from cnf.tests.packet_capture import capture_during_test, PacketCapture
from cnf.tests.packet_analyzer import PacketAnalyzer


async def comprehensive_target_test(
    host: Host,
    target_ip: str,
    target_url: Optional[str] = None,
    target_name: Optional[str] = None,
    ping_count: int = 20,
    http_samples: int = 5,
    mtr_cycles: int = 10,
    capture_packets: bool = True,
    max_capture_packets: int = 2000
) -> Dict[str, Any]:
    """
    Run comprehensive diagnostics on a single target.

    Combines:
    - ICMP ping with statistics
    - MTR path analysis
    - HTTP GET with detailed timing (if URL provided)
    - Packet capture during all tests
    - Packet analysis for connection quality

    All tests run on the remote AWS probe with packet capture.
    """
    result = {
        "target": {
            "ip": target_ip,
            "url": target_url,
            "name": target_name or target_ip
        },
        "tests": {},
        "packet_analysis": None,
        "combined_metrics": {},
        "status": "unknown"
    }

    try:
        if capture_packets:
            # Run all tests with packet capture
            async with PacketCapture(host) as capture:
                # Start packet capture
                capture_start = await capture.start_capture(
                    target_ip,
                    max_packets=max_capture_packets
                )

                if capture_start["status"] == "capturing":
                    # Wait for capture to initialize
                    await asyncio.sleep(1)

                    # Run tests sequentially while capturing
                    result["tests"]["ping"] = await ping_test(host, target_ip, ping_count)
                    result["tests"]["mtr"] = await run_mtr_test(host, target_ip, report_cycles=mtr_cycles)

                    if target_url:
                        result["tests"]["http"] = await comprehensive_http_get(host, target_url, http_samples)

                    # Wait for packets to settle
                    await asyncio.sleep(2)

                    # Stop capture
                    capture_stop = await capture.stop_capture()
                    result["capture_info"] = capture_stop

                    # Analyze packets if we captured any
                    if capture_stop.get("packet_count", 0) > 0:
                        analyzer = PacketAnalyzer(host, capture.capture_file)
                        result["packet_analysis"] = await analyzer.analyze_full()

                else:
                    # Capture failed, run tests without it
                    result["tests"]["ping"] = await ping_test(host, target_ip, ping_count)
                    result["tests"]["mtr"] = await run_mtr_test(host, target_ip, report_cycles=mtr_cycles)

                    if target_url:
                        result["tests"]["http"] = await comprehensive_http_get(host, target_url, http_samples)

        else:
            # Run tests without capture
            result["tests"]["ping"] = await ping_test(host, target_ip, ping_count)
            result["tests"]["mtr"] = await run_mtr_test(host, target_ip, report_cycles=mtr_cycles)

            if target_url:
                result["tests"]["http"] = await comprehensive_http_get(host, target_url, http_samples)

        # Generate combined metrics
        result["combined_metrics"] = _generate_combined_metrics(result)
        result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _generate_combined_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate combined metrics from all test results."""
    metrics = {
        "overall_health": "unknown",
        "latency_quality": "unknown",
        "path_quality": "unknown",
        "connection_quality": "unknown",
        "issues": []
    }

    # Analyze ping results
    ping = result.get("tests", {}).get("ping", {})
    if ping.get("success"):
        avg_latency = ping.get("avg_ms", 0)
        loss_pct = ping.get("packet_loss_pct", 0)

        if loss_pct == 0 and avg_latency < 20:
            metrics["latency_quality"] = "excellent"
        elif loss_pct == 0 and avg_latency < 50:
            metrics["latency_quality"] = "good"
        elif loss_pct < 1:
            metrics["latency_quality"] = "fair"
        else:
            metrics["latency_quality"] = "poor"
            metrics["issues"].append({
                "type": "packet_loss",
                "severity": "high" if loss_pct > 5 else "medium",
                "value": f"{loss_pct}%"
            })

    # Analyze MTR results
    mtr = result.get("tests", {}).get("mtr", {})
    if mtr.get("status") == "success":
        summary = mtr.get("summary", {})
        metrics["path_quality"] = summary.get("path_quality", "unknown")

        if summary.get("problematic_hops"):
            for hop_issue in summary["problematic_hops"]:
                metrics["issues"].append({
                    "type": f"mtr_{hop_issue['issue']}",
                    "severity": "medium",
                    "hop": hop_issue["hop"],
                    "host": hop_issue["host"]
                })

    # Analyze packet capture
    packet_analysis = result.get("packet_analysis", {})
    if packet_analysis and packet_analysis.get("status") == "success":
        conn_metrics = packet_analysis.get("connection_metrics", {})
        metrics["connection_quality"] = conn_metrics.get("quality_score", "unknown")

        # Add packet-level issues
        for issue in packet_analysis.get("issues_detected", []):
            metrics["issues"].append(issue)

    # Determine overall health
    qualities = [
        metrics["latency_quality"],
        metrics["path_quality"],
        metrics["connection_quality"]
    ]

    if "poor" in qualities or len(metrics["issues"]) > 3:
        metrics["overall_health"] = "poor"
    elif "fair" in qualities or len(metrics["issues"]) > 1:
        metrics["overall_health"] = "fair"
    elif "good" in qualities:
        metrics["overall_health"] = "good"
    elif all(q in ["excellent", "unknown"] for q in qualities):
        metrics["overall_health"] = "excellent"
    else:
        metrics["overall_health"] = "good"

    return metrics


async def comprehensive_multi_target_test(
    host: Host,
    targets: List[Dict[str, Any]],
    concurrent: bool = False
) -> List[Dict[str, Any]]:
    """
    Run comprehensive tests on multiple targets.

    Args:
        host: Probe host to run tests from
        targets: List of target configurations with keys:
            - ip: Target IP address
            - url: Optional HTTP(S) URL
            - name: Optional display name
        concurrent: Run tests in parallel (faster but higher load)
    """
    results = []

    if concurrent:
        # Run all targets in parallel
        tasks = []
        for target in targets:
            task = comprehensive_target_test(
                host,
                target.get("ip"),
                target.get("url"),
                target.get("name"),
                capture_packets=True
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        results = [
            r if not isinstance(r, Exception)
            else {"status": "error", "error": str(r)}
            for r in results
        ]

    else:
        # Run sequentially
        for target in targets:
            result = await comprehensive_target_test(
                host,
                target.get("ip"),
                target.get("url"),
                target.get("name"),
                capture_packets=True
            )
            results.append(result)

            # Brief pause between targets
            await asyncio.sleep(2)

    return results


async def continuous_monitoring(
    host: Host,
    target_ip: str,
    duration_minutes: int = 60,
    test_interval_seconds: int = 60,
    capture_all: bool = True
) -> Dict[str, Any]:
    """
    Continuous monitoring of a target over extended period.

    Useful for:
    - Detecting intermittent issues
    - Identifying time-based patterns
    - Long-term stability testing
    - Peak vs off-peak comparison

    Args:
        host: Probe host
        target_ip: Target to monitor
        duration_minutes: How long to monitor
        test_interval_seconds: Time between test iterations
        capture_all: Capture packets for entire duration
    """
    result = {
        "target_ip": target_ip,
        "duration_minutes": duration_minutes,
        "test_interval_seconds": test_interval_seconds,
        "iterations": [],
        "summary": {},
        "status": "unknown"
    }

    total_iterations = int(duration_minutes * 60 / test_interval_seconds)

    try:
        for i in range(total_iterations):
            # Run quick test iteration
            iteration_result = {
                "iteration": i + 1,
                "timestamp": None  # Would add actual timestamp
            }

            # Quick ping test
            ping_result = await ping_test(host, target_ip, count=10)
            iteration_result["ping"] = ping_result

            result["iterations"].append(iteration_result)

            # Sleep until next iteration
            if i < total_iterations - 1:
                await asyncio.sleep(test_interval_seconds)

        # Generate summary statistics
        result["summary"] = _generate_monitoring_summary(result["iterations"])
        result["status"] = "completed"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _generate_monitoring_summary(iterations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary from continuous monitoring iterations."""
    if not iterations:
        return {}

    latencies = []
    loss_values = []

    for iteration in iterations:
        ping = iteration.get("ping", {})
        if ping.get("success"):
            latencies.append(ping.get("avg_ms", 0))
            loss_values.append(ping.get("packet_loss_pct", 0))

    if not latencies:
        return {"status": "no_data"}

    return {
        "total_iterations": len(iterations),
        "latency": {
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "avg": round(sum(latencies) / len(latencies), 2),
            "median": round(sorted(latencies)[len(latencies) // 2], 2),
            "variability": round(max(latencies) - min(latencies), 2)
        },
        "packet_loss": {
            "min": round(min(loss_values), 2),
            "max": round(max(loss_values), 2),
            "avg": round(sum(loss_values) / len(loss_values), 2)
        },
        "stability": "stable" if max(latencies) - min(latencies) < 20 else "variable"
    }
