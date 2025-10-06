#!/usr/bin/env bash
# Bootstrap script to install network testing tools on probe hosts
# Usage: ./bootstrap_hosts.sh [apt|yum|dnf]

set -euo pipefail

PKG_MGR="${1:-apt}"

echo "=== Cloud NetTest Framework - Host Bootstrap ==="
echo "Package Manager: $PKG_MGR"
echo ""

# Common tools needed for network testing
TOOLS=(
    "iputils-ping"     # ping
    "traceroute"       # traceroute
    "mtr-tiny"         # mtr (My TraceRoute)
    "curl"             # HTTP testing
    "dnsutils"         # dig, nslookup (Debian/Ubuntu)
    "bind-tools"       # dig, nslookup (RHEL/CentOS)
    "iperf3"           # Bandwidth testing
    "tcpdump"          # Packet capture
    "net-tools"        # netstat, ifconfig
    "iproute2"         # ip command
)

install_apt() {
    echo "Installing tools via apt..."
    sudo apt-get update -qq
    
    for tool in iputils-ping traceroute mtr-tiny curl dnsutils iperf3 tcpdump net-tools iproute2 jq; do
        if ! dpkg -l | grep -q "^ii  $tool"; then
            echo "Installing $tool..."
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $tool
        else
            echo "$tool already installed"
        fi
    done
}

install_yum() {
    echo "Installing tools via yum..."
    sudo yum install -y epel-release
    sudo yum update -y -q
    
    for tool in iputils traceroute mtr curl bind-utils iperf3 tcpdump net-tools iproute jq; do
        if ! rpm -q $tool &>/dev/null; then
            echo "Installing $tool..."
            sudo yum install -y -q $tool
        else
            echo "$tool already installed"
        fi
    done
}

install_dnf() {
    echo "Installing tools via dnf..."
    sudo dnf install -y epel-release
    sudo dnf update -y -q
    
    for tool in iputils traceroute mtr curl bind-utils iperf3 tcpdump net-tools iproute jq; do
        if ! rpm -q $tool &>/dev/null; then
            echo "Installing $tool..."
            sudo dnf install -y -q $tool
        else
            echo "$tool already installed"
        fi
    done
}

verify_tools() {
    echo ""
    echo "=== Verifying Installed Tools ==="
    
    for cmd in ping traceroute mtr curl dig iperf3 tcpdump ip; do
        if command -v $cmd &> /dev/null; then
            echo "✓ $cmd: $(command -v $cmd)"
        else
            echo "✗ $cmd: NOT FOUND"
        fi
    done
}

# Main installation
case "$PKG_MGR" in
    apt)
        install_apt
        ;;
    yum)
        install_yum
        ;;
    dnf)
        install_dnf
        ;;
    *)
        echo "Error: Unknown package manager: $PKG_MGR"
        echo "Usage: $0 [apt|yum|dnf]"
        exit 1
        ;;
esac

verify_tools

echo ""
echo "=== Bootstrap Complete ==="
echo "Host is ready for Cloud NetTest Framework testing"
