# Declare and run a clojure function from jython
# Albert Cardona 2020-02-17


from org.scijava.plugins.scripting.clojure import ClojureScriptEngine
from ij import IJ

clj = ClojureScriptEngine()

code = """
(import ij.ImagePlus)
(defn meanPixelIntensity [^ImagePlus imp]
  (let [^floats pixels (.. imp getProcessor getPixels)]
    (/ (areduce pixels i sum 0.0 (+ sum (aget pixels i)))
       (count pixels))))
"""

var = clj.eval(code) # returns a clojure.lang.Var
fn = var.get() # returns a clojure.lang.AFunction

# ASSUMES an 32-bit image is open
print fn.invoke(IJ.getImage())