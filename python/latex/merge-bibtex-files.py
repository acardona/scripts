# 2020-06-27 Albert Cardona
# Merges two or more .bib files into a new .bib file
# Assumes input .bib files are valid
# Assumes '@' for e.g. @article is at the begining of a line always
# Right-to-left preference: last (right) filepaths override first (left) filepaths
# Writes a new .bib file, never overwriting any file


import sys, os

if len(sys.argv) < 3:
    print("Usage: python merge-bib-files.py file1.bib file2.bib ...")
    sys.exit(0)

# Check file extensions
for bibpath in sys.argv[1:]:
    if not bibpath.endswith(".bib"):
        answer = input("File %s lack .bib extension. Proceed anyway? (N/y)" % bibpath)
        if not answer or answer.lower().startswith("n"):
            sys.exit(0)

def put(entry, entries):
    key = entry[0][entry[0].find('{') + 1 : entry[0].rfind(',')]
    if key in entries:
        print("WARNING: repeated entry with key %s. Ignoring." % key)
    else:
        entries[key] = entry

def parse(filepath):
    entries = {}
    with open(filepath, 'r') as f:
        entry = None
        for line in f:
            if '@' == line[0]:
                # Enter previous one if any
                if entry:
                    put(entry, entries)
                # Start new entry
                entry = []
            entry.append(line)
        # Last one
        if entry:
            put(entry, entries)
    return entries

libraries = map(parse, sys.argv[1:])

merged = {}
for lib in libraries:
    merged.update(lib)

# Choose non-existing name to avoid overwriting
mergedpath = "merged.bib"
count = 1
while os.path.exists(mergedpath):
    mergedpath = "merged%i.bib" % count
    count += 1

with open(mergedpath, 'w') as f:
    for entry in merged.values():
        for line in entry:
            f.write(line)


