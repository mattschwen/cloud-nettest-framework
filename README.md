# ANUBIS 🔷
## Network Path Guardian - Multi-Cloud Diagnostics Suite

<div align="center">

```
     ___      .__   __.  __    __  .______    __       _______.
    /   \     |  \ |  | |  |  |  | |   _  \  |  |     /       |
   /  ^  \    |   \|  | |  |  |  | |  |_)  | |  |    |   (----`
  /  /_\  \   |  . `  | |  |  |  | |   _  <  |  |     \   \
 /  _____  \  |  |\   | |  `--'  | |  |_)  | |  | .----)   |
/__/     \__\ |__| \__|  \______/  |______/  |__| |_______/
```

**🌐 Egyptian God of Pathfinding | Cyberpunk Network Diagnostics 🌐**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Network Tests](https://img.shields.io/badge/tests-21%20endpoints-brightgreen)](.)

*Multi-cloud network testing framework with full L3→L4→L7 correlation and packet-level analysis*

[Quick Start](#-quick-start) • [Features](#-features) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🎯 What is ANUBIS?

**ANUBIS** (inspired by the Egyptian god who guides souls through the underworld) is a production-ready network diagnostics framework that guides you through every layer of your network infrastructure. Like its namesake, ANUBIS sees what's hidden and illuminates the path through complex network topologies.

### Why ANUBIS?

Born from real-world Oracle Cloud Infrastructure troubleshooting, ANUBIS enables:

- 🌐 **Multi-Cloud Testing** - AWS, Azure, GCP probe deployment
- 🔬 **Full Stack Analysis** - L3 (ICMP/MTR) → L4 (TCP) → L7 (HTTP) correlation
- 📊 **Beautiful Output** - Cyberpunk-themed, colorized terminal displays
- 🎯 **Oracle OCI Focus** - Specialized tests for Oracle Object Storage
- 💠 **Packet Correlation** - TCP events mapped to HTTP timing phases
- 🗺️ **Path Intelligence** - MTR + WHOIS for complete route analysis

## 🚀 Quick Start

### One-Command Test

Test **ALL Oracle OCI endpoints** from **ALL AWS probes**:

```bash
./run_tests
```

This executes comprehensive diagnostics:
- ✅ 3 AWS EC2 probes (Virginia, California, Ohio)
- ✅ 7 Oracle endpoints (Ashburn, Phoenix, San Jose)
- ✅ ICMP ping, MTR path analysis, HTTP timing
- ✅ WHOIS lookup for every network hop
- ✅ Beautiful cyberpunk-themed output

**Sample output:**
```
🥇 TOP 3 BEST PERFORMING ROUTES
┌────┬───────────────────────────────────────────┬─────────┬──────┬───────┐
│ 🥇 │ us-west-1 → San Jose (134.70.124.2)       │  0.91ms │ 0.0% │ 🥇 A+ │
│ 🥈 │ us-east-1 → Ashburn (134.70.24.1)         │  0.95ms │ 0.0% │ 🥇 A+ │
│ 🥉 │ us-east-2 → Ashburn (134.70.24.1)         │ 11.72ms │ 0.0% │ 🥉 B+ │
└────┴───────────────────────────────────────────┴─────────┴──────┴───────┘
```

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd cloud-nettest-framework

# Setup virtual environment (Python 3.11+)
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
.venv/bin/pip install rich asyncssh pyyaml pydantic typer dnspython

# Verify installation
.venv/bin/python scripts/run_comprehensive_oracle_tests.py --help
```

### Prerequisites

- Python 3.11 or higher
- SSH access to probe nodes (AWS/Azure/GCP instances)
- Private SSH keys for authentication
- Network tools on probes: `ping`, `mtr`, `curl`

## ✨ Features

### 🔬 Comprehensive Network Tests

All tests execute on **remote cloud probes** with full packet capture:

#### ICMP Ping
- Multi-sample latency with statistical analysis
- Packet loss detection
- Jitter measurement (latency variability)

#### MTR (My TraceRoute)
- Complete path analysis with per-hop statistics
- Packet loss at each hop
- WHOIS lookup for ASN and organization
- Path quality scoring

#### HTTP/HTTPS Timing
- DNS lookup timing
- TCP handshake duration
- TLS negotiation time
- Server processing (TTFB)
- Content download speed
- Multi-sample statistics (min/max/avg/median)

#### Packet-Level Analysis
- **TCP Connection Tracking**: SYN/SYN-ACK/ACK handshakes
- **Retransmission Detection**: Identifies packet loss
- **Window Size Evolution**: Tracks TCP window scaling
- **Connection Quality Grading**: Automatic quality scores

### 📦 Layered Correlation (L3→L4→L7)

ANUBIS uniquely correlates network behavior across all layers:

```
Layer 3 (Network)     Layer 4 (Transport)    Layer 7 (Application)
     ↓                        ↓                        ↓
  ICMP Ping  ─────────→  TCP Sessions  ─────────→  HTTP Timing
  MTR Paths  ─────────→  Retransmissions ─────→  TLS Phases
```

**Example Correlation:**
- MTR shows 50ms path latency
- TCP handshake takes 52ms (matches!)
- TLS phase shows 3 retransmissions
- **Insight**: "TCP retransmissions during TLS causing 150ms slowdown"

