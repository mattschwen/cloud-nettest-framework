# Layered Network Correlation (L3 → L4 → L7)

## Overview

The Cloud NetTest Framework provides **deep packet-level correlation** across all network layers, giving you a complete picture from the physical network path all the way to application performance.

## What Gets Correlated

### Layer 3 (Network)
- **ICMP Ping**: Latency, jitter, packet loss
- **MTR Path Analysis**: Hop-by-hop latency and loss
- **Route Quality**: Path stability and problematic hop detection

### Layer 4 (Transport)
- **TCP Session Analysis**: Connection establishment, retransmissions
- **Packet Capture**: Live tcpdump during all tests
- **Connection Quality**: Window sizes, duplicate ACKs, out-of-order packets

### Layer 7 (Application)
- **HTTP Timing**: DNS, TCP handshake, TLS negotiation, TTFB, download
- **Phase Breakdown**: Percentage of time in each HTTP phase
- **Performance Grading**: Overall application responsiveness

## Cross-Layer Correlations

### 1. TCP-to-HTTP Phase Mapping

**Question Answered**: *"Which TCP events happened during which HTTP phase?"*

For each HTTP request, we capture TCP packets and map them to specific phases:

```
HTTP Request Timeline:
├── DNS Lookup (0-2ms)
│   └── TCP Events: [captured packet events]
├── TCP Handshake (2-5ms)
│   ├── SYN sent
│   ├── SYN-ACK received
│   └── ACK sent
├── TLS Negotiation (5-60ms)
│   ├── ClientHello
│   ├── ServerHello
│   ├── Certificates exchanged
│   └── [retransmissions here impact TLS timing!]
├── Server Processing (60-63ms)
│   └── Waiting for response
└── Content Download (63-70ms)
    ├── Data packets received
    └── [window size evolution tracked]
```

**What You Learn**:
- If retransmissions occur during TLS, you'll see TLS timing spike
- If window sizes are small during download, you'll see slow transfer
- If duplicate ACKs happen, you'll see which HTTP phase was affected

### 2. MTR-to-TCP Correlation

**Question Answered**: *"Does network path latency match actual TCP handshake time?"*

MTR gives us the expected round-trip time based on the network path. We compare this to the actual TCP handshake duration:

```
MTR Analysis:
Hop 1: 1.2ms
Hop 2: 1.5ms
Hop 3: 2.0ms
...
Hop 6 (final): 1.0ms one-way = 2.0ms RTT predicted

TCP Handshake: 2.1ms actual

Variance: +0.1ms (+5%) ✅ Good correlation!
```

**What You Learn**:
- If TCP is slower than predicted, there may be server-side delays
- If TCP matches path latency, network is the bottleneck
- Identifies whether issues are network or endpoint

### 3. L3 → L4 Correlation

**Question Answered**: *"Are network path issues causing TCP problems?"*

We correlate ICMP/MTR results with TCP connection quality:

```
Scenario A: Path is degraded → TCP is degraded
  Finding: "Path issues causing TCP degradation"
  Action: Investigate network route or ISP

Scenario B: Path is excellent → TCP is degraded
  Finding: "TCP issues despite good path (endpoint problem?)"
  Action: Investigate server congestion or firewall
```

### 4. L4 → L7 Correlation

**Question Answered**: *"Are TCP issues affecting application performance?"*

We track which TCP events correlate with HTTP slowdowns:

```
HTTP Phase: TLS Negotiation (should be ~50ms)
TCP Events During This Phase:
  - 3 retransmissions detected
  - Window size: 32KB (limited)

Result: TLS phase took 150ms instead of 50ms
Finding: "TCP retransmissions during TLS handshake: 3 retransmissions"
```

## How It Works

### 1. Synchronized Packet Capture

```python
async with PacketCapture(host) as capture:
    # Start capturing ALL TCP packets to target
    await capture.start_capture(target_ip, max_packets=2000)

    # Record timestamp when HTTP starts
    http_start_time = time.time()

    # Run HTTP test (with detailed timing)
    http_result = await comprehensive_http_get(host, url, samples=5)

    # Stop capture
    await capture.stop_capture()

    # Now correlate: we have timestamps for:
    # - When each HTTP phase started/ended
    # - When each TCP packet was sent/received
    # We can map packets to phases!
```

### 2. Timestamp Correlation

