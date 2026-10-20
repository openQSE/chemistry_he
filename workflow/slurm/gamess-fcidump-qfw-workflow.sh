#!/usr/bin/env bash
# Execute the GAMESS -> FCIDUMP -> QFw FMO-VQE workflow inside a Slurm
# allocation. The companion .sbatch file reserves its classical and quantum
# resources before this program begins.

set -euo pipefail

workflow_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
input_dir=${CHEMISTRY_INPUT_DIR:-"${workflow_dir}/input"}
output_root=${WORKFLOW_OUTPUT_ROOT:-"${SLURM_SUBMIT_DIR}/chemistry-runs/${SLURM_JOB_ID}"}
inputs=${GAMESS_INPUTS:-"He1-1.inp He1-2.inp He1-4.inp He1-8.inp He1-10.inp He1-14.inp"}
macro_iterations=${MAX_MACRO_ITERATIONS:-3}
amplitude_iterations=${MAX_AMPLITUDE_ITERATIONS:-50}
qfw_provider=${QFW_PROVIDER:-iqm}
qfw_shots=${QFW_SHOTS:-4096}

mkdir -p "${output_root}"
exec > >(tee -a "${output_root}/workflow.log") 2>&1

# GAMESS is the licensed tree mounted with this checkout. It uses both
# allocated tasks: one compute process plus one DDI data-server process.
gamess_root=${GAMESS_ROOT:-/workspace/qfw-container-base/gamess}
rungms=${gamess_root}/rungms
[[ -x ${rungms} ]] || { echo "GAMESS launcher not found: ${rungms}" >&2; exit 2; }

# Activate the image-contained QFw environment once for all QFw stages.
# The shared root is mounted on every virtual node and holds directory-service
# information plus QFw run records for this job.
export QFW_SHARED_ROOT=${QFW_SHARED_ROOT:-/workspace/qfw-container-base}
export QFW_RUN_BASE_DIR=${QFW_RUN_BASE_DIR:-"${output_root}/qfw-runs"}
mkdir -p "${QFW_RUN_BASE_DIR}"
source /opt/openqse/qfw/bin/qfw-activate --venv /opt/openqse/qfw-venv
trap 'type qfw-deactivate >/dev/null 2>&1 && qfw-deactivate || true' EXIT

for input_name in ${inputs}; do
    input_file=${input_dir}/${input_name}
    [[ -f ${input_file} ]] || { echo "missing GAMESS input: ${input_file}" >&2; exit 2; }
    case_name=${input_name%.inp}
    case_dir=${output_root}/${case_name}
    gamess_dir=${case_dir}/gamess
    fcidump_dir=${case_dir}/fcidump
    mkdir -p "${gamess_dir}" "${fcidump_dir}"

    # GAMESS writes its persistent files and FCIDUMP into this case directory.
    export GAMESS_OUTPUT_DIR=${gamess_dir}
    export GAMESS_FCIDUMP_DIR=${fcidump_dir}
    rm -f "${fcidump_dir}/FCIDUMP"
    "${rungms}" "$(realpath -e "${input_file}")" 00 1 1
    test -s "${fcidump_dir}/FCIDUMP"

    # The unified program splits FMO FCIDUMPs, runs all required monomer and
    # dimer VQE calculations, and writes manifest.json plus workflow-result.json.
    python3 "${workflow_dir}/chemapp_fcidump_workflow.py" \
        --path "${fcidump_dir}/FCIDUMP" \
        --gamess-input "${input_file}" \
        --output-dir "${case_dir}/chemapp" \
        --qfw --provider "${qfw_provider}" --shots "${qfw_shots}" \
        --max-macro-iterations "${macro_iterations}" \
        --max-amplitude-iterations "${amplitude_iterations}"
done
