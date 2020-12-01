from org.python.core import ParserFacade
from org.python.core import CompileMode
from org.python.core import CompilerFlags
import sys

code = """
from ij import IJ, ImageJ

imp = IJ.getImage()

def setRoi(an_imp):
  ip = imp.getStack().getProcessor(3)
  pixels = ip.
"""

# Last line would fail compilation, so must not be included
code_without_last = "\n".join(code.split("\n")[:-2])


# The goal: discover the type of "ip" so that we can find out
# which methods we could autocomplete with:

try:
  mod = ParserFacade.parse(code_without_last,
                                CompileMode.exec,
                                "<none>",
                                CompilerFlags())
except:
  print sys.exc_info()

# mod.body is a list of parsed code blocks

# ImportFrom
importStatement = mod.body[0]
print importStatement.module # ij
print importStatement.names[0].name # IJ
print importStatement.names[1].name # ImageJ

# Assign
assign = mod.body[1]
print assign.targets[0].id # imp
print assign.value.func.value.id # IJ
print assign.value.func.attr # getImage
print assign.value.args # []

# FunctionDef
fn = mod.body[2]
print fn.name # setRoi
print fn.args.args[0].id # an_imp
fn_assign = fn.body[0]
print fn_assign.targets[0].id # ip
print fn_assign.value.func.value.func.value.id # imp
print fn_assign.value.func.value.func.attr # getStack
print fn_assign.value.func.attr # getProcessor
print fn_assign.value.args # [3]


# We don't know the class of ip, as it depends on
# a typeless argument of setRoi: that's why python developed annotation libraries like mypy
# But at least we have all the "Assign" entries for autocompletion


