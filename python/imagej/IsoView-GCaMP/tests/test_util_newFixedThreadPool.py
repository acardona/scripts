import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")

from java.lang import Runtime
from lib.util import newFixedThreadPool, Task

def doSomething(number):
  return number + 10

exe = newFixedThreadPool(-5)

print "available:", Runtime.getRuntime().availableProcessors()
print "n_threads:", exe.getCorePoolSize()

try:
  futures = [exe.submit(Task(doSomething, i)) for i in xrange(10)]

  for f in futures:
    print f.get()
finally:
  exe.shutdown()