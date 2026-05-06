package infra

import rego.v1

# Thresholds come from data.json — never hardcoded here

default allow := {
    "allow": false,
    "reason": "blocked by default",
    "violations": []
}

# ALLOW: all checks pass
allow := result if {
    input.disk_free_gb >= data.min_disk_gb
    input.cpu_load     <= data.max_cpu_load
    input.mem_free_gb  >= data.min_mem_gb
    result := {
        "allow":      true,
        "reason":     "infrastructure checks passed",
        "violations": []
    }
}

# DENY: disk too low
allow := result if {
    input.disk_free_gb < data.min_disk_gb
    result := {
        "allow":      false,
        "reason":     sprintf("disk free %.1fGB is below minimum %.1fGB", [input.disk_free_gb, data.min_disk_gb]),
        "violations": ["disk_free < min_disk_gb"]
    }
}

# DENY: cpu too high
allow := result if {
    input.cpu_load > data.max_cpu_load
    result := {
        "allow":      false,
        "reason":     sprintf("cpu load %.2f exceeds maximum %.2f", [input.cpu_load, data.max_cpu_load]),
        "violations": ["cpu_load > max_cpu_load"]
    }
}

# DENY: memory too low
allow := result if {
    input.mem_free_gb < data.min_mem_gb
    result := {
        "allow":      false,
        "reason":     sprintf("memory free %.1fGB is below minimum %.1fGB", [input.mem_free_gb, data.min_mem_gb]),
        "violations": ["mem_free < min_mem_gb"]
    }
}
