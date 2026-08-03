import argparse
import os

from puccd import (
	pairUCC,
	of2qiskit,
	puccd_add_runtime_args,
	puccd_apply_legacy_args,
	puccd_initialize_from_args,
	puccd_finalize,
)

from pyscf import fci
from pyscf.tools import fcidump


def example_2_He2_from_FCIDUMP(smoke=False, draw=True):
	# 1. Initialize a pairUCC object from a FCIDUMP file
	file = os.path.dirname(os.path.abspath(__file__)) + "/He4/He1-4.FCIDUMP-2-1"
	puccd_obj = pairUCC.from_FCIDUMP(file)

	# 2. (Optional) use pyscf to compute the mean field
	#    and FCI (exact) energy
	mf = fcidump.to_scf(file)
	mf.conv_tol_grad = 1e-14
	mf.max_cycle = 200
	mf.kernel()

	cisolver = fci.FCI(mf)
	e,fcivec = cisolver.kernel()
	print('E(FCI) = %.12f' % e)

	# 3. Print the system Hamiltonian as a basis of Pauli words
	pauli_ham = of2qiskit(puccd_obj.ham_qubit(),puccd_obj.n_qubits)
	print(pauli_ham)

	# 4. Print the ansatz circuit
	ansatz = puccd_obj.givens_rot_ansatz()
	print(ansatz)
	if draw:
		ansatz.draw(output='mpl',filename='example_2_ansatz.jpeg')

	# 5. Prepare an initial guess for the VQE from diagonal MP2
	guess = puccd_obj.initial_guess_mp2d()
	print("Initial guess:", guess)

	# 6. Measure the expectation value of the Hamiltonian using
	#    the diagonal MP2 initial guess. This prepares the state
	#    and measures each of the Pauli strings present in the
	#    Hamiltonian using the Qiskit "estimator" primitive
	guess_energy = puccd_obj.compute_energy_qk(guess)
	print('E(guess) = %.12f'%guess_energy)

	# 7. Expectation values are stored in a dictionary as a member
	#    variable of the pUCCD class, enabling them to be reused to
	#    calculate the energy, orbital gradient, and orbital Hessian
	guess_energy2 = puccd_obj.expected_energy()
	guess_orb_grad = puccd_obj.orb_grad_qk()
	guess_orb_hess = puccd_obj.orb_hess_qk()
	print('E(guess) = %.12f'%guess_energy2)
	print("Guess orbital gradient:")
	print(guess_orb_grad)
	print("Guess orbital hessian:")
	print(guess_orb_hess)

	# 8. Perform an orbital-optimized VQE subroutine to optimize the
	#    pUCCD parameters and orbital rotation parameters.
	opt_kwargs = {}
	if smoke:
		opt_kwargs = {
			"maxiter_macro": 1,
			"maxiter_amps": 1,
			"maxiter_orbs": 1,
		}
	e_oopuccd = puccd_obj.optimize_ansatz_qk(guess, **opt_kwargs)
	print('E(oo-pUCCD) = %.12f'%e_oopuccd)


def parse_args():
	parser = argparse.ArgumentParser(
		description="Run the He dimer pUCCD example from FCIDUMP input")
	puccd_add_runtime_args(parser)
	parser.add_argument("--smoke", action="store_true",
		help="limit optimizer iterations for integration testing")
	parser.add_argument("--no-draw", action="store_true",
		help="skip ansatz image generation")
	parser.add_argument("legacy_qfw", nargs="?", help=argparse.SUPPRESS)
	return puccd_apply_legacy_args(parser.parse_args())


if __name__ == "__main__":
	args = parse_args()
	puccd_initialize_from_args(args)
	try:
		example_2_He2_from_FCIDUMP(
			smoke=args.smoke, draw=not args.no_draw)
	finally:
		puccd_finalize(qfw=args.qfw)
