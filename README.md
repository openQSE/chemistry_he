# HPC+Q Chemistry Example Aim 2 
This is simulation code to implement the VQE aspect of a FMO-VQE workflow to approximate the ground state energies of molecular clusters. 
The current implementation utilizes a unitary coupled cluster with pair double excitations (pUCCD) ansatz for the monomer and dimer calculations. More information on this approach may be found here [article](https://www.nature.com/articles/s41534-023-00730-8).

This directory contains the following source and data files:

- puccd.py : source code to implement the pUCCD ansatz and orbital optimization
- setup_FMO.py : source code to setup a FMO-VQE calculation from a GAMESS output of FCIDUMP files
- He4/ : directory containing output FCIDUMP files from GAMESS to be ingested by the VQE approach
- example_1_He_from_pyscf.py : example input for running pUCCD on a He atom initialized from pyscf
- example_2_He2_from_FCIDUMP.py : example input for running pUCCD on a He dimer initialized from a FCIDUMP file
- example_3_He4_FMO_VQE.py : example input file for running a FMO-VQE calculation using the monomer and dimer FCIDUMP files from the He4/ directory
- requirements.txt : Python package requirements for executing the example scripts
