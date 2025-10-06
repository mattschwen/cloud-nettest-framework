"""AWS-specific provider module."""

from typing import Any, Dict, Optional

from cnf.registry import Host
from cnf.ssh import SSHClient


class AWSProvider:
    """AWS cloud provider specific functionality."""
    
    @staticmethod
    def get_default_ssh_user() -> str:
        """Get default SSH user for AWS instances."""
        return "ubuntu"  # Most common for Ubuntu AMIs
    
    @staticmethod
    def get_package_manager() -> str:
        """Get package manager for AWS instances."""
        return "apt"  # Assuming Ubuntu/Debian
    
    @staticmethod
    async def get_instance_metadata(host: Host) -> Dict[str, Any]:
        """Fetch AWS EC2 instance metadata."""
        metadata = {
            "provider": "aws",
            "instance_id": None,
            "instance_type": None,
            "availability_zone": None,
            "region": None,
            "public_ipv4": None,
            "private_ipv4": None,
            "ami_id": None,
        }
        
        try:
            async with SSHClient(host) as ssh:
                # Use IMDSv2 (token-based) for security
                token_cmd = "TOKEN=$(curl -X PUT 'http://169.254.169.254/latest/api/token' -H 'X-aws-ec2-metadata-token-ttl-seconds: 21600' 2>/dev/null)"
                
                # Helper to get metadata
                async def get_metadata(path: str) -> Optional[str]:
                    cmd = f"{token_cmd} && curl -H \"X-aws-ec2-metadata-token: $TOKEN\" http://169.254.169.254/latest/meta-data/{path} 2>/dev/null"
                    returncode, stdout, _ = await ssh.execute(cmd, timeout=5)
                    return stdout.strip() if returncode == 0 else None
                
                metadata["instance_id"] = await get_metadata("instance-id")
                metadata["instance_type"] = await get_metadata("instance-type")
                metadata["availability_zone"] = await get_metadata("placement/availability-zone")
                metadata["public_ipv4"] = await get_metadata("public-ipv4")
                metadata["private_ipv4"] = await get_metadata("local-ipv4")
                metadata["ami_id"] = await get_metadata("ami-id")
                
                # Extract region from AZ
                if metadata["availability_zone"]:
                    metadata["region"] = metadata["availability_zone"][:-1]
                
        except Exception as e:
            metadata["error"] = f"Failed to fetch metadata: {e}"
        
        return metadata
    
    @staticmethod
    async def install_tools(host: Host, tools: list[str]) -> Dict[str, bool]:
        """Install network testing tools on AWS instance."""
        results = {}
        
        try:
            async with SSHClient(host) as ssh:
                # Update package cache
                await ssh.execute("sudo apt-get update -qq", timeout=60)
                
                for tool in tools:
                    # Check if already installed
                    check_code, _, _ = await ssh.execute(f"which {tool}", timeout=5)
                    
                    if check_code == 0:
                        results[tool] = True
                    else:
                        # Install tool
                        install_code, _, _ = await ssh.execute(
                            f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {tool}",
                            timeout=120
                        )
                        results[tool] = (install_code == 0)
                        
        except Exception as e:
            for tool in tools:
                results[tool] = False
        
        return results
