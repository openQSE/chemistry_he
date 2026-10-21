# GAMESS to QFw chemistry workflow

This sample connects GAMESS FCIDUMP generation with pUCCD VQE calculations
through QFw. It is intended as a compact reference workflow that can be
reimplemented in StreamFlow, TIERKries, COMPSs, or another workflow engine.

## Workflow

1. Submit separate classical and QFw jobs connected by Slurm dependencies.
2. Run GAMESS for a supplied helium input file.
3. Read the resulting FCIDUMP and split its final monomer and dimer blocks.
4. Run pUCCD VQE for each monomer and dimer through QFw.
5. Combine the fragment energies into an FMO energy and save JSON results.

`chemapp_fcidump_workflow.py` is the unified FCIDUMP consumer. Existing
example scripts remain available as focused standalone examples.

## Resource estimate

| Resource | Sample value | Reason |
| --- | ---: | --- |
| Classical tasks | 2 | GAMESS uses one compute task and one DDI server task. |
| QFw device | `nwqsim` or `ornl-iqm-20q` | Select the Slurm resource and matching QFw provider at submission. |
| Maximum qubits | 10 | The helium dimer FCIDUMP blocks contain `NORB=10`. |
| Maximum circuit depth | 1000 | Raw pUCCD dimer depth is about 129; the allowance covers transpilation. |
| Maximum shots | 4096 | QFw's estimator precision default corresponds to 4096 shots. |
| Circuit count | 32000 | Initial sample reservation; calibrate against measured estimator circuit usage. |

The six inputs require 210 fragment calculations in total. Circuit usage also
depends on measurement grouping, the optimizer's minimum evaluation count,
and orbital optimization. The sample circuit reservation is not a proven
upper bound for a converged calculation. Adjust `--circ-count` at submission
after measuring the intended run. `MAX_MACRO_ITERATIONS`,
`MAX_AMPLITUDE_ITERATIONS`, and `MAX_ORBITAL_ITERATIONS` control the optimizer;
their defaults are 3, 50, and 1000 respectively.

## Validate the two stages separately

The checkout, inputs, and results must be accessible from the allocated node.
The QFw environment must contain PySCF, OpenFermion, SciPy, Qiskit, and the
QFw backend. Load the installed GAMESS module on Janus, or set `GAMESS_ROOT`
to the built licensed tree in the virtual cluster. GAMESS's launcher must
honor `GAMESS_OUTPUT_DIR` and `GAMESS_FCIDUMP_DIR`.

Use an existing writable directory for Slurm's own output. Slurm opens that
file before executing the script, so a script cannot repair a missing or
unwritable Slurm output directory.

```bash
# Set this to the chemistry_he checkout on the cluster.
export CHEMISTRY_ROOT=/path/to/chemistry_he
mkdir -p "$HOME/chemistry-validation"

# Virtual cluster only; Janus can use its gamess module instead.
export GAMESS_ROOT=/workspace/qfw-container-base/gamess

# Stage 1: a classical job. Record its job ID from sbatch's response.
sbatch -A gen233 --output="$HOME/chemistry-validation/gamess-%j.out" \
  "$CHEMISTRY_ROOT/workflow/slurm/gamess.sbatch" \
  "$CHEMISTRY_ROOT/input/He1-4.inp"

# Inspect state and exit code. A successful run prints GAMESS PASS.
sacct -j GAMESS_JOB_ID --format=JobID,State,ExitCode,Elapsed,NodeList
```

Stage 1 defaults to `gamess-runs/<job-id>/` under the submission directory.
An optional second script argument sets an exact output directory. The
original FCIDUMP is `<GAMESS_OUTPUT_DIRECTORY>/fcidump/FCIDUMP`.

