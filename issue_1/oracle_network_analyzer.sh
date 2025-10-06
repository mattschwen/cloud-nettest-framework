#!/bin/bash

# Oracle Network Analyzer with TCP Dump Analysis
# Enhanced diagnostic script for deep packet-level analysis of Oracle connectivity
# Author: Network Diagnostics Team  
# Version: 2.0

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_VERSION="2.0"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S UTC')
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "unknown")
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null || echo "unknown")
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
LOCAL_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "unknown")
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")

# Analysis directories
CAPTURE_DIR="/tmp/oracle_captures"
ANALYSIS_DIR="/tmp/oracle_analysis"
RESULTS_DIR="/tmp/oracle_results"

# Oracle IP ranges for filtering
declare -a ORACLE_IPS=(
    "134.70.8.1"      # Phoenix
    "134.70.12.1"     # Phoenix  
    "134.70.16.1"     # Phoenix (the one with 471ms spike!)
    "134.70.24.1"     # Ashburn
    "134.70.28.1"     # Ashburn
    "134.70.32.1"     # Ashburn
    "134.70.124.2"    # San Jose
)

# Oracle Object Storage endpoints
declare -A OCI_ENDPOINTS=(
    ["us-ashburn-1"]="objectstorage.us-ashburn-1.oraclecloud.com"
    ["us-phoenix-1"]="objectstorage.us-phoenix-1.oraclecloud.com"
    ["us-sanjose-1"]="objectstorage.us-sanjose-1.oraclecloud.com"
)

# Function to print header
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}Oracle Network Analyzer with TCP Dump Analysis${NC}"
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

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites for TCP analysis...${NC}"
    
    # Check if running as root or with sudo access
    if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
        echo -e "${RED}✗ Root access required for TCP dump analysis${NC}"
        echo -e "${YELLOW}Please run with sudo or configure passwordless sudo${NC}"
        return 1
    fi
    
    # Check for required tools
    local missing_tools=()
    for tool in tcpdump curl dig mtr traceroute netstat ss; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=($tool)
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}✗ Missing tools: ${missing_tools[*]}${NC}"
        echo -e "${YELLOW}Installing missing tools...${NC}"
        sudo yum install -y tcpdump net-tools traceroute bind-utils mtr &>/dev/null || true
    fi
    
    # Create analysis directories
    sudo mkdir -p "$CAPTURE_DIR" "$ANALYSIS_DIR" "$RESULTS_DIR"
    sudo chmod 755 "$CAPTURE_DIR" "$ANALYSIS_DIR" "$RESULTS_DIR"
    
    echo -e "${GREEN}✓ All prerequisites ready${NC}"
    echo ""
}

# Function to start TCP dump for Oracle traffic
start_tcpdump() {
    local target_ip=$1
    local test_name=$2
    local capture_file="$CAPTURE_DIR/oracle_${test_name}_$(date +%s).pcap"
    
    echo -e "${CYAN}Starting TCP dump for $target_ip...${NC}"
    
    # Build tcpdump filter for Oracle traffic
    local filter="host $target_ip and (port 80 or port 443 or port 22)"
    
    # Start tcpdump in background
    sudo tcpdump -i any -w "$capture_file" -s 65535 "$filter" &>/dev/null &
    local tcpdump_pid=$!
    
    echo "$tcpdump_pid:$capture_file" > "/tmp/tcpdump_${test_name}.info"
    echo -e "${GREEN}✓ TCP dump started (PID: $tcpdump_pid, File: $(basename $capture_file))${NC}"
    
    # Give tcpdump time to initialize
    sleep 2
}

# Function to stop TCP dump and analyze
stop_and_analyze_tcpdump() {
    local test_name=$1
    local info_file="/tmp/tcpdump_${test_name}.info"
    
    if [ ! -f "$info_file" ]; then
        echo -e "${RED}✗ No TCP dump info found for $test_name${NC}"
        return 1
    fi
    
    local pid_file=$(cat "$info_file")
    local tcpdump_pid=$(echo "$pid_file" | cut -d: -f1)
    local capture_file=$(echo "$pid_file" | cut -d: -f2)
    
    echo -e "${CYAN}Stopping TCP dump and analyzing...${NC}"
    
    # Stop tcpdump
    if ps -p $tcpdump_pid > /dev/null; then
        sudo kill -TERM $tcpdump_pid 2>/dev/null || true
        sleep 2
    fi
    
    # Analyze the capture
    if [ -f "$capture_file" ]; then
        analyze_pcap "$capture_file" "$test_name"
    fi
    
    # Cleanup
    rm -f "$info_file"
}