```python
# HTTP phases with durations
phases = {
    "tcp_handshake": 3.2ms,
    "tls_negotiation": 52.5ms,
    "server_processing": 2.1ms,
    "download": 5.8ms
}

# Calculate phase boundaries
tcp_end = 3.2ms
tls_end = 3.2ms + 52.5ms = 55.7ms
server_end = 55.7ms + 2.1ms = 57.8ms

# For each TCP packet with timestamp
for packet in tcp_packets:
    if packet.time <= tcp_end:
        phase = "tcp_handshake"
    elif packet.time <= tls_end:
        phase = "tls_negotiation"
    # ... map packet to phase

    if packet.is_retransmission:
        retransmissions_by_phase[phase] += 1
```

### 3. Multi-Layer Quality Assessment

```python
# Assess each layer independently
L3_quality = assess_icmp_and_mtr(ping_result, mtr_result)
L4_quality = assess_tcp_session(packet_analysis)
L7_quality = assess_http_performance(http_result)

# Then look for correlations
if L3_quality == "degraded" and L4_quality == "degraded":
    insight = "Path issues causing TCP degradation"
elif L3_quality == "excellent" but L4_quality == "degraded":
    insight = "TCP issues despite good path - investigate endpoint"
```

## Example Output

### Layered Analysis Table

```
┌─────────────────────────── Network Stack Analysis ───────────────────────────┐
│ Layer │ Component           │  Quality   │ Key Metrics                        │
├───────┼─────────────────────┼────────────┼────────────────────────────────────┤
│  L3   │ Network/ICMP        │  EXCELLENT │ Latency: 1.02ms avg, 0.15ms jitter │
│       │                     │            │ Path: 6 hops, Quality: excellent   │
├───────┼─────────────────────┼────────────┼────────────────────────────────────┤
│  L4   │ Transport/TCP       │  EXCELLENT │ Score: EXCELLENT, Retrans: 0.0%    │
│       │                     │            │ Packets: 117, DupACK: 0, OOO: 0    │
├───────┼─────────────────────┼────────────┼────────────────────────────────────┤
│  L7   │ Application/HTTP    │    GOOD    │ Total: 58.2ms                      │
│       │                     │            │ TCP 5%, TLS 88%, Server 4%, DL 3%  │
└───────┴─────────────────────┴────────────┴────────────────────────────────────┘
```

### TCP-to-HTTP Phase Correlation

```
┌─────────────────────── TCP Events During HTTP Phases ───────────────────────┐
│ HTTP Phase           │   Duration │  TCP Events │ Retransmissions │ Retrans Rate │
├──────────────────────┼────────────┼─────────────┼─────────────────┼──────────────┤
│ Tcp Handshake        │     3.08ms │          15 │               0 │        0.00% │
│ Tls Negotiation      │    52.67ms │          58 │               0 │        0.00% │
│ Server Processing    │     1.79ms │          12 │               0 │        0.00% │
│ Content Download     │     5.12ms │          32 │               0 │        0.00% │
└──────────────────────┴────────────┴─────────────┴─────────────────┴──────────────┘
```

### Cross-Layer Correlations Tree

```
🔗 Cross-Layer Correlations
├── L3 → L4 (Path affects TCP)
│   └── No issues detected - excellent path quality
├── L4 → L7 (TCP affects HTTP)
│   ├── Retransmissions per HTTP phase: None
│   ├── Window size tracked across 117 events
│   └── Total bytes transferred: 4,892
└── End-to-End Summary
    └── Excellent performance across all layers
```

### Insights

```
💡 Network Insights

🟢 [L3→L4] Path quality excellent - no impact on TCP
🟢 [L4→L7] Zero retransmissions - clean TCP session
✅ Overall: All layers performing optimally
```

## Running Layered Correlation

### Option 1: Comprehensive Test (Automatic)

The comprehensive test automatically performs layered correlation:

```python
from cnf.tests.comprehensive import comprehensive_target_test

result = await comprehensive_target_test(
    host=probe,
    target_ip="134.70.124.2",
    target_url="https://objectstorage.us-sanjose-1.oraclecloud.com",
    capture_packets=True  # Enable packet correlation
)

# Result includes:
# - result["layered_analysis"] - Full L3→L4→L7 analysis
# - result["tcp_http_correlation"] - TCP events per HTTP phase
# - result["mtr_tcp_correlation"] - Path vs TCP comparison
```

### Option 2: Demo Script

Run the demonstration:

```bash
source .venv/bin/activate
python scripts/demo_layered_correlation.py
```

This shows:
1. Individual test results (ping, MTR, HTTP, packets)
2. Layered correlation analysis
3. TCP-to-HTTP phase mapping
4. MTR-to-TCP comparison
5. Cross-layer insights