```bash
# Stage 2: consume the completed GAMESS file; do not rerun GAMESS.
# Reduced iteration counts validate execution, not chemistry convergence.
export MAX_MACRO_ITERATIONS=1 MAX_AMPLITUDE_ITERATIONS=18 MAX_ORBITAL_ITERATIONS=1
sbatch -A gen233 --qpu=nwqsim \
  --output="$HOME/chemistry-validation/chemistry-%j.out" \
  "$CHEMISTRY_ROOT/workflow/slurm/chemistry-fcidump.sbatch" \
  /absolute/path/to/gamess-runs/GAMESS_JOB_ID/fcidump/FCIDUMP \
  "$CHEMISTRY_ROOT/input/He1-4.inp" nwqsim
```

The chemistry script takes `FCIDUMP INPUT.inp [BACKEND] [OUTPUT_DIRECTORY]`.
Its default output is `chemistry-runs/<job-id>/` under the submission directory.
`--qpu` is the Slurm resource name; `BACKEND` is the QFw provider. For Janus
IQM, use `--qpu=ornl-iqm-20q` and the script argument `iqm`. The site config
defaults to `/etc/openqse/qfw/site.yaml`; `QFW_SITE_CONFIG`,
`QFW_INSTALL_PREFIX`, and `QFW_VENV` can select other installation paths.

The chemistry stage performs `qfw-setup`, passes the Python application
directly to `qfw-srun`, and runs `qfw-teardown --keep-run-dir` on exit. It
retains `chemistry.log`, `manifest.json`, normalized `fragments/`, the
`qfw/` diagnostic directory, and `workflow-result.json`. Successful collection
prints `CHEMISTRY PASS`. Results are written before backend shutdown, because
QFw's shutdown exits the application process.

## Run the complete workflow

The submission wrapper creates a separate GAMESS job and chemistry job for
each input. Every chemistry job has an `afterok` dependency on its GAMESS job,
so it starts only after the corresponding FCIDUMP exists. A final classical
job collects the chemistry results after every chemistry job succeeds. This
keeps QPU reservations out of the GAMESS stage.

```bash
SLURM_ACCOUNT=gen233 QFW_QPU_RESOURCE=nwqsim QFW_BACKEND=nwqsim \
GAMESS_INPUTS="He1-1.inp He1-4.inp" \
WORKFLOW_OUTPUT_ROOT="$HOME/chemistry-results" \
  "$CHEMISTRY_ROOT/workflow/slurm/submit-gamess-fcidump-qfw-workflow.sh"

# Janus uses the same scripts; select its resource and provider.
SLURM_ACCOUNT=gen233 QFW_QPU_RESOURCE=ornl-iqm-20q QFW_BACKEND=iqm \
WORKFLOW_OUTPUT_ROOT="$HOME/chemistry-results" \
  "$CHEMISTRY_ROOT/workflow/slurm/submit-gamess-fcidump-qfw-workflow.sh"
```

The default inputs are `input/He1-1.inp`, `input/He1-2.inp`,
`input/He1-4.inp`, `input/He1-8.inp`, `input/He1-10.inp`, and
`input/He1-14.inp`.

`SLURM_ACCOUNT` is required and is passed to every submitted job with `-A`.
The submission wrapper also accepts normal `sbatch` options and defaults
`WORKFLOW_OUTPUT_ROOT` to `$HOME/chemistry-runs`. It creates a unique run
directory named with a UTC timestamp and the submission process ID.
`WORKFLOW_RUN_ID` can supply a stable name instead. `jobs.tsv` records every
GAMESS job, chemistry job, input, and expected result path.

```text
<WORKFLOW_OUTPUT_ROOT>/<run-id>/jobs.tsv
<WORKFLOW_OUTPUT_ROOT>/<run-id>/slurm-gamess-<job-id>.out
<WORKFLOW_OUTPUT_ROOT>/<run-id>/slurm-chemistry-<job-id>.out
<WORKFLOW_OUTPUT_ROOT>/<run-id>/slurm-collect-<job-id>.out
<WORKFLOW_OUTPUT_ROOT>/<run-id>/gamess-runs/<job-id>/gamess.log
<WORKFLOW_OUTPUT_ROOT>/<run-id>/gamess-runs/<job-id>/fcidump/FCIDUMP
<WORKFLOW_OUTPUT_ROOT>/<run-id>/chemistry-runs/<job-id>/manifest.json
<WORKFLOW_OUTPUT_ROOT>/<run-id>/chemistry-runs/<job-id>/workflow-result.json
<WORKFLOW_OUTPUT_ROOT>/<run-id>/chemistry-runs/<job-id>/qfw/application/logs/
<WORKFLOW_OUTPUT_ROOT>/<run-id>/workflow-results.json
```

