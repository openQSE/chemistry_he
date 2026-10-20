# GAMESS to QFw chemistry workflow

This sample connects GAMESS FCIDUMP generation with pUCCD VQE calculations
through QFw. It is intended as a compact reference workflow that can be
reimplemented in StreamFlow, TIERKries, COMPSs, or another workflow engine.

## Workflow

1. Reserve two classical Slurm tasks and a QFw IQM reservation.
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
| QFw device | `ornl-iqm-20q` | Janus exposes this IQM QPU resource. |
| Maximum qubits | 10 | The helium dimer FCIDUMP blocks contain `NORB=10`. |
| Maximum circuit depth | 1000 | Raw pUCCD dimer depth is about 129; the allowance covers transpilation. |
| Maximum shots | 4096 | QFw's estimator precision default corresponds to 4096 shots. |
| Circuit count | 32000 | Six inputs, 210 fragment calculations, and a 3 by 50 VQE iteration cap. |

The circuit-count estimate uses at most one initial energy evaluation plus 150
COBYLA evaluations for every monomer or dimer. Increase the Slurm reservation
when increasing `MAX_MACRO_ITERATIONS` or `MAX_AMPLITUDE_ITERATIONS`.

## Running the Slurm sample

Submit from the `chemistry_he` checkout:

```bash
sbatch workflow/slurm/gamess-fcidump-qfw-workflow.sbatch
```

The default inputs are `input/He1-1.inp`, `input/He1-2.inp`,
`input/He1-4.inp`, `input/He1-8.inp`, `input/He1-10.inp`, and
`input/He1-14.inp`.

Each input receives a separate result directory under
`chemistry-runs/<job-id>/<input-name>/`. It contains the GAMESS files,
FCIDUMP, `chemapp/manifest.json`, and `chemapp/workflow-result.json`.

## Generalizing the splitter

The workflow determines the fragment count from `NFRAG` in the GAMESS input.
For FMO2 calculations it selects the final `NFRAG` monomer blocks and final
`NFRAG * (NFRAG - 1) / 2` dimer blocks. The observed GAMESS He1-4 dimer order
is recorded in `manifest.json` so the FMO correction uses the corresponding
monomer pair for every dimer.

Validate this ordering against each new GAMESS version or molecular family
before treating the sample as a production chemistry workflow.
