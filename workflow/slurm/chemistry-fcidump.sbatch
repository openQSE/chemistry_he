#!/usr/bin/env bash
# Split an existing FCIDUMP, run pUCCD through QFw, and collect fragment energies.
# Usage: sbatch --qpu=RESOURCE [Slurm options] chemistry-fcidump.sbatch \
#            FCIDUMP INPUT.inp [BACKEND] [OUTPUT_DIRECTORY]
# BACKEND is the QFw provider (nwqsim or iqm); --qpu selects its Slurm resource.
# Submit from a writable directory, or set --output=/existing/path/slurm-%j.out.
# This script can also run with bash inside an existing quantum allocation.
#SBATCH --job-name=chemistry-fcidump
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --workload-kind=hybrid
#SBATCH --circ-count=32000
#SBATCH --max-qubits=10
#SBATCH --max-depth=1000
#SBATCH --max-shots=4096
#SBATCH --time=12:00:00

set -euo pipefail

fcidump=$(realpath -e "${1:?supply the existing FCIDUMP path}")
input_file=$(realpath -e "${2:?supply the GAMESS input that generated the FCIDUMP}")
backend=${3:-${QFW_BACKEND:-nwqsim}}
output_dir=${4:-"${SLURM_SUBMIT_DIR}/chemistry-runs/${SLURM_JOB_ID}"}
mkdir -p "${output_dir}"
output_dir=$(realpath -e "${output_dir}")
exec > >(tee -a "${output_dir}/chemistry.log") 2>&1
printf 'Chemistry input: %s\nGAMESS input: %s\nQFw backend: %s\nOutput: %s\n' \
    "${fcidump}" "${input_file}" "${backend}" "${output_dir}"
[[ ! -e ${output_dir}/workflow-result.json ]] || {
    echo "Results already exist; choose a new output directory: ${output_dir}" >&2
    exit 2
}

# Slurm executes a spooled copy of this script. Find the submitted checkout,
# or accept CHEMISTRY_ROOT from the combined workflow's submission wrapper.
if [[ -z ${CHEMISTRY_ROOT:-} ]]; then
    submitted_script=$(scontrol show job "${SLURM_JOB_ID}" -o | \
        sed -n 's/.* Command=\([^ ]*\).*/\1/p')
    export CHEMISTRY_ROOT=$(cd "$(dirname "${submitted_script}")/../.." && pwd)
fi
test -f "${CHEMISTRY_ROOT}/chemapp_fcidump_workflow.py"

# These are installation settings shared by the virtual cluster and Janus.
# Use a separate runtime directory for this calculation, including its logs.
site_config=${QFW_SITE_CONFIG:-/etc/openqse/qfw/site.yaml}
run_dir=${output_dir}/qfw
source "${QFW_INSTALL_PREFIX:-/opt/openqse/qfw}/bin/qfw-activate" \
    --venv "${QFW_VENV:-/opt/openqse/qfw-venv}"
cleanup() {
    # Stop the runtime while retaining DEFw tracebacks and QFw diagnostics.
    qfw-teardown --run-dir "${run_dir}" --keep-run-dir || true
    qfw-deactivate || true
}
trap cleanup EXIT
qfw-setup --site-config "${site_config}" --run-dir "${run_dir}"

# Keep NumPy/PySCF threads within this step's classical CPU allocation.
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
export OPENBLAS_NUM_THREADS=${OMP_NUM_THREADS}
export MKL_NUM_THREADS=${OMP_NUM_THREADS}
export PYTHONUNBUFFERED=1
# qfw-srun invokes defw-python, so its application is the Python script itself.
qfw-srun --run-dir "${run_dir}" --nodes=1 --ntasks=1 -- \
    "${CHEMISTRY_ROOT}/chemapp_fcidump_workflow.py" \
    --path "${fcidump}" --gamess-input "${input_file}" \
    --output-dir "${output_dir}" --qfw --provider "${backend}" \
    --shots "${QFW_SHOTS:-4096}" \
    --max-macro-iterations "${MAX_MACRO_ITERATIONS:-3}" \
    --max-amplitude-iterations "${MAX_AMPLITUDE_ITERATIONS:-50}" \
    --max-orbital-iterations "${MAX_ORBITAL_ITERATIONS:-1000}"
if [[ ! -s ${output_dir}/workflow-result.json ]]; then
    echo "CHEMISTRY FAILED: no workflow-result.json; see ${output_dir}/chemistry.log and ${run_dir}/application/logs" >&2
    exit 1
fi
printf 'CHEMISTRY PASS: %s\n' "${output_dir}/workflow-result.json"
