from puccd import puccd_initialize, puccd_finalize
from example_1_He import example_1_He
import time, sys

if __name__ == "__main__":
	args = sys.argv
	qfw = False
	if (len(args) > 1):
		qfw = True

	puccd_initialize(qfw=qfw)

	start = time.time()
	example_1_He()
	print(f"####Example 1 HE completed in {time.time() - start}")

	puccd_finalize(qfw=qfw)
