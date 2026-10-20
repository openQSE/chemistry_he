#!/usr/bin/env bash
# Run the complete GAMESS -> FCIDUMP -> QFw FMO-VQE sample workflow.
# The job reserves two classical Slurm tasks for GAMESS DDI and one IQM QPU
# reservation for the QFw estimator work that follows the GAMESS stage.
#
# Override CHEMISTRY_INPUT_DIR, WORKFLOW_OUTPUT_ROOT, or GAMESS_INPUTS at
# submission time to select another input collection or result location.
#SBATCH --account=gen233
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --qpu=ornl-iqm-20q
#SBATCH --workload-kind=hybrid
#SBATCH --circ-count=32000
#SBATCH --max-qubits=10
#SBATCH --max-depth=1000
#SBATCH --max-shots=4096
#SBATCH --time=12:00:00
#SBATCH --job-name=gamess-fcidump-qfw

# qfw-slurm reads this submitted file to create its reservation. Keep the
# wrapper small: the controller limits QFW directives to a 2 KiB batch script.
# The companion shell program performs the documented workflow after Slurm
# allocates the two GAMESS DDI tasks and the QFw reservation.
set -euo pipefail

workflow_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec "${workflow_dir}/gamess-fcidump-qfw-workflow.sh"
