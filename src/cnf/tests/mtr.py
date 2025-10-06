"""MTR (My TraceRoute) network path analysis tests."""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient


async def run_mtr_test(
    host: Host,
    target: str,
    count: int = 10,
    report_cycles: int = 10,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Run MTR test from probe host to target.

    MTR combines traceroute and ping to provide:
    - Complete path to destination
    - Packet loss at each hop
    - Latency statistics per hop
    - Jitter and standard deviation
    """
    result = {
        "target": target,
        "count": count,
        "status": "unknown",
        "hops": [],
        "summary": {},
        "raw_output": ""
    }

    try:
        async with SSHClient(host) as ssh:
            # Run MTR with JSON output for easy parsing
            # Also run text version for display
            cmd_json = f"mtr -n -c {report_cycles} -r -j {target} 2>/dev/null || echo 'MTR_FAILED'"
            cmd_text = f"mtr -n -c {report_cycles} -r {target} 2>/dev/null || mtr -c {report_cycles} -r {target}"

            # Try JSON output first (newer MTR versions)
            stdout, stderr, exit_code = await ssh.run_command(cmd_json, timeout=timeout)

            if "MTR_FAILED" in stdout or exit_code != 0:
                # Fallback to text parsing
                stdout, stderr, exit_code = await ssh.run_command(cmd_text, timeout=timeout)
                result["raw_output"] = stdout
                result["hops"] = _parse_mtr_text(stdout)
            else:
                result["raw_output"] = stdout
                result["hops"] = _parse_mtr_json(stdout)

            if result["hops"]:
                result["status"] = "success"
                result["summary"] = _generate_mtr_summary(result["hops"])
            else:
                result["status"] = "failed"
                result["error"] = "No hops parsed from MTR output"

    except asyncio.TimeoutError:
        result["status"] = "timeout"
        result["error"] = f"MTR test timed out after {timeout}s"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _parse_mtr_json(output: str) -> List[Dict[str, Any]]:
    """Parse MTR JSON output."""
    try:
        data = json.loads(output)
        hops = []

        for hop_data in data.get("report", {}).get("hubs", []):
            hop = {
                "hop": hop_data.get("count", 0),
                "host": hop_data.get("host", "???"),
                "loss_pct": hop_data.get("Loss%", 0.0),
                "packets_sent": hop_data.get("Snt", 0),
                "packets_received": hop_data.get("Rcv", 0),
                "last_ms": hop_data.get("Last", 0.0),
                "avg_ms": hop_data.get("Avg", 0.0),
                "best_ms": hop_data.get("Best", 0.0),
                "worst_ms": hop_data.get("Wrst", 0.0),
                "stddev_ms": hop_data.get("StDev", 0.0)
            }
            hops.append(hop)

        return hops
    except Exception:
        return []


def _parse_mtr_text(output: str) -> List[Dict[str, Any]]:
    """Parse MTR text output."""
    hops = []

    # MTR text format:
    # HOST: hostname                    Loss%   Snt   Last   Avg  Best  Wrst StDev
    #   1.|-- 172.31.0.1                 0.0%    10    0.3   0.3   0.2   0.4   0.1

    lines = output.split('\n')
    for line in lines:
        # Match hop lines
        match = re.match(
            r'\s*(\d+)\.\|--\s+(\S+)\s+(\d+\.\d+)%\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)',
            line
        )

        if match:
            hop_num, host, loss, sent, last, avg, best, worst, stddev = match.groups()
            hop = {
                "hop": int(hop_num),
                "host": host,
                "loss_pct": float(loss),
                "packets_sent": int(sent),
                "packets_received": int(sent) - int(float(sent) * float(loss) / 100),
                "last_ms": float(last),
                "avg_ms": float(avg),
                "best_ms": float(best),
                "worst_ms": float(worst),
                "stddev_ms": float(stddev)
            }
            hops.append(hop)

    return hops


def _generate_mtr_summary(hops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics from MTR hops."""
    if not hops:
        return {}

    total_hops = len(hops)
    final_hop = hops[-1]

    # Find problematic hops (high loss or latency spikes)
    problematic_hops = []
    for hop in hops:
        if hop["loss_pct"] > 5.0:
            problematic_hops.append({
                "hop": hop["hop"],
                "host": hop["host"],
                "issue": "high_packet_loss",
                "loss_pct": hop["loss_pct"]
            })

        # Check for latency spikes (sudden increase > 20ms from previous hop)
        if hop["hop"] > 1:
            prev_hop = hops[hop["hop"] - 2]  # -2 because hop numbers are 1-indexed
            if hop["avg_ms"] - prev_hop["avg_ms"] > 20:
                problematic_hops.append({
                    "hop": hop["hop"],
                    "host": hop["host"],
                    "issue": "latency_spike",
                    "latency_increase": hop["avg_ms"] - prev_hop["avg_ms"]
                })

    return {
        "total_hops": total_hops,
        "final_hop": {
            "host": final_hop["host"],
            "avg_ms": final_hop["avg_ms"],
            "loss_pct": final_hop["loss_pct"],
            "stddev_ms": final_hop["stddev_ms"]
        },
        "problematic_hops": problematic_hops,
        "path_quality": _assess_path_quality(hops)
    }


def _assess_path_quality(hops: List[Dict[str, Any]]) -> str:
    """Assess overall path quality based on all hops."""
    if not hops:
        return "unknown"

    max_loss = max(hop["loss_pct"] for hop in hops)
    final_hop = hops[-1]

    if max_loss > 10:
        return "poor"
    elif max_loss > 5:
        return "fair"
    elif final_hop["stddev_ms"] > 10:
        return "unstable"
    elif final_hop["avg_ms"] < 20:
        return "excellent"
    elif final_hop["avg_ms"] < 50:
        return "good"
    else:
        return "acceptable"


async def run_mtr_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run MTR tests for multiple targets."""
    results = []

    for target_config in targets:
        target = target_config.get("host") or target_config.get("name")
        count = target_config.get("count", 10)
        report_cycles = target_config.get("report_cycles", 10)
        timeout = target_config.get("timeout", 120)

        result = await run_mtr_test(host, target, count, report_cycles, timeout)
        result["name"] = target_config.get("name", target)
        results.append(result)

    return results


async def continuous_mtr(
    host: Host,
    target: str,
    duration_seconds: int = 60,
    interval: int = 1
) -> Dict[str, Any]:
    """
    Run continuous MTR for extended period to detect intermittent issues.

    Useful for identifying:
    - Route flapping
    - Intermittent packet loss
    - Latency variability over time
    """
    result = {
        "target": target,
        "duration_seconds": duration_seconds,
        "snapshots": [],
        "status": "unknown"
    }

    try:
        async with SSHClient(host) as ssh:
            # Run MTR in continuous mode for specified duration
            cmd = f"timeout {duration_seconds} mtr -n -i {interval} -c {duration_seconds // interval} -r {target}"

            stdout, stderr, exit_code = await ssh.run_command(cmd, timeout=duration_seconds + 30)

            result["raw_output"] = stdout
            result["hops"] = _parse_mtr_text(stdout)
            result["status"] = "success" if result["hops"] else "failed"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result
