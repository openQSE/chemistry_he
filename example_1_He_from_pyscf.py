import argparse
from puccd import (
	puccd_add_runtime_args,
	puccd_apply_legacy_args,
	puccd_initialize_from_args,
	puccd_finalize,
)
from example_1_He import example_1_He
import time

def parse_args():
	parser = argparse.ArgumentParser(
		description="Run the He pUCCD example from PySCF input")
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
		start = time.time()
		example_1_He(smoke=args.smoke, draw=not args.no_draw)
		print(f"####Example 1 HE completed in {time.time() - start}")
	finally:
		puccd_finalize(qfw=args.qfw)
