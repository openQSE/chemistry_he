import os

def split_fcidump_blocks(filename):
    base = os.path.split(filename)[0]

    with open(filename, 'r') as f:
        lines = f.readlines()

    # Identify the start lines of each block
    block_starts = []
    for i, line in enumerate(lines):
        if line.startswith(" &FCI NORB=10,NELEC=4,MS2=0") or line.startswith(" &FCI NORB=5,NELEC=2,MS2=0"):
            block_starts.append(i)

    # Append end-of-file index to slice last block
    block_starts.append(len(lines))

    # Extract all blocks with their content
    blocks = []
    for i in range(len(block_starts) - 1):
        block = lines[block_starts[i]:block_starts[i+1]]
        blocks.append((lines[block_starts[i]].strip(), block))

    # Separate blocks into categories
    type2_blocks = [b[1] for b in blocks if b[0] == "&FCI NORB=10,NELEC=4,MS2=0"]
    type1_blocks = [b[1] for b in blocks if b[0] == "&FCI NORB=5,NELEC=2,MS2=0"]

    # Write last 6 type2 blocks
    for idx, block in enumerate(type2_blocks[-6:], 1):
        with open(os.path.join(base, f"He1-4.FCIDUMP-2-{idx}"), 'w') as out:
            out.writelines(block)

    # Write last 4 type1 blocks
    for idx, block in enumerate(type1_blocks[-4:], 1):
        with open(os.path.join(base, f"He1-4.FCIDUMP-1-{idx}"), 'w') as out:
            out.writelines(block)

    print("Blocks written successfully.")

# Example usage
if __name__ == '__main__':
    import argparse, os

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--path", required=True, help="Path to use")
    args = parser.parse_args()

    path = args.path
    split_fcidump_blocks(path)