`workflow-results.json` collects every completed case's fragment energies and
FMO total together with the Slurm job IDs. A failed GAMESS job prevents its
chemistry job from starting. Other independent cases may still finish, while
the final collection job requires every chemistry job to succeed. Unset the
three `MAX_*_ITERATIONS` variables after a short validation run to restore
normal optimizer settings.

## Diagnosing failures

The standalone scripts isolate failures that a simple Qiskit connectivity test
does not cover:

| Symptom | Cause or check |
| --- | --- |
| No application output; Slurm reports `0:53` | Check `slurmd.log` for failure to open the Slurm output file. The submission directory may be unwritable. |
| `clone: Operation not permitted` before the script starts | `--export=ALL,NAME=value` requests Slurm's login environment helper. The submission wrapper exports variables first and uses plain `--export=ALL`. |
| Python tries to open a file named `python3` | Pass the application script directly to `qfw-srun`; it already invokes `defw-python`. |
| PySCF rejects the GAMESS FCIDUMP | Normalize the header and Fortran exponents in fragment copies before parsing. |
| Calculations finish but results are absent | Collect and write results before QFw backend shutdown exits the process. |
| `RuntimeError: deque mutated during iteration` in statistics | Deploy the snapshot locking fixes in QFw's `CircuitMetrics.dump` and DEFw's `RPCMetrics.dump`, including on Janus. |

## Generalizing the splitter

The workflow determines the fragment count from `NFRAG` in the GAMESS input.
It writes PySCF-readable copies with a comma between `ISYM` and `UHF` and
converts Fortran `D` exponents to `E`. The original GAMESS FCIDUMP is retained.
For FMO2 calculations it selects the final `NFRAG` monomer blocks and final
`NFRAG * (NFRAG - 1) / 2` dimer blocks. The observed GAMESS He1-4 dimer order
is recorded in `manifest.json` so the FMO correction uses the corresponding
monomer pair for every dimer.

Validate this ordering against each new GAMESS version or molecular family
before treating the sample as a production chemistry workflow.

## Virtual cluster validation, 2026-10-21

| Stage | Jobs | Inputs | Result |
| --- | --- | --- | --- |
| GAMESS alone | 41, 43 | He1-1, He1-4 | Completed, exit `0:0`; generated FCIDUMP and normal-termination log. |
| Chemistry alone | 47, 49 | Saved FCIDUMPs from jobs 41 and 43 | Completed, exit `0:0`; collected one monomer for He1-1 and four monomers plus six dimers for He1-4. |
| Earlier single-allocation integration | 50 | He1-1, He1-4 | Completed, exit `0:0`, in 2m58s; fresh FCIDUMP handoffs, both result files, and job summary verified. |

Chemistry used NWQSIM with one macro iteration, 18 amplitude evaluations
(six in job 47), and one orbital iteration. These are execution checks;
the optimizer reported nonconvergence, so the saved energies are not validated
scientific results. The complete six-input calculation with normal optimizer
settings and execution on Janus have not been validated. The independent
stage scripts were validated in the jobs above. The dependency submission
wrapper was added afterward and has not yet been exercised on a cluster.

Job 50 retained its summary in the virtual cluster at
`/workspace/home/user-a/chemistry-combined-validation/50/workflow-results.json`.
Its Slurm log is
`/workspace/home/user-a/chemistry-combined-validation/slurm-50.out`.
The QFw reservation was released after completion. The tests included the
statistics snapshot fixes in the local QFw and DEFw sources, copied into the
running compute containers; these fixes must also be installed on Janus.
