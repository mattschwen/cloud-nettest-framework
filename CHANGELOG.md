# Changelog

All notable changes to ANUBIS - Network Path Guardian will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-06

### Added
- 🎨 **Cyberpunk-themed output** with pink/purple/blue colorization
- 🔬 **L3→L4→L7 Network Correlation** - Full stack analysis from ICMP to HTTP
- 🌐 **Multi-Cloud Probe Support** - AWS, Azure, GCP deployment ready
- 📊 **MTR Path Analysis** with per-hop WHOIS lookups
- 💠 **TCP Packet Capture** with connection quality grading
- 🎯 **Oracle OCI Specialized Testing** for Object Storage endpoints
- 🏆 **Performance Rankings** - Automatic top 3 best/worst route identification
- 📈 **HTTP Timing Breakdown** - DNS, TCP, TLS, TTFB, download phases
- 🔍 **WHOIS Integration** - ASN and organization lookup for network hops
- ⚡ **Async SSH Execution** - Parallel test execution across probes
- 🎨 **Colorized Logo** - Egyptian mythology meets cyberpunk aesthetics

### Infrastructure
- 3 AWS EC2 probes (us-east-1, us-west-1, us-east-2)
- 7 Oracle OCI endpoint testing
- Comprehensive test matrix (21 probe×endpoint combinations)

### Documentation
- Complete README with architecture diagrams
- CONTRIBUTING guide with code style and PR process
- LAYERED_CORRELATION.md explaining L3→L4→L7 analysis
- ARCHITECTURE.md detailing system design
- MIT License

### Features
- **ICMP Ping Tests**: Multi-sample latency with jitter measurement
- **MTR Traceroute**: Complete path analysis with packet loss per hop
- **HTTP/HTTPS Timing**: Full timing breakdown with multi-sample statistics
- **Packet Analysis**: TCP handshake tracking, retransmission detection, window scaling
- **Quality Grading**: A+ to D grading system based on performance metrics
- **Cyberpunk UI**: Rich tables, panels, trees with emoji indicators

### Initial Release
This is the first official release of ANUBIS, born from real-world Oracle Cloud Infrastructure Sev 1 incident analysis and multi-region AWS EC2 testing campaigns.

[1.0.0]: https://github.com/mattschwen/cloud-nettest-framework/releases/tag/v1.0.0
