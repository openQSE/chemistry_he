#!/usr/bin/env python3
"""Run helium pUCCD calculations from a GAMESS FCIDUMP file."""

import argparse
import json
import re
import traceback
from itertools import combinations
from pathlib import Path

from puccd import pairUCC, puccd_finalize, puccd_initialize


HEADER = re.compile(r"&FCI\s+NORB=(\d+),\s*NELEC=(\d+),", re.IGNORECASE)


def fragment_count(input_path):
    text = Path(input_path).read_text()
    match = re.search(r"\bNFRAG\s*=\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else 1


def fcidump_blocks(path):
    lines = Path(path).read_text().splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.lstrip().startswith("&FCI")]
    if not starts:
        raise ValueError(f"no FCIDUMP blocks found in {path}")
    starts.append(len(lines))
    blocks = []
    for start, end in zip(starts, starts[1:]):
        match = HEADER.search(lines[start])
        if not match:
            raise ValueError(f"unrecognized FCIDUMP header: {lines[start].strip()}")
        blocks.append({"norb": int(match.group(1)), "nelec": int(match.group(2)), "lines": lines[start:end]})
    return blocks


def gamess_fmo_pair_order(count):
    pairs = list(combinations(range(count), 2))
    # GAMESS emits the first FMO2 pair after all other pair blocks.  This order
    # matches the checked He1-4 FCIDUMP and keeps the manifest explicit.
    return pairs[1:] + pairs[:1] if len(pairs) > 1 else pairs


def write_pyscf_fcidump(block, target):
    """Write a PySCF-readable copy without changing the GAMESS output."""
    text = "".join(block["lines"])
    text = re.sub(r"(\bISYM\s*=\s*\d+)\s+(?=UHF\s*=)", r"\1,", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)[dD](?=[+-]\d)", "E", text)
    target.write_text(text)


def split_fcidump(path, fragment_total, output_dir):
    path = Path(path).resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = fcidump_blocks(path)
    if fragment_total == 1:
        if len(blocks) != 1:
            raise ValueError("expected one FCIDUMP block for a single fragment")
        target = output_dir / f"{path.name}-1-1"
        write_pyscf_fcidump(blocks[0], target)
        return {"source": str(path), "fragment_count": 1,
                "monomers": [{"id": 0, "path": str(target)}], "dimers": []}

    monomer_electrons = min(block["nelec"] for block in blocks)
    monomers = [block for block in blocks if block["nelec"] == monomer_electrons]
    dimers = [block for block in blocks if block["nelec"] == 2 * monomer_electrons]
    expected_dimers = fragment_total * (fragment_total - 1) // 2
    if len(monomers) < fragment_total or len(dimers) < expected_dimers:
        raise ValueError("FCIDUMP does not contain the expected final monomer and dimer blocks")

    prefix = path.name
    manifest = {"source": str(path), "fragment_count": fragment_total,
                "pair_order": "gamess-fmo2-rotated-lexicographic",
                "monomers": [], "dimers": []}
    for index, block in enumerate(monomers[-fragment_total:]):
        target = output_dir / f"{prefix}-1-{index + 1}"
        write_pyscf_fcidump(block, target)
        manifest["monomers"].append({"id": index, "path": str(target)})
    for index, (block, pair) in enumerate(zip(dimers[-expected_dimers:], gamess_fmo_pair_order(fragment_total))):
        target = output_dir / f"{prefix}-2-{index + 1}"
        write_pyscf_fcidump(block, target)
        manifest["dimers"].append({"id": index, "fragments": list(pair), "path": str(target)})
    return manifest


def calculate(path, macro_iterations, amplitude_iterations, orbital_iterations):
    print(f"Calculating fragment: {path}", flush=True)
    ansatz = pairUCC.from_FCIDUMP(path)
    energy = ansatz.optimize_ansatz_qk(
        ansatz.initial_guess_mp2d(),
        maxiter_macro=macro_iterations,
        maxiter_amps=amplitude_iterations,
        maxiter_orbs=orbital_iterations,
    )
    return float(energy)


def main():
    parser = argparse.ArgumentParser(description="Split a GAMESS FCIDUMP and run helium FMO-VQE.")
    parser.add_argument("-p", "--path", required=True, help="path to the GAMESS FCIDUMP file")
    parser.add_argument("-i", "--gamess-input", required=True, help="GAMESS input used to create the FCIDUMP")
    parser.add_argument("-o", "--output-dir", help="directory for split files and workflow-result.json")
    parser.add_argument("--qfw", action="store_true", help="use QFw for estimator executions")
    parser.add_argument("--provider", default="iqm", help="QFw provider when --qfw is set")
    parser.add_argument("--shots", type=int, default=4096, help="shots per QFw circuit")
    parser.add_argument("--max-macro-iterations", type=int, default=3)
    parser.add_argument("--max-amplitude-iterations", type=int, default=50)
    parser.add_argument("--max-orbital-iterations", type=int, default=1000)
    args = parser.parse_args()

    fcidump = Path(args.path).resolve(strict=True)
    output_dir = Path(args.output_dir or fcidump.parent / "chemapp").resolve()
    manifest = split_fcidump(fcidump, fragment_count(args.gamess_input), output_dir / "fragments")
    (output_dir / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    puccd_initialize(qfw=args.qfw, provider=args.provider if args.qfw else None, shots=args.shots)
    try:
        monomer_energy = {item["id"]: calculate(item["path"], args.max_macro_iterations, args.max_amplitude_iterations, args.max_orbital_iterations)
                          for item in manifest["monomers"]}
        dimer_energy = {item["id"]: calculate(item["path"], args.max_macro_iterations, args.max_amplitude_iterations, args.max_orbital_iterations)
                        for item in manifest["dimers"]}

        total = sum(monomer_energy.values())
        for item in manifest["dimers"]:
            left, right = item["fragments"]
            total += dimer_energy[item["id"]] - monomer_energy[left] - monomer_energy[right]
        result = {"manifest": str(output_dir / "manifest.json"), "monomer_energies": monomer_energy,
                  "dimer_energies": dimer_energy, "fmo_energy": total}
        # QFw backend shutdown exits DEFw's application process. Collect and
        # flush results before finalizing, while the Python code still runs.
        (output_dir / "workflow-result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
    except Exception:
        # Report the error before backend finalization exits the application.
        traceback.print_exc()
        raise
    finally:
        puccd_finalize(qfw=args.qfw)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # DEFw records uncaught exceptions in its own log; expose them in the
        # Slurm/application log too, so a failed calculation has a visible cause.
        traceback.print_exc()
        raise
