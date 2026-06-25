# Teardown scripts

One teardown script per post that creates billable AWS resources, named
`teardown_NN_<slug>.sh`. Each post's "Clean up" section invokes its script.

- Post 1 is local-only — nothing to tear down.
- Post 2 (Runtime) onward will add scripts here, e.g. `teardown_02_runtime.sh`.

Each script should be idempotent and safe to re-run (ignore "not found" errors).
