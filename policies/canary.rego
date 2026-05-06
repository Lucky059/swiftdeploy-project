package canary

default allow := {
  "allow": false,
  "reason": "blocked by default",
  "violations": []
}

allow := {
  "allow": true,
  "reason": "canary healthy",
  "violations": []
} if {
  input.error_rate <= input.thresholds.max_error_rate
  input.p99_latency <= input.thresholds.max_p99_latency
}

allow := {
  "allow": false,
  "reason": "error rate too high",
  "violations": ["error_rate > 1%"]
} if {
  input.error_rate > input.thresholds.max_error_rate
}

allow := {
  "allow": false,
  "reason": "latency too high",
  "violations": ["p99_latency > 500ms"]
} if {
  input.p99_latency > input.thresholds.max_p99_latency
}