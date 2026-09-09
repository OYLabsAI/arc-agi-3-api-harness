# Notebook compliance — NOT SATISFIED

Prepared verification.ipynb uses the same api_run entry point as local validation. It starts
timing before setup, verifies a source archive hash, installs into a fresh venv/empty HOME,
loads only evaluator secrets, enforces the plan and preserves exit status plus artifacts.
Fixture mode requires no keys, consumes no inference, and creates no real scorecard.

Local baseline: 92 tests passed. API candidate: 115 tests passed. Pinned dependencies install
and pip check succeeds on macOS/Python 3.12. All 45 pinned Linux x86_64 wheels were downloaded
and individually SHA-256 locked; this verifies availability, not Linux execution.
The current Kaggle Dockerfile template references Python 3.12, but no particular notebook
session or image revision has been observed or executed:
[Kaggle runtime source](https://github.com/Kaggle/docker-python/blob/main/Dockerfile.tmpl).

Fresh notebook bootstrap fixture execution is recorded in the delivery's notebook validation
JSON. This is a local macOS execution, not a Kaggle result. The synthetic replacement-data
path and no-public-fallback behavior are tested; actual organizer delivery is not confirmed.

Requirements NOT SATISFIED: actual fresh Linux execution, private Kaggle fixture/pilot execution and its version
URL, actual API access, public immutable source URL and anonymous post-release retrieval.
No Docker/Podman/Colima runtime is installed on this host. Dockerfile execution requirement is NOT SATISFIED;
its base image tag is not an immutable image digest. No public or private Kaggle notebook
was uploaded from this preparation. A parsing check alone does not pass Kaggle readiness.
