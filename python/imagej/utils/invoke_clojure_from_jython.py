from ij import IJ
from java.lang import Object, Thread
cl = IJ.getClassLoader()
if cl is not None:
  Thread.currentThread().setContextClassLoader(cl)

from clojure.lang import Compiler, LineNumberingPushbackReader, LispReader, Symbol, Var, RT
from java.io import StringReader
from java.util.concurrent import Executors, Callable

exe = Executors.newFixedThreadPool(1)

class Task(Callable):
  def __init__(fn, *args):
    self.fn = fn
    self.args = args
  def call(self):
    return self.fn(*self.args)

def init():
  cl = IJ.getClassLoader()
  if cl is not None:
    Thread.currentThread().setContextClassLoader(cl)
  print "init", cl
  ns = RT.var("clojure.core", "*ns*")
  warn_on_reflection = RT.var("clojure.core", "*warn-on-reflection*")
  unchecked_math = RT.var("clojure.core", "*unchecked-math*")
  compile_path = RT.var("clojure.core", "*compile-path*")
  Var.pushThreadBindings(ns, ns.get(),
                         warn_on_reflection, warn_on_reflection.get(),
                         unchecked_math, unchecked_math.get(),
                         compile_path, "classes")
  in_ns = RT.var("clojure.core", "in-ns")
  refer = RT.var("clojure.core", "refer")
  in_ns.invoke(Symbol.intern("user"))
  refer.invoke(Symbol.intern("clojure.core"))


exe.submit(Task, init).get()

def parse(code):
  EOF = Object()
  ret = None
  thread = Thread.currentThread()
  # Evaluate all tokens in code, one by one
  while not thread.isInterrupted():
    r = LispReader.read(LineNumberingPushbackReader(StringReader(code)), False, EOF, False)
    if EOF == r:
      break
    ret = Compiler.eval(r)
  # Return the result of evaluating the last token
  return ret

def evaluate(code):
  return exe.submit(Task(parse, code)).get()


code = """
  (import [java.util.concurrent.Callable])
  (reify Callable
    (call [this]
      (+ 10 20))
"""

call = evaluate(code)
print call()
