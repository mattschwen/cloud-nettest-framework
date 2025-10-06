"""
Layered correlation of network diagnostics from L3 to L7.

Provides deep correlation between:
- L3 (ICMP ping, MTR path)
- L4 (TCP session analysis)
- L7 (HTTP timing phases)
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from cnf.registry import Host
from cnf.ssh import SSHClient


async def correlate_tcp_to_http_phases(
    host: Host,
    capture_file: str,
    http_start_time: float,
    http_phases: Dict[str, float]
) -> Dict[str, Any]:
    """
    Correlate TCP packets to specific HTTP timing phases.

    Maps TCP events (handshake, retransmissions, window changes) to:
    - DNS lookup phase
    - TCP handshake phase
    - TLS negotiation phase
    - Server processing phase
    - Content download phase

    Args:
        host: SSH host
        capture_file: Path to pcap file on remote host
        http_start_time: Unix timestamp when HTTP request started
        http_phases: Dict with keys: dns_ms, tcp_handshake_ms, tls_handshake_ms,
                     server_process_ms, download_ms

    Returns:
        Dict with TCP events correlated to each HTTP phase
    """
    correlation = {
        "phases": {
            "tcp_handshake": {
                "duration_ms": http_phases.get("tcp_handshake_ms", 0),
                "tcp_events": []
            },
            "tls_negotiation": {
                "duration_ms": http_phases.get("tls_handshake_ms", 0),
                "tcp_events": []
            },
            "server_processing": {
                "duration_ms": http_phases.get("server_process_ms", 0),
                "tcp_events": []
            },
            "content_download": {
                "duration_ms": http_phases.get("download_ms", 0),
                "tcp_events": []
            }
        },
        "retransmissions_by_phase": {},
        "window_evolution": [],
        "total_bytes": 0,
        "status": "unknown"
    }

    try:
        async with SSHClient(host) as ssh:
            # Extract timestamped TCP events from packet capture
            tcp_events = await _extract_tcp_timeline(ssh, capture_file)

            if not tcp_events:
                correlation["status"] = "no_tcp_data"
                return correlation

            # Calculate phase boundaries
            dns_end = http_phases.get("dns_ms", 0)
            tcp_end = dns_end + http_phases.get("tcp_handshake_ms", 0)
            tls_end = tcp_end + http_phases.get("tls_handshake_ms", 0)
            server_end = tls_end + http_phases.get("server_process_ms", 0)
            download_end = server_end + http_phases.get("download_ms", 0)

            # Correlate TCP events to phases
            for event in tcp_events:
                relative_time_ms = event["relative_time_ms"]

                # Determine which phase this event belongs to
                if relative_time_ms <= tcp_end:
                    phase = "tcp_handshake"
                elif relative_time_ms <= tls_end:
                    phase = "tls_negotiation"
                elif relative_time_ms <= server_end:
                    phase = "server_processing"
                elif relative_time_ms <= download_end:
                    phase = "content_download"
                else:
                    continue  # After HTTP request completed

                # Add event to appropriate phase
                correlation["phases"][phase]["tcp_events"].append(event)

                # Track retransmissions per phase
                if event.get("is_retransmission"):
                    if phase not in correlation["retransmissions_by_phase"]:
                        correlation["retransmissions_by_phase"][phase] = 0
                    correlation["retransmissions_by_phase"][phase] += 1

                # Track window size evolution
                if "window_size" in event:
                    correlation["window_evolution"].append({
                        "time_ms": relative_time_ms,
                        "phase": phase,
                        "window_size": event["window_size"]
                    })

                # Track bytes
                if "length" in event:
                    correlation["total_bytes"] += event["length"]

            # Calculate per-phase statistics
            for phase_name, phase_data in correlation["phases"].items():
                events = phase_data["tcp_events"]
                phase_data["event_count"] = len(events)
                phase_data["retransmissions"] = correlation["retransmissions_by_phase"].get(phase_name, 0)
                phase_data["retransmission_rate"] = (
                    phase_data["retransmissions"] / len(events) * 100
                    if events else 0
                )

            correlation["status"] = "success"

    except Exception as e:
        correlation["status"] = "error"
        correlation["error"] = str(e)

    return correlation


async def _extract_tcp_timeline(ssh: SSHClient, capture_file: str) -> List[Dict[str, Any]]:
    """
    Extract timestamped TCP events from packet capture.

    Returns list of events with relative timestamps and TCP details.
    """
    events = []

    # Use tcpdump with timestamp and detailed output
    cmd = f"""sudo tcpdump -r {capture_file} -tttt -n -v tcp 2>/dev/null | head -1000"""

    result = await ssh.run_command(cmd, timeout=30)
    if result["exit_code"] != 0:
        return events

    lines = result["stdout"].strip().split("\n")
    first_timestamp = None

    for line in lines:
        if not line.strip():
            continue

        # Parse tcpdump line (simplified - real parsing would be more robust)
        # Format: timestamp IP > IP: Flags [S], seq 123, win 65535, ...
        try:
            parts = line.split()
            if len(parts) < 8:
                continue

            # Extract timestamp (first 4 parts typically)
            timestamp_str = " ".join(parts[:4])

            # Find IP addresses
            src_ip = None
            dst_ip = None
            for i, part in enumerate(parts):
                if ">" in part and i > 0:
                    src_ip = parts[i-1]
                    if i+1 < len(parts):
                        dst_ip = parts[i+1].rstrip(":")
                    break

            # Extract TCP flags
            flags = None
            for part in parts:
                if part.startswith("Flags") and "[" in parts[parts.index(part)+1]:
                    flags = parts[parts.index(part)+1].strip("[]")
                    break

            # Extract sequence numbers
            seq = None
            ack = None
            for i, part in enumerate(parts):
                if part.startswith("seq"):
                    seq = parts[i+1].rstrip(",")
                elif part.startswith("ack"):
                    ack = parts[i+1].rstrip(",")

            # Extract window size
            window = None
            for i, part in enumerate(parts):
                if part.startswith("win"):
                    window = parts[i+1].rstrip(",")

            # Extract packet length
            length = None
            for i, part in enumerate(parts):
                if part.startswith("length"):
                    length = int(parts[i+1].rstrip(","))

            # Set first timestamp as reference
            if first_timestamp is None:
                first_timestamp = 0  # Would parse actual timestamp
                relative_time = 0
            else:
                relative_time = 0  # Would calculate delta

            # Determine if retransmission (simplified)
            is_retrans = "retransmission" in line.lower()

            event = {
                "relative_time_ms": relative_time,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "flags": flags,
                "seq": seq,
                "ack": ack,
                "window_size": int(window) if window and window.isdigit() else None,
                "length": length,
                "is_retransmission": is_retrans
            }

            events.append(event)

        except Exception:
            # Skip malformed lines
            continue

    return events


async def correlate_mtr_to_tcp(
    host: Host,
    mtr_hops: List[Dict[str, Any]],
    tcp_handshake_ms: float
) -> Dict[str, Any]:
    """
    Correlate MTR hop latencies with TCP handshake timing.

    Shows how network path latency affects TCP connection establishment.

    Args:
        host: SSH host
        mtr_hops: List of MTR hop data
        tcp_handshake_ms: Actual TCP handshake time observed

    Returns:
        Correlation between expected (MTR) and actual (TCP) latency
    """
    correlation = {
        "mtr_predicted_rtt": 0,
        "tcp_actual_rtt": tcp_handshake_ms,
        "variance_ms": 0,
        "variance_percentage": 0,
        "contributing_hops": [],
        "status": "unknown"
    }

    try:
        # Calculate expected RTT from MTR (last hop latency * 2 for round trip)
        if mtr_hops:
            last_hop = mtr_hops[-1]
            mtr_predicted = last_hop.get("avg_ms", 0) * 2

            correlation["mtr_predicted_rtt"] = round(mtr_predicted, 2)
            correlation["variance_ms"] = round(tcp_handshake_ms - mtr_predicted, 2)

            if mtr_predicted > 0:
                correlation["variance_percentage"] = round(
                    (correlation["variance_ms"] / mtr_predicted) * 100, 1
                )

            # Identify hops contributing most to latency
            for hop in mtr_hops:
                if hop.get("avg_ms", 0) > 5:  # Significant latency
                    correlation["contributing_hops"].append({
                        "hop_number": hop.get("hop"),
                        "ip": hop.get("host"),
                        "latency_ms": hop.get("avg_ms"),
                        "loss_pct": hop.get("loss_pct", 0)
                    })

            correlation["status"] = "success"
        else:
            correlation["status"] = "no_mtr_data"

    except Exception as e:
        correlation["status"] = "error"
        correlation["error"] = str(e)

    return correlation


async def generate_layered_analysis(
    ping_result: Dict[str, Any],
    mtr_result: Dict[str, Any],
    http_result: Dict[str, Any],
    packet_analysis: Dict[str, Any],
    tcp_http_correlation: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive layered analysis from L3 to L7.

    Creates a unified view showing:
    - L3: ICMP latency and MTR path quality
    - L4: TCP connection quality and session behavior
    - L7: HTTP performance and phase-by-phase breakdown
    - Cross-layer correlations and insights

    Returns:
        Comprehensive multi-layer analysis with insights
    """
    analysis = {
        "layer3": {
            "icmp_latency": {},
            "path_analysis": {},
            "quality": "unknown"
        },
        "layer4": {
            "tcp_quality": {},
            "connection_metrics": {},
            "quality": "unknown"
        },
        "layer7": {
            "http_performance": {},
            "phase_breakdown": {},
            "quality": "unknown"
        },
        "correlations": {
            "l3_l4": {},  # How path affects TCP
            "l4_l7": {},  # How TCP affects HTTP
            "end_to_end": {}  # Overall insights
        },
        "insights": [],
        "overall_grade": "unknown"
    }

    # L3 Analysis
    if ping_result and ping_result.get("success"):
        analysis["layer3"]["icmp_latency"] = {
            "avg_ms": ping_result.get("avg_ms"),
            "min_ms": ping_result.get("min_ms"),
            "max_ms": ping_result.get("max_ms"),
            "jitter_ms": ping_result.get("max_ms", 0) - ping_result.get("min_ms", 0),
            "packet_loss_pct": ping_result.get("packet_loss_pct", 0)
        }

        # Grade L3 quality
        if ping_result.get("packet_loss_pct", 0) == 0 and ping_result.get("avg_ms", 999) < 20:
            analysis["layer3"]["quality"] = "excellent"
        elif ping_result.get("packet_loss_pct", 0) < 1 and ping_result.get("avg_ms", 999) < 50:
            analysis["layer3"]["quality"] = "good"
        else:
            analysis["layer3"]["quality"] = "degraded"

    if mtr_result and mtr_result.get("status") == "success":
        summary = mtr_result.get("summary", {})
        analysis["layer3"]["path_analysis"] = {
            "hop_count": summary.get("hop_count"),
            "path_quality": summary.get("path_quality"),
            "max_hop_latency": summary.get("max_hop_latency"),
            "problematic_hops": summary.get("problematic_hops", [])
        }

    # L4 Analysis
    if packet_analysis and packet_analysis.get("status") == "success":
        conn_metrics = packet_analysis.get("connection_metrics", {})
        analysis["layer4"]["tcp_quality"] = {
            "quality_score": conn_metrics.get("quality_score"),
            "retransmission_rate": conn_metrics.get("retransmission_rate_pct"),
            "connection_success_rate": conn_metrics.get("connection_success_rate")
        }

        analysis["layer4"]["connection_metrics"] = {
            "total_packets": packet_analysis.get("packet_count", 0),
            "retransmissions": conn_metrics.get("retransmissions", 0),
            "duplicate_acks": conn_metrics.get("duplicate_acks", 0),
            "out_of_order": conn_metrics.get("out_of_order", 0)
        }

        # Grade L4 quality
        quality_score = conn_metrics.get("quality_score", "unknown")
        if quality_score in ["excellent", "EXCELLENT"]:
            analysis["layer4"]["quality"] = "excellent"
        elif quality_score in ["good", "GOOD"]:
            analysis["layer4"]["quality"] = "good"
        else:
            analysis["layer4"]["quality"] = "degraded"

    # L7 Analysis
    if http_result and http_result.get("status") == "success":
        stats = http_result.get("statistics", {})

        analysis["layer7"]["http_performance"] = {
            "total_time_ms": stats.get("total", {}).get("avg"),
            "dns_ms": stats.get("dns_lookup", {}).get("avg"),
            "tcp_handshake_ms": stats.get("tcp_handshake", {}).get("avg"),
            "tls_handshake_ms": stats.get("tls_handshake", {}).get("avg"),
            "ttfb_ms": stats.get("server_processing", {}).get("avg"),
            "download_ms": stats.get("download", {}).get("avg")
        }

        analysis["layer7"]["phase_breakdown"] = {
            "dns_pct": round((stats.get("dns_lookup", {}).get("avg", 0) / stats.get("total", {}).get("avg", 1)) * 100, 1),
            "tcp_pct": round((stats.get("tcp_handshake", {}).get("avg", 0) / stats.get("total", {}).get("avg", 1)) * 100, 1),
            "tls_pct": round((stats.get("tls_handshake", {}).get("avg", 0) / stats.get("total", {}).get("avg", 1)) * 100, 1),
            "server_pct": round((stats.get("server_processing", {}).get("avg", 0) / stats.get("total", {}).get("avg", 1)) * 100, 1),
            "download_pct": round((stats.get("download", {}).get("avg", 0) / stats.get("total", {}).get("avg", 1)) * 100, 1)
        }

        # Grade L7 quality
        total_ms = stats.get("total", {}).get("avg", 999)
        if total_ms < 100:
            analysis["layer7"]["quality"] = "excellent"
        elif total_ms < 500:
            analysis["layer7"]["quality"] = "good"
        else:
            analysis["layer7"]["quality"] = "degraded"

    # Cross-layer correlations

    # L3 → L4: Does path quality affect TCP?
    if analysis["layer3"]["quality"] != "unknown" and analysis["layer4"]["quality"] != "unknown":
        if analysis["layer3"]["quality"] == "degraded" and analysis["layer4"]["quality"] == "degraded":
            analysis["correlations"]["l3_l4"]["finding"] = "Path issues causing TCP degradation"
            analysis["insights"].append({
                "type": "correlation",
                "layers": "L3→L4",
                "severity": "high",
                "message": "Network path quality is directly impacting TCP connection quality"
            })
        elif analysis["layer3"]["quality"] == "excellent" but analysis["layer4"]["quality"] == "degraded":
            analysis["correlations"]["l3_l4"]["finding"] = "TCP issues despite good path (endpoint problem?)"
            analysis["insights"].append({
                "type": "correlation",
                "layers": "L3→L4",
                "severity": "medium",
                "message": "TCP degradation not explained by network path - investigate endpoint congestion"
            })

    # L4 → L7: Does TCP affect HTTP?
    if tcp_http_correlation:
        analysis["correlations"]["l4_l7"] = tcp_http_correlation

        # Check if retransmissions happened during critical HTTP phases
        retrans_by_phase = tcp_http_correlation.get("retransmissions_by_phase", {})
        if retrans_by_phase.get("tls_negotiation", 0) > 0:
            analysis["insights"].append({
                "type": "correlation",
                "layers": "L4→L7",
                "severity": "high",
                "message": f"TCP retransmissions during TLS handshake: {retrans_by_phase['tls_negotiation']} retransmissions"
            })

    # End-to-end insights
    if all(analysis[f"layer{i}"]["quality"] == "excellent" for i in [3, 4, 7] if analysis[f"layer{i}"]["quality"] != "unknown"):
        analysis["overall_grade"] = "A+"
        analysis["correlations"]["end_to_end"]["summary"] = "Excellent performance across all layers"
    elif "degraded" in [analysis[f"layer{i}"]["quality"] for i in [3, 4, 7]]:
        analysis["overall_grade"] = "C"
        analysis["correlations"]["end_to_end"]["summary"] = "Performance degraded at one or more layers"
    else:
        analysis["overall_grade"] = "B"
        analysis["correlations"]["end_to_end"]["summary"] = "Good overall performance"

    return analysis
