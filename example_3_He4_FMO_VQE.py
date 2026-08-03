import argparse
import os

import numpy as np

from puccd import (
	pairUCC,
	of2qiskit,
	puccd_add_runtime_args,
	puccd_apply_legacy_args,
	puccd_initialize_from_args,
	puccd_finalize,
)

from setup_FMO import setup_FMO


def _optimization_kwargs(smoke):
	if not smoke:
		return {}
	return {
		"maxiter_macro": 1,
		"maxiter_amps": 1,
		"maxiter_orbs": 1,
	}


def example_3_He4_FMO_VQE(smoke=False, draw=True):
	# 1. Locate monomer and dimer FCIDUMP files to be read in
	folder = os.path.dirname(os.path.abspath(__file__)) + "/He4/"
	monomer_files, dimer_files = setup_FMO(folder,"He1-4.FCIDUMP")
	if smoke:
		monomer_files = monomer_files[:1]
		dimer_files = []

	# 2. Mapping of dimers to corresponding monomers
	#    Currently hardcoded, to be automated by S. Irle
	mDimers2Monomers = {
		0: (2, 0),
		1: (2, 1),
		2: (3, 0),
		3: (3, 1),
		4: (3, 2),
		5: (1, 0),
	}

	opt_kwargs = _optimization_kwargs(smoke)

	# 3. Loop over monomers. This step should be performed in parallel on (v)QPU
	monomer_energies = []
	monomer_idx = 0
	for monomer in monomer_files:
		# 3a. Initialize a new pairUCC object for each monomer
		puccd = pairUCC.from_FCIDUMP(monomer)

		# 3b. Print Hamiltonian for each monomer
		ham = of2qiskit(puccd.ham_qubit(),puccd.n_qubits)
		print(ham)

		# 3c. Print state-prep ansatz
		ansatz = puccd.givens_rot_ansatz()
		print(ansatz)
		if draw:
			ansatz.draw(
				output='mpl',
				filename='He4_monomer_'+str(monomer_idx)+'_ansatz.jpeg')

		# 3d. Perform oo-VQE subroutine to optimize amplitudes and orbitals
		guess = puccd.initial_guess_mp2d()
		e_oopuccd = puccd.optimize_ansatz_qk(guess, **opt_kwargs)
		print("*Converged monomer %d energy = %.12f"%(monomer_idx,e_oopuccd))

		# 3e. Append optimized energy to monomer energies list
		monomer_energies.append(e_oopuccd)
		monomer_idx += 1

	# 4. Loop over dimers. This step should be performed in parallel on (v)QPU
	dimer_energies = []
	dimer_idx = 0
	for dimer in dimer_files:
		# 4a. Initialize a new pairUCC object for each dimer
		puccd = pairUCC.from_FCIDUMP(dimer)

		# 4b. Print Hamiltonian for each dimer
		ham = of2qiskit(puccd.ham_qubit(),puccd.n_qubits)
		print(ham)

		# 4c. Print state-prep ansatz
		ansatz = puccd.givens_rot_ansatz()
		print(ansatz)
		if draw:
			ansatz.draw(
				output='mpl',
				filename='He4_dimer_'+str(dimer_idx)+'_ansatz.jpeg')

		# 4d. Perform oo-VQE subroutine to optimize amplitudes and orbitals
		guess = puccd.initial_guess_mp2d()
		e_oopuccd = puccd.optimize_ansatz_qk(guess, **opt_kwargs)
		print("*Converged dimer %d energy = %.12f"%(dimer_idx,e_oopuccd))

		# 4e. Append optimized energy to dimer energies list
		dimer_energies.append(e_oopuccd)
		dimer_idx += 1

	if smoke:
		print("*FMO-VQE smoke completed with %d monomer energies"%(
			len(monomer_energies)))
		return

	# 5. Compute FMO energy from monomer and dimer contributions
	e_fmo = np.sum(monomer_energies)
	for dimer, monomers in mDimers2Monomers.items():
		e_fmo += dimer_energies[dimer]
		e_fmo -= monomer_energies[monomers[0]]
		e_fmo -= monomer_energies[monomers[1]]

	print("*FMO-VQE energy = %.12f"%e_fmo)


def parse_args():
	parser = argparse.ArgumentParser(
		description="Run the He4 FMO-VQE pUCCD example")
	puccd_add_runtime_args(parser)
	parser.add_argument("--smoke", action="store_true",
		help="limit optimizer iterations and run one monomer")
	parser.add_argument("--no-draw", action="store_true",
		help="skip ansatz image generation")
	parser.add_argument("legacy_qfw", nargs="?", help=argparse.SUPPRESS)
	return puccd_apply_legacy_args(parser.parse_args())


if __name__ == "__main__":
	args = parse_args()
	puccd_initialize_from_args(args)
	try:
		example_3_He4_FMO_VQE(smoke=args.smoke, draw=not args.no_draw)
	finally:
		puccd_finalize(qfw=args.qfw)
