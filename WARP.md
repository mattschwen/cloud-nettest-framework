# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Cloud NetTest Framework is a production-ready Python framework for orchestrating comprehensive network tests from persistent free-tier probe nodes across AWS, Azure, and GCP, targeting Oracle Cloud Infrastructure (OCI) Object Storage endpoints. Built from real-world Oracle Object Storage network analysis, it enables reproducible network testing with advanced diagnostics including bufferbloat detection and conntrack monitoring.

## Development Setup

### Quick Start
```bash
# Setup virtual environment and install
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your SSH keys and credentials

# Verify installation
cnf version
cnf registry list
```

### Development Dependencies
```bash
# Install with development tools
pip install -e ".[dev]"

# Run tests
pytest

# Lint and type check
ruff check .
mypy .
```

## Core Commands

### Registry Management
```bash
cnf registry list                    # List all registered probe hosts
cnf registry list --provider aws     # Filter by cloud provider
cnf registry list --status active    # Filter by status
```

### Test Execution
```bash
# Run comprehensive test plan
cnf test run --plan configs/testplan.sample.yaml

# Quick smoke test
cnf test smoke --target 134.70.16.1

# Test from specific probe
cnf test smoke --host aws-us-east-1-probe01 --target oracle-endpoint

# Dry run (validate without executing)
cnf test run --plan configs/testplan.sample.yaml --dry-run
```

### Results and Reporting
```bash
# View live test results with beautiful formatting
cnf report view

# View specific test run
cnf report view runs/20251005-120000

# Generate summary reports
cnf report summarize runs/20251005-120000 --to md,csv,json
```

### Helper Scripts
```bash
# Run comprehensive Oracle diagnostics
python scripts/run_comprehensive_test.py

# View formatted live results
python scripts/view_results.py

# Bootstrap probe hosts
bash scripts/bootstrap_hosts.sh
```

## Architecture Overview

### Hub-and-Spoke Model
- **Control Machine**: Orchestrates tests via CLI using asyncio for concurrent execution
- **Probe Nodes**: Cloud-hosted instances (AWS/Azure/GCP) that execute actual network tests
- **SSH Communication**: All test execution happens remotely via SSH to probe nodes

### Core Components
- **CLI (`src/cnf/cli.py`)**: Typer-based interface with registry, test, and report subcommands
- **Registry (`src/cnf/registry.py`)**: Manages inventory of probe hosts with Pydantic models
- **Test Runner (`src/cnf/runner.py`)**: Orchestrates parallel test execution across probes
- **SSH Client (`src/cnf/ssh.py`)**: Async SSH client using asyncssh with connection pooling
- **Test Modules (`src/cnf/tests/`)**: Pluggable network diagnostic modules

### Test Module Architecture
Each test module implements async functions that execute remotely on probe nodes:
- **Standard Tests**: DNS, latency (ICMP/TCP), HTTP/HTTPS, TLS, traceroute/MTR, throughput
- **Oracle-Specific**: Bufferbloat detection, conntrack monitoring, TCP packet analysis

### Provider Support
- **AWS**: EC2 metadata integration, default `ubuntu` user
- **Azure**: VM metadata support (configuration ready)
- **GCP**: Compute Engine metadata support (configuration ready)

## Configuration Management

### Hierarchy (load order)
1. `.env` file (environment variables, secrets)
2. `configs/providers.yaml` (provider defaults)
3. `configs/registry.json` (canonical host registry - auto-synced)
4. `configs/inventory.yaml` (human-editable host definitions)
5. Test plan YAML files
6. CLI argument overrides

### Key Configuration Files
- **`.env`**: SSH credentials, Oracle endpoints, thresholds
- **`configs/registry.json`**: Canonical source of truth for all probe hosts
- **`configs/inventory.yaml`**: Human-editable host definitions (sync with registry)
- **`configs/testplan.sample.yaml`**: Comprehensive Oracle test plan template
- **`configs/oci_endpoints.yaml`**: Oracle OCI endpoint definitions

## Test Plan Structure

Test plans are YAML files defining what to test from which probes:

