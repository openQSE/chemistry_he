import puccd
from puccd import pairUCC, of2qiskit
import setup_FMO
from pyscf import gto, scf, ao2mo, fci 
from pyscf.tools import fcidump

def example_1_He(smoke=False, draw=True):
	# 1. Create a pyscf.Mole object for He atom
	mol = gto.Mole()
	mol.atom = [('He', (0,0,0))]
	#mol.atom = [('He', (0,0,0)),('He',(0,0,2))]
	mol.max_memory = 8e3 # MB
	mol.charge = 0
	mol.spin = 0
	mol.basis = "cc-pvdz"
	mol.symmetry = False
	mol.build()
	e_nuc = mol.get_enuc()

	# 2. (Optional) use pyscf to compute the mean field
	#    and FCI (exact) energy
	mf = scf.RHF(mol)
	mf.conv_tol_grad = 1e-14
	mf.max_cycle = 200
	mf.kernel()

	cisolver = fci.FCI(mf)
	e,fcivec = cisolver.kernel()
	print('E(FCI) = %.12f' % e)

	# 3. Initialize a pairUCC object from a pyscf.Mole object
	puccd = pairUCC.from_pyscf_Mole(mol)

	# 4. Print the system Hamiltonian as a basis of Pauli words
	pauli_ham = of2qiskit(puccd.ham_qubit(),puccd.n_qubits)
	print(pauli_ham)

	# 5. Print the ansatz circuit
	ansatz = puccd.givens_rot_ansatz()
	print(ansatz)
	if draw:
		ansatz.draw(output='mpl',filename='/tmp/example_1_ansatz.jpeg')

	# 6. Prepare an initial guess for the VQE from diagonal MP2
	guess = puccd.initial_guess_mp2d()
	print("Initial guess:", guess)

	# 7. Measure the expectation value of the Hamiltonian using 
	#    the diagonal MP2 initial guess. This prepares the state
	#    and measures each of the Pauli strings present in the 
	#    Hamiltonian using the Qiskit "estimator" primitive
	guess_energy = puccd.compute_energy_qk(guess)
	print('E(guess) = %.12f'%guess_energy)

	# 8. Expectation values are stored in a dictionary as a member
	#    variable of the pUCCD class, enabling them to be reused to 
	#    calculate the energy, orbital gradient, and orbital Hessian
	guess_energy2 = puccd.expected_energy()
	guess_orb_grad = puccd.orb_grad_qk()
	guess_orb_hess = puccd.orb_hess_qk()
	print('E(guess) = %.12f'%guess_energy2)
	print("Guess orbital gradient:")
	print(guess_orb_grad)
	print("Guess orbital hessian:")
	print(guess_orb_hess)

	# 9. Perform a VQE subroutine to optimize the pUCCD parameters
	maxiter_amps = 1 if smoke else 1000
	maxiter_orbs = 1 if smoke else 1000
	e_puccd = puccd.optimize_amps_qk(guess, maxiter_amps=maxiter_amps)
	print('E(pUCCD) = %.12f'%e_puccd)

	# 7. Rotate orbitals to optimize VQE energy using converged VQE results
	#    Note: orbital rotations are implemented by transforming the integrals
	#    used to build the Hamiltonian/gradient/hessian
	e_oopuccd = puccd.optimize_orbs_qk(maxiter=maxiter_orbs)
	print('E(oo-pUCCD) = %.12f'%e_oopuccd)

