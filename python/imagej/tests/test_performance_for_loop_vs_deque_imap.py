# Test looping pixels
from net.imglib2.img.array import ArrayImgs
from net.imglib2.view import Views
from itertools import imap
from collections import deque
from net.imglib2.type.numeric.integer import UnsignedByteType, GenericByteType
from java.lang import System


def test_for_loop(img):
  for t in img:
    t.setOne()


def test_deque_imap(img):
  deque(imap(GenericByteType.setOne, img), maxlen=0)

def test_deque_generator(img):
  deque(t.setOne() for t in img, maxlen=0)

def run(fn, args, msg="", n_iterations=20):
  timings = []
  for i in xrange(n_iterations):
    t0 = System.nanoTime()
    fn(*args)
    t1 = System.nanoTime()
    timings.append(t1 - t0)

  minimum = min(timings)
  maximum = max(timings)
  average = sum(timings) / float(len(timings))
  
  print msg, "min:", minimum, "max:", maximum, "avg:", average


img = ArrayImgs.unsignedBytes([100, 100, 100])

run(test_for_loop, [img], msg="for loop:")

run(test_deque_imap, [img], msg="deque imap:")

run(test_deque_generator, [img], msg="deque generator:")

# Results: same
# for loop: min: 405987873 max: 480388258 avg: 438218245.25
# deque imap: min: 413622007 max: 472052359 avg: 433818125.35

