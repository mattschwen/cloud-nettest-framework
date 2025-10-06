# Oracle OCI Object Storage Tests

Specialized testing for Oracle Cloud Infrastructure Object Storage, based on comprehensive network analysis conducted in October 2025.

## Background

This framework was built from real-world Oracle Object Storage network analysis that investigated:
- 471ms latency spike on IP 134.70.16.1 (since resolved to 59.5ms)
- ISP-level bufferbloat causing packet reordering
- Connection tracking table exhaustion on backend servers
- Multi-region performance variations

## Test Types

### 1. DNS Timing

Measures DNS resolution performance for Oracle Object Storage endpoints.

```yaml
targets:
  dns:
    - name: objectstorage.us-ashburn-1.oraclecloud.com
      qtype: A
      attempts: 3
```

**Metrics**:
- Query time (should be <10ms)
- IP addresses returned
- Success rate

**Oracle Baseline**: 0-2ms from AWS probes

### 2. TCP Connect Timing

Measures time to establish TCP connection to Oracle endpoints.

**Oracle Baselines**:
- Ashburn from us-east-1: 12.4ms
- Phoenix from us-west-1: 93.4ms
- San Jose from us-west-1: 12.4ms

### 3. TLS Handshake Timing

Measures TLS negotiation time.

**Expected**:
- Protocol: TLSv1.3
- Cipher: Strong ciphers (AES-256-GCM)
- Verification: OK

### 4. HTTP TTFB (Time To First Byte)

Measures server response time for Oracle Object Storage.

**Breakdown**:
```
TTFB = DNS + TCP Connect + TLS + Server Processing
```

**Oracle Baselines**:
- Ashburn: 20.1ms total (from us-east-1)
- Phoenix: 252ms total (from us-east-1)

### 5. Bufferbloat Detection

**Critical Test** - Detects ISP-level bufferbloat that causes:
- Packet reordering
- SACK (Selective ACK) events
- High latency variance
- Degraded performance

```yaml
targets:
  oci_object:
    - endpoint: us-phoenix-1
      test_types:
        - bufferbloat_detection
```

**How It Works**:
1. Sends 100 rapid pings (200ms interval)
2. Calculates min/avg/max latency
3. Computes bufferbloat score (max/min ratio)
4. Classifies severity

**Interpretation**:

| Score | Severity | Impact | Example |
|-------|----------|--------|---------|
| <5x | NONE | Normal network | 1ms min, 4ms max |
| 5-10x | MILD | Noticeable under load | 1ms min, 8ms max |
| 10-20x | MODERATE | Packet reordering likely | 1ms min, 15ms max |
| >20x | SEVERE | Significant performance issues | 2.7ms min, 471ms max |

**Real-World Example**:

From Oracle network analysis, hop 10.128.212.97 showed:
- Min: 2.7ms
- Max: 471ms
- **Ratio: 174x** - SEVERE bufferbloat

This caused:
- 447 SACK events in TCP dumps
- Out-of-order packet delivery
- 20-30s download times (vs 1-2s from office)

**Resolution**:
- Customer ISP issue (not Oracle)
- Explained office (fast) vs home (slow) performance difference

### 6. Conntrack Table Monitoring

**Critical Test** - Detects Linux connection tracking table exhaustion.

```yaml
targets:
  oci_object:
    - endpoint: us-ashburn-1
      test_types:
        - conntrack_check
```

**What It Checks**:
```bash
# Current connections
cat /proc/sys/net/netfilter/nf_conntrack_count

# Maximum connections
cat /proc/sys/net/netfilter/nf_conntrack_max

# Kernel errors
dmesg | grep -i conntrack
```

**Alert Thresholds**:
- >75% full: WARNING
- >90% full: CRITICAL

**Impact of Exhaustion**:
- Connection tracking state loss
- Packet drops
- Retry storms
- "90% read wait" times in storage requests

**Real-World Finding**:

From Oracle analysis, suspected issue:
- Default conntrack max: ~65k connections
- Web server likely near-full/full table
- Different customer IPs hashed to different web servers
- Server receiving problematic requests had exhausted conntrack
- Caused "90% of 10 seconds spent on read wait time"

**Verification Commands**:
```bash
# On suspected web server
cat /proc/sys/net/netfilter/nf_conntrack_count  # Should be << max
cat /proc/sys/net/netfilter/nf_conntrack_max    # Usually 65536
dmesg | grep -i conntrack                        # Check for "table full"
```

### 7. Packet Loss Detection

Standard packet loss measurement with Oracle-specific baselines.

**Expected**: 0% packet loss for healthy connections

**Alerts**:
- >1%: WARNING
- >5%: CRITICAL

### 8. Problem IP Monitoring

Monitors specific Oracle IPs with history of issues.

```yaml
targets:
  oci_object:
    - endpoint: us-phoenix-1
      monitor_ips:
        - 134.70.16.1  # Previously problematic
```

**Example: 134.70.16.1**

**History**:
- **Before**: 471ms latency (MTR analysis)
- **After**: 59.5ms latency (resolved)
- **Monitoring**: Alert if >100ms

**What Changed**:
- Different routing path through GTT network
- Oracle backend optimization
- Load balancer health restored

**Current Status**: ✅ Resolved and stable

## Comprehensive OCI Test

Run all Oracle-specific tests at once:

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
        - conntrack_check