```yaml
name: test_plan_name
description: "Test description"
concurrency: 5

# Probe selection criteria
probes:
  include:
    - provider: aws
      regions: ["us-east-1", "us-west-1"]
      status: active
  limit: 3

# Test targets by type
targets:
  dns: [...] 
  latency: [...]
  http: [...]
  tls: [...]
  traceroute: [...]
  oci_object: [...]  # Oracle-specific tests

# Alert thresholds
alerts:
  latency:
    warn: 150
    critical: 200
```

## Oracle-Specific Features

### Advanced Diagnostics
The framework includes specialized Oracle OCI Object Storage tests:

- **Bufferbloat Detection**: Uses ping variance analysis to detect ISP-level bufferbloat causing packet reordering
- **Conntrack Monitoring**: Detects Linux connection tracking table exhaustion (causes "90% read wait times")
- **Problem IP Monitoring**: Tracks historically problematic endpoints with baseline comparison
- **TCP Packet Analysis**: Real-time packet capture and analysis for SACK events, retransmissions

### Current Infrastructure
Based on Oracle Object Storage network analysis (2025-10-05):

**Active AWS Probes**:
- `us-east-1`: i-08b98d43fd53b67e4 (54.87.147.228) - Optimal for Oracle Ashburn
- `us-west-1`: i-03b2487f6057c504b (54.219.239.121) - Optimal for Oracle San Jose/Phoenix  
- `us-east-2`: i-04b05d483c4d369c1 (18.218.117.3) - Balanced/Backup

**Oracle OCI Endpoints**:
- Ashburn (us-ashburn-1): 134.70.24.1, 134.70.28.1, 134.70.32.1
- Phoenix (us-phoenix-1): 134.70.8.1, 134.70.12.1, 134.70.16.1
- San Jose (us-sanjose-1): 134.70.124.2

## Code Architecture Principles

### Async-First Design
All I/O operations use asyncio for non-blocking execution:
- Parallel probe execution across multiple cloud regions
- Concurrent test execution per probe
- Connection pooling and reuse for SSH clients

### Type Safety
Extensive use of Pydantic models for data validation:
- `Host` model for probe definitions
- Structured result schemas
- Configuration validation

### Modularity
Pluggable architecture for extending functionality:
- Add new test types in `src/cnf/tests/new_test.py`
- Add new cloud providers in `src/cnf/providers/new_provider.py`
- Register new components in respective `__init__.py` files

### Data Flow
1. CLI loads test plan and host registry
2. TestRunner selects probes based on criteria
3. Parallel SSH connections established to selected probes
4. Remote test execution with result collection
5. Result aggregation and threshold checking
6. Multi-format output generation (JSON, CSV, Markdown)

## Result Storage

### Directory Structure
```
runs/YYYYMMDD-HHMMSS/
├── raw_results.json      # Complete test data
├── summary.md           # Human-readable summary  
├── latency_report.csv   # Latency statistics
└── alerts.json          # Threshold violations
```

### Result Schema
Results include probe metadata, test execution details, and comprehensive metrics for each test type with structured error handling.

## Security Considerations

- Private SSH keys loaded from environment/filesystem (never stored in repo)
- Host key verification configurable (disabled for automation)
- All tests are read-only network diagnostics
- No destructive operations or unauthorized access attempts
- Credentials managed via `.env` file (gitignored)

## Performance Characteristics

- **Concurrency**: ~10 probes tested in parallel
- **Memory**: ~100MB base + ~10MB per active probe  
- **Throughput**: Limited by SSH connection overhead (~100-500ms per test)
- **Scalability**: Horizontal (add more probes) and vertical (increase concurrency)

## Extension Points

### Adding New Test Types
1. Create module in `src/cnf/tests/new_test.py`
2. Implement async test function with `Host` and targets parameters
3. Register in `src/cnf/tests/__init__.py`
4. Update `runner.py` to call new test

### Adding New Cloud Providers
1. Create module in `src/cnf/providers/new_provider.py`
2. Implement provider class with metadata and SSH user methods
3. Register in `src/cnf/providers/__init__.py` 
4. Update `providers.yaml` with defaults

## Important Notes

- Framework requires SSH access to probe nodes with private key authentication
- Tests execute remotely on probe nodes, not locally
- All network diagnostics are non-destructive and respect rate limits
- Built from real-world Oracle Object Storage network analysis findings
- Production-ready with comprehensive error handling and beautiful terminal output