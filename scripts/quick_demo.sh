#!/bin/bash
# Quick demo of all network diagnostic capabilities

echo "🔬 Cloud NetTest Framework - Quick Demo"
echo "========================================"
echo ""

# Test 1: Simple ping from us-west-1 to Oracle San Jose
echo "Test 1: Ping from us-west-1 → Oracle San Jose (134.70.124.2)"
echo "------------------------------------------------------------"
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'ping -c 10 134.70.124.2 | grep -E "transmitted|rtt"'
echo ""

# Test 2: MTR from us-west-1 to Oracle San Jose
echo "Test 2: MTR Path Analysis from us-west-1 → Oracle San Jose"
echo "-----------------------------------------------------------"
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'mtr -n -c 10 -r 134.70.124.2 | head -20'
echo ""

# Test 3: HTTP GET timing from us-west-1
echo "Test 3: HTTP GET Timing from us-west-1 → Oracle San Jose"
echo "---------------------------------------------------------"
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'curl -w "DNS: %{time_namelookup}s\nTCP: %{time_connect}s\nTLS: %{time_appconnect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" -o /dev/null -s https://objectstorage.us-sanjose-1.oraclecloud.com'
echo ""

# Test 4: tcpdump packet capture
echo "Test 4: Packet Capture (5 seconds)"
echo "-----------------------------------"
echo "Starting tcpdump on us-west-1..."
ssh -i ~/.ssh/network-testing-key-west.pem ubuntu@3.101.64.113 \
  'sudo timeout 5 tcpdump -i any -n -c 20 host 134.70.124.2 2>/dev/null &
   sleep 1
   ping -c 5 134.70.124.2 > /dev/null 2>&1
   sleep 5
   echo "Captured packets"'
echo ""

# Test 5: Ping from us-east-2 to Oracle Ashburn
echo "Test 5: Ping from us-east-2 → Oracle Ashburn (134.70.24.1)"
echo "-----------------------------------------------------------"
ssh -i ~/.ssh/network-testing-key-east2.pem ubuntu@18.222.238.187 \
  'ping -c 10 134.70.24.1 | grep -E "transmitted|rtt"'
echo ""

echo "✅ Demo Complete!"
echo ""
echo "All tests executed on AWS EC2 instances:"
echo "  • us-west-1 (California): 3.101.64.113"
echo "  • us-east-2 (Ohio): 18.222.238.187"
echo ""
echo "Full framework capabilities:"
echo "  ✅ ICMP Ping with statistics"
echo "  ✅ MTR path analysis"
echo "  ✅ HTTP GET with detailed timing"
echo "  ✅ tcpdump packet capture"
echo "  ✅ All executed remotely on AWS probes"
