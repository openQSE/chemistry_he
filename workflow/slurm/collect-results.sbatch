#!/usr/bin/env bash
# Collect completed chemistry jobs into one workflow-level JSON document.
# This job runs only after every chemistry dependency completes successfully.
#SBATCH --job-name=chemistry-collect
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00

set -euo pipefail

run_dir=$(realpath -e "${1:?supply the workflow run directory}")
backend=${2:?supply the QFw backend name}
plan=$(realpath -e "${3:?supply the workflow job plan}")

python3 - "${run_dir}" "${backend}" "${plan}" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
backend = sys.argv[2]
plan = Path(sys.argv[3])
cases = {}
jobs = {}
for line in plan.read_text().splitlines():
    if not line or line.startswith("#"):
        continue
    case, input_path, gamess_job, chemistry_job, result_path = line.split("\t")
    result = Path(result_path)
    if not result.is_file():
        raise FileNotFoundError(f"missing chemistry result for {case}: {result}")
    cases[case] = json.loads(result.read_text())
    jobs[case] = {
        "input": input_path,
        "gamess_job": int(gamess_job),
        "chemistry_job": int(chemistry_job),
        "result": str(result),
    }

target = run_dir / "workflow-results.json"
temporary = target.with_suffix(".json.tmp")
temporary.write_text(json.dumps({"backend": backend, "jobs": jobs,
                                 "cases": cases}, indent=2) + "\n")
temporary.replace(target)
print(f"WORKFLOW PASS: {target}")
PY
