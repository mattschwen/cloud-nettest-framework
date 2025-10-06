"""Host registry management for probe nodes."""

import json
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class Host(BaseModel):
    """Probe host definition."""
    id: str
    provider: str
    region: str
    hostname: str
    instance_id: Optional[str] = None
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_key: Optional[str] = None
    status: Optional[str] = "unknown"
    capabilities: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    last_verified: Optional[str] = None


class Registry(BaseModel):
    """Registry of all probe hosts."""
    schema: int = 1
    version: str = "0.1.0"
    last_updated: Optional[str] = None
    providers: List[str] = Field(default_factory=lambda: ["aws", "azure", "gcp"])
    hosts: List[Host] = Field(default_factory=list)
    metadata: Optional[dict] = None


def get_config_dir() -> Path:
    """Get the configs directory path."""
    # Try to find configs relative to this file
    current = Path(__file__).parent.parent.parent
    config_dir = current / "configs"
    if config_dir.exists():
        return config_dir
    
    # Fallback to current working directory
    config_dir = Path.cwd() / "configs"
    if config_dir.exists():
        return config_dir
    
    raise FileNotFoundError("Cannot find configs directory")


def load_registry(registry_file: Optional[Path] = None) -> Registry:
    """Load the host registry from JSON file."""
    if registry_file is None:
        registry_file = get_config_dir() / "registry.json"
    
    if not registry_file.exists():
        return Registry()
    
    with open(registry_file) as f:
        data = json.load(f)
    
    return Registry(**data)


def save_registry(registry: Registry, registry_file: Optional[Path] = None):
    """Save the host registry to JSON file."""
    if registry_file is None:
        registry_file = get_config_dir() / "registry.json"
    
    with open(registry_file, "w") as f:
        json.dump(registry.model_dump(), f, indent=2)


def load_inventory(inventory_file: Optional[Path] = None) -> List[Host]:
    """Load hosts from inventory YAML file."""
    if inventory_file is None:
        inventory_file = get_config_dir() / "inventory.yaml"
    
    if not inventory_file.exists():
        return []
    
    with open(inventory_file) as f:
        data = yaml.safe_load(f)
    
    hosts = []
    for host_data in data.get("hosts", []):
        hosts.append(Host(**host_data))
    
    return hosts


def sync_inventory_to_registry(inventory_file: Optional[Path] = None, registry_file: Optional[Path] = None):
    """Sync inventory.yaml hosts to registry.json."""
    hosts = load_inventory(inventory_file)
    registry = load_registry(registry_file)
    
    # Update or add hosts
    existing_ids = {h.id for h in registry.hosts}
    
    for host in hosts:
        if host.id in existing_ids:
            # Update existing
            for i, existing in enumerate(registry.hosts):
                if existing.id == host.id:
                    registry.hosts[i] = host
                    break
        else:
            # Add new
            registry.hosts.append(host)
    
    # Update metadata
    provider_counts = {}
    for host in registry.hosts:
        provider_counts[host.provider] = provider_counts.get(host.provider, 0) + 1
    
    registry.metadata = {
        "total_hosts": len(registry.hosts),
        "active_hosts": len([h for h in registry.hosts if h.status == "active"]),
        "providers_count": provider_counts,
    }
    
    save_registry(registry, registry_file)
    return registry
