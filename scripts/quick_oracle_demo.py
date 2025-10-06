#!/usr/bin/env python3
"""Quick demo - tests 1 IP per Oracle region from all probes."""

import sys
sys.path.insert(0, '/Users/matthewschwen/projects/cloud-nettest-framework/scripts')

from run_comprehensive_oracle_tests import *

# Override to test just 1 IP per region for speed
ORACLE_ENDPOINTS = {
    "Ashburn": {
        "location": "Virginia, USA",
        "ips": ["134.70.24.1"],  # Just one IP
        "url": "https://objectstorage.us-ashburn-1.oraclecloud.com",
        "status": "✅ Tested",
        "color": CYBER_GREEN
    },
    "Phoenix": {
        "location": "Arizona, USA",
        "ips": ["134.70.16.1"],  # Just the problem IP
        "url": "https://objectstorage.us-phoenix-1.oraclecloud.com",
        "status": "⚠️ Problem IP",
        "color": CYBER_ORANGE
    },
    "San Jose": {
        "location": "California, USA",
        "ips": ["134.70.124.2"],
        "url": "https://objectstorage.us-sanjose-1.oraclecloud.com",
        "status": "✅ Tested",
        "color": CYBER_BLUE
    }
}

if __name__ == "__main__":
    # Patch the global variable
    import run_comprehensive_oracle_tests
    run_comprehensive_oracle_tests.ORACLE_ENDPOINTS = ORACLE_ENDPOINTS
    main()
