# Cloud NetTest Framework

> **Multi-cloud network testing framework for Oracle Cloud Infrastructure Object Storage**

A production-ready Python framework for orchestrating comprehensive network tests from persistent free-tier probe nodes across AWS, Azure, and GCP, targeting Oracle Cloud Infrastructure (OCI) Object Storage endpoints.

## 🎯 Purpose

Built from real-world Oracle Object Storage network analysis, this framework enables:

- **Reproducible network testing** across multiple cloud providers
- **Oracle OCI Object Storage** performance monitoring and diagnostics
- **Advanced diagnostics** including bufferbloat detection and conntrack monitoring
- **Multi-region orchestration** from a single control point
- **Persistent probe infrastructure** using cloud free-tier resources

## 🚀 Quick Start

```bash
# Clone and setup
cd cloud-nettest-framework
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your SSH keys and credentials

# List registered probes
cnf registry list

# Run a test plan
cnf test run --plan configs/testplan.sample.yaml

# Generate report
cnf report summarize --run runs/latest --to md,csv,json
```

## 📊 Current Infrastructure

Based on Oracle Object Storage network analysis (2025-10-05):

### Active AWS Probes

| Region | Instance ID | Public IP | Optimal For | Baseline Latency |
|--------|-------------|-----------|-------------|------------------|
| **us-east-1** | i-08b98d43fd53b67e4 | 54.87.147.228 | Oracle Ashburn | 1.05ms ⭐ |
| **us-west-1** | i-03b2487f6057c504b | 54.219.239.121 | Oracle San Jose/Phoenix | <1ms ⭐ |
| **us-east-2** | i-04b05d483c4d369c1 | 18.218.117.3 | Balanced/Backup | 13.8ms |

### Oracle OCI Endpoints Tested

- **Ashburn** (us-ashburn-1): 134.70.24.1, 134.70.28.1, 134.70.32.1
- **Phoenix** (us-phoenix-1): 134.70.8.1, 134.70.12.1, 134.70.16.1
- **San Jose** (us-sanjose-1): 134.70.124.2

## ✨ Features

### Network Tests

- **DNS Resolution**: Timing and accuracy testing
- **Latency**: ICMP ping and TCP connection timing
- **HTTP/HTTPS**: Full request timing breakdown (DNS, connect, TLS, TTFB)
- **TLS**: Handshake timing and certificate validation
- **Traceroute/MTR**: Network path analysis
- **Throughput**: iperf3-based bandwidth testing

### Oracle-Specific Diagnostics

- **Bufferbloat Detection**: Identifies network queuing delays causing packet reordering
- **Conntrack Monitoring**: Detects connection table exhaustion (90% read wait times)
- **TCP Packet Analysis**: SACK events, retransmissions, out-of-order packets
- **Problem IP Monitoring**: Tracks previously problematic endpoints (e.g., 134.70.16.1)

### Multi-Cloud Support

- **AWS**: Full support with EC2 metadata integration
- **Azure**: Ready for VM deployment (configuration included)
- **GCP**: Ready for Compute Engine deployment (configuration included)

## 📖 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Usage Guide](docs/USAGE.md) - Detailed usage instructions
- [Test Matrix](docs/TEST_MATRIX.md) - Available tests and parameters
- [Provider Guide](docs/PROVIDERS.md) - Cloud provider specifics
- [OCI Object Tests](docs/OCI_OBJECT_TESTS.md) - Oracle-specific testing

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Control Machine (CLI)                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Test Plans  │  │  Registry    │  │  Results     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │ SSH + Async Orchestration
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ AWS Probes  │  │Azure Probes │  │ GCP Probes  │
│             │  │             │  │             │
│ us-east-1   │  │  eastus     │  │ us-east1    │
│ us-west-1   │  │  westus2    │  │ us-west1    │
│ us-east-2   │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Oracle OCI      │
              │  Object Storage  │
              │                  │
              │  Ashburn         │
              │  Phoenix         │
              │  San Jose        │
              └──────────────────┘
```

## 🧪 Test Plans

Example test plan structure:

```yaml
name: oracle_object_storage_full_suite
description: "Comprehensive OCI Object Storage testing"
concurrency: 5

probes:
  include:
    - provider: aws
      regions: ["us-east-1", "us-west-1"]
      status: active

