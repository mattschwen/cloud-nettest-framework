# Test Matrix

Complete reference for all available network tests in Cloud NetTest Framework.

## Test Types Overview

| Test Type | Purpose | Protocol | Requires Sudo | Outputs |
|-----------|---------|----------|---------------|---------|
| DNS | Resolution timing | UDP/53 | No | Query time, IPs |
| Latency | Round-trip time | ICMP/TCP | No* | Min/avg/max/stddev |
| HTTP | Request timing | TCP/443 | No | DNS, connect, TLS, TTFB, total |
| TLS | Handshake timing | TCP/443 | No | Handshake time, cert info |
| Traceroute | Path discovery | ICMP/TCP/UDP | No* | Hop-by-hop latency |
| Throughput | Bandwidth | TCP (iperf3) | No | Mbps, retransmits |
| OCI Object | Oracle diagnostics | Multiple | Yes** | Comprehensive |

\* ICMP may require sudo on some systems  
\** Conntrack and packet capture require sudo

## DNS Tests

### Configuration

```yaml
targets:
  dns:
    - name: objectstorage.us-ashburn-1.oraclecloud.com
      qtype: A              # A, AAAA, CNAME, MX, TXT, etc.
      attempts: 3           # Number of query attempts
      timeout_s: 5          # Timeout per attempt
```

### Metrics Collected

- **query_time_ms**: DNS resolution time
- **answers**: List of IP addresses or records
- **success_rate**: Percentage of successful queries
- **avg_query_time_ms**: Average across attempts

### Use Cases

- Verify DNS resolution works
- Measure DNS server response time
- Detect DNS issues causing delays
- Compare DNS performance across regions

### Example Output

```json
{
  "target": "objectstorage.us-ashburn-1.oraclecloud.com",
  "qtype": "A",
  "success_rate": 1.0,
  "avg_query_time_ms": 2.3,
  "attempts": [
    {
      "success": true,
      "query_time_ms": 2.1,
      "answers": ["134.70.24.1", "134.70.28.1"]
    }
  ]
}
```

## Latency Tests

### Configuration

```yaml
targets:
  latency:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      mode: icmp            # icmp or tcp
      count: 10             # Number of pings
      port: 443             # For TCP mode
      fallback_tcp_port: 443  # Fallback if ICMP fails
      alert_threshold: 100  # Alert if avg > threshold
```

### Metrics Collected

- **min_ms**: Minimum RTT
- **avg_ms**: Average RTT
- **max_ms**: Maximum RTT
- **stddev_ms**: Standard deviation (jitter)
- **packet_loss_pct**: Packet loss percentage
- **packets_sent/received**: Packet counts

### Use Cases

- Measure network latency
- Detect packet loss
- Identify jitter/variance
- Monitor latency over time
- Alert on degradation

### Example Output

```json
{
  "target": "objectstorage.us-ashburn-1.oraclecloud.com",
  "test_type": "icmp_ping",
  "success": true,
  "stats": {
    "min_ms": 1.01,
    "avg_ms": 1.05,
    "max_ms": 1.12,
    "stddev_ms": 0.04,
    "packet_loss_pct": 0.0,
    "packets_sent": 10,
    "packets_received": 10
  }
}
```

## HTTP Tests

### Configuration

```yaml
targets:
  http:
    - url: "https://objectstorage.us-ashburn-1.oraclecloud.com/test"
      name: ashburn_get       # Optional name
      method: GET             # GET, POST, HEAD, etc.
      retries: 2              # Number of retries on failure
      timeout_s: 15           # Total timeout
      expected_status: [200, 404]  # Expected HTTP codes
```

### Metrics Collected

- **dns_time_ms**: DNS resolution time
- **connect_time_ms**: TCP connection time
- **tls_time_ms**: TLS handshake time
- **ttfb_ms**: Time to first byte
- **total_time_ms**: Total request time
- **status_code**: HTTP status code
- **content_length**: Response size

### Timing Breakdown

```
total_time = dns_time + connect_time + tls_time + ttfb + download_time
```

