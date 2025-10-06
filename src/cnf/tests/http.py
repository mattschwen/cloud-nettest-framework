"""HTTP/HTTPS request testing with comprehensive timing breakdown."""

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from cnf.registry import Host
from cnf.ssh import SSHClient
from cnf.utils import Timer


async def http_get_local(url: str, timeout: int = 15, verify: bool = True) -> Dict[str, Any]:
    """Perform HTTP GET from local machine with timing."""
    result = {
        "url": url,
        "method": "GET",
        "success": False,
        "status_code": None,
        "total_time_ms": None,
        "headers": {},
        "content_length": None,
        "error": None,
    }
    
    try:
        async with httpx.AsyncClient(verify=verify, http2=True, timeout=timeout) as client:
            with Timer() as timer:
                response = await client.get(url)
            
            result["success"] = True
            result["status_code"] = response.status_code
            result["total_time_ms"] = timer.elapsed_ms
            result["headers"] = dict(response.headers)
            result["content_length"] = len(response.content)
            
    except httpx.TimeoutException:
        result["error"] = "Request timed out"
    except httpx.HTTPError as e:
        result["error"] = f"HTTP error: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
    
    return result


async def http_test_remote(host: Host, url: str, method: str = "GET", timeout: int = 15) -> Dict[str, Any]:
    """Perform HTTP request from remote probe host using curl."""
    result = {
        "url": url,
        "method": method,
        "success": False,
        "status_code": None,
        "total_time_ms": None,
        "dns_time_ms": None,
        "connect_time_ms": None,
        "tls_time_ms": None,
        "ttfb_ms": None,
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Use curl with timing output
            curl_format = (
                'time_namelookup:%{time_namelookup}\\n'
                'time_connect:%{time_connect}\\n'
                'time_appconnect:%{time_appconnect}\\n'
                'time_starttransfer:%{time_starttransfer}\\n'
                'time_total:%{time_total}\\n'
                'http_code:%{http_code}\\n'
                'size_download:%{size_download}\\n'
            )
            
            cmd = (
                f'curl -X {method} -o /dev/null -s -w "{curl_format}" '
                f'--max-time {timeout} "{url}"'
            )
            
            returncode, stdout, stderr = await ssh.execute(cmd, timeout=timeout + 5)
            
            # Parse curl timing output
            timing_data = {}
            for line in stdout.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    timing_data[key] = value.strip()
            
            if 'http_code' in timing_data:
                result["success"] = True
                result["status_code"] = int(timing_data['http_code']) if timing_data['http_code'] else None
                
                # Convert seconds to milliseconds
                if 'time_namelookup' in timing_data:
                    result["dns_time_ms"] = float(timing_data['time_namelookup']) * 1000
                if 'time_connect' in timing_data:
                    result["connect_time_ms"] = float(timing_data['time_connect']) * 1000
                if 'time_appconnect' in timing_data:
                    tls_total = float(timing_data['time_appconnect']) * 1000
                    result["tls_time_ms"] = tls_total - (result["connect_time_ms"] or 0)
                if 'time_starttransfer' in timing_data:
                    result["ttfb_ms"] = float(timing_data['time_starttransfer']) * 1000
                if 'time_total' in timing_data:
                    result["total_time_ms"] = float(timing_data['time_total']) * 1000
            else:
                result["error"] = stderr or "Request failed"
                
    except Exception as e:
        result["error"] = f"Remote HTTP test failed: {e}"
    
    return result


async def comprehensive_http_get(
    host: Host,
    url: str,
    samples: int = 5,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Perform comprehensive HTTP GET with multiple samples and detailed analysis.

    Returns:
    - Multiple samples for statistical accuracy
    - Full timing breakdown (DNS, connect, TLS, TTFB, download)
    - Response headers and size
    - Transfer rate
    - Consistency metrics
    """
    result = {
        "url": url,
        "samples": samples,
        "individual_results": [],
        "statistics": {},
        "status": "unknown"
    }

    try:
        async with SSHClient(host) as ssh:
            for i in range(samples):
                sample_result = await _detailed_http_get(ssh, url, timeout)
                result["individual_results"].append(sample_result)

                if i < samples - 1:
                    await asyncio.sleep(0.5)  # Brief pause between samples

            # Calculate statistics
            if result["individual_results"]:
                result["statistics"] = _calculate_http_statistics(result["individual_results"])
                result["status"] = "success"
            else:
                result["status"] = "failed"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def _detailed_http_get(ssh: SSHClient, url: str, timeout: int) -> Dict[str, Any]:
    """Perform a single detailed HTTP GET with full metrics."""
    curl_format = (
        'time_namelookup:%{time_namelookup}\\n'
        'time_connect:%{time_connect}\\n'
        'time_appconnect:%{time_appconnect}\\n'
        'time_pretransfer:%{time_pretransfer}\\n'
        'time_starttransfer:%{time_starttransfer}\\n'
        'time_total:%{time_total}\\n'
        'http_code:%{http_code}\\n'
        'size_download:%{size_download}\\n'
        'size_header:%{size_header}\\n'
        'speed_download:%{speed_download}\\n'
        'remote_ip:%{remote_ip}\\n'
        'local_ip:%{local_ip}\\n'
    )

    cmd = (
        f'curl -X GET -o /dev/null -s -w "{curl_format}" '
        f'--max-time {timeout} -v "{url}" 2>&1'
    )

    returncode, stdout, stderr = await ssh.execute(cmd, timeout=timeout + 5)

    # Parse timing data
    timing = {}
    for line in stdout.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            timing[key] = value.strip()

    # Extract timing metrics (convert to ms)
    dns_ms = float(timing.get('time_namelookup', 0)) * 1000
    connect_ms = float(timing.get('time_connect', 0)) * 1000
    appconnect_ms = float(timing.get('time_appconnect', 0)) * 1000
    pretransfer_ms = float(timing.get('time_pretransfer', 0)) * 1000
    starttransfer_ms = float(timing.get('time_starttransfer', 0)) * 1000
    total_ms = float(timing.get('time_total', 0)) * 1000

    # Calculate phase durations
    tcp_handshake_ms = connect_ms - dns_ms
    tls_handshake_ms = appconnect_ms - connect_ms if appconnect_ms > 0 else 0
    server_processing_ms = starttransfer_ms - (appconnect_ms if appconnect_ms > 0 else connect_ms)
    download_ms = total_ms - starttransfer_ms

    return {
        "success": True,
        "status_code": int(timing.get('http_code', 0)),
        "timings": {
            "dns_lookup_ms": round(dns_ms, 2),
            "tcp_handshake_ms": round(tcp_handshake_ms, 2),
            "tls_handshake_ms": round(tls_handshake_ms, 2),
            "server_processing_ms": round(server_processing_ms, 2),
            "content_download_ms": round(download_ms, 2),
            "total_ms": round(total_ms, 2)
        },
        "transfer": {
            "size_bytes": int(float(timing.get('size_download', 0))),
            "header_bytes": int(float(timing.get('size_header', 0))),
            "speed_bps": int(float(timing.get('speed_download', 0))),
            "speed_mbps": round(float(timing.get('speed_download', 0)) * 8 / 1_000_000, 2)
        },
        "connection": {
            "remote_ip": timing.get('remote_ip', 'unknown'),
            "local_ip": timing.get('local_ip', 'unknown')
        }
    }


def _calculate_http_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics across multiple HTTP GET samples."""
    if not results:
        return {}

    successful_results = [r for r in results if r.get("success")]
    if not successful_results:
        return {"success_rate": 0.0}

    # Extract timing values
    total_times = [r["timings"]["total_ms"] for r in successful_results]
    dns_times = [r["timings"]["dns_lookup_ms"] for r in successful_results]
    tcp_times = [r["timings"]["tcp_handshake_ms"] for r in successful_results]
    tls_times = [r["timings"]["tls_handshake_ms"] for r in successful_results]
    server_times = [r["timings"]["server_processing_ms"] for r in successful_results]
    download_times = [r["timings"]["content_download_ms"] for r in successful_results]

    speeds_mbps = [r["transfer"]["speed_mbps"] for r in successful_results]

    def calc_stats(values):
        if not values:
            return {}
        return {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "median": round(sorted(values)[len(values) // 2], 2)
        }

    return {
        "success_rate": len(successful_results) / len(results),
        "total_time": calc_stats(total_times),
        "dns_lookup": calc_stats(dns_times),
        "tcp_handshake": calc_stats(tcp_times),
        "tls_handshake": calc_stats(tls_times),
        "server_processing": calc_stats(server_times),
        "content_download": calc_stats(download_times),
        "transfer_speed_mbps": calc_stats(speeds_mbps),
        "status_code": successful_results[0]["status_code"],
        "remote_ip": successful_results[0]["connection"]["remote_ip"],
        "content_size_kb": round(successful_results[0]["transfer"]["size_bytes"] / 1024, 2)
    }


async def run_http_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run HTTP tests for all targets from a probe host."""
    results = []

    for target in targets:
        url = target.get("url")
        method = target.get("method", "GET")
        retries = target.get("retries", 0)
        timeout = target.get("timeout_s", 15)
        expected_status = target.get("expected_status", [200])
        samples = target.get("samples", 1)

        # Use comprehensive test if samples > 1
        if samples > 1:
            result = await comprehensive_http_get(host, url, samples, timeout)
            result["name"] = target.get("name", url)
            results.append(result)
            continue

        test_result = None
        last_error = None

        # Attempt request with retries
        for attempt in range(retries + 1):
            result = await http_test_remote(host, url, method, timeout)

            if result["success"]:
                test_result = result

                # Check if status code is expected
                if expected_status and result["status_code"] not in expected_status:
                    result["warning"] = f"Unexpected status {result['status_code']}, expected {expected_status}"

                break
            else:
                last_error = result["error"]
                if attempt < retries:
                    await asyncio.sleep(1)  # Wait before retry

        if test_result is None:
            test_result = {
                "url": url,
                "method": method,
                "success": False,
                "error": last_error or "All retries failed",
            }

        test_result["name"] = target.get("name", url)
        test_result["attempts"] = retries + 1
        results.append(test_result)

    return results
