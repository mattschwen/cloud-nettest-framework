"""Azure-specific provider module."""

from typing import Any, Dict, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient


class AzureProvider:
    """Azure cloud provider specific functionality."""
    
    @staticmethod
    def get_default_ssh_user() -> str:
        """Get default SSH user for Azure VMs."""
        return "azureuser"
    
    @staticmethod
    def get_package_manager() -> str:
        """Get package manager for Azure VMs."""
        return "apt"  # Assuming Ubuntu
    
    @staticmethod
    async def get_instance_metadata(host: Host) -> Dict[str, Any]:
        """Fetch Azure VM instance metadata."""
        metadata = {
            "provider": "azure",
            "vm_id": None,
            "vm_size": None,
            "location": None,
            "subscription_id": None,
            "resource_group": None,
        }
        
        try:
            async with SSHClient(host) as ssh:
                # Azure Instance Metadata Service
                cmd = (
                    "curl -H Metadata:true --noproxy '*' "
                    "'http://169.254.169.254/metadata/instance?api-version=2021-02-01' "
                    "2>/dev/null"
                )
                
                returncode, stdout, _ = await ssh.execute(cmd, timeout=10)
                
                if returncode == 0 and stdout:
                    import json
                    data = json.loads(stdout)
                    
                    compute = data.get("compute", {})
                    metadata["vm_id"] = compute.get("vmId")
                    metadata["vm_size"] = compute.get("vmSize")
                    metadata["location"] = compute.get("location")
                    metadata["subscription_id"] = compute.get("subscriptionId")
                    metadata["resource_group"] = compute.get("resourceGroupName")
                    
        except Exception as e:
            metadata["error"] = f"Failed to fetch metadata: {e}"
        
        return metadata
    
    @staticmethod
    async def install_tools(host: Host, tools: list[str]) -> Dict[str, bool]:
        """Install network testing tools on Azure VM."""
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
