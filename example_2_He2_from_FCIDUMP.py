import puccd
from puccd import pairUCC, of2qiskit

from pyscf import gto, scf, ao2mo, fci 
from pyscf.tools import fcidump

import os
from pathlib import Path

# 1. Initialize a pairUCC object from a FCIDUMP file
file = os.path.dirname(os.path.abspath(__file__)) + "/He4/He1-4.FCIDUMP-2-1"
puccd = pairUCC.from_FCIDUMP(file)

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
pauli_ham = of2qiskit(puccd.ham_qubit(),puccd.n_qubits)
print(pauli_ham)

# 4. Print the ansatz circuit
ansatz = puccd.givens_rot_ansatz()
print(ansatz)
ansatz.draw(output='mpl',filename='example_2_ansatz.jpeg')

# 5. Prepare an initial guess for the VQE from diagonal MP2
guess = puccd.initial_guess_mp2d()
print("Initial guess:", guess)

# 6. Measure the expectation value of the Hamiltonian using 
#    the diagonal MP2 initial guess. This prepares the state
#    and measures each of the Pauli strings present in the 
#    Hamiltonian using the Qiskit "estimator" primitive
guess_energy = puccd.compute_energy_qk(guess)
print('E(guess) = %.12f'%guess_energy)

# 7. Expectation values are stored in a dictionary as a member
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

# 8. Perform an orbital-optimized VQE subroutine to optimize the pUCCD parameters
#    and orbital rotation parameters
#    Note: orbital rotations are implemented by transforming the integrals
#    used to build the Hamiltonian/gradient/hessian
e_oopuccd = puccd.optimize_ansatz_qk(guess)
print('E(oo-pUCCD) = %.12f'%e_oopuccd)