### Use Cases

- Measure end-to-end HTTP performance
- Identify bottlenecks (DNS, connect, TLS, server)
- Validate HTTPS connectivity
- Monitor API endpoints
- Track Time To First Byte (TTFB)

### Example Output

```json
{
  "url": "https://objectstorage.us-ashburn-1.oraclecloud.com/...",
  "method": "GET",
  "success": true,
  "status_code": 404,
  "dns_time_ms": 0.024,
  "connect_time_ms": 11.949,
  "tls_time_ms": 8.001,
  "ttfb_ms": 19.973,
  "total_time_ms": 19.973
}
```

## TLS Tests

### Configuration

```yaml
targets:
  tls:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      port: 443
      timeout_s: 10
      verify: true          # Verify certificate
```

### Metrics Collected

- **handshake_time_ms**: TLS handshake duration
- **cert_info.common_name**: Certificate CN
- **cert_info.protocol**: TLS version (TLSv1.2, TLSv1.3)
- **cert_info.cipher**: Cipher suite
- **cert_info.verification**: OK or FAILED

### Use Cases

- Verify TLS configuration
- Measure handshake performance
- Check certificate validity
- Audit TLS versions and ciphers
- Detect SSL/TLS issues

### Example Output

```json
{
  "host": "objectstorage.us-ashburn-1.oraclecloud.com",
  "port": 443,
  "success": true,
  "handshake_time_ms": 12.4,
  "cert_info": {
    "common_name": "*.objectstorage.us-ashburn-1.oraclecloud.com",
    "protocol": "TLSv1.3",
    "cipher": "TLS_AES_256_GCM_SHA384",
    "verification": "OK"
  }
}
```

## Traceroute Tests

### Configuration

```yaml
targets:
  traceroute:
    - host: objectstorage.us-ashburn-1.oraclecloud.com
      max_hops: 30
      mode: tcp             # tcp, udp, or icmp
      port: 443             # For TCP/UDP mode
      use_mtr: false        # Use MTR instead of traceroute
      count: 10             # MTR packet count
```

### Metrics Collected

- **hops**: List of intermediate routers
  - **hop**: Hop number
  - **ip**: Router IP
  - **latencies_ms**: RTT measurements
  - **avg_latency_ms**: Average latency to this hop
- **total_hops**: Number of hops to destination

### MTR Additional Metrics

- **loss_pct**: Packet loss at hop
- **sent**: Packets sent
- **best_ms/worst_ms**: Min/max latency
- **stddev_ms**: Latency variance

### Use Cases

- Identify network path
- Find routing issues
- Detect packet loss locations
- Measure hop-by-hop latency
- Diagnose bufferbloat (with MTR)

### Example Output

```json
{
  "target": "objectstorage.us-ashburn-1.oraclecloud.com",
  "mode": "tcp",
  "success": true,
  "total_hops": 8,
  "hops": [
    {
      "hop": 1,
      "ip": "172.31.0.1",
      "latencies_ms": [0.2, 0.3, 0.2],
      "avg_latency_ms": 0.23
    },
    {
      "hop": 2,
      "ip": "100.100.32.116",
      "latencies_ms": [0.5, 0.6, 0.5],
      "avg_latency_ms": 0.53
    }
  ]
}
```

## Throughput Tests

### Configuration

```yaml
targets:
  throughput:
    - iperf_server: iperf.example.com
      port: 5201
      duration_s: 10
      reverse: false        # false=upload, true=download
      udp: false            # TCP or UDP
      parallel: 1           # Parallel streams
```

### Metrics Collected

- **throughput_mbps**: Measured throughput
- **protocol**: TCP or UDP
- **direction**: upload or download
- **retransmits**: TCP retransmission count
- **bytes_transferred**: Total bytes

### Use Cases

- Measure available bandwidth
- Test network capacity
- Identify throttling
- Compare upload vs download
- Validate network SLAs

### Requirements

- iperf3 installed on probe
- iperf3 server accessible
- Server running: `iperf3 -s`