```

**Output**:
```json
{
  "endpoint": "us-ashburn-1",
  "hostname": "objectstorage.us-ashburn-1.oraclecloud.com",
  "tests": {
    "dns": { "avg_query_time_ms": 0.024 },
    "latency": { "avg_ms": 1.05, "packet_loss_pct": 0.0 },
    "tls": { "handshake_time_ms": 12.4 },
    "http": { "ttfb_ms": 19.973 },
    "bufferbloat": { "severity": "NONE", "bufferbloat_score": 1.1 },
    "conntrack": { "usage_pct": 23.2, "status": "OK" }
  },
  "overall_health": "HEALTHY",
  "issues": []
}
```

## Performance Baselines

### From Oracle Network Analysis (2025-10-05)

#### Ashburn (us-ashburn-1)

| Probe Region | ICMP Ping | TCP Connect | HTTPS Total | Grade |
|--------------|-----------|-------------|-------------|-------|
| **aws-us-east-1** | 1.05ms | 12.4ms | 20.1ms | A+ |
| aws-us-east-2 | ~13.8ms | - | 60.3ms | A |
| aws-us-west-1 | ~63.4ms | - | 259.8ms | B |

#### Phoenix (us-phoenix-1)

| Probe Region | ICMP Ping | TCP Connect | HTTPS Total | Grade |
|--------------|-----------|-------------|-------------|-------|
| **aws-us-west-1** | 19.4ms | 93.4ms | 93.4ms | A+ |
| aws-us-east-1 | 61.96ms | 84.8ms | 252ms | B |
| aws-us-east-2 | ~58.8ms | - | 208.7ms | B |

#### San Jose (us-sanjose-1)

| Probe Region | ICMP Ping | TCP Connect | HTTPS Total | Grade |
|--------------|-----------|-------------|-------------|-------|
| **aws-us-west-1** | <1ms | 12.4ms | 12.4ms | A+ |
| aws-us-east-1 | 62.34ms | 61.4ms | 255ms | B |
| aws-us-east-2 | ~50.9ms | - | 206.6ms | B |

## Oracle IP Addresses

### Ashburn IPs
- 134.70.24.1
- 134.70.28.1
- 134.70.32.1

**Behavior**: Respond to ICMP, filter TCP direct connections, require hostname-based HTTPS

### Phoenix IPs
- 134.70.8.1 (baseline: 53.9ms from us-east-1)
- 134.70.12.1 (baseline: 56.5ms from us-east-1)
- **134.70.16.1** (baseline: 59.5ms - previously 471ms) ⚠️ Monitor

**Note**: All IPs now performing normally

### San Jose IPs
- 134.70.124.2

## Security Posture

Oracle implements proper defense-in-depth:

```
✅ ICMP (Ping):         ALLOWED     (Network health monitoring)
❌ TCP Direct Connect:  FILTERED    (Security policy)
✅ HTTPS via Hostname:  ALLOWED     (Proper routing)
❌ HTTP (port 80):      FILTERED    (Security policy)
❌ SSH (port 22):       FILTERED    (Security policy)
```

**Expected Behavior**:
- Ping works
- `curl https://IP/` fails (requires hostname)
- `curl https://objectstorage.region.oraclecloud.com/` works
- Returns 404 for unauthenticated requests (correct)

## Troubleshooting Guide

### High Latency

**Symptom**: Latency >200ms to Oracle endpoint

**Check**:
1. Run bufferbloat test
2. Check geographic proximity (use optimal region)
3. Test from different probe
4. Run traceroute to identify slow hop

**Common Causes**:
- ISP bufferbloat
- Suboptimal routing
- Geographic distance

### Packet Loss

**Symptom**: >1% packet loss

**Check**:
1. Run MTR to identify loss location
2. Check conntrack status
3. Verify security groups
4. Test different protocols (ICMP vs TCP)

**Common Causes**:
- Conntrack table full
- Rate limiting
- Network congestion

### Slow Downloads

**Symptom**: "90% read wait time" or slow object retrieval

**Check**:
1. Conntrack table status
2. Bufferbloat severity
3. TCP packet analysis (SACK events)
4. Network path (traceroute)

**Common Causes**:
- Conntrack exhaustion (server-side)
- Bufferbloat (client ISP)
- Packet reordering
- Server backend issues

### Previously Problematic IP

**Symptom**: 134.70.16.1 showing high latency again

**Action**:
1. Confirm with multiple probes
2. Check routing path changes
3. Alert Oracle support
4. Reference historical baseline (59.5ms)

## Integration with Test Plans

### Minimal OCI Test

```yaml
name: oci_quick_health
targets:
  dns:
    - name: objectstorage.us-ashburn-1.oraclecloud.com
  latency:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      count: 10
```

### Standard OCI Test

```yaml
name: oci_standard_test
targets:
  dns: [...]
  latency: [...]
  http: [...]
  tls: [...]
```

### Full Diagnostic

```yaml
name: oci_full_diagnostic
targets:
  oci_object:
    - endpoint: us-phoenix-1
      test_types:
        - dns_timing
        - tcp_connect_timing
        - tls_handshake_timing
        - http_ttfb
        - bufferbloat_detection
        - conntrack_check
      monitor_ips:
        - 134.70.16.1
```

## Monitoring Recommendations

### Continuous Monitoring

Run every 15 minutes:
```yaml
name: oci_continuous_monitor
targets:
  latency:
    - host: 134.70.16.1
      alert_threshold: 100
```

### Daily Baseline

Run daily for trending:
```yaml
name: oci_daily_baseline
targets:
  oci_object:
    - endpoint: us-ashburn-1
    - endpoint: us-phoenix-1
    - endpoint: us-sanjose-1
```

### Alert Conditions

- Latency >150ms (warn), >200ms (critical)
- Packet loss >1% (warn), >5% (critical)
- Bufferbloat severity: MODERATE or SEVERE
- Conntrack usage >75% (warn), >90% (critical)
- 134.70.16.1 latency >100ms (regression)

---

**Reference**: Based on comprehensive Oracle Object Storage network analysis including TCP packet capture, MTR path analysis, and multi-region performance testing (2025-10-05).
