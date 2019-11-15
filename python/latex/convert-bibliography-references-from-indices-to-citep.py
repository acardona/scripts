# Albert Cardona 2019-10-21
# 
# Parse a .tex file whose references are literal numbers like: $^{2,3,8-9}$
# with a list of entries at the end like: \item[3] Author, I., This and that (1999).
# and replace them with proper \citep{Author1999} bibtex.
#

import re

manuscript_file = 'FB-manuscript.tex'
methods_file = 'materials-and-methods.tex'
references_file = 'references.bib'

pattern1 = re.compile('\$\^{(\d[\s\d,-]*)}\$')
pattern2 = re.compile('\s+\\\\item\[(\d+)\]')

unique = set()
entries = {} # number key vs text of the bibliographic reference

def parseIndices(s):
  for ref in s.split(','):
    r = ref.split('-')
    if 1 == len(r):
      # single number
      yield int(ref)
    else:
      # range like 9-14
      for num in range(int(r[0]), int(r[1]) + 1):
        yield num

with open(manuscript_file, 'r') as f:
  section_references_found = False
  for line in f:
    # re.findall returns an empty list when none found
    for s in re.findall(pattern1, line):
      unique.update(parseIndices(s))

    if not section_references_found:
      section_references_found = line.startswith("\\section*{References}")

    if section_references_found:
      m = re.findall(pattern2, line)
      if len(m) > 0:
        entries[int(m[0])] = line[line.find(']')+1:].strip()

#for k in sorted(entries):
#  print("%i: %s" % (k, entries[k]))

# Print numbers that were erased
previous = 1
removed = []
for i in sorted(entries):
  if i > previous + 1:
    for k in range(previous + 1, i):
      removed.append(k)
  previous = i
print("Removed refs: " + ",".join(str(k) for k in removed))


existing_ref_handles = {}


def getRefHandle(index):
  handle = existing_ref_handles.get(index, None)
  if handle:
    return handle
  # Create it
  text = entries.get(index, None)
  if not text:
    return "MISSING"
  # First author surname plus year - NOTE, could overlap with a different one
  handle_base = text[0:text.find(",")] + text[text.rfind(")")-4:text.rfind(")")]
  handle = handle_base
  suffix = 96 # chr(97) == 'a'
  while handle in existing_ref_handles:
    handle = handle + chr(suffix + 1)
  existing_ref_handles[index] = handle
  if suffix > 96:
    print("Avoided duplicating ref handle by using: " + handle)
  return handle


def asBibtex(m):
  """ m is a Match object. """
  content = m.group(0)[3:-2] # remove starting '$^{' and ending '}$'
  return " \citep{" + ", ".join(getRefHandle(i) for i in parseIndices(content)) + "}"

# Replace numeric tags like '$^{1,3-5}$' with ' \citep{Author2007, Author1999, <etc> }'
with open(manuscript_file, 'r') as source:
  with open(manuscript_file[:-4] + '.bib.tex', 'w') as target:
    pattern3 = re.compile('\$\^{\d[\s\d,-]*}\$')
    started = False
    ended = False
    for line in source:
      if ended:
        target.write(line)
        continue
      if not started:
        started = line.startswith("\section*{Introduction}")
        target.write(line)
        continue
      if not ended:
        ended = line.startswith("\section*{References}")
        if not ended:
          line = re.sub(pattern3, asBibtex, line)
        target.write(line)

# Same, for the methods file
if methods_file:
  with open(methods_file, 'r') as source:
    with open(methods_file[:-4] + '.bib.tex', 'w') as target:
      pattern3 = re.compile('\$\^{\d[\s\d,-]*}\$')
      # Whole file, not a subset
      for line in source:
        target.write(re.sub(pattern3, asBibtex, line))


# Check bibliography for missing references
with open(references_file, 'r') as f:
  text = f.read()
  text = text[text.find('@'):] # jump to first entry
  chunks = re.split(r'@article{|@book{|@incollection{', text) # e.g. @article at the beginning of a line
  refs = [c[:c.find(',')] for c in chunks if c]
  set_refs = set(refs)
  if len(set_refs) < len(refs):
    duplicates = [ref for ref in refs if refs.count(ref) > 1]
    print("WARNING: your .bib file has duplicated entries: " + ", ".join(duplicates))
  # 
  for handle in existing_ref_handles.values():
    if handle not in set_refs:
      print("Missing reference handle " + handle + " in " + references_file)

