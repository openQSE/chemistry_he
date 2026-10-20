import argparse
import time

from puccd import pairUCC, of2qiskit
from puccd import puccd_finalize, puccd_initialize
from pyscf import fci
from pyscf.tools import fcidump

def run(fcidump_file):
	# 1. Initialize a pairUCC object from a FCIDUMP file
	puccd = pairUCC.from_FCIDUMP(fcidump_file)

	# 2. (Optional) use pyscf to compute the mean field
	#    and FCI (exact) energy
	mf = fcidump.to_scf(fcidump_file)
	mf.conv_tol_grad = 1e-14
	mf.max_cycle = 200
	mf.kernel()

	cisolver = fci.FCI(mf)
	e, fcivec = cisolver.kernel()
	print('E(FCI) = %.12f' % e)

	# 3. Print the system Hamiltonian as a basis of Pauli words
	pauli_ham = of2qiskit(puccd.ham_qubit(), puccd.n_qubits)
	print(pauli_ham)

	# 4. Print the ansatz circuit
	ansatz = puccd.givens_rot_ansatz()
	print(ansatz)
	ansatz.draw(output='mpl', filename='example_2_ansatz.jpeg')

	# 5. Prepare an initial guess for the VQE from diagonal MP2
	guess = puccd.initial_guess_mp2d()
	print("Initial guess:", guess)

	# 6. Measure the expectation value of the Hamiltonian using
	#    the diagonal MP2 initial guess.
	guess_energy = puccd.compute_energy_qk(guess)
	print('E(guess) = %.12f' % guess_energy)

	# 7. Reuse expectation values for energy, gradient, and Hessian.
	guess_energy2 = puccd.expected_energy()
	guess_orb_grad = puccd.orb_grad_qk()
	guess_orb_hess = puccd.orb_hess_qk()
	print('E(guess) = %.12f' % guess_energy2)
	print("Guess orbital gradient:")
	print(guess_orb_grad)
	print("Guess orbital hessian:")
	print(guess_orb_hess)

	# 8. Perform an orbital-optimized VQE subroutine.
	e_oopuccd = puccd.optimize_ansatz_qk(guess)
	print('E(oo-pUCCD) = %.12f' % e_oopuccd)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Run pUCCD from one FCIDUMP file.")
	parser.add_argument("-p", "--path", required=True, help="path to the FCIDUMP file")
	parser.add_argument("--qfw", action="store_true", help="use the QFw estimator")
	args = parser.parse_args()

	puccd_initialize(qfw=args.qfw)
	try:
		start = time.time()
		run(args.path)
		print(f"####Example 2 completed in {time.time() - start}")
	finally:
		puccd_finalize(qfw=args.qfw)


