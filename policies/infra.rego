package infra

default allow := {
  "allow": false,
  "reason": "blocked by default",
  "violations": []
}

allow := {
  "allow": true,
  "reason": "infra ok",
  "violations": []
} if {
  input.disk_free >= input.thresholds.min_disk
  input.cpu_load <= input.thresholds.max_cpu
}

allow := {
  "allow": false,
  "reason": "disk too low",
  "violations": ["disk_free < min_disk"]
} if {
  input.disk_free < input.thresholds.min_disk
}

allow := {
  "allow": false,
  "reason": "cpu too high",
  "violations": ["cpu_load > max_cpu"]
} if {
  input.cpu_load > input.thresholds.max_cpu
}