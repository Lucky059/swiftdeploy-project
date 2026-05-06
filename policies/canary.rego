package canary

import rego.v1

# Thresholds come from data.json — never hardcoded here

default allow := {
    "allow": false,
    "reason": "blocked by default",
    "violations": []
}

# ALLOW: canary is healthy
allow := result if {
    input.error_rate     <= data.max_error_rate
    input.p99_latency_ms <= data.max_p99_latency_ms
    result := {
        "allow":      true,
        "reason":     "canary is healthy - error rate and latency within thresholds",
        "violations": []
    }
}

# DENY: error rate too high
allow := result if {
    input.error_rate > data.max_error_rate
    result := {
        "allow":      false,
        "reason":     sprintf("error rate %.2f%% exceeds maximum %.2f%%", [input.error_rate * 100, data.max_error_rate * 100]),
        "violations": ["error_rate > max_error_rate"]
    }
}

# DENY: P99 latency too high
allow := result if {
    input.p99_latency_ms > data.max_p99_latency_ms
    result := {
        "allow":      false,
        "reason":     sprintf("P99 latency %dms exceeds maximum %dms", [input.p99_latency_ms, data.max_p99_latency_ms]),
        "violations": ["p99_latency_ms > max_p99_latency_ms"]
    }
}
