#!/bin/bash

# Oracle PAR Download Test with Network Diagnostics
# Captures MTR, packet capture, and performance metrics during download

set -euo pipefail

# Configuration
# Original PAR URL from user - may need adjustment if truncated
ORACLE_PAR_URL="https://objectstorage.us-phoenix-1.oraclecloud.com/p/XtN0_qOm_zbfobEv9SvQEyg4liV0ry58SB7-8NRIizkVBCr2SBL4z79cQ/n/bmcostests/b/mtrinh-test/o/27MiB"

# Note: If the URL above doesn't work, you may need to get a fresh PAR from Mark
# The PAR might be expired or the URL might have been truncated
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="/Users/matthewschwen/projects/oracle_par_test_${TIMESTAMP}"
OBJECT_SIZE="27MiB"

# Extract hostname for MTR
HOSTNAME=$(echo "$ORACLE_PAR_URL" | sed -n 's|https://\([^/]*\).*|\1|p')

echo "🚀 Starting Oracle PAR Download Test"
echo "📅 Timestamp: $TIMESTAMP"
echo "🎯 Target: $HOSTNAME"
echo "📦 Object Size: $OBJECT_SIZE"
echo "📁 Output Directory: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Function to cleanup background processes
cleanup() {
    echo "🧹 Cleaning up background processes..."
    # Kill MTR process
    if [[ -n "${MTR_PID:-}" ]] && kill -0 "$MTR_PID" 2>/dev/null; then
        kill "$MTR_PID" 2>/dev/null || true
    fi
    
    # Kill tcpdump process (requires sudo)
    if [[ -n "${TCPDUMP_PID:-}" ]] && kill -0 "$TCPDUMP_PID" 2>/dev/null; then
        sudo kill "$TCPDUMP_PID" 2>/dev/null || true
    fi
    
    # Wait a moment for processes to terminate
    sleep 2
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

echo "🔍 Starting network diagnostics..."

# Start continuous MTR in background
echo "📡 Starting MTR to $HOSTNAME..."
mtr --report-cycles=1000 --interval=0.1 --json "$HOSTNAME" > "mtr_oracle_${TIMESTAMP}.json" &
MTR_PID=$!

# Start packet capture in background (requires sudo)
echo "📦 Starting packet capture..."
sudo tcpdump -i any -w "oracle_download_${TIMESTAMP}.pcap" -s 65535 host "$HOSTNAME" &
TCPDUMP_PID=$!

# Wait a moment for diagnostics to start
sleep 3

echo "⬇️  Starting download with timing..."

# Capture download with detailed timing
time_start=$(date +%s.%N)

# Download with verbose curl output
curl -v \
  -L \
  -o "oracle_27MiB_${TIMESTAMP}.bin" \
  -w "@-" <<'EOF' > "curl_stats_${TIMESTAMP}.txt" 2>"curl_verbose_${TIMESTAMP}.log" \
  "$ORACLE_PAR_URL"
{
  "time_namelookup": %{time_namelookup},
  "time_connect": %{time_connect},
  "time_appconnect": %{time_appconnect},
  "time_pretransfer": %{time_pretransfer},
  "time_redirect": %{time_redirect},
  "time_starttransfer": %{time_starttransfer},
  "time_total": %{time_total},
  "speed_download": %{speed_download},
  "speed_upload": %{speed_upload},
  "size_download": %{size_download},
  "size_upload": %{size_upload},
  "size_header": %{size_header},
  "size_request": %{size_request},
  "http_code": %{http_code},
  "ssl_verify_result": %{ssl_verify_result},
  "redirect_count": %{redirect_count},
  "num_connects": %{num_connects},
  "num_redirects": %{num_redirects},
  "remote_ip": %{remote_ip},
  "remote_port": %{remote_port},
  "local_ip": %{local_ip},
  "local_port": %{local_port}
}
EOF

download_exit_code=$?
time_end=$(date +%s.%N)

# Calculate total time with high precision
download_time=$(echo "$time_end - $time_start" | bc -l)

echo "✅ Download completed with exit code: $download_exit_code"
echo "⏱️  Total download time: ${download_time}s"

# Wait a bit more to capture post-download network activity
sleep 5

# Stop background processes
cleanup

# Capture final system state
echo "📊 Capturing system network statistics..."

# Network interface statistics
netstat -i > "netstat_interfaces_${TIMESTAMP}.txt"

# Network connections
netstat -an > "netstat_connections_${TIMESTAMP}.txt"

# Network routes
netstat -rn > "netstat_routes_${TIMESTAMP}.txt"

# System network buffers (macOS specific)
netstat -s > "netstat_stats_${TIMESTAMP}.txt"

# DNS resolution check
echo "🔍 DNS resolution test..."
dig "$HOSTNAME" > "dns_resolution_${TIMESTAMP}.txt"

# Basic connectivity check
echo "🏓 Post-download connectivity check..."
ping -c 10 "$HOSTNAME" > "ping_post_download_${TIMESTAMP}.txt"

# File verification
if [[ -f "oracle_27MiB_${TIMESTAMP}.bin" ]]; then
    file_size=$(stat -f%z "oracle_27MiB_${TIMESTAMP}.bin" 2>/dev/null || stat -c%s "oracle_27MiB_${TIMESTAMP}.bin" 2>/dev/null)
    file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc -l)
    echo "📁 Downloaded file size: ${file_size} bytes (${file_size_mb} MB)"
    
    # Create checksum
    shasum -a 256 "oracle_27MiB_${TIMESTAMP}.bin" > "oracle_file_checksum_${TIMESTAMP}.txt"
