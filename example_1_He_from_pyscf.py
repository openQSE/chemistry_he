import argparse
import time

from puccd import puccd_initialize, puccd_finalize
from example_1_He import example_1_He

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Run the PySCF He pUCCD example.")
	parser.add_argument("--qfw", action="store_true", help="use the QFw estimator")
	args = parser.parse_args()

	puccd_initialize(qfw=args.qfw)
	try:
		start = time.time()
		example_1_He()
		print(f"####Example 1 HE completed in {time.time() - start}")
	finally:
		puccd_finalize(qfw=args.qfw)
