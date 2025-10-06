# Running Network Diagnostics

Complete guide to running comprehensive network tests from AWS EC2 probes to Oracle OCI endpoints.

## 🚀 Quick Start

### Option 1: Quick Demo (30 seconds)

See all capabilities in action:

```bash
./scripts/quick_demo.sh
```

**What it shows:**
- ✅ Ping from us-west-1 → Oracle San Jose (0.98ms)
- ✅ MTR path analysis (6 hops, full route)
- ✅ HTTP GET timing breakdown (DNS, TCP, TLS phases)
- ✅ Live packet capture (tcpdump)
- ✅ Ping from us-east-2 → Oracle Ashburn (13.38ms)

**Output example:**
```
Test 1: Ping from us-west-1 → Oracle San Jose
10 packets transmitted, 10 received, 0% packet loss
rtt min/avg/max/mdev = 0.943/0.982/1.111/0.050 ms

Test 2: MTR Path Analysis
HOST: ip-172-31-23-26    Loss%   Snt   Last   Avg  Best  Wrst StDev
  1. 240.0.168.13         0.0%    10    1.2   1.3   1.2   1.6   0.1
  2. 240.0.168.30         0.0%    10    1.0   1.0   0.9   1.1   0.1
  ...
  6. 134.70.124.2         0.0%    10    1.0   1.0   1.0   1.1   0.0

Test 3: HTTP GET Timing
DNS: 0.002073s | TCP: 0.003080s | TLS: 0.065148s | Total: 0.067594s
```

---

### Option 2: Multi-Probe Comprehensive Test (5 minutes)

Run full diagnostics from both AWS probes:

```bash
source .venv/bin/activate
python scripts/run_all_probes.py
```

**What it does:**
- Tests from **us-west-1** → Oracle San Jose
- Tests from **us-east-2** → Oracle Ashburn
- For each test runs:
  1. Packet capture (tcpdump on probe)
  2. Ping (20 packets)
  3. MTR (15 cycles)
  4. HTTP GET (5 samples with statistics)
  5. Packet analysis (retransmissions, quality)

**Output includes:**
```
🌐 HTTP Timing Breakdown
Phase             Min      Avg      Max      Median
DNS Lookup       0.95ms   1.41ms   2.96ms   1.06ms
TCP Handshake    1.02ms   1.05ms   1.10ms   1.03ms
TLS Handshake   52.67ms  53.06ms  53.47ms  52.98ms
Server Process   1.79ms   2.15ms   2.51ms   2.16ms
Total           57.20ms  57.78ms  58.64ms  57.63ms

📊 Connection Quality
Total Packets: 117
Retransmissions: 0 (0.00%)
Duplicate ACKs: 0
Out-of-Order: 0
Quality Score: EXCELLENT

Overall Health: 🟢 EXCELLENT
```

---

### Option 3: View Existing Results

Display previously run test results with beautiful formatting:

```bash
cnf report view
```

Shows the last live test results from `LIVE_TEST_RESULTS.md`.

---

## 🧪 Detailed Test Options

### Test Individual Components

#### Just Ping Test
```bash
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'ping -c 20 134.70.124.2'
```

#### Just MTR
```bash
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'mtr -n -c 15 -r 134.70.124.2'
```

#### Just HTTP Timing
```bash
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'curl -w "@curl-format.txt" -o /dev/null -s https://objectstorage.us-sanjose-1.oraclecloud.com'
```

#### Packet Capture Only
```bash
# Start capture
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'sudo tcpdump -i any -n host 134.70.124.2 -w /tmp/capture.pcap' &

# Run your tests...

# Stop capture
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'sudo pkill tcpdump'

# Analyze
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'sudo tcpdump -r /tmp/capture.pcap -n'
```

---

## 📋 Available Probes

| Region | Instance ID | Public IP | Best For | Key |
|--------|-------------|-----------|----------|-----|
| **us-west-1** | i-035a2165f45edc09c | 3.101.64.113 | San Jose, Phoenix | `~/.ssh/network-testing-key-west.pem` |
| **us-east-2** | i-0dfc6bdd6a24ca82e | 18.222.238.187 | Ashburn, Central | `~/.ssh/network-testing-key-east2.pem` |

### SSH to Probes

```bash
# us-west-1
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113

# us-east-2
ssh -i ~/.ssh/network-testing-key-east2.pem ubuntu@18.222.238.187
```

---

## 🎯 Test Targets

### Oracle OCI Object Storage Endpoints

| Region | Primary IP | DNS |
|--------|-----------|-----|
| **Ashburn** | 134.70.24.1 | objectstorage.us-ashburn-1.oraclecloud.com |
| **Phoenix** | 134.70.16.1 | objectstorage.us-phoenix-1.oraclecloud.com |
| **San Jose** | 134.70.124.2 | objectstorage.us-sanjose-1.oraclecloud.com |

---

## 🔬 Comprehensive Diagnostic Modes

### Mode 1: Single Target Deep Dive

Test one target with all diagnostics:

