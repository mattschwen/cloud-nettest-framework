# Usage Guide

Complete guide to using the Cloud NetTest Framework for Oracle Object Storage network testing.

## Installation

### Prerequisites

- Python 3.11 or higher
- SSH access to probe nodes
- SSH private key for authentication

### Setup

```bash
# Clone repository
cd cloud-nettest-framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install framework
pip install -e .

# Verify installation
cnf version
```

### Configuration

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your settings**:
   ```bash
   CNF_SSH_USER=ubuntu
   CNF_SSH_KEY=~/.ssh/your-key.pem
   
   # Oracle endpoints
   OCI_ASHBURN_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com
   ```

3. **Verify SSH connectivity**:
   ```bash
   ssh -i ~/.ssh/your-key.pem ubuntu@54.87.147.228
   ```

## Basic Operations

### List Registered Probes

```bash
# List all probes
cnf registry list

# Filter by provider
cnf registry list --provider aws

# Filter by status
cnf registry list --status active
```

Output:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ ID                      ┃ Provider┃ Region    ┃ Public IP     ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ aws-us-east-1-probe01   │ aws     │ us-east-1 │ 54.87.147.228 │ active │
│ aws-us-west-1-probe01   │ aws     │ us-west-1 │54.219.239.121 │ active │
│ aws-us-east-2-probe01   │ aws     │ us-east-2 │ 18.218.117.3  │ active │
└─────────────────────────┴─────────┴───────────┴───────────────┴────────┘
```

### Run Tests

#### Quick Smoke Test

```bash
# Test connectivity to a target from all probes
cnf test smoke --target 134.70.16.1

# Test from specific probe
cnf test smoke --host aws-us-east-1-probe01 --target objectstorage.us-ashburn-1.oraclecloud.com
```

#### Run Full Test Plan

```bash
# Run sample Oracle test plan
cnf test run --plan configs/testplan.sample.yaml

# Specify output directory
cnf test run --plan configs/testplan.sample.yaml --output runs/my-test-$(date +%Y%m%d)

# Dry run (validate without executing)
cnf test run --plan configs/testplan.sample.yaml --dry-run
```

### Generate Reports

```bash
# Summarize results from a run
cnf report summarize --run runs/20251005-120000 --to md

# Generate multiple formats
cnf report summarize --run runs/20251005-120000 --to md,csv,json
```

## Test Plans

### Test Plan Structure

A test plan is a YAML file defining what to test and from where:

```yaml
name: my_test_plan
description: "Description of test plan"
version: "1.0"
concurrency: 5

# Select which probes to use
probes:
  include:
    - provider: aws
      regions: ["us-east-1", "us-west-1"]
      status: active
  limit: 3  # Optional: max number of probes

# Define test targets
targets:
  dns:
    - name: objectstorage.us-ashburn-1.oraclecloud.com
      qtype: A
      attempts: 3
      timeout_s: 5
  
  latency:
    - host: 134.70.16.1
      mode: icmp
      count: 10
      alert_threshold: 100
  
  http:
    - url: "https://objectstorage.us-phoenix-1.oraclecloud.com/..."
      method: GET
      retries: 2
      timeout_s: 15
      expected_status: [200, 404]
  
  tls:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      port: 443
      verify: true
  
  traceroute:
    - host: objectstorage.us-phoenix-1.oraclecloud.com
      max_hops: 30
      mode: tcp
      port: 443

# Output configuration
outputs:
  formats: ["json", "csv", "md"]
  save_raw: true
  create_summary: true

# Alert thresholds
alerts:
  latency:
    warn: 150
    critical: 200
  packet_loss:
    warn: 1.0
    critical: 5.0
```

### Example Test Plans

#### 1. Oracle Ashburn Performance Test

```yaml
name: oracle_ashburn_perf
description: "Test Oracle Ashburn from US-East-1"

probes:
  include:
    - provider: aws
      regions: ["us-east-1"]

targets:
  dns:
    - name: objectstorage.us-ashburn-1.oraclecloud.com
  
  latency:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      count: 20
  
  http:
    - url: "https://objectstorage.us-ashburn-1.oraclecloud.com/..."
      timeout_s: 15
```

#### 2. Multi-Region Baseline

```yaml
name: multi_region_baseline
description: "Establish baseline from all regions"

probes:
  include:
    - provider: aws
      regions: ["us-east-1", "us-west-1", "us-east-2"]

targets:
  latency:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      count: 50
    - host: objectstorage.us-phoenix-1.oraclecloud.com
      count: 50
    - host: objectstorage.us-sanjose-1.oraclecloud.com
      count: 50
```

#### 3. Problem IP Monitoring

```yaml
name: problem_ip_monitor
description: "Monitor 134.70.16.1 (previously 471ms)"

probes:
  include:
    - provider: aws
      regions: ["us-east-1", "us-west-1"]

targets:
  latency:
    - host: 134.70.16.1
      name: phoenix_problem_ip
      mode: icmp
      count: 100
      alert_threshold: 100  # Alert if >100ms
  
  oci_object:
    - endpoint: us-phoenix-1
      monitor_ips:
        - 134.70.16.1
