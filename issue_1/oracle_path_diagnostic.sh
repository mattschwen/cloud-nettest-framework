#!/bin/bash

# Oracle Path Diagnostic Script
# Tests network connectivity, latency, and paths to Oracle Cloud Infrastructure destinations
# Author: Network Diagnostics Team
# Version: 1.0

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_VERSION="1.0"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S UTC')
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "unknown")
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null || echo "unknown")
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
LOCAL_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "unknown")
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")

# Oracle destinations to test
declare -a ORACLE_DESTINATIONS=(
    "objectstorage.us-ashburn-1.oraclecloud.com"
    "objectstorage.us-phoenix-1.oraclecloud.com" 
    "objectstorage.us-sanjose-1.oraclecloud.com"
)

# Additional Oracle services to test
declare -a ORACLE_SERVICES=(
    "cloud.oracle.com"
    "console.us-ashburn-1.oraclecloud.com"
    "iad.ocir.io"
)

# Function to print header
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}Oracle Network Path Diagnostic Report${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}Script Version:${NC} $SCRIPT_VERSION"
    echo -e "${GREEN}Timestamp:${NC} $TIMESTAMP"
    echo -e "${GREEN}Test Region:${NC} $REGION"
    echo -e "${GREEN}Availability Zone:${NC} $AZ"
    echo -e "${GREEN}Instance ID:${NC} $INSTANCE_ID"
    echo -e "${GREEN}Local IP:${NC} $LOCAL_IP"
    echo -e "${GREEN}Public IP:${NC} $PUBLIC_IP"
    echo ""
}

# Function to test DNS resolution
test_dns() {
    local destination=$1
    echo -e "${YELLOW}DNS Resolution Test for $destination:${NC}"
    
    # Test DNS resolution
    if dig +short $destination > /dev/null 2>&1; then
        local ips=$(dig +short $destination)
        echo -e "${GREEN}✓ DNS Resolution: SUCCESS${NC}"
        echo "  Resolved IPs:"
        for ip in $ips; do
            echo "    - $ip"
        done
    else
        echo -e "${RED}✗ DNS Resolution: FAILED${NC}"
        return 1
    fi
    
    # DNS timing
    local dns_time=$(dig $destination | grep "Query time" | awk '{print $4}')
    echo "  Query Time: ${dns_time}ms"
    echo ""
}

# Function to test ping connectivity
test_ping() {
    local destination=$1
    echo -e "${YELLOW}Ping Test for $destination:${NC}"
    
    if ping -c 4 -W 5 $destination > /tmp/ping_$destination 2>&1; then
        echo -e "${GREEN}✓ Ping: SUCCESS${NC}"
        local stats=$(grep "packets transmitted" /tmp/ping_$destination)
        local timing=$(grep "min/avg/max" /tmp/ping_$destination)
        echo "  $stats"
        echo "  RTT: $timing"
    else
        echo -e "${RED}✗ Ping: FAILED${NC}"
        cat /tmp/ping_$destination
    fi
    echo ""
}

# Function to test traceroute
test_traceroute() {
    local destination=$1
    echo -e "${YELLOW}Traceroute Test for $destination:${NC}"
    
    if timeout 30 traceroute -m 15 $destination > /tmp/trace_$destination 2>&1; then
        echo -e "${GREEN}✓ Traceroute: COMPLETED${NC}"
        # Count hops
        local hops=$(grep -c "^ *[0-9]" /tmp/trace_$destination)
        echo "  Total Hops: $hops"
        echo "  Path:"
        head -n 20 /tmp/trace_$destination | tail -n +2
    else
        echo -e "${RED}✗ Traceroute: TIMEOUT or FAILED${NC}"
    fi
    echo ""
}

