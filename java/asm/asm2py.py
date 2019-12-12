import sys, re

filename_in = sys.argv[1]
print("Processing file: " + filename_in)
filename_out = filename_in + ".py"

newClasses = set()
def captureNewClassname(matchobj):
  strings = matchobj.groups()
  if strings:
    newClasses.add(strings[1])
    return strings[1] + '('

with open(filename_in, 'r') as f_in:
    with open(filename_out, 'w') as f_out:
        for line in f_in:
            line = line.rstrip()
            # Remove curly braces from code blocks
            if 0 == len(line) or "{" == line or "}" == line:
                f_out.write("\n")
                continue
            # Remove ending semicolon
            if ";" == line[-1]:
                line = line[:-1]
            # NOTE: matching regex must escape literal parentheses and square brackets, whereas replacement string doesn't. The leading 'r' for the replacement string enables replacement groups like \1, \2 etc.
            # Fix variable declarations for Label
            line = re.sub(r"Label ([a-z][a-z0-9]+) = new Label", r"\1 = Label", line)
            # Add Opcode namespace
            line = re.sub(r"(Insn|Frame|Method|Field)\(([A-Z_][A-Z_0-9]+?[,\) ])", r"\1(Opcodes.\2", line)
            line = re.sub(r"([+,]) ([A-Z_][A-Z_0-9]+?[,\) ])", r"\1 Opcodes.\2", line)
            # Rename nulls
            line = re.sub(r"\bnull\b", r"None", line)
            # Fix arrays
            line = re.sub(r"new ([A-Z][a-zA-Z0-9]*)\[\] \{(.*?)\}", r"[\2]", line)
            # Fix references to inner classes: replace $ with _
            line = re.sub(r"\$(\d+\")", r"_\1", line)
            # Fix booleans
            line = re.sub(r"\bfalse\b", r"False", line)
            line = re.sub(r"\btrue\b", r"True", line)
            # Remove 'new'
            line = re.sub(r"(\bnew\b) ([a-zA-Z0-9_]+)\(", captureNewClassname, line)
            #
            f_out.write(line + "\n")

print("---> 'new' invocations on: %s" % ", ".join(newClasses))

