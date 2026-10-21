#!/usr/bin/env bash
# Generate a FCIDUMP using classical resources only.
# Usage: sbatch [Slurm options] gamess.sbatch INPUT.inp [OUTPUT_DIRECTORY]
# Submit from a writable directory, or pass --output=/existing/path/slurm-%j.out.
# GAMESS_ROOT selects a source installation; otherwise load the gamess module.
# This script can also run with bash inside an existing two-task allocation.
#SBATCH --job-name=gamess
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00

set -euo pipefail

input_file=$(realpath -e "${1:?usage: gamess.sbatch INPUT.inp [OUTPUT_DIRECTORY]}")
output_dir=${2:-${GAMESS_OUTPUT_DIR:-"${SLURM_SUBMIT_DIR}/gamess-runs/${SLURM_JOB_ID}"}}
mkdir -p "${output_dir}"
export GAMESS_OUTPUT_DIR=$(realpath -e "${output_dir}")
export GAMESS_FCIDUMP_DIR=${GAMESS_OUTPUT_DIR}/fcidump
mkdir -p "${GAMESS_FCIDUMP_DIR}"

if [[ -n ${GAMESS_ROOT:-} ]]; then
    launcher=${GAMESS_ROOT}/rungms
else
    source /etc/profile.d/modules.sh
    module load gamess
    launcher=$(command -v rungms)
fi
[[ -x ${launcher} ]] || { echo "GAMESS launcher not found: ${launcher}" >&2; exit 2; }

# Refuse to validate a previous calculation's FCIDUMP or supplementary files.
[[ ! -e ${GAMESS_FCIDUMP_DIR}/FCIDUMP ]] || {
    echo "FCIDUMP already exists; choose a new output directory: ${GAMESS_OUTPUT_DIR}" >&2
    exit 2
}
printf 'GAMESS input: %s\nGAMESS output: %s\n' "${input_file}" "${GAMESS_OUTPUT_DIR}"

# One compute rank plus its DDI data server consumes the two allocated tasks.
# rungms launches MPI itself; wrapping it in a two-task srun would run it twice.
"${launcher}" "${input_file}" 00 1 1 2>&1 | tee "${GAMESS_OUTPUT_DIR}/gamess.log"
grep -q 'TERMINATED NORMALLY' "${GAMESS_OUTPUT_DIR}/gamess.log"
test -s "${GAMESS_FCIDUMP_DIR}/FCIDUMP"
printf 'GAMESS PASS: %s\n' "${GAMESS_FCIDUMP_DIR}/FCIDUMP"
