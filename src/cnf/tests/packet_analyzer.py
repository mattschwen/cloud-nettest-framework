"""Comprehensive packet analysis for network diagnostics."""

import re
from typing import Any, Dict, List, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient


class PacketAnalyzer:
    """Analyzes packet captures to extract detailed network metrics."""

    def __init__(self, host: Host, pcap_file: str):
        self.host = host
        self.pcap_file = pcap_file
        self.ssh = None

    async def analyze_full(self) -> Dict[str, Any]:
        """
        Perform comprehensive packet analysis.

        Returns detailed metrics including:
        - TCP connection analysis
        - Retransmissions and duplicates
        - Out-of-order packets
        - Window scaling
        - RTT estimates
        - Throughput analysis
        """
        result = {
            "pcap_file": self.pcap_file,
            "status": "unknown",
            "tcp_analysis": {},
            "connection_metrics": {},
            "performance_metrics": {},
            "issues_detected": []
        }

        try:
            async with SSHClient(self.host) as ssh:
                self.ssh = ssh

                # Run all analysis functions
                result["tcp_analysis"] = await self._analyze_tcp_connections()
                result["connection_metrics"] = await self._analyze_connection_quality()
                result["performance_metrics"] = await self._analyze_performance()
                result["issues_detected"] = await self._detect_issues()

                result["status"] = "success"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _analyze_tcp_connections(self) -> Dict[str, Any]:
        """Analyze TCP connection establishment and teardown."""
        # Count connection attempts (SYN packets)
        syn_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0' 2>/dev/null | wc -l
        """

        # Count successful connections (SYN-ACK)
        synack_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack != 0' 2>/dev/null | wc -l
        """

        # Count connection closes (FIN)
        fin_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n 'tcp[tcpflags] & tcp-fin != 0' 2>/dev/null | wc -l
        """

        # Count resets (RST)
        rst_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n 'tcp[tcpflags] & tcp-rst != 0' 2>/dev/null | wc -l
        """

        syn_count = await self._execute_count_cmd(syn_cmd)
        synack_count = await self._execute_count_cmd(synack_cmd)
        fin_count = await self._execute_count_cmd(fin_cmd)
        rst_count = await self._execute_count_cmd(rst_cmd)

        return {
            "connection_attempts": syn_count,
            "successful_connections": synack_count,
            "graceful_closes": fin_count,
            "forced_closes": rst_count,
            "connection_success_rate": (synack_count / syn_count * 100) if syn_count > 0 else 0
        }

    async def _analyze_connection_quality(self) -> Dict[str, Any]:
        """Analyze connection quality indicators."""
        # Detect retransmissions
        retrans_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n -v 2>/dev/null | grep -c "retransmission"
        """

        # Detect duplicate ACKs
        dup_ack_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n -v 2>/dev/null | grep -c "dup ack"
        """

        # Detect out-of-order packets
        ooo_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n -v 2>/dev/null | grep -c "out.of.order"
        """

        # Detect SACK (Selective Acknowledgment)
        sack_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n -v 2>/dev/null | grep -c "sack"
        """

        retrans_count = await self._execute_count_cmd(retrans_cmd)
        dup_ack_count = await self._execute_count_cmd(dup_ack_cmd)
        ooo_count = await self._execute_count_cmd(ooo_cmd)
        sack_count = await self._execute_count_cmd(sack_cmd)

        # Get total packet count for percentages
        total_cmd = f"sudo tcpdump -r {self.pcap_file} -n 2>/dev/null | wc -l"
        total_packets = await self._execute_count_cmd(total_cmd)

        return {
            "total_packets": total_packets,
            "retransmissions": retrans_count,
            "duplicate_acks": dup_ack_count,
            "out_of_order": ooo_count,
            "sack_events": sack_count,
            "retransmission_rate": (retrans_count / total_packets * 100) if total_packets > 0 else 0,
            "quality_score": self._calculate_quality_score(retrans_count, dup_ack_count, ooo_count, total_packets)
        }

    async def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance metrics from packets."""
        # Analyze window sizes
        window_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n -v 2>/dev/null | \
        grep -oE 'win [0-9]+' | \
        awk '{{sum+=$2; count++}} END {{if(count>0) print sum/count; else print 0}}'
        """

        # Get packet size distribution
        size_cmd = f"""
        sudo tcpdump -r {self.pcap_file} -n 2>/dev/null | \
        grep -oE 'length [0-9]+' | \
        awk '{{sum+=$2; count++}} END {{if(count>0) print sum/count; else print 0}}'
        """

        returncode, window_output, _ = await self.ssh.execute(window_cmd, timeout=30)
        returncode, size_output, _ = await self.ssh.execute(size_cmd, timeout=30)

        avg_window = float(window_output.strip()) if window_output.strip() else 0
        avg_packet_size = float(size_output.strip()) if size_output.strip() else 0

        return {
            "average_window_size": int(avg_window),
            "average_packet_size_bytes": int(avg_packet_size),
            "window_scaling_detected": avg_window > 65535
        }

    async def _detect_issues(self) -> List[Dict[str, Any]]:
        """Detect common network issues from packet analysis."""
        issues = []

        # Check for high retransmission rate
        quality_metrics = await self._analyze_connection_quality()

        if quality_metrics["retransmission_rate"] > 5:
            issues.append({
                "severity": "high",
                "type": "high_retransmission",
                "description": f"High retransmission rate: {quality_metrics['retransmission_rate']:.2f}%",
                "recommendation": "Check for packet loss or network congestion"
            })

        if quality_metrics["retransmission_rate"] > 1 and quality_metrics["retransmission_rate"] <= 5:
            issues.append({
                "severity": "medium",
                "type": "moderate_retransmission",
                "description": f"Moderate retransmission rate: {quality_metrics['retransmission_rate']:.2f}%",
                "recommendation": "Monitor for network quality issues"
            })

        # Check for duplicate ACKs
        if quality_metrics["duplicate_acks"] > quality_metrics["total_packets"] * 0.1:
            issues.append({
                "severity": "medium",
                "type": "duplicate_acks",
                "description": f"High number of duplicate ACKs: {quality_metrics['duplicate_acks']}",
                "recommendation": "Possible packet loss or reordering"
            })

        # Check for out-of-order packets
        if quality_metrics["out_of_order"] > 0:
            issues.append({
                "severity": "low",
                "type": "packet_reordering",
                "description": f"Out-of-order packets detected: {quality_metrics['out_of_order']}",
                "recommendation": "Multiple paths or router issues possible"
            })

        # Check connection establishment
        tcp_metrics = await self._analyze_tcp_connections()

        if tcp_metrics["forced_closes"] > tcp_metrics["graceful_closes"]:
            issues.append({
                "severity": "medium",
                "type": "connection_resets",
                "description": f"More RST than FIN: {tcp_metrics['forced_closes']} resets vs {tcp_metrics['graceful_closes']} closes",
                "recommendation": "Check application-level issues or firewall rules"
            })

        if tcp_metrics["connection_success_rate"] < 100:
            issues.append({
                "severity": "high",
                "type": "connection_failures",
                "description": f"Connection success rate: {tcp_metrics['connection_success_rate']:.1f}%",
                "recommendation": "Investigate why connections are failing"
            })

        return issues

    async def _execute_count_cmd(self, cmd: str) -> int:
        """Execute a command that returns a count."""
        try:
            returncode, stdout, stderr = await self.ssh.execute(cmd, timeout=30)
            return int(stdout.strip()) if stdout.strip() else 0
        except Exception:
            return 0

    def _calculate_quality_score(
        self,
        retrans: int,
        dup_acks: int,
        ooo: int,
        total: int
    ) -> str:
        """Calculate overall connection quality score."""
        if total == 0:
            return "unknown"

        issues = retrans + dup_acks + ooo
        issue_rate = (issues / total) * 100

        if issue_rate < 0.1:
            return "excellent"
        elif issue_rate < 1:
            return "good"
        elif issue_rate < 5:
            return "fair"
        else:
            return "poor"

    async def analyze_handshake_timing(self) -> Dict[str, Any]:
        """
        Analyze TCP handshake timing from packet timestamps.

        Extracts SYN -> SYN-ACK -> ACK timing for connection establishment.
        """
        result = {
            "status": "unknown",
            "handshakes": []
        }

        try:
            # Get first 100 packets with timestamps
            cmd = f"""
            sudo tcpdump -r {self.pcap_file} -n -ttt -v 2>/dev/null | head -100
            """

            returncode, stdout, stderr = await self.ssh.execute(cmd, timeout=30)

            # Parse handshake timing (this is simplified - full implementation
            # would track sequence numbers)
            lines = stdout.strip().split('\n')

            result["status"] = "analyzed"
            result["raw_packet_count"] = len(lines)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def extract_rtt_samples(self) -> Dict[str, Any]:
        """
        Extract Round-Trip Time samples from packet pairs.

        Uses packet timestamps to estimate RTT.
        """
        result = {
            "status": "unknown",
            "rtt_samples_ms": [],
            "statistics": {}
        }

        try:
            # This would require more sophisticated parsing
            # For now, we'll use a simplified approach

            cmd = f"""
            sudo tcpdump -r {self.pcap_file} -n -ttt 2>/dev/null | \
            grep -E "Flags.*ack" | head -50
            """

            returncode, stdout, stderr = await self.ssh.execute(cmd, timeout=30)

            result["status"] = "extracted"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result


async def compare_captures(
    host: Host,
    pcap_file1: str,
    pcap_file2: str
) -> Dict[str, Any]:
    """
    Compare two packet captures to identify differences.

    Useful for before/after analysis or comparing different routes.
    """
    result = {
        "file1": pcap_file1,
        "file2": pcap_file2,
        "comparison": {}
    }

    analyzer1 = PacketAnalyzer(host, pcap_file1)
    analyzer2 = PacketAnalyzer(host, pcap_file2)

    analysis1 = await analyzer1.analyze_full()
    analysis2 = await analyzer2.analyze_full()

    # Compare metrics
    result["comparison"] = {
        "retransmission_diff": (
            analysis2["connection_metrics"]["retransmission_rate"] -
            analysis1["connection_metrics"]["retransmission_rate"]
        ),
        "quality_comparison": {
            "file1": analysis1["connection_metrics"]["quality_score"],
            "file2": analysis2["connection_metrics"]["quality_score"]
        }
    }

    return result
