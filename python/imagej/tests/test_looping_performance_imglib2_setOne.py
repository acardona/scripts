from net.imglib2.img.array import ArrayImgs
from time import time
from itertools import imap
from collections import deque
from net.imglib2.util.Util import getTypeFromInterval
from org.scijava.plugins.scripting.clojure import ClojureScriptEngine
from net.imglib2.type.numeric.integer import UnsignedByteType


img = ArrayImgs.unsignedBytes([512, 512, 5])

n_iterations = 4

# Test 1: for loop
for i in xrange(n_iterations):
  t0 = time()
  for t in img.cursor():
    t.setOne()
  t1 = time()
  print "looping:", t1 - t0 # About 1.1 seconds


# Test 2: imap + deque with maxlen=0
for i in xrange(n_iterations):
  t0 = time()
  # Performance almost as bad as the for loop
  #deque(imap(lambda t: t.setOne(), img.cursor()), maxlen=0)
  # Discover the type and grab it's setOne method
  setter = getattr(getTypeFromInterval(img).getClass(), "setOne")
  deque(imap(setter, img.cursor()), maxlen=0)
  # Just as slow as above, but less general
  #deque(imap(UnsignedByteType.setOne, img.cursor()), maxlen=0)
  t1 = time()
  print "deque:", t1 - t0 # About 0.6 seconds


# Test 3: with clojure
clj = ClojureScriptEngine()
type_class = getTypeFromInterval(img).getClass().getName()
code = """
(import '(net.imglib2 IterableInterval Cursor))
(defn setOne [^IterableInterval img]
  (loop [^Cursor c (.cursor img)]
    (when (.hasNext c)
      (let [^%s t (.next c)]
        (.setOne t)
        (recur c)))))
""" % type_class
var = clj.eval(code) # returns a clojure.lang.Var
clj_fn = var.get() # returns a clojure.lang.AFunction

for i in xrange(n_iterations):
  t0 = time()
  clj_fn.invoke(img)
  t1 = time()
  print "clojure:", t1 - t0 # About 1 to 10 milliseconds !!!