```

## Advanced Usage

### Oracle-Specific Tests

#### Bufferbloat Detection

Test for ISP-level bufferbloat causing packet reordering:

```yaml
targets:
  oci_object:
    - endpoint: us-phoenix-1
      test_types:
        - bufferbloat_detection
```

This test:
- Sends 100 rapid pings
- Calculates max/min latency ratio
- Classifies severity: NONE, MILD, MODERATE, SEVERE
- Identifies if ratio >20x (severe bufferbloat)

#### Conntrack Monitoring

Monitor Linux connection tracking table exhaustion:

```yaml
targets:
  oci_object:
    - endpoint: us-ashburn-1
      test_types:
        - conntrack_check
```

Monitors:
- Current connection count
- Maximum table size
- Usage percentage
- Kernel error messages

Alerts if:
- >75% full: WARNING
- >90% full: CRITICAL

#### Comprehensive OCI Test Suite

Run all Oracle-specific diagnostics:

```yaml
targets:
  oci_object:
    - endpoint: us-ashburn-1
      test_types:
        - dns_timing
        - tcp_connect_timing
        - tls_handshake_timing
        - http_ttfb
        - full_request_timing
        - bufferbloat_detection
        - packet_loss_check
```

### Adding Azure/GCP Probes

#### 1. Provision VM/Instance

**Azure**:
```bash
az vm create \
  --resource-group cnf-probes \
  --name cnf-eastus-probe01 \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-values @~/.ssh/id_rsa.pub
```

**GCP**:
```bash
gcloud compute instances create cnf-us-east1-probe01 \
  --machine-type e2-micro \
  --zone us-east1-b \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud
```

#### 2. Add to Inventory

Edit `configs/inventory.yaml`:

```yaml
hosts:
  # ... existing AWS probes ...
  
  - id: azure-eastus-probe01
    provider: azure
    region: eastus
    hostname: probe01
    public_ip: 20.123.45.67
    ssh_user: azureuser
    ssh_key: ~/.ssh/id_rsa
    status: active
    capabilities:
      - icmp_ping
      - tcp_connect
      - https_timing
```

#### 3. Sync to Registry

```bash
# Python script or manual sync
python -c "from cnf.registry import sync_inventory_to_registry; sync_inventory_to_registry()"
```

#### 4. Verify

```bash
cnf registry list --provider azure
```

### Custom Test Development

#### Create Custom Test Module

```python
# src/cnf/tests/my_custom_test.py
from typing import Any, Dict, List
from cnf.registry import Host
from cnf.ssh import SSHClient

async def run_my_tests(host: Host, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run custom tests."""
    results = []
    
    async with SSHClient(host) as ssh:
        for target in targets:
            # Run your custom test
            returncode, stdout, stderr = await ssh.execute(
                f"my-custom-command {target['param']}"
            )
            
            results.append({
                "target": target,
                "success": returncode == 0,
                "output": stdout,
            })
    
    return results
```

#### Register in Runner

Edit `src/cnf/runner.py`:

```python
# Add to imports
from cnf.tests.my_custom_test import run_my_tests

# Add to TestRunner.run_tests()
if "my_custom" in self.plan.get("targets", {}):
    test_results["tests"]["my_custom"] = await run_my_tests(
        probe, self.plan["targets"]["my_custom"]
    )
```

## Troubleshooting

### SSH Connection Issues

**Problem**: Cannot connect to probe

```bash
# Test SSH manually
ssh -i ~/.ssh/your-key.pem -v ubuntu@54.87.147.228

# Check key permissions
chmod 600 ~/.ssh/your-key.pem

# Verify host in inventory
cnf registry list
```

### Test Failures

**Problem**: Tests timing out

- Increase timeout in test plan: `timeout_s: 30`
- Check probe connectivity
- Verify tools installed on probe

**Problem**: Permission denied errors

- Some tests require sudo (tcpdump, conntrack)
- Ensure probe user has sudo access
- Tests will gracefully degrade if unavailable

### Missing Tools on Probes

Install required tools:

```bash
# SSH to probe
ssh -i ~/.ssh/your-key.pem ubuntu@probe-ip

# Install tools
sudo apt-get update
sudo apt-get install -y \
  iputils-ping \
  traceroute \
  mtr-tiny \
  curl \
  dnsutils \
  iperf3 \
  tcpdump
```

Or use the bootstrap script:

```bash
# From control machine
scp scripts/bootstrap_hosts.sh ubuntu@probe-ip:~
ssh ubuntu@probe-ip 'bash bootstrap_hosts.sh'
```

## Best Practices

### 1. Test Plan Organization

- Keep test plans in version control
- Use descriptive names
- Document test purpose in description field
- Set appropriate timeouts
- Define alert thresholds

### 2. Probe Management

- Keep inventory.yaml updated
- Verify probe health regularly
- Remove inactive probes
- Document probe purpose

### 3. Result Management

- Use timestamped output directories
- Archive old results
- Extract key metrics to dashboard
- Review alerts regularly

### 4. Security

- Never commit `.env` file
- Rotate SSH keys periodically
- Use read-only credentials where possible
- Limit probe SSH access

---

**Next Steps**:
- Review [Test Matrix](TEST_MATRIX.md) for all available tests
- See [Architecture](ARCHITECTURE.md) for system design
- Check [OCI Object Tests](OCI_OBJECT_TESTS.md) for Oracle-specific features