# Function to test HTTP/HTTPS connectivity
test_http() {
    local destination=$1
    local protocol=${2:-https}
    
    echo -e "${YELLOW}HTTP/HTTPS Test for $protocol://$destination:${NC}"
    
    # Test HTTPS connectivity
    local start_time=$(date +%s.%N)
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 $protocol://$destination > /tmp/http_$destination 2>&1; then
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "unknown")
        local http_code=$(cat /tmp/http_$destination)
        
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
            echo -e "${GREEN}✓ HTTP/HTTPS: SUCCESS (${http_code})${NC}"
        else
            echo -e "${YELLOW}⚠ HTTP/HTTPS: Unexpected response (${http_code})${NC}"
        fi
        echo "  Response Time: ${duration}s"
        
        # Get detailed timing
        curl -s -o /dev/null -w "  DNS Lookup: %{time_namelookup}s\n  TCP Connect: %{time_connect}s\n  TLS Handshake: %{time_appconnect}s\n  Total Time: %{time_total}s\n" --connect-timeout 10 --max-time 30 $protocol://$destination
    else
        echo -e "${RED}✗ HTTP/HTTPS: FAILED${NC}"
        echo "  Error details in /tmp/http_$destination"
    fi
    echo ""
}

# Function to test MTR (if available)
test_mtr() {
    local destination=$1
    echo -e "${YELLOW}MTR Test for $destination:${NC}"
    
    if command -v /usr/sbin/mtr >/dev/null 2>&1; then
        if timeout 60 /usr/sbin/mtr -r -c 10 $destination > /tmp/mtr_$destination 2>&1; then
            echo -e "${GREEN}✓ MTR: COMPLETED${NC}"
            cat /tmp/mtr_$destination
        else
            echo -e "${YELLOW}⚠ MTR: Limited permissions or timeout${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ MTR: Not available${NC}"
    fi
    echo ""
}

# Function to test port connectivity
test_port() {
    local destination=$1
    local port=$2
    echo -e "${YELLOW}Port $port connectivity test for $destination:${NC}"
    
    if timeout 10 nc -zv $destination $port 2>&1 | grep -q "succeeded"; then
        echo -e "${GREEN}✓ Port $port: OPEN${NC}"
    else
        echo -e "${RED}✗ Port $port: CLOSED or FILTERED${NC}"
    fi
}

# Function to run comprehensive test for a destination
run_comprehensive_test() {
    local destination=$1
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}Testing: $destination${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    test_dns $destination
    test_ping $destination
    test_traceroute $destination
    test_http $destination "https"
    test_mtr $destination
    
    # Test common Oracle Cloud ports
    test_port $destination 443
    test_port $destination 80
    
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

# Function to generate summary
generate_summary() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}DIAGNOSTIC SUMMARY${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo "Test completed at: $(date '+%Y-%m-%d %H:%M:%S UTC')"
    echo "Source: $REGION ($AZ) - $PUBLIC_IP"
    echo ""
    
    echo "Tested Destinations:"
    for dest in "${ORACLE_DESTINATIONS[@]}" "${ORACLE_SERVICES[@]}"; do
        echo "  - $dest"
    done
    echo ""
    
    echo "Log files created:"
    echo "  - /tmp/ping_* (ping results)"
    echo "  - /tmp/trace_* (traceroute results)"
    echo "  - /tmp/http_* (HTTP test results)"
    echo "  - /tmp/mtr_* (MTR results, if available)"
    echo ""
    
    echo -e "${GREEN}Diagnostic completed successfully!${NC}"
}

# Main execution
main() {
    print_header
    
    echo -e "${YELLOW}Starting comprehensive Oracle network diagnostics...${NC}"
    echo ""
    
    # Test Oracle Object Storage endpoints
    echo -e "${BLUE}Testing Oracle Object Storage Endpoints:${NC}"
    for destination in "${ORACLE_DESTINATIONS[@]}"; do
        run_comprehensive_test $destination
    done
    
    # Test additional Oracle services
    echo -e "${BLUE}Testing Additional Oracle Services:${NC}"
    for destination in "${ORACLE_SERVICES[@]}"; do
        run_comprehensive_test $destination
    done
    
    generate_summary
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up temporary files...${NC}"
    rm -f /tmp/ping_* /tmp/trace_* /tmp/http_* /tmp/mtr_* 2>/dev/null || true
}

# Set trap for cleanup
trap cleanup EXIT

# Run main function
main "$@"