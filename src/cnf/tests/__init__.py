"""Network test modules for Cloud NetTest Framework."""

from cnf.tests.dns import run_dns_tests
from cnf.tests.http import run_http_tests
from cnf.tests.latency import run_latency_tests
from cnf.tests.tls import run_tls_tests
from cnf.tests.traceroute import run_traceroute_tests
from cnf.tests.throughput import run_throughput_tests
from cnf.tests.oci_object import run_oci_object_tests

__all__ = [
    "run_dns_tests",
    "run_http_tests",
    "run_latency_tests",
    "run_tls_tests",
    "run_traceroute_tests",
    "run_throughput_tests",
    "run_oci_object_tests",
]