## Use Cases

### 1. Troubleshooting Slow HTTP Requests

**Symptom**: HTTP requests taking 500ms instead of 50ms

**Analysis**:
```
Layer 3: Excellent (1ms latency, 0% loss)
Layer 4: Degraded (15% retransmission rate)
Layer 7: Degraded (HTTP 500ms total)

TCP-HTTP Correlation:
  - TLS Negotiation: 450ms with 12 retransmissions

Finding: TCP retransmissions during TLS causing slowdown
Action: Investigate firewall or middlebox interfering with TLS
```

### 2. Identifying Network vs Server Issues

**Symptom**: Inconsistent performance

**Analysis**:
```
MTR Predicted RTT: 2.5ms
TCP Actual RTT: 45ms
Variance: +42.5ms (+1700%) ❌

Finding: TCP much slower than path predicts
Correlation: L3 excellent, L4 degraded
Action: Server-side issue (congestion, rate limiting, firewall)
```

### 3. Detecting Bufferbloat

**Symptom**: Occasional packet reordering

**Analysis**:
```
ICMP: 2ms avg, 150ms max (high jitter)
TCP: Many out-of-order packets during download phase
HTTP: Download phase has high variance

Finding: Bufferbloat causing packet reordering
Correlation: L3 jitter correlates with L4 OOO packets
Action: ISP bufferbloat - recommend QoS or different route
```

## Implementation Details

### Code Structure

```
src/cnf/tests/
├── comprehensive.py              # Orchestrates all tests with packet capture
├── layered_correlation.py        # NEW: L3→L4→L7 correlation logic
│   ├── correlate_tcp_to_http_phases()
│   ├── correlate_mtr_to_tcp()
│   └── generate_layered_analysis()
├── packet_capture.py             # Manages tcpdump on remote hosts
├── packet_analyzer.py            # Parses TCP packets from captures
└── [other test modules]

src/cnf/formatter.py
└── print_layered_analysis()      # Beautiful display of correlation
```

### Data Flow

```
1. Start packet capture on remote probe
   ↓
2. Run tests sequentially (capture runs throughout):
   - ICMP ping (L3)
   - MTR path trace (L3)
   - HTTP with timing (L7) ← Record timestamps!
   ↓
3. Stop packet capture
   ↓
4. Analyze captured packets:
   - Extract TCP events with timestamps
   - Identify retransmissions, window sizes
   ↓
5. Correlate:
   - Map TCP events to HTTP phases using timestamps
   - Compare MTR path latency to TCP handshake
   - Assess quality at each layer
   ↓
6. Generate insights:
   - Find cross-layer correlations
   - Identify root causes
   - Assign overall grade
```

## Benefits

### Complete Visibility

Instead of isolated metrics, you see the **full picture**:
- Not just "HTTP is slow" but "HTTP is slow BECAUSE TLS has retransmissions"
- Not just "high latency" but "high latency at hop 4 affects TCP handshake"

### Root Cause Analysis

Correlations point to root causes:
- **L3 degraded + L4 degraded** → Network path issue
- **L3 excellent + L4 degraded** → Endpoint/server issue
- **L4 excellent + L7 degraded** → Application issue

### Proof with Evidence

Every finding is backed by packet-level evidence:
- "3 retransmissions during TLS" → Can review actual packets
- "Window size limited to 32KB" → See window evolution
- "Hop 4 has 5% loss" → MTR data shows exact hop

## Technical Notes

### Timestamp Synchronization

- All tests run sequentially during one packet capture session
- HTTP phases have relative timestamps from request start
- TCP packets have capture timestamps
- Correlation uses relative timing within the capture window

### Packet Capture Limitations

- Captures on the **client side** (probe host), not server
- See packets as they arrive at/leave from probe
- Cannot see server-internal processing
- Limited to configured max packet count (default 2000)

### Performance Impact

- Packet capture adds ~2-3 seconds per test (start/stop overhead)
- Correlation analysis is done post-capture (no runtime impact)
- Memory usage: ~10MB per 2000 packets captured

## Future Enhancements

Potential additions:
- [ ] Server-side packet capture for full bidirectional view
- [ ] Wireshark-compatible PCAP export
- [ ] Real-time stream analysis (vs post-processing)
- [ ] ML-based anomaly detection across layers
- [ ] Historical correlation trending

---

**The layered correlation feature gives you unprecedented visibility into exactly what's happening at every network layer during your tests, with packet-level evidence to back up every finding.**
