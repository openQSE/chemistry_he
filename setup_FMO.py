import os
from pathlib import Path
import numpy as np

def setup_FMO(folder:str, base:str):
	monomer_files = []
	dimer_files = []

	n_monomers = len(list(Path(folder).glob(base + '-1-*')))
	n_dimers = len(list(Path(folder).glob(base + '-2-*')))

	for monomer in range(1,n_monomers+1):
		monomer_files.append(folder+base+"-1-"+str(monomer))
	for dimer in range(1,n_dimers+1):
		dimer_files.append(folder + base+"-2-"+str(dimer))
	return monomer_files, dimer_files

# folder = os.path.dirname(os.path.abspath(__file__)) + "/He4/"
# setup_FMO(folder,"He1-4.FCIDUMP")