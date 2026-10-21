#!/usr/bin/env bash
# Submit independent GAMESS and QFw chemistry jobs linked by Slurm dependencies.
# Usage: SLURM_ACCOUNT=ACCOUNT QFW_BACKEND=nwqsim ./submit-...sh [sbatch options]
# For Janus IQM, select QFW_QPU_RESOURCE=ornl-iqm-20q and QFW_BACKEND=iqm.

set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export CHEMISTRY_ROOT=$(cd "${script_dir}/../.." && pwd)
qpu_resource=${QFW_QPU_RESOURCE:-nwqsim}
qfw_backend=${QFW_BACKEND:-nwqsim}
slurm_account=${SLURM_ACCOUNT:-}
[[ -n ${slurm_account} ]] || {
    echo "SLURM_ACCOUNT must name the account used for every workflow job" >&2
    exit 2
}
input_dir=${CHEMISTRY_INPUT_DIR:-"${CHEMISTRY_ROOT}/input"}
output_root=${WORKFLOW_OUTPUT_ROOT:-"${HOME}/chemistry-runs"}
run_id=${WORKFLOW_RUN_ID:-"$(date -u +%Y%m%dT%H%M%SZ)-$$"}
[[ ${run_id} =~ ^[A-Za-z0-9._-]+$ ]] || {
    echo "WORKFLOW_RUN_ID may contain only letters, numbers, dot, underscore, and dash" >&2
    exit 2
}
[[ ! -e ${output_root}/${run_id} ]] || {
    echo "Workflow directory already exists: ${output_root}/${run_id}" >&2
    exit 2
}
mkdir -p "${output_root}/${run_id}"
run_dir=$(realpath -e "${output_root}/${run_id}")
plan=${run_dir}/jobs.tsv
: > "${plan}"
printf '# case\tinput\tgamess_job\tchemistry_job\tresult\n' >> "${plan}"

# Keep this as plain --export=ALL. Slurm treats ALL plus an explicit variable
# as an implicit --get-user-env request, which needs PID and mount namespaces.
export QFW_BACKEND=${qfw_backend}
cd "${run_dir}"
read -r -a inputs <<< \
    "${GAMESS_INPUTS:-He1-1.inp He1-2.inp He1-4.inp He1-8.inp He1-10.inp He1-14.inp}"
(( ${#inputs[@]} > 0 )) || { echo "GAMESS_INPUTS is empty" >&2; exit 2; }
chemistry_jobs=()
for input_name in "${inputs[@]}"; do
    input_file=$(realpath -e "${input_dir}/${input_name}")
    case_name=${input_name%.inp}

    gamess_job=$(sbatch "$@" -A "${slurm_account}" --parsable --export=ALL \
        --job-name="gamess-${case_name}" \
        --output="${run_dir}/slurm-gamess-%j.out" \
        "${script_dir}/gamess.sbatch" "${input_file}")
    gamess_job=${gamess_job%%;*}
    [[ ${gamess_job} =~ ^[0-9]+$ ]] || {
        echo "Unexpected GAMESS sbatch response: ${gamess_job}" >&2
        exit 1
    }
    fcidump=${run_dir}/gamess-runs/${gamess_job}/fcidump/FCIDUMP

    chemistry_job=$(sbatch "$@" -A "${slurm_account}" --parsable --export=ALL \
        --dependency="afterok:${gamess_job}" --kill-on-invalid-dep=yes \
        --qpu="${qpu_resource}" --job-name="chemistry-${case_name}" \
        --output="${run_dir}/slurm-chemistry-%j.out" \
        "${script_dir}/chemistry-fcidump.sbatch" \
        "${fcidump}" "${input_file}" "${qfw_backend}")
    chemistry_job=${chemistry_job%%;*}
    [[ ${chemistry_job} =~ ^[0-9]+$ ]] || {
        echo "Unexpected chemistry sbatch response: ${chemistry_job}" >&2
        exit 1
    }
    chemistry_jobs+=("${chemistry_job}")
    result=${run_dir}/chemistry-runs/${chemistry_job}/workflow-result.json
    printf '%s\t%s\t%s\t%s\t%s\n' \
        "${case_name}" "${input_file}" "${gamess_job}" \
        "${chemistry_job}" "${result}" >> "${plan}"
    printf '%s: GAMESS job %s -> chemistry job %s\n' \
        "${case_name}" "${gamess_job}" "${chemistry_job}"
done

dependency=$(IFS=:; echo "${chemistry_jobs[*]}")
collect_job=$(sbatch "$@" -A "${slurm_account}" --parsable --export=ALL \
    --dependency="afterok:${dependency}" --kill-on-invalid-dep=yes \
    --job-name=chemistry-collect \
    --output="${run_dir}/slurm-collect-%j.out" \
    "${script_dir}/collect-results.sbatch" \
    "${run_dir}" "${qfw_backend}" "${plan}")
collect_job=${collect_job%%;*}
printf 'Collection job: %s\nWorkflow directory: %s\n' \
    "${collect_job}" "${run_dir}"