else
    echo "❌ Downloaded file not found!"
fi

# Create summary report
cat > "test_summary_${TIMESTAMP}.txt" <<EOF
Oracle PAR Download Test Summary
================================

Test Details:
- Timestamp: $TIMESTAMP
- Target URL: $ORACLE_PAR_URL
- Target Host: $HOSTNAME
- Object Size: $OBJECT_SIZE
- Download Exit Code: $download_exit_code
- Total Download Time: ${download_time}s
- Downloaded File Size: ${file_size:-"N/A"} bytes (${file_size_mb:-"N/A"} MB)

Files Generated:
- oracle_27MiB_${TIMESTAMP}.bin (downloaded object)
- curl_stats_${TIMESTAMP}.txt (curl timing statistics)
- curl_verbose_${TIMESTAMP}.log (curl verbose output)
- mtr_oracle_${TIMESTAMP}.json (MTR network path analysis)
- oracle_download_${TIMESTAMP}.pcap (packet capture)
- netstat_*.txt (network statistics)
- dns_resolution_${TIMESTAMP}.txt (DNS resolution)
- ping_post_download_${TIMESTAMP}.txt (connectivity test)
- oracle_file_checksum_${TIMESTAMP}.txt (file integrity)

Next Steps:
1. Review curl statistics for download performance
2. Analyze MTR data for network path quality
3. Examine packet capture for network behavior
4. Compare with AWS S3 equivalent test
EOF

echo "📋 Test Summary:"
cat "test_summary_${TIMESTAMP}.txt"

echo ""
echo "🎉 Oracle PAR test completed successfully!"
echo "📁 All results saved in: $OUTPUT_DIR"
echo ""
echo "📊 Quick Stats:"
if [[ -f "curl_stats_${TIMESTAMP}.txt" ]]; then
    echo "   Download Speed: $(cat "curl_stats_${TIMESTAMP}.txt" | grep -o '"speed_download": [0-9.]*' | cut -d':' -f2 | tr -d ' ') bytes/sec"
    echo "   Total Time: $(cat "curl_stats_${TIMESTAMP}.txt" | grep -o '"time_total": [0-9.]*' | cut -d':' -f2 | tr -d ' ')s"
    echo "   Remote IP: $(cat "curl_stats_${TIMESTAMP}.txt" | grep -o '"remote_ip": "[^"]*"' | cut -d'"' -f4)"
fi

echo ""
echo "🔄 Ready for AWS S3 comparison test!"