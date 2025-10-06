# Architecture

## System Overview

Cloud NetTest Framework is a distributed network testing system with centralized orchestration. The architecture follows a hub-and-spoke model where a control machine orchestrates tests across multiple cloud-hosted probe nodes.

## Core Components

### 1. CLI (Command-Line Interface)

**Location**: `src/cnf/cli.py`

The CLI provides the main user interface using Typer:

```
cnf
├── registry        # Host registry management
│   ├── list        # List all registered probes
│   ├── discover    # Discover and register new probes
│   └── sync        # Sync inventory to registry
├── test            # Test execution
│   ├── run         # Run a test plan
│   └── smoke       # Quick smoke test
└── report          # Result reporting
    └── summarize   # Generate summary reports
```

### 2. Registry System

**Location**: `src/cnf/registry.py`

Manages the inventory of all probe hosts:

- **registry.json**: Canonical source of truth for all probes
- **inventory.yaml**: Human-editable host definitions
- **Host Model**: Pydantic models for type safety

```python
class Host(BaseModel):
    id: str                      # Unique identifier
    provider: str                # aws, azure, gcp
    region: str                  # Cloud region
    public_ip: str               # SSH target
    ssh_user: str                # SSH username
    capabilities: List[str]      # Available tools
    status: str                  # active, inactive
```

### 3. Test Runner

**Location**: `src/cnf/runner.py`

Orchestrates test execution:

1. **Probe Selection**: Filters hosts based on test plan criteria
2. **Parallel Execution**: Runs tests concurrently across probes
3. **Result Aggregation**: Collects and structures results
4. **Output Management**: Saves results in multiple formats

**Execution Flow**:
```
Test Plan → Probe Selection → Test Execution → Result Collection → Report Generation
```

### 4. SSH Client

**Location**: `src/cnf/ssh.py`

Async SSH client using asyncssh:

- Connection pooling and reuse
- Command execution with timeout
- Host fact gathering
- Error handling and retries

**Features**:
- Automatic key-based authentication
- Context manager support
- Parallel connections
- Host fingerprint management

### 5. Test Modules

**Location**: `src/cnf/tests/`

Pluggable test modules for different network diagnostics:

#### Standard Tests

- **dns.py**: DNS resolution timing and accuracy
- **latency.py**: ICMP ping and TCP connection timing
- **http.py**: HTTP/HTTPS request timing breakdown
- **tls.py**: TLS handshake and certificate validation
- **traceroute.py**: Network path analysis (traceroute/MTR)
- **throughput.py**: Bandwidth testing (iperf3)

#### Oracle-Specific Tests

- **oci_object.py**: Specialized Oracle OCI Object Storage tests
  - Bufferbloat detection
  - Conntrack table monitoring
  - TCP packet analysis
  - Problem IP monitoring

### 6. Provider Modules

**Location**: `src/cnf/providers/`

Cloud provider-specific functionality:

- **aws.py**: AWS EC2 metadata, instance details
- **azure.py**: Azure VM metadata, resource info
- **gcp.py**: GCP Compute Engine metadata

Each provider implements:
- Metadata fetching
- Tool installation
- Default SSH users
- Package managers

## Data Flow

### Test Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User invokes: cnf test run --plan testplan.yaml             │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. CLI loads test plan and registry                            │
│    - Parse YAML test plan                                      │
│    - Load host registry                                        │
│    - Validate configuration                                    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. TestRunner selects probes based on criteria                 │
│    - Filter by provider (aws, azure, gcp)                      │
│    - Filter by region                                          │
│    - Filter by status (active)                                 │
│    - Apply limits                                              │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. For each selected probe (parallel execution):               │
│    ┌───────────────────────────────────────────────────────┐  │
│    │ a. Establish SSH connection                           │  │
│    │ b. Run DNS tests                                      │  │
│    │ c. Run latency tests                                  │  │
│    │ d. Run HTTP tests                                     │  │
│    │ e. Run TLS tests                                      │  │
│    │ f. Run traceroute tests                               │  │
│    │ g. Run Oracle-specific tests                          │  │
│    │ h. Collect results                                    │  │
│    │ i. Close SSH connection                               │  │
│    └───────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Aggregate results from all probes                           │
│    - Combine test results                                      │
│    - Check alert thresholds                                    │
│    - Calculate statistics                                      │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Save results to output directory                            │
│    - runs/TIMESTAMP/raw_results.json                           │
│    - runs/TIMESTAMP/summary.md                                 │
│    - runs/TIMESTAMP/latency_report.csv                         │
└─────────────────────────────────────────────────────────────────┘
```

### SSH Communication Pattern

```
Control Machine                     Probe Node (AWS/Azure/GCP)
      │                                      │
      │──── SSH Connect ────────────────────▶│
      │                                      │
      │◀─── Connection Established ──────────│
      │                                      │
      │──── Execute: ping target ───────────▶│
      │                                      │
      │                                      │─┐
      │                                      │ │ Run ping
      │                                      │◀┘
      │                                      │
      │◀─── Return: ping output ─────────────│
      │                                      │
      │──── Execute: curl timing ───────────▶│
      │                                      │
      │                                      │─┐
      │                                      │ │ Run curl
      │                                      │◀┘
      │                                      │
      │◀─── Return: timing data ─────────────│
      │                                      │
      │──── Close connection ────────────────▶│
      │                                      │