# Function to analyze PCAP file
analyze_pcap() {
    local pcap_file=$1
    local test_name=$2
    local analysis_file="$ANALYSIS_DIR/${test_name}_analysis.txt"
    
    echo -e "${PURPLE}Analyzing packet capture for $test_name...${NC}"
    
    # Basic packet statistics
    echo "=== PACKET CAPTURE ANALYSIS: $test_name ===" > "$analysis_file"
    echo "Capture File: $pcap_file" >> "$analysis_file"
    echo "Analysis Time: $(date)" >> "$analysis_file"
    echo "" >> "$analysis_file"
    
    # Total packet count
    local total_packets=$(sudo tcpdump -r "$pcap_file" 2>/dev/null | wc -l)
    echo "Total Packets Captured: $total_packets" >> "$analysis_file"
    
    # Protocol breakdown
    echo "" >> "$analysis_file"
    echo "=== PROTOCOL BREAKDOWN ===" >> "$analysis_file"
    sudo tcpdump -r "$pcap_file" -n 2>/dev/null | awk '{print $3}' | sort | uniq -c | sort -rn | head -10 >> "$analysis_file"
    
    # Connection attempts and responses
    echo "" >> "$analysis_file"
    echo "=== TCP CONNECTION ANALYSIS ===" >> "$analysis_file"
    
    # SYN packets (connection attempts)
    local syn_count=$(sudo tcpdump -r "$pcap_file" 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0' 2>/dev/null | wc -l)
    echo "SYN packets (connection attempts): $syn_count" >> "$analysis_file"
    
    # SYN-ACK packets (successful connections)
    local synack_count=$(sudo tcpdump -r "$pcap_file" 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack != 0' 2>/dev/null | wc -l)
    echo "SYN-ACK packets (successful connections): $synack_count" >> "$analysis_file"
    
    # RST packets (connection resets)
    local rst_count=$(sudo tcpdump -r "$pcap_file" 'tcp[tcpflags] & tcp-rst != 0' 2>/dev/null | wc -l)
    echo "RST packets (connection resets): $rst_count" >> "$analysis_file"
    
    # Retransmissions
    echo "" >> "$analysis_file"
    echo "=== RETRANSMISSION ANALYSIS ===" >> "$analysis_file"
    sudo tcpdump -r "$pcap_file" -n 2>/dev/null | grep -E "(retransmission|dup|out-of-order)" >> "$analysis_file" || echo "No obvious retransmissions detected" >> "$analysis_file"
    
    # HTTP/HTTPS traffic analysis
    echo "" >> "$analysis_file"
    echo "=== HTTP/HTTPS ANALYSIS ===" >> "$analysis_file"
    local http_count=$(sudo tcpdump -r "$pcap_file" 'port 80' 2>/dev/null | wc -l)
    local https_count=$(sudo tcpdump -r "$pcap_file" 'port 443' 2>/dev/null | wc -l)
    echo "HTTP packets (port 80): $http_count" >> "$analysis_file"
    echo "HTTPS packets (port 443): $https_count" >> "$analysis_file"
    
    # Show first few packets for detailed analysis
    echo "" >> "$analysis_file"
    echo "=== SAMPLE PACKET DETAILS ===" >> "$analysis_file"
    sudo tcpdump -r "$pcap_file" -n -v 2>/dev/null | head -20 >> "$analysis_file"
    
    echo -e "${GREEN}✓ Analysis complete: $(basename $analysis_file)${NC}"
}

# Function to test Oracle endpoint with TCP capture
test_oracle_endpoint_with_capture() {
    local region=$1
    local hostname=$2
    local target_ips=()
    
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}Testing Oracle $region with TCP Capture${NC}"
    echo -e "${BLUE}Hostname: $hostname${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    # Resolve hostname to IPs
    local resolved_ips=$(dig +short "$hostname" | grep -E '^[0-9]+\.' | head -3)
    
    echo -e "${YELLOW}Resolved IPs for $hostname:${NC}"
    for ip in $resolved_ips; do
        echo "  - $ip"
        target_ips+=("$ip")
    done
    echo ""
    
    # Test each resolved IP
    for ip in "${target_ips[@]}"; do
        echo -e "${CYAN}=== Testing IP: $ip ===${NC}"
        
        # Start TCP dump for this IP
        start_tcpdump "$ip" "${region}_${ip//\./_}"
        
        # Run connectivity tests
        echo -e "${YELLOW}Running connectivity tests to $ip...${NC}"
        
        # Ping test
        echo -e "${CYAN}Ping test:${NC}"
        ping -c 5 -W 5 "$ip" 2>&1 | tee "$RESULTS_DIR/ping_${region}_${ip//\./_}.txt"
        
        # Connection timing test
        echo -e "${CYAN}Connection timing test:${NC}"
        for attempt in {1..3}; do
            echo "Attempt $attempt:"
            curl -w "  DNS: %{time_namelookup}s | Connect: %{time_connect}s | TLS: %{time_appconnect}s | Total: %{time_total}s | Code: %{http_code}\n" \
                 -o /dev/null -s --connect-timeout 10 --max-time 30 "https://$ip/" 2>/dev/null || echo "  Connection failed"
        done
        
        # Traceroute
        echo -e "${CYAN}Traceroute to $ip:${NC}"
        traceroute -m 15 "$ip" 2>&1 | tee "$RESULTS_DIR/traceroute_${region}_${ip//\./_}.txt"
        
        # Stop and analyze TCP dump
        stop_and_analyze_tcpdump "${region}_${ip//\./_}"
        
        echo -e "${GREEN}✓ Completed testing $ip${NC}"
        echo ""
    done
}

# Function to detect network anomalies
detect_anomalies() {
    echo -e "${PURPLE}=== NETWORK ANOMALY DETECTION ===${NC}"
    
    # Check for high latency patterns
    echo -e "${YELLOW}Analyzing latency patterns...${NC}"
    
    for result_file in "$RESULTS_DIR"/ping_*.txt; do
        if [ -f "$result_file" ]; then
            local filename=$(basename "$result_file")
            local avg_latency=$(grep "min/avg/max" "$result_file" | awk -F'/' '{print $5}' | awk '{print $1}')
            
            if [ ! -z "$avg_latency" ]; then
                # Check if latency is unusually high (>100ms)
                if (( $(echo "$avg_latency > 100" | bc -l 2>/dev/null || echo "0") )); then
                    echo -e "${RED}⚠️  HIGH LATENCY DETECTED: $filename - ${avg_latency}ms${NC}"
                elif (( $(echo "$avg_latency > 50" | bc -l 2>/dev/null || echo "0") )); then
                    echo -e "${YELLOW}⚠️  ELEVATED LATENCY: $filename - ${avg_latency}ms${NC}"
                else
                    echo -e "${GREEN}✓ Normal latency: $filename - ${avg_latency}ms${NC}"
                fi
            fi
        fi
    done
    
    # Check for packet loss
    echo -e "${YELLOW}Analyzing packet loss...${NC}"
    grep -l "packet loss" "$RESULTS_DIR"/ping_*.txt | while read -r file; do
        local loss=$(grep "packet loss" "$file" | awk '{print $6}' | sed 's/%//')
        local filename=$(basename "$file")
        
        if [ ! -z "$loss" ] && (( $(echo "$loss > 0" | bc -l 2>/dev/null || echo "0") )); then
            echo -e "${RED}⚠️  PACKET LOSS DETECTED: $filename - ${loss}%${NC}"
        fi
    done
    
    # Analyze TCP dump results for retransmissions
    echo -e "${YELLOW}Analyzing retransmissions from TCP dumps...${NC}"
    for analysis_file in "$ANALYSIS_DIR"/*_analysis.txt; do
        if [ -f "$analysis_file" ]; then
            local filename=$(basename "$analysis_file")
            local rst_count=$(grep "RST packets" "$analysis_file" | awk '{print $NF}')
            
            if [ ! -z "$rst_count" ] && [ "$rst_count" -gt 0 ]; then
                echo -e "${YELLOW}⚠️  TCP RESETS DETECTED: $filename - $rst_count resets${NC}"
            fi
        fi
    done
    
    echo ""
}

# Function to generate comprehensive summary
generate_comprehensive_summary() {
    local summary_file="$RESULTS_DIR/comprehensive_summary.txt"
    
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}COMPREHENSIVE NETWORK ANALYSIS SUMMARY${NC}"
    echo -e "${BLUE}============================================================${NC}"
    
    # Create summary file
    {
        echo "============================================================"
        echo "Oracle Network Analysis Summary"
        echo "============================================================"
        echo "Analysis Date: $TIMESTAMP"
        echo "Source Region: $REGION ($AZ)"
        echo "Instance: $INSTANCE_ID ($PUBLIC_IP)"
        echo ""
        
        echo "=== TEST CONFIGURATION ==="
        echo "Oracle Regions Tested: ${!OCI_ENDPOINTS[*]}"
        echo "Oracle IPs Monitored: ${ORACLE_IPS[*]}"
        echo ""
        
        echo "=== FILES GENERATED ==="
        echo "Ping Results: $(ls "$RESULTS_DIR"/ping_*.txt 2>/dev/null | wc -l) files"
        echo "Traceroute Results: $(ls "$RESULTS_DIR"/traceroute_*.txt 2>/dev/null | wc -l) files"
        echo "TCP Captures: $(ls "$CAPTURE_DIR"/*.pcap 2>/dev/null | wc -l) files"
        echo "TCP Analysis: $(ls "$ANALYSIS_DIR"/*_analysis.txt 2>/dev/null | wc -l) files"
        echo ""
        
        echo "=== ANOMALY SUMMARY ==="
    } > "$summary_file"
    
    # Add anomaly detection to summary
    detect_anomalies | tee -a "$summary_file"
    
    echo ""
    echo -e "${GREEN}Comprehensive summary saved to: $summary_file${NC}"
    echo -e "${GREEN}All analysis files available in:${NC}"
    echo -e "${CYAN}  - Captures: $CAPTURE_DIR${NC}"
    echo -e "${CYAN}  - Analysis: $ANALYSIS_DIR${NC}" 
    echo -e "${CYAN}  - Results: $RESULTS_DIR${NC}"
}

# Function to test all Oracle regions with comprehensive analysis
test_all_regions_comprehensive() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}COMPREHENSIVE ORACLE NETWORK ANALYSIS${NC}"
    echo -e "${BLUE}============================================================${NC}"
    
    for region in "${!OCI_ENDPOINTS[@]}"; do
        test_oracle_endpoint_with_capture "$region" "${OCI_ENDPOINTS[$region]}"
    done
    
    # Additional focused test on the problematic IP
    echo -e "${RED}=== FOCUSED ANALYSIS: Problematic IP 134.70.16.1 ===${NC}"
    start_tcpdump "134.70.16.1" "problem_ip_focus"
    
    echo -e "${YELLOW}Running extended tests on 134.70.16.1 (the 471ms spike IP)...${NC}"
    ping -c 20 -i 0.5 134.70.16.1 | tee "$RESULTS_DIR/extended_ping_134_70_16_1.txt"
    
    for i in {1..10}; do
        echo "Extended connection test $i:"
        curl -w "Connect: %{time_connect}s | Total: %{time_total}s | Code: %{http_code}\n" \
             -o /dev/null -s --connect-timeout 10 --max-time 30 "https://134.70.16.1/" 2>/dev/null || echo "Failed"
    done | tee "$RESULTS_DIR/extended_connection_134_70_16_1.txt"
    
    stop_and_analyze_tcpdump "problem_ip_focus"
    
    # Generate comprehensive summary
    generate_comprehensive_summary
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --version  Show script version"
    echo "  --quick        Run quick analysis (no extended tests)"
    echo ""
    echo "This script performs comprehensive Oracle network analysis including:"
    echo "  - TCP packet capture and analysis"
    echo "  - Connection latency measurements"
    echo "  - Retransmission and anomaly detection"  
    echo "  - Focused analysis of problematic IPs"
    echo ""
    echo "Requires root/sudo access for TCP dump functionality."
}

# Main function
main() {
    local quick_mode=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--version)
                echo "Oracle Network Analyzer v$SCRIPT_VERSION"
                exit 0
                ;;
            --quick)
                quick_mode=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Execute analysis
    print_header
    check_prerequisites
    
    if [ "$quick_mode" = true ]; then
        echo -e "${YELLOW}Running in quick mode...${NC}"
        # Just test one region for demonstration
        test_oracle_endpoint_with_capture "us-phoenix-1" "${OCI_ENDPOINTS[us-phoenix-1]}"
    else
        test_all_regions_comprehensive
    fi
    
    echo -e "${GREEN}Oracle network analysis completed!${NC}"
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Cleaning up background processes...${NC}"
    
    # Kill any remaining tcpdump processes
    pkill -f "tcpdump.*oracle" 2>/dev/null || true
    
    # Remove temp info files
    rm -f /tmp/tcpdump_*.info 2>/dev/null || true
}

# Set trap for cleanup
trap cleanup EXIT

# Run main function with arguments
main "$@"