```python
from cnf.tests.comprehensive import comprehensive_target_test
from cnf.registry import load_registry

registry = load_registry()
probe = registry.hosts[1]  # us-west-1

result = await comprehensive_target_test(
    host=probe,
    target_ip="134.70.124.2",
    target_url="https://objectstorage.us-sanjose-1.oraclecloud.com",
    ping_count=30,
    http_samples=5,
    mtr_cycles=20,
    capture_packets=True
)
```

### Mode 2: Multi-Target Survey

Test all Oracle endpoints:

```bash
cnf test run --plan configs/oracle_comprehensive.yaml
```

### Mode 3: Continuous Monitoring

Monitor one target over time:

```python
from cnf.tests.comprehensive import continuous_monitoring

result = await continuous_monitoring(
    host=probe,
    target_ip="134.70.124.2",
    duration_minutes=60,
    test_interval_seconds=60
)
```

---

## 📊 What Gets Measured

### Ping Tests
- Min/max/avg/stddev latency (ms)
- Packet loss percentage
- Jitter (latency variability)

### MTR Tests
- Number of hops
- Per-hop packet loss
- Per-hop latency statistics
- Path quality score
- Problematic hop identification

### HTTP Tests (5 samples each)
- **DNS lookup**: Name resolution time
- **TCP handshake**: 3-way handshake duration
- **TLS handshake**: SSL/TLS negotiation
- **Server processing**: Time to first byte (TTFB)
- **Content download**: Transfer time
- **Transfer speed**: Mbps measurement

### Packet Analysis
- TCP connection attempts vs successful
- SYN/SYN-ACK/ACK tracking
- FIN vs RST closes
- Retransmission count and rate
- Duplicate ACK detection
- Out-of-order packets
- SACK events
- Window size analysis
- Connection quality score

---

## 🎨 Output Formats

Results are displayed in multiple formats:

### 1. Beautiful Terminal Output
- Color-coded metrics (green/yellow/red)
- Unicode tables and boxes
- Performance grades (A+, A, B, C, D)
- Emoji indicators 🥇🥈🥉
- Real-time progress bars

### 2. JSON Files
```bash
# Results saved to:
runs/<timestamp>/raw_results.json
```

### 3. Markdown Reports
```bash
# Human-readable markdown:
runs/<timestamp>/summary.md
```

---

## 💡 Pro Tips

### 1. Compare Routes

Test the same endpoint from different probes:

```bash
# From us-west-1
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'ping -c 10 134.70.16.1' # Phoenix

# From us-east-2
ssh -i ~/.ssh/network-testing-key-east2.pem ubuntu@18.222.238.187 \
  'ping -c 10 134.70.16.1' # Phoenix
```

### 2. Long-Term Monitoring

Use cron on the probe itself:

```bash
# Add to crontab on probe
*/5 * * * * ping -c 5 134.70.124.2 >> /var/log/oracle-ping.log
```

### 3. Capture Specific Issues

Target specific TCP flags:

```bash
# Only capture SYN packets
sudo tcpdump -i any 'tcp[tcpflags] & tcp-syn != 0' host 134.70.124.2
```

### 4. Analyze Retransmissions

```bash
# Look for retransmissions in capture
sudo tcpdump -r /tmp/capture.pcap -n -v | grep retransmission
```

---

## 🐛 Troubleshooting

### Can't SSH to probe?

```bash
# Check if instance is running
aws ec2 describe-instances --instance-ids i-035a2165f45edc09c \
  --query 'Reservations[0].Instances[0].State.Name'

# Verify SSH key permissions
chmod 400 ~/.ssh/network-testing-key-west.pem
```

### tcpdump permission denied?

```bash
# The user needs sudo access for tcpdump
# If failing, check: sudo tcpdump --version
```

### MTR command not found?

```bash
# Install on probe if missing
ssh ubuntu@3.101.64.113 'sudo apt-get update && sudo apt-get install -y mtr-tiny'
```

---

## 📖 Examples

### Example 1: Quick Health Check

```bash
./scripts/quick_demo.sh
```

### Example 2: Detailed San Jose Analysis

```bash
python scripts/run_all_probes.py
# Select us-west-1 → San Jose test
```

### Example 3: Compare All Routes

```bash
# Run comprehensive plan (tests all combinations)
cnf test run --plan configs/oracle_comprehensive.yaml
```

---

## ✅ Verification

After running tests, verify results:

```bash
# Check latency quality
grep "avg_ms" runs/latest/raw_results.json

# Check packet loss
grep "packet_loss_pct" runs/latest/raw_results.json

# View comprehensive summary
cnf report view
```

---

## 🎯 Best Practices

1. **Always test from probe nearest to target**
   - us-west-1 → San Jose/Phoenix (best)
   - us-east-2 → Ashburn (best)

2. **Run multiple samples for statistical accuracy**
   - Ping: 20-30 packets
   - HTTP: 5+ samples
   - MTR: 15+ cycles

3. **Capture packets when troubleshooting**
   - Enables TCP-level diagnosis
   - Can review offline later

4. **Compare before/after when changes made**
   - Save baseline results
   - Re-run after infrastructure changes

---

**All tests execute on AWS EC2 instances. Local machine only orchestrates and displays results.**

For more details, see:
- `README.md` - Framework overview
- `docs/OUTPUT_FORMATTING.md` - Display formatting guide
- `configs/oracle_comprehensive.yaml` - Full test plan example
