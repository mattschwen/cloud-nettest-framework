"""HTTP/HTTPS request testing with timing breakdown."""

import asyncio
import time
from typing import Any, Dict, List

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


async def run_http_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run HTTP tests for all targets from a probe host."""
    results = []
    
    for target in targets:
        url = target.get("url")
        method = target.get("method", "GET")
        retries = target.get("retries", 0)
        timeout = target.get("timeout_s", 15)
        expected_status = target.get("expected_status", [200])
        
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