See `docs/LAYERED_CORRELATION.md` for details.

### 🎨 Beautiful Cyberpunk Output

Inspired by Egyptian mythology and cyberpunk aesthetics:

- 🌈 **Color-coded metrics**: Green (excellent), Yellow (warning), Red (critical)
- 📊 **Rich tables**: Unicode box-drawing with performance grades
- 🏆 **Rankings**: Top 3 best/worst routes automatically identified
- 🎯 **Progress bars**: Real-time status with spinners
- 💠 **Hierarchical trees**: Nested test results and correlations

### 🎯 Oracle-Specific Diagnostics

Built from real Sev 1 incident analysis:

- **Bufferbloat Detection**: Identifies network queuing delays
- **Conntrack Monitoring**: Detects connection table exhaustion
- **Problem IP Tracking**: Monitors historically problematic endpoints (e.g., 134.70.16.1)
- **Regional Optimization**: Tests optimal probe→endpoint pairings

### 🌐 Multi-Cloud Support

Deploy probes across cloud providers:

- **AWS**: EC2 instances with metadata integration
- **Azure**: VM deployment (configuration ready)
- **GCP**: Compute Engine (configuration ready)

## 📊 Current Infrastructure

### Active AWS Probes

| Region | Instance ID | Public IP | Optimal For | Baseline Latency |
|--------|-------------|-----------|-------------|------------------|
| **us-east-1** (Virginia) | i-08b98d43fd53b67e4 | 54.87.147.228 | Oracle Ashburn | 0.95ms ⭐ |
| **us-west-1** (California) | i-03b2487f6057c504b | 3.101.64.113 | Oracle San Jose/Phoenix | 0.97ms ⭐ |
| **us-east-2** (Ohio) | i-04b05d483c4d369c1 | 18.218.117.3 | Balanced/Backup | 11.72ms |

### Oracle OCI Endpoints Tested

- **Ashburn** (us-ashburn-1): 134.70.24.1, 134.70.28.1, 134.70.32.1
- **Phoenix** (us-phoenix-1): 134.70.8.1, 134.70.12.1, 134.70.16.1 ⚠️
- **San Jose** (us-sanjose-1): 134.70.124.2

## 📖 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design and components
- **[Layered Correlation](docs/LAYERED_CORRELATION.md)** - L3→L4→L7 analysis explained
- **[Running Tests](RUNNING_TESTS.md)** - Detailed test execution guide
- **[Contributing](CONTRIBUTING.md)** - How to contribute
- **[Development Guide](WARP.md)** - For WARP IDE users

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

## 🧪 Example Test Plans

### Quick Demo (3 endpoints)

```bash
.venv/bin/python scripts/quick_oracle_demo.py
```

Tests 1 IP per Oracle region from all probes (~2 minutes).

### Comprehensive (7 endpoints)

```bash
./run_tests
```

Tests ALL Oracle IPs from ALL probes with full MTR (~5 minutes).

### Custom Test Plan

```yaml
# configs/custom_test.yaml
name: custom_oracle_test
description: "Custom endpoint testing"

probes:
  include:
    - provider: aws
      regions: ["us-west-1"]

targets:
  latency:
    - host: 134.70.124.2
      count: 20
  
  mtr:
    - host: 134.70.124.2
      cycles: 10
  
  http:
    - url: "https://objectstorage.us-sanjose-1.oraclecloud.com"
      samples: 5
```

## 🎯 Use Cases

### 1. Oracle Object Storage Performance

Monitor Oracle OCI performance from multiple regions with automatic best/worst route identification.

### 2. Network Troubleshooting

Identify where slowdowns occur:
- L3 issues: MTR shows problematic hops
- L4 issues: TCP retransmissions detected
- L7 issues: HTTP phase breakdown shows TLS delays

### 3. Multi-Region Baseline

Establish performance baselines across cloud regions for capacity planning.

### 4. Incident Response

Quickly diagnose Sev 1 network incidents with:
- Immediate multi-region testing
- Packet-level evidence capture
- Historical comparison to baselines

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code of Conduct
- Development setup
- Pull request process
- Coding standards

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

**ANUBIS** was forged in the fires of real-world production incidents:

- Oracle Object Storage Sev 1 network analysis
- Multi-region AWS EC2 testing campaigns
- TCP packet capture deep dives
- Real customer impact investigations

Built from comprehensive analysis documented in:
- `Oracle_Object_Storage_Network_Analysis_Report.md`
- `Oracle_Network_Diagnostic_Report.md`
- `Oracle_Network_Analysis_Handoff_Document.md`

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/anubis/issues)
- **Documentation**: `docs/` directory
- **Discussions**: [GitHub Discussions](https://github.com/your-username/anubis/discussions)

---

<div align="center">

**⚡ ANUBIS - Network Path Guardian ⚡**

*Guiding you through the network underworld, one packet at a time*

🔷 Egyptian Mythology Meets Cyberpunk Network Diagnostics 🔷

**[Get Started](#-quick-start)** • **[View Docs](#-documentation)** • **[Contribute](#-contributing)**

</div>
