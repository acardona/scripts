from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Regions
from net.imglib2.view import Views
from net.imglib2.type.logic import BitType
from collections import deque
from itertools import imap
from org.scijava.plugins.scripting.clojure import ClojureScriptEngine
from jarray import array
from time import time


# A binary image
img = ArrayImgs.bits([512, 512, 5])

center = img.dimension(0) / 2, img.dimension(1) / 2


def looping(img, center):
  for z in xrange(img.dimension(2)):
    radius = img.dimension(0) * 0.5 / (z + 1)
    circle = GeomMasks.openSphere(center, radius)
    # Works, explicit iteration of every pixel
    for t in Regions.sample(circle, Views.hyperSlice(img, 2, z)):
      t.setOne()

def dequeing(img, center):
  for z in xrange(img.dimension(2)):
    radius = img.dimension(0) * 0.5 / (z + 1)
    circle = GeomMasks.openSphere(center, radius)
    deque(imap(BitType.setOne, Regions.sample(circle, Views.hyperSlice(img, 2, z))), maxlen=0)


clj = ClojureScriptEngine()
code = """
(import '(net.imglib2 IterableInterval RandomAccessibleInterval Cursor)
        '(net.imglib2.roi Regions Mask RealMask)
        '(net.imglib2.roi.geom.real OpenWritableSphere)
        '(net.imglib2.roi.geom GeomMasks)
        '(net.imglib2.view Views)
        '(net.imglib2.type.logic BitType))
(defn setOne [^RandomAccessibleInterval rai
              ^doubles center]
  (doseq [z (range (.numDimensions rai))] ; can't primitive type-hint a local
      (let [radius (/ (* (.dimension rai 0) 0.5) (+ z 1)) ; can't type-hint local
            ^IterableInterval sphere (GeomMasks/openSphere center radius)
            ^IterableInterval region (Regions/sample sphere (Views/hyperSlice rai 2 z))]
        (loop [^Cursor c (.cursor region)]
          (when (.hasNext c)
            (let [^BitType t (.next c)] ; without this, ~15x slower for (.setOne (.next c))
              (.setOne t)
              (recur c)))))))

        ; Should work but doesn't: paints only some lines within the circle
        ; (doseq [^BitType t region]
        ;  (.setOne t)))))
"""
var = clj.eval(code) # returns a clojure.lang.Var
clj_fn = var.get() # returns a clojure.lang.AFunction
print clj_fn  

n_iterations = 4

for i in range(n_iterations):
  t0 = time()
  clj_fn.invoke(img, array(center, 'd'))
  t1 = time()
  print "Clojure", t1 - t0  # 0.03 to 0.07

for i in range(n_iterations):
  t0 = time()
  dequeing(img, center)
  t1 = time()
  print "deque", t1 - t0  # 0.17 to 0.18: 2x to 3x slower than clojure

for i in range(n_iterations):
  t0 = time()
  looping(img, center)
  t1 = time()
  print "loop", t1 - t0  # 0.19 to 0.22



IL.wrap(img, "bit img").show()