# Output Formatting Guide

The Cloud NetTest Framework features **beautiful, production-quality output** using the Rich Python library for terminal formatting.

## 🎨 Overview

All test results are displayed with:
- **Color-coded metrics** for instant visual assessment
- **Unicode box drawings** for professional table layouts
- **Emoji indicators** for performance grades and status
- **Dynamic progress bars** during test execution
- **Hierarchical displays** for complex results

## 📊 Output Components

### 1. Test Headers

Every test run starts with a beautiful header:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  Cloud NetTest Framework - LIVE TEST RESULTS                                 ║
║  Oracle OCI Object Storage Network Performance | Test Run: 2025-10-05 21:57  ║
║  MDT                                                                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 2. Test Configuration Panel

Displays test plan details in a clean, bordered panel:

```
╭─────────────────────────── 📋 Test Configuration ────────────────────────────╮
│   Test Plan:  oracle_live_diagnostic                                         │
│ Description:  Live Oracle OCI Object Storage test from AWS probes            │
│     Version:  1.0                                                            │
│      Probes:  2 active                                                       │
│   Timestamp:  2025-10-05 22:04:06                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 3. Probe Host Table

Lists all selected probes with color-coded status:

```
                           🔍 Selected Probe Hosts
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ ID                    ┃ Provider ┃ Region    ┃ Public IP      ┃  Status   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━━━━━╋━━━━━━━━━━━╋━━━━━━━━━━━━━━━━╋━━━━━━━━━━━┫
┃ aws-us-west-1-probe01 ┃ AWS      ┃ us-west-1 ┃ 3.101.64.113   ┃ ✅ active ┃
┃ aws-us-east-2-probe01 ┃ AWS      ┃ us-east-2 ┃ 18.222.238.187 ┃ ✅ active ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━┻━━━━━━━━━━━┻━━━━━━━━━━━━━━━━┻━━━━━━━━━━━┛
```

### 4. DNS Resolution Results

Shows DNS query results with success indicators:

```
                         🌐 DNS Resolution: All Probes
╭────────────────────────────────────────────┬──────────┬──────────┬───────────╮
│ Hostname                                   │  Record  │ Resolved │  Status   │
│                                            │   Type   │ IPs      │           │
├────────────────────────────────────────────┼──────────┼──────────┼───────────┤
│ objectstorage.us-ashburn-1.oraclecloud.com │    A     │ 134.70.… │    ✅     │
│                                            │          │ 134.70.… │  Success  │
│                                            │          │ 134.70.… │           │
╰────────────────────────────────────────────┴──────────┴──────────┴───────────╯
```

### 5. Latency Test Results

**Most advanced display** with automatic performance grading:

```
     📡 Latency Results: aws-us-west-1-probe01 (California (3.101.64.113))
╭──────────────────────────────────────────────┬────────┬──────┬──────┬────────╮
│ Target                                       │Packets │ Loss │  Avg │ Grade  │
├──────────────────────────────────────────────┼────────┼──────┼──────┼────────┤
│ Oracle Ashburn (134.70.24.1)                 │  10/10 │ 0.0% │63.01 │ A  🥈  │
│ Oracle Phoenix (134.70.16.1) ⚠️ PROBLEM IP   │  20/20 │ 0.0% │20.48 │ A+ 🥇  │
│ Oracle San Jose (134.70.124.2)               │  10/10 │ 0.0% │ 0.97 │ A+ 🥇  │
╰──────────────────────────────────────────────┴────────┴──────┴──────┴────────╯
```

**Performance Grading System:**
- **A+ 🥇**: Excellent (varies by distance category)
- **A 🥈**: Very Good
- **B 🥉**: Good
- **C ⚠️**: Fair (warning)
- **D ❌**: Poor (critical)

**Grading is distance-aware:**
- Same-region: < 2ms = A+, < 5ms = A
- Regional: < 20ms = A+, < 40ms = A
- Cross-country: < 50ms = A+, < 70ms = A

**Color Coding:**
- Green: Excellent performance
- Yellow: Acceptable with warnings
- Orange: Needs attention
- Red: Critical issues

### 6. Problem IP Monitoring

Special panel for tracking historically problematic IPs:

```
┏━━━━━━━━━━━━━━━━━━━━━ 🔍 Problem IP Monitor: 134.70.16.1 ━━━━━━━━━━━━━━━━━━━━━┓
┃  IP Address:  134.70.16.1                                                    ┃
┃  Historical:  471.00ms                                                       ┃
┃     Current:  20.48ms                                                        ┃
┃ Improvement:  95.7%                                                          ┃
┃      Status:  ✅ RESOLVED                                                    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### 7. Performance Champions

Tree view showing the best performers:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🏆 Performance Champions                                                     ┃
┃ ├── 🥇 Best Overall: us-west-1 → San Jose (0.97ms)                           ┃
┃ ├── 🥈 Best Regional: us-east-2 → Ashburn (13.80ms)                          ┃
┃ └── 🥉 Best Cross-Country: us-west-1 → Phoenix (20.48ms)                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### 8. Overall Health Status

Large, prominent health indicator:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Overall Health ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                 🟢 EXCELLENT                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Health Levels:**
- 🟢 **EXCELLENT**: No failures, avg latency < 50ms
- 🟡 **GOOD**: No failures, avg latency < 100ms
- 🟠 **FAIR**: <10% failure rate
- 🔴 **POOR**: ≥10% failure rate

### 9. Test Statistics Panel

Summary of all test metrics:

```
╭───────────────────────────── 📊 Test Statistics ─────────────────────────────╮
│ Total Tests:  46                                                             │
│  Successful:  46                                                             │
│      Failed:  0                                                              │
│ Packet Loss:  0.00%                                                          │
│ Avg Latency:  32.84ms                                                        │
│  Avg Jitter:  0.25ms                                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 10. Success/Error Messages

Formatted completion messages:

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ ✅ All tests completed successfully! 🎉                                      │
│ Framework Status: PRODUCTION READY ✅                                        │
│ Problem IP 134.70.16.1: RESOLVED (95.7% improvement)                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## 🎯 Using the Formatter

### Via CLI

View live results:
```bash
cnf report view
```

View specific test run:
```bash
cnf report view runs/oracle-test-20251005-120000/
```

### Programmatically

```python
from cnf.formatter import NetworkTestFormatter

formatter = NetworkTestFormatter()

# Print header
formatter.print_header("My Test Run", "Running comprehensive tests")

# Print latency results
latency_results = [
    {
        "name": "Target Server",
        "packets_sent": 10,
        "packets_received": 10,
        "packet_loss_pct": 0.0,
        "min_ms": 1.0,
        "avg_ms": 1.5,
        "max_ms": 2.0,
        "stddev_ms": 0.3
    }
]
formatter.print_latency_results("probe-01", "us-west-1", latency_results)

# Print summary
stats = {
    "overall_health": "EXCELLENT",
    "total_tests": 10,
    "successful_tests": 10,
    "failed_tests": 0,
    "avg_packet_loss": 0.0,
    "avg_latency": 15.5,
    "avg_jitter": 0.5
}
formatter.print_summary_statistics(stats)
```

### Custom Output

Create your own formatters by extending `NetworkTestFormatter`:

```python
from cnf.formatter import NetworkTestFormatter
from rich.panel import Panel
from rich.text import Text

class MyCustomFormatter(NetworkTestFormatter):
    def print_custom_metric(self, metric_name: str, value: float):
        text = Text(f"{metric_name}: {value:.2f}", style="cyan")
        panel = Panel(text, title="Custom Metric", border_style="blue")
        self.console.print(panel)
```

## 🎨 Color Scheme

The framework uses a consistent color palette:

| Element | Color | Usage |
|---------|-------|-------|
| Headers | Cyan | Section titles, test names |
| Success | Bright Green | Successful tests, good metrics |
| Warning | Yellow | Moderate issues, thresholds |
| Error | Red | Failed tests, critical issues |
| Info | Blue | Metadata, configurations |
| Metric Values | White/Bold | Numerical results |
| Dim | Gray | Secondary information |

## 📈 Progress Indicators

During test execution, you'll see real-time progress:

```
⠹ Running tests... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 0:00:12
```

Features:
- Animated spinner
- Progress bar
- Percentage complete
- Time remaining estimate

## 🔧 Configuration

Output formatting respects terminal capabilities:
- **Color support**: Auto-detected (falls back to no-color if unsupported)
- **Width**: Auto-adapts to terminal width
- **Unicode**: Falls back to ASCII if needed

Force specific behavior:
```bash
# Disable colors
NO_COLOR=1 cnf report view

# Force colors (even in pipes)
FORCE_COLOR=1 cnf report view

# Set specific width
COLUMNS=120 cnf report view
```

## 📝 Output Files

All formatted output can be captured:

```bash
# Save to file (preserves colors with ANSI codes)
cnf report view > results.txt

# Strip colors for plain text
cnf report view | cat > results_plain.txt

# Convert to HTML with ANSI-to-HTML
cnf report view | ansi2html > results.html
```

## 🎯 Best Practices

1. **Use `cnf report view`** for human-readable results
2. **Use JSON output** for programmatic processing
3. **Capture to file** for sharing results
4. **Use wide terminals** (120+ chars) for best display
5. **Check color support** before sharing screenshots

## 🚀 Examples

### Quick Health Check
```bash
cnf report view | grep "Overall Health"
```

### Export Performance Champions
```bash
cnf report view | grep -A 5 "Performance Champions" > champions.txt
```

### Monitor Problem IPs
```bash
cnf report view | grep -A 6 "Problem IP Monitor"
```

---

The beautiful output makes Cloud NetTest Framework results **instantly comprehensible**, enabling rapid diagnosis and confident decision-making for network performance analysis.