### Example Output

```json
{
  "server": "iperf.example.com",
  "port": 5201,
  "success": true,
  "throughput_mbps": 945.2,
  "protocol": "TCP",
  "direction": "upload",
  "retransmits": 0,
  "bytes_transferred": 1179648000
}
```

## Oracle OCI Object Tests

### Configuration

```yaml
targets:
  oci_object:
    - endpoint: us-ashburn-1     # OCI region
      test_types:
        - dns_timing
        - tcp_connect_timing
        - tls_handshake_timing
        - http_ttfb
        - full_request_timing
        - bufferbloat_detection
        - packet_loss_check
        - conntrack_check
      monitor_ips:
        - 134.70.16.1              # Specific IPs to monitor
```

### Test Types

#### bufferbloat_detection

Detects ISP-level bufferbloat using ping variance:

**Metrics**:
- min_ms, avg_ms, max_ms, stddev_ms
- bufferbloat_score (max/min ratio)
- severity: NONE, MILD, MODERATE, SEVERE

**Classification**:
- Severe: ratio >20x
- Moderate: ratio 10-20x
- Mild: ratio 5-10x
- None: ratio <5x

**Interpretation**:
- Severe bufferbloat causes packet reordering and SACK events
- High coefficient of variation indicates jitter

#### conntrack_check

Monitors Linux netfilter connection tracking table:

**Metrics**:
- count: Current connections
- max: Maximum table size
- usage_pct: Percentage full

**Alerts**:
- WARNING: >75% full
- CRITICAL: >90% full

**Impact**:
- Connection tracking state loss
- Packet drops
- "90% read wait" times in storage requests

#### tcp_packet_analysis

Captures and analyzes TCP packets:

**Metrics** (requires sudo):
- packets_captured: Total packets
- sack_events: Selective ACK count
- retransmissions: Retransmitted packets
- sack_rate_pct: SACK event rate

**Alerts**:
- High SACK rate (>5%) indicates packet loss/reordering

#### problem_ip_monitor

Monitors specific IPs with history of issues:

**Example**: 134.70.16.1 (Oracle Phoenix)
- Previously: 471ms latency
- Resolved to: 59.5ms
- Alert threshold: 100ms

### Use Cases

- Diagnose Oracle Object Storage performance issues
- Detect network-level problems (bufferbloat, conntrack)
- Monitor previously problematic endpoints
- Comprehensive Oracle endpoint health checks

### Example Output

```json
{
  "endpoint": "us-ashburn-1",
  "hostname": "objectstorage.us-ashburn-1.oraclecloud.com",
  "tests": {
    "dns": { ... },
    "latency": { ... },
    "bufferbloat": {
      "test": "bufferbloat_detection",
      "success": true,
      "min_ms": 1.01,
      "avg_ms": 1.05,
      "max_ms": 5.2,
      "bufferbloat_score": 5.1,
      "severity": "MILD"
    },
    "conntrack": {
      "test": "conntrack_check",
      "success": true,
      "count": 15234,
      "max": 65536,
      "usage_pct": 23.2,
      "status": "OK"
    }
  },
  "overall_health": "HEALTHY"
}
```

## Test Combinations

### Recommended Test Suites

#### 1. Quick Health Check
```yaml
targets:
  dns: [...]
  latency: [...]
```

#### 2. Performance Baseline
```yaml
targets:
  dns: [...]
  latency: [...]
  http: [...]
  tls: [...]
```

#### 3. Comprehensive Diagnostic
```yaml
targets:
  dns: [...]
  latency: [...]
  http: [...]
  tls: [...]
  traceroute: [...]
  oci_object: [...]
```

#### 4. Oracle Problem Investigation
```yaml
targets:
  oci_object:
    - endpoint: us-phoenix-1
      test_types:
        - bufferbloat_detection
        - conntrack_check
        - tcp_packet_analysis
      monitor_ips:
        - 134.70.16.1
```

---

**Performance Note**: Tests run sequentially per probe but probes execute in parallel (configurable concurrency).
