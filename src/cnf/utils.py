"""Utility functions for Cloud NetTest Framework."""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def get_timestamp(fmt: str = "iso") -> str:
    """Get current UTC timestamp."""
    now = datetime.now(timezone.utc)
    if fmt == "iso":
        return now.isoformat()
    elif fmt == "filename":
        return now.strftime("%Y%m%d-%H%M%S")
    else:
        return now.strftime(fmt)


def expand_path(path: str | Path) -> Path:
    """Expand user home directory in path."""
    return Path(path).expanduser().resolve()


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with open(file_path) as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], file_path: Path):
    """Save data to YAML file."""
    with open(file_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file."""
    with open(file_path) as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: Path, pretty: bool = True):
    """Save data to JSON file."""
    with open(file_path, "w") as f:
        if pretty:
            json.dump(data, f, indent=2)
        else:
            json.dump(data, f)


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists."""
    path = expand_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def run_command(cmd: List[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a shell command asynchronously."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        if proc:
            proc.kill()
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def parse_latency(output: str) -> Optional[float]:
    """Parse latency from ping output (in milliseconds)."""
    import re
    
    # Look for patterns like "time=1.23 ms" or "time=1.23ms"
    match = re.search(r'time[=\s]+([\d.]+)\s*ms', output)
    if match:
        return float(match.group(1))
    
    # Look for avg latency in summary
    match = re.search(r'avg[=/\s]+([\d.]+)', output)
    if match:
        return float(match.group(1))
    
    return None


class Timer:
    """Simple context manager for timing operations."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.elapsed is not None:
            return self.elapsed * 1000
        return 0.0
