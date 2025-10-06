"""SSH connectivity and remote command execution for probe nodes."""

import asyncio
from pathlib import Path
from typing import Optional, Tuple

import asyncssh
from asyncssh import SSHClientConnection

from cnf.registry import Host
from cnf.utils import expand_path


class SSHClient:
    """Async SSH client for probe nodes."""
    
    def __init__(self, host: Host):
        self.host = host
        self.conn: Optional[SSHClientConnection] = None
    
    async def connect(self, timeout: int = 10) -> SSHClientConnection:
        """Establish SSH connection to probe host."""
        ssh_key = expand_path(self.host.ssh_key or "~/.ssh/id_rsa")
        
        try:
            self.conn = await asyncio.wait_for(
                asyncssh.connect(
                    self.host.public_ip or self.host.private_ip,
                    username=self.host.ssh_user or "ubuntu",
                    client_keys=[str(ssh_key)],
                    known_hosts=None,  # Skip host key verification for automation
                ),
                timeout=timeout
            )
            return self.conn
        except asyncio.TimeoutError:
            raise ConnectionError(f"SSH connection to {self.host.id} timed out")
        except Exception as e:
            raise ConnectionError(f"SSH connection to {self.host.id} failed: {e}")
    
    async def execute(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Execute command on remote host."""
        if not self.conn:
            await self.connect()
        
        try:
            result = await asyncio.wait_for(
                self.conn.run(command),
                timeout=timeout
            )
            return result.exit_status or 0, result.stdout, result.stderr
        except asyncio.TimeoutError:
            return -1, "", f"Command timed out: {command}"
        except Exception as e:
            return -1, "", f"Command failed: {e}"
    
    async def close(self):
        """Close SSH connection."""
        if self.conn:
            self.conn.close()
            await self.conn.wait_closed()
            self.conn = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.close()


async def gather_host_facts(host: Host) -> dict:
    """Gather system facts from a probe host."""
    facts = {
        "host_id": host.id,
        "timestamp": None,
        "system": {},
        "network": {},
        "packages": {},
    }
    
    async with SSHClient(host) as ssh:
        # System info
        returncode, stdout, _ = await ssh.execute("uname -a")
        if returncode == 0:
            facts["system"]["uname"] = stdout.strip()
        
        returncode, stdout, _ = await ssh.execute("cat /etc/os-release")
        if returncode == 0:
            facts["system"]["os_release"] = stdout.strip()
        
        # CPU/Memory
        returncode, stdout, _ = await ssh.execute("nproc")
        if returncode == 0:
            facts["system"]["cpu_count"] = stdout.strip()
        
        returncode, stdout, _ = await ssh.execute("free -h")
        if returncode == 0:
            facts["system"]["memory"] = stdout.strip()
        
        # Network info
        returncode, stdout, _ = await ssh.execute("ip addr show")
        if returncode == 0:
            facts["network"]["interfaces"] = stdout.strip()
        
        returncode, stdout, _ = await ssh.execute("ip route show")
        if returncode == 0:
            facts["network"]["routes"] = stdout.strip()
        
        # Check for tools
        for tool in ["ping", "traceroute", "mtr", "iperf3", "tcpdump", "curl"]:
            returncode, stdout, _ = await ssh.execute(f"which {tool}")
            if returncode == 0:
                facts["packages"][tool] = stdout.strip()
    
    from cnf.utils import get_timestamp
    facts["timestamp"] = get_timestamp()
    
    return facts