```

## Configuration Management

### Configuration Hierarchy

```
.env                          # Environment variables (secrets)
├── CNF_SSH_USER
├── CNF_SSH_KEY
└── Provider credentials

configs/
├── providers.yaml            # Provider defaults
├── inventory.yaml            # Host definitions (editable)
├── registry.json             # Canonical registry (auto-synced)
├── oci_endpoints.yaml        # Oracle endpoints
└── testplan.*.yaml           # Test plans
```

### Configuration Loading Order

1. Load environment variables from `.env`
2. Load provider defaults from `providers.yaml`
3. Load host registry from `registry.json`
4. Load test plan from specified YAML
5. Override with CLI arguments

## Concurrency Model

### Asyncio-Based Execution

The framework uses Python's asyncio for concurrent execution:

```python
# Parallel probe execution
async def run_tests(probes):
    tasks = [test_probe(probe) for probe in probes]
    results = await asyncio.gather(*tasks)
    return results

# Parallel test execution per probe
async def test_probe(probe):
    async with SSHClient(probe) as ssh:
        dns_task = run_dns_tests(ssh, targets)
        http_task = run_http_tests(ssh, targets)
        latency_task = run_latency_tests(ssh, targets)
        
        results = await asyncio.gather(
            dns_task, http_task, latency_task
        )
```

**Concurrency Limits**:
- Maximum concurrent probes: Configurable in test plan
- Maximum concurrent SSH connections per probe: 1
- Maximum concurrent tests per probe: Based on test plan

## Storage and State

### Directory Structure

```
cloud-nettest-framework/
├── configs/                  # Configuration files
├── src/cnf/                  # Source code
├── docs/                     # Documentation
├── scripts/                  # Helper scripts
├── state/                    # Runtime state
│   ├── ops_log.md           # Operations log
│   └── hosts/               # Host-specific data
│       └── {host-id}/
│           ├── facts.json   # System facts
│           └── health.json  # Health status
└── runs/                     # Test results
    └── YYYYMMDD-HHMMSS/
        ├── raw_results.json
        ├── summary.md
        └── *.csv
```

### Result Schema

```json
{
  "results": [
    {
      "probe_id": "aws-us-east-1-probe01",
      "provider": "aws",
      "region": "us-east-1",
      "timestamp": "2025-10-05T12:00:00Z",
      "tests": {
        "dns": [...],
        "latency": [...],
        "http": [...],
        "tls": [...],
        "oci_object": [...]
      }
    }
  ],
  "plan": {...}
}
```

## Extension Points

### Adding New Test Types

1. Create module in `src/cnf/tests/new_test.py`
2. Implement async test function:
   ```python
   async def run_new_tests(host: Host, targets: List[Dict]) -> List[Dict]:
       # Implementation
   ```
3. Register in `src/cnf/tests/__init__.py`
4. Update `runner.py` to call new test

### Adding New Providers

1. Create module in `src/cnf/providers/new_provider.py`
2. Implement provider class:
   ```python
   class NewProvider:
       @staticmethod
       def get_default_ssh_user() -> str: ...
       
       @staticmethod
       async def get_instance_metadata(host: Host) -> Dict: ...
   ```
3. Register in `src/cnf/providers/__init__.py`
4. Update `providers.yaml` with defaults

## Security Considerations

### SSH Security

- Private keys never stored in repository
- Keys loaded from environment or local filesystem
- Host key verification configurable (disabled for automation)
- Connection timeouts prevent hanging

### Credential Management

- All secrets in `.env` file (gitignored)
- No hardcoded credentials
- Provider credentials from environment
- SSH keys with appropriate permissions (0600)

### Network Security

- Tests are read-only (no destructive operations)
- ICMP and TCP tests only
- No unauthorized access attempts
- Respects target rate limits

## Performance Characteristics

### Scalability

- **Horizontal**: Add more probe nodes
- **Vertical**: Increase concurrency limits
- **Throughput**: ~10 probes tested in parallel
- **Latency**: SSH overhead ~100-500ms per test

### Resource Usage

- **Memory**: ~100MB base + ~10MB per active probe
- **Network**: Minimal (test traffic only)
- **CPU**: Low (I/O bound, not CPU bound)

## Monitoring and Observability

### Logging

- Rich console output with progress indicators
- Structured JSON results
- Error messages with context
- Test timing information

### Alerting

- Configurable thresholds in test plans
- Alert conditions in results
- Warning vs. critical severity levels

### Metrics

- Test execution time
- Success/failure rates
- Latency percentiles
- Packet loss rates

---

**Design Principles**:
1. **Reproducibility**: All tests are idempotent and repeatable
2. **Auditability**: Complete logging and result preservation
3. **Modularity**: Pluggable test and provider modules
4. **Async-First**: Non-blocking I/O for performance
5. **Type Safety**: Pydantic models for data validation