targets:
  dns:
    - name: objectstorage.us-ashburn-1.oraclecloud.com
      qtype: A
      attempts: 3
  
  latency:
    - host: 134.70.16.1  # Previously problematic IP
      mode: icmp
      count: 20
      alert_threshold: 100  # Alert if >100ms
  
  http:
    - url: "https://objectstorage.us-ashburn-1.oraclecloud.com/..."
      method: GET
      timeout_s: 15
      expected_status: [200, 404]
  
  oci_object:
    - endpoint: us-phoenix-1
      test_types:
        - bufferbloat_detection
        - packet_loss_check
      monitor_ips:
        - 134.70.16.1
```

## 📦 Installation

### Requirements

- Python 3.11+
- SSH access to probe nodes
- Private SSH key for authentication

### Install from Source

```bash
git clone <your-repo-url>
cd cloud-nettest-framework
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

### Development Setup

```bash
pip install -e ".[dev]"
pytest  # Run tests
ruff check .  # Lint
mypy .  # Type check
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# SSH Configuration
CNF_SSH_USER=ubuntu
CNF_SSH_KEY=~/.ssh/id_rsa

# Oracle Endpoints
OCI_ASHBURN_ENDPOINT=https://objectstorage.us-ashburn-1.oraclecloud.com
OCI_PHOENIX_ENDPOINT=https://objectstorage.us-phoenix-1.oraclecloud.com

# Thresholds
LATENCY_WARN_THRESHOLD=150
LATENCY_CRITICAL_THRESHOLD=200
```

### Host Registry

The framework maintains a registry of all probe hosts in `configs/registry.json` and `configs/inventory.yaml`.

To sync inventory to registry:
```python
from cnf.registry import sync_inventory_to_registry
sync_inventory_to_registry()
```

## 🎯 Use Cases

### 1. Oracle Object Storage Performance Monitoring

Monitor Oracle OCI Object Storage performance from multiple regions:

```bash
cnf test run --plan configs/testplan.sample.yaml
```

### 2. Bufferbloat Detection

Detect ISP-level bufferbloat causing packet reordering:

```bash
# Test plan with bufferbloat detection
cnf test run --plan configs/oci_bufferbloat_test.yaml
```

### 3. Multi-Region Baseline

Establish performance baselines across regions:

```bash
cnf test run --plan configs/baseline_test.yaml --output runs/baseline-$(date +%Y%m%d)
```

### 4. Problem IP Monitoring

Monitor previously problematic IPs (e.g., 134.70.16.1 which showed 471ms→59ms improvement):

```bash
cnf test smoke --target 134.70.16.1
```

## 📈 Results and Reporting

Test results are saved in structured formats:

```
runs/20251005-120000/
├── raw_results.json          # Complete test data
├── summary.md                # Human-readable summary
├── latency_report.csv        # Latency statistics
└── alerts.json               # Threshold violations
```

## 🔍 Advanced Diagnostics

### Conntrack Table Monitoring

Detects Linux conntrack table exhaustion (causes "90% read wait"):

```python
from cnf.tests.oci_object import check_conntrack_status
result = await check_conntrack_status(host)
# Warns if >75% full, alerts if >90%
```

### Bufferbloat Detection

Identifies network queuing delays:

```python
from cnf.tests.oci_object import detect_bufferbloat
result = await detect_bufferbloat(host, target, ping_count=100)
# Classifies: NONE, MILD, MODERATE, SEVERE
```

## 🤝 Contributing

This framework was built from real Oracle Object Storage network analysis. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

Built from comprehensive Oracle Object Storage network analysis including:
- Multi-region AWS testing (us-east-1, us-west-1, us-east-2)
- TCP packet capture analysis
- MTR network path tracing
- Real-world Sev 1 incident investigation

Based on findings from:
- `Oracle_Object_Storage_Network_Analysis_Report.md`
- `Oracle_Network_Diagnostic_Report.md`
- `Oracle_Network_Analysis_Handoff_Document.md`

## 📞 Support

For issues and questions:
- GitHub Issues: [your-repo-url]/issues
- Documentation: `docs/` directory

---

**Status**: Production-ready framework with 3 active AWS probes  
**Version**: 0.1.0  
**Last Updated**: 2025-10-05
