"""TLS/SSL handshake and certificate tests."""

import asyncio
import ssl
from typing import Any, Dict, List

from cnf.registry import Host
from cnf.ssh import SSHClient
from cnf.utils import Timer


async def tls_test_remote(host: Host, target: str, port: int = 443, timeout: int = 10, verify: bool = True) -> Dict[str, Any]:
    """Test TLS handshake from remote probe host."""
    result = {
        "host": target,
        "port": port,
        "success": False,
        "handshake_time_ms": None,
        "cert_info": {},
        "error": None,
    }
    
    try:
        async with SSHClient(host) as ssh:
            # Use openssl s_client for TLS testing
            verify_flag = "" if verify else "-noverify"
            cmd = f"timeout {timeout} openssl s_client -connect {target}:{port} {verify_flag} -brief 2>&1 | head -20"
            
            with Timer() as timer:
                returncode, stdout, stderr = await ssh.execute(cmd, timeout=timeout + 2)
            
            # Check for successful connection
            if "Verification: OK" in stdout or "Verification error" in stdout or "CONNECTED" in stdout:
                result["success"] = True
                result["handshake_time_ms"] = timer.elapsed_ms
                
                # Parse certificate info
                if "CN =" in stdout:
                    import re
                    cn_match = re.search(r'CN\s*=\s*([^\n,]+)', stdout)
                    if cn_match:
                        result["cert_info"]["common_name"] = cn_match.group(1).strip()
                
                # Parse protocol and cipher
                protocol_match = re.search(r'Protocol\s*:\s*(\S+)', stdout)
                if protocol_match:
                    result["cert_info"]["protocol"] = protocol_match.group(1)
                
                cipher_match = re.search(r'Cipher\s*:\s*(\S+)', stdout)
                if cipher_match:
                    result["cert_info"]["cipher"] = cipher_match.group(1)
                
                # Check verification
                if "Verification: OK" in stdout:
                    result["cert_info"]["verification"] = "OK"
                elif "Verification error" in stdout:
                    result["cert_info"]["verification"] = "FAILED"
            else:
                result["error"] = "TLS handshake failed"
                
    except Exception as e:
        result["error"] = f"TLS test failed: {e}"
    
    return result


async def run_tls_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run TLS tests for all targets from a probe host."""
    results = []
    
    for target in targets:
        target_host = target.get("host")
        port = target.get("port", 443)
        timeout = target.get("timeout_s", 10)
        verify = target.get("verify", True)
        
        result = await tls_test_remote(host, target_host, port, timeout, verify)
        result["name"] = target.get("name", f"{target_host}:{port}")
        results.append(result)
    
    return results
