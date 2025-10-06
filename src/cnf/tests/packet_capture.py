"""Packet capture and analysis using tcpdump on remote probes."""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from cnf.registry import Host
from cnf.ssh import SSHClient


class PacketCapture:
    """Manages packet captures on remote probe hosts."""

    def __init__(self, host: Host):
        self.host = host
        self.capture_file = None
        self.ssh = None

    async def start_capture(
        self,
        target_ip: str,
        capture_filter: Optional[str] = None,
        max_packets: int = 1000,
        max_size_mb: int = 50,
        interface: str = "any"
    ) -> Dict[str, Any]:
        """
        Start packet capture on remote host.

        Args:
            target_ip: IP address to filter on
            capture_filter: tcpdump filter expression
            max_packets: Maximum packets to capture
            max_size_mb: Maximum file size in MB
            interface: Network interface (default: any)

        Returns:
            Dict with capture metadata including remote file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.capture_file = f"/tmp/capture_{timestamp}_{target_ip.replace('.', '_')}.pcap"

        # Build tcpdump filter
        if not capture_filter:
            # Default filter: capture traffic to/from target IP
            capture_filter = f"host {target_ip}"

        # tcpdump command with options
        # -i: interface
        # -n: don't resolve names
        # -s: snapshot length (0 = capture full packet)
        # -c: packet count limit
        # -W: file size limit
        # -w: write to file
        cmd = (
            f"sudo tcpdump -i {interface} -n -s 0 "
            f"-c {max_packets} -W {max_size_mb} "
            f"-w {self.capture_file} '{capture_filter}' "
            f"> /dev/null 2>&1 &"
        )

        result = {
            "status": "unknown",
            "remote_file": self.capture_file,
            "filter": capture_filter,
            "interface": interface,
            "max_packets": max_packets
        }

        try:
            self.ssh = SSHClient(self.host)
            await self.ssh.connect()

            # Start tcpdump in background
            returncode, stdout, stderr = await self.ssh.execute(cmd, timeout=5)

            # Get tcpdump process ID
            pid_cmd = f"pgrep -f 'tcpdump.*{self.capture_file}'"
            returncode, stdout, stderr = await self.ssh.execute(pid_cmd, timeout=5)

            if stdout.strip():
                result["pid"] = stdout.strip()
                result["status"] = "capturing"
            else:
                result["status"] = "failed"
                result["error"] = "tcpdump process not found"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def stop_capture(self, timeout: int = 10) -> Dict[str, Any]:
        """Stop packet capture and return file info."""
        result = {
            "status": "unknown",
            "remote_file": self.capture_file,
            "packet_count": 0,
            "file_size_bytes": 0
        }

        try:
            if not self.ssh:
                self.ssh = SSHClient(self.host)
                await self.ssh.connect()

            # Stop tcpdump (find and kill process)
            stop_cmd = f"sudo pkill -f 'tcpdump.*{self.capture_file}'"
            await self.ssh.execute(stop_cmd, timeout=5)

            # Wait briefly for file to be written
            await asyncio.sleep(2)

            # Get file info
            stat_cmd = f"ls -l {self.capture_file} 2>/dev/null || echo 'NOT_FOUND'"
            returncode, stdout, stderr = await self.ssh.execute(stat_cmd, timeout=5)

            if "NOT_FOUND" not in stdout and stdout.strip():
                # Parse file size from ls output
                parts = stdout.strip().split()
                if len(parts) >= 5:
                    result["file_size_bytes"] = int(parts[4])
                    result["status"] = "completed"

            # Get packet count using tcpdump
            count_cmd = f"sudo tcpdump -r {self.capture_file} -n 2>/dev/null | wc -l"
            returncode, stdout, stderr = await self.ssh.execute(count_cmd, timeout=30)

            if stdout.strip():
                result["packet_count"] = int(stdout.strip())

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def analyze_capture(self) -> Dict[str, Any]:
        """Analyze packet capture and extract metrics."""
        result = {
            "file": self.capture_file,
            "status": "unknown",
            "analysis": {}
        }

        try:
            if not self.ssh:
                self.ssh = SSHClient(self.host)
                await self.ssh.connect()

            # Basic packet statistics
            stats_cmd = f"sudo tcpdump -r {self.capture_file} -n -q 2>/dev/null | head -1000"
            returncode, stdout, stderr = await self.ssh.execute(stats_cmd, timeout=30)

            # Analyze TCP flags
            tcp_analysis = await self._analyze_tcp_flags()

            # Analyze retransmissions
            retrans_analysis = await self._analyze_retransmissions()

            # Analyze connection timing
            timing_analysis = await self._analyze_connection_timing()

            result["analysis"] = {
                "tcp_flags": tcp_analysis,
                "retransmissions": retrans_analysis,
                "timing": timing_analysis
            }

            result["status"] = "success"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _analyze_tcp_flags(self) -> Dict[str, Any]:
        """Analyze TCP flags in capture."""
        # Count SYN, ACK, FIN, RST packets
        cmd = f"""
        sudo tcpdump -r {self.capture_file} -n 2>/dev/null | grep -oE 'Flags \\[[^\\]]+\\]' | sort | uniq -c
        """

        returncode, stdout, stderr = await self.ssh.execute(cmd, timeout=30)

        flags = {
            "SYN": 0,
            "SYN-ACK": 0,
            "ACK": 0,
            "FIN": 0,
            "RST": 0,
            "PSH": 0
        }

        for line in stdout.split('\n'):
            if 'S' in line and 'Flags' in line:
                count = int(line.strip().split()[0])
                if 'S.' in line:
                    flags["SYN-ACK"] += count
                elif 'S' in line:
                    flags["SYN"] += count
            if '.' in line and 'Flags' in line:
                flags["ACK"] += int(line.strip().split()[0])
            if 'F' in line:
                flags["FIN"] += 1
            if 'R' in line:
                flags["RST"] += 1
            if 'P' in line:
                flags["PSH"] += 1

        return flags

    async def _analyze_retransmissions(self) -> Dict[str, Any]:
        """Detect TCP retransmissions in capture."""
        # Use tshark if available, otherwise parse tcpdump output
        retrans_cmd = f"""
        sudo tcpdump -r {self.capture_file} -n -v 2>/dev/null | \
        grep -i "retransmission\\|duplicate\\|out-of-order" | wc -l
        """

        returncode, stdout, stderr = await self.ssh.execute(retrans_cmd, timeout=30)

        retrans_count = 0
        if stdout.strip():
            retrans_count = int(stdout.strip())

        return {
            "retransmission_count": retrans_count,
            "detected": retrans_count > 0
        }

    async def _analyze_connection_timing(self) -> Dict[str, Any]:
        """Analyze connection establishment timing from packets."""
        # Extract SYN and SYN-ACK timestamps to calculate handshake time
        cmd = f"""
        sudo tcpdump -r {self.capture_file} -n -ttt 2>/dev/null | head -50
        """

        returncode, stdout, stderr = await self.ssh.execute(cmd, timeout=30)

        timing = {
            "handshake_ms": None,
            "first_packet_time": None,
            "last_packet_time": None
        }

        lines = stdout.strip().split('\n')
        if len(lines) >= 3:
            # This is approximate - proper timing needs tshark
            timing["handshake_detected"] = True

        return timing

    async def download_capture(self, local_path: Path) -> bool:
        """Download capture file to local machine."""
        try:
            if not self.ssh:
                self.ssh = SSHClient(self.host)
                await self.ssh.connect()

            # Use scp to download file
            # Note: This is a simplified version, actual implementation
            # would use asyncssh's sftp functionality
            download_cmd = f"cat {self.capture_file}"
            returncode, stdout, stderr = await self.ssh.execute(download_cmd, timeout=60)

            if returncode == 0:
                local_path.write_bytes(stdout.encode('latin-1'))
                return True

        except Exception as e:
            print(f"Download failed: {e}")

        return False

    async def cleanup(self):
        """Remove capture file from remote host."""
        if self.capture_file and self.ssh:
            try:
                cleanup_cmd = f"sudo rm -f {self.capture_file}"
                await self.ssh.execute(cleanup_cmd, timeout=5)
            except Exception:
                pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        if self.ssh:
            await self.ssh.close()


async def capture_during_test(
    host: Host,
    target_ip: str,
    test_func,
    test_args: tuple = (),
    test_kwargs: dict = None,
    capture_filter: Optional[str] = None,
    max_packets: int = 1000
) -> Dict[str, Any]:
    """
    Run a test while capturing packets.

    Args:
        host: Probe host to run capture on
        target_ip: Target IP for packet filtering
        test_func: Async function to run during capture
        test_args: Arguments for test function
        test_kwargs: Keyword arguments for test function
        capture_filter: Optional tcpdump filter
        max_packets: Maximum packets to capture

    Returns:
        Dict with both test results and packet analysis
    """
    test_kwargs = test_kwargs or {}

    result = {
        "target_ip": target_ip,
        "test_result": None,
        "capture_result": None,
        "analysis": None,
        "status": "unknown"
    }

    async with PacketCapture(host) as capture:
        try:
            # Start capture
            capture_start = await capture.start_capture(
                target_ip,
                capture_filter=capture_filter,
                max_packets=max_packets
            )

            if capture_start["status"] != "capturing":
                result["status"] = "capture_failed"
                result["capture_result"] = capture_start
                return result

            # Wait briefly for capture to initialize
            await asyncio.sleep(1)

            # Run test
            test_result = await test_func(*test_args, **test_kwargs)
            result["test_result"] = test_result

            # Wait briefly after test completes
            await asyncio.sleep(2)

            # Stop capture
            capture_stop = await capture.stop_capture()
            result["capture_result"] = capture_stop

            # Analyze capture
            if capture_stop["status"] == "completed" and capture_stop["packet_count"] > 0:
                analysis = await capture.analyze_capture()
                result["analysis"] = analysis
                result["status"] = "success"
            else:
                result["status"] = "no_packets"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

    return result


async def multi_target_capture(
    host: Host,
    targets: List[str],
    duration_seconds: int = 60,
    max_packets: int = 5000
) -> Dict[str, Any]:
    """
    Capture packets for multiple targets simultaneously.

    Useful for comprehensive network analysis across all Oracle endpoints.
    """
    result = {
        "targets": targets,
        "duration": duration_seconds,
        "captures": [],
        "status": "unknown"
    }

    try:
        # Build filter for all targets
        filter_parts = [f"host {ip}" for ip in targets]
        capture_filter = " or ".join(filter_parts)

        async with PacketCapture(host) as capture:
            # Start capture
            start_result = await capture.start_capture(
                "multi_target",
                capture_filter=capture_filter,
                max_packets=max_packets
            )

            # Let it run for specified duration
            await asyncio.sleep(duration_seconds)

            # Stop and analyze
            stop_result = await capture.stop_capture()
            analysis_result = await capture.analyze_capture()

            result["captures"] = {
                "start": start_result,
                "stop": stop_result,
                "analysis": analysis_result
            }

            result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result
