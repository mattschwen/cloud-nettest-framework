# Contributing to ANUBIS 🔷

Thank you for your interest in contributing to **ANUBIS** - Network Path Guardian! This document provides guidelines for contributing to the project.

## 🌟 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Our Standards

**Positive behaviors include:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behaviors include:**
- Harassment, trolling, or derogatory comments
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- SSH access to cloud instances (for testing)
- Basic understanding of networking concepts (ICMP, TCP, HTTP)

### Development Setup

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/anubis.git
   cd anubis
   ```

2. **Set up development environment**
   ```bash
   # Create virtual environment
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install rich asyncssh pyyaml pydantic typer dnspython
   
   # Install development dependencies (when available)
   # pip install -e ".[dev]"
   ```

3. **Configure remote for upstream**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/anubis.git
   git fetch upstream
   ```

## 🛠️ Development Workflow

### 1. Create a Branch

Always create a new branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style and conventions
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run comprehensive tests
./run_tests

# Test specific functionality
.venv/bin/python scripts/quick_oracle_demo.py

# Verify no regressions
# (Add automated tests when test suite is implemented)
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: Add support for Azure VM probes

- Implement Azure metadata integration
- Add Azure-specific SSH configuration
- Update documentation with Azure examples

Closes #123"
```

**Commit message format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Detailed description of what changed and why
- Reference to any related issues
- Screenshots (if applicable)

## 📝 Code Style Guidelines

### Python Style

Follow PEP 8 with these specifics:

```python
# Use type hints
def run_ping_test(probe: Host, target_ip: str, count: int = 20) -> Optional[Dict[str, Any]]:
    """
    Run ping test from probe to target.
    
    Args:
        probe: Host object representing the probe
        target_ip: IP address to ping
        count: Number of packets to send
        
    Returns:
        Dictionary with ping results or None on failure
    """
    pass

# Async functions for I/O operations
async def comprehensive_target_test(
    host: Host,
    target_ip: str,
    capture_packets: bool = True
) -> Dict[str, Any]:
    """Async function for remote test execution."""
    pass

# Use descriptive variable names
best_route_latency = 0.91  # Good
brl = 0.91  # Bad

# Constants in CAPS
CYBER_CYAN = "bright_cyan"
MAX_RETRIES = 3
```

### File Organization

```
anubis/
├── src/cnf/              # Core framework
│   ├── tests/            # Test modules
│   ├── formatter.py      # Output formatting
│   ├── registry.py       # Host registry
│   └── ssh.py            # SSH client
├── scripts/              # Executable scripts
├── configs/              # Configuration files
├── docs/                 # Documentation
└── tests/                # Automated tests (to be added)
```

### Documentation Style

- Use docstrings for all public functions/classes
- Keep line length ≤ 100 characters for comments
- Use markdown for all documentation files
- Include examples in documentation

## 🧪 Testing Guidelines

### Manual Testing

Before submitting:
1. Test on at least one cloud provider (AWS preferred)
2. Verify output formatting looks correct
3. Check that all MTR, ping, and HTTP tests work
4. Ensure no SSH connection errors

### Automated Testing (Coming Soon)

```python
# Example test structure (when implemented)
def test_ping_parsing():
    """Test ping output parsing."""
    sample_output = "..."
    result = parse_ping_output(sample_output)
    assert result["loss_pct"] == 0.0
    assert result["avg_ms"] > 0
```

## 🎨 Output Formatting Guidelines

### Cyberpunk Theme

Maintain the cyberpunk aesthetic:

```python
# Use theme colors consistently
CYBER_CYAN = "bright_cyan"      # Headers, primary
CYBER_MAGENTA = "bright_magenta"  # Secondary highlights
CYBER_YELLOW = "bright_yellow"  # Warnings
CYBER_GREEN = "bright_green"    # Success
CYBER_RED = "bright_red"        # Errors
CYBER_ORANGE = "orange3"        # Caution

# Box styles for different severities
Panel(content, box=box.DOUBLE, border_style=CYBER_CYAN)  # Important
Table(box=box.ROUNDED, border_style=CYBER_MAGENTA)       # Data
```

### Emojis

Use emojis consistently:
- 🥇 A+ grade (< 2ms)
- 🥈 A grade (< 10ms)
- 🥉 B+ grade (< 20ms)
- ⭐ B grade (< 50ms)
- ⚠️ Warning/C grade (50-100ms)
- ❌ Error/D+ grade (> 100ms)

## 🌐 Adding New Cloud Providers

To add support for a new cloud provider:

1. **Create provider module**
   ```python
   # src/cnf/providers/gcp.py
   class GCPProvider:
       def get_metadata(self):
           """Fetch GCP instance metadata."""
           pass
   ```

2. **Update probe configuration**
   ```yaml
   # configs/providers.yaml
   gcp:
     default_user: ubuntu
     metadata_endpoint: http://metadata.google.internal
   ```

3. **Add to test probes list**
   ```python
   PROBES = [
       # ... existing probes ...
       {
           "name": "us-central1",
           "provider": "gcp",
           "ip": "x.x.x.x",
           "key": "~/.ssh/gcp-key",
           "user": "ubuntu"
       }
   ]
   ```

4. **Document in README.md**

## 🔧 Adding New Test Types

To add a new network test:

1. **Create test module**
   ```python
   # src/cnf/tests/traceroute.py
   async def run_traceroute_test(host: Host, target: str) -> Dict[str, Any]:
       """Run traceroute test."""
       pass
   ```

2. **Add to comprehensive tests**
   ```python
   # src/cnf/tests/comprehensive.py
   result["tests"]["traceroute"] = await run_traceroute_test(host, target_ip)
   ```

3. **Add formatter output**
   ```python
   # src/cnf/formatter.py
   def print_traceroute_results(self, results):
       """Print traceroute results."""
       pass
   ```

4. **Update documentation**

## 📋 Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass (manual testing for now)
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] No sensitive information (keys, IPs) in commits
- [ ] Screenshots added (if UI changes)
- [ ] CHANGELOG.md updated (if applicable)

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify it's reproducible
3. Test on latest version

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the issue.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. Observe error '...'

**Expected behavior**
What you expected to happen.

**Environment**
- OS: [e.g., macOS 14.0]
- Python: [e.g., 3.11.5]
- ANUBIS version: [e.g., 0.1.0]
- Cloud provider: [e.g., AWS]

**Logs**
```
Paste relevant logs here
```

**Screenshots**
If applicable.
```

## 💡 Feature Requests

We welcome feature suggestions! Please:

1. Check existing feature requests
2. Describe the use case
3. Explain the proposed solution
4. Consider implementation complexity

## 🏆 Recognition

Contributors will be:
- Listed in README.md acknowledgments
- Credited in release notes
- Welcomed to the community

## 📞 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an Issue
- **Security**: Email security concerns privately

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

<div align="center">

**Thank you for contributing to ANUBIS! 🔷**

*Together, we guide networks through the underworld*

**[Back to README](README.md)** • **[View Issues](https://github.com/your-username/anubis/issues)**

</div>
