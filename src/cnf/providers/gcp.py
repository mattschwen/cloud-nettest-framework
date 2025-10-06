"""GCP-specific provider module."""

from typing import Any, Dict, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient


class GCPProvider:
    """Google Cloud Platform provider specific functionality."""
    
    @staticmethod
    def get_default_ssh_user() -> str:
        """Get default SSH user for GCP instances."""
        return "debian"  # Common for Debian images
    
    @staticmethod
    def get_package_manager() -> str:
        """Get package manager for GCP instances."""
        return "apt"  # Assuming Debian/Ubuntu
    
    @staticmethod
    async def get_instance_metadata(host: Host) -> Dict[str, Any]:
        """Fetch GCP Compute Engine instance metadata."""
        metadata = {
            "provider": "gcp",
            "instance_id": None,
            "instance_name": None,
            "machine_type": None,
            "zone": None,
            "project_id": None,
        }
        
        try:
            async with SSHClient(host) as ssh:
                # Helper to get GCP metadata
                async def get_metadata(path: str) -> Optional[str]:
                    cmd = (
                        f"curl -H 'Metadata-Flavor: Google' "
                        f"'http://metadata.google.internal/computeMetadata/v1/{path}' "
                        f"2>/dev/null"
                    )
                    returncode, stdout, _ = await ssh.execute(cmd, timeout=5)
                    return stdout.strip() if returncode == 0 else None
                
                metadata["instance_id"] = await get_metadata("instance/id")
                metadata["instance_name"] = await get_metadata("instance/name")
                metadata["machine_type"] = await get_metadata("instance/machine-type")
                metadata["zone"] = await get_metadata("instance/zone")
                metadata["project_id"] = await get_metadata("project/project-id")
                
                # Extract short zone name
                if metadata["zone"] and "/" in metadata["zone"]:
                    metadata["zone"] = metadata["zone"].split("/")[-1]
                
                # Extract machine type
                if metadata["machine_type"] and "/" in metadata["machine_type"]:
                    metadata["machine_type"] = metadata["machine_type"].split("/")[-1]
                    
        except Exception as e:
            metadata["error"] = f"Failed to fetch metadata: {e}"
        
        return metadata
    
    @staticmethod
    async def install_tools(host: Host, tools: list[str]) -> Dict[str, bool]:
        """Install network testing tools on GCP instance."""
        results = {}
        
        try:
            async with SSHClient(host) as ssh:
                await ssh.execute("sudo apt-get update -qq", timeout=60)
                
                for tool in tools:
                    check_code, _, _ = await ssh.execute(f"which {tool}", timeout=5)
                    
                    if check_code == 0:
                        results[tool] = True
                    else:
                        install_code, _, _ = await ssh.execute(
                            f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {tool}",
                            timeout=120
                        )
                        results[tool] = (install_code == 0)
                        
        except Exception as e:
            for tool in tools:
                results[tool] = False
        
        return results
