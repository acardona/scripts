from __future__ import print_function
from synchronize import make_synchronized
from java.util.concurrent import Callable, Future, Executors, ThreadFactory, TimeUnit
from java.util.concurrent.atomic import AtomicInteger
from java.lang.reflect.Array import newInstance as newArray
from java.lang import Runtime, Thread, Double, Float, Byte, Short, Integer, Long, Boolean, Character, System, Runnable
from net.imglib2.realtransform import AffineTransform3D
from net.imglib2.view import Views
from java.util import LinkedHashMap, Collections, LinkedList, HashMap
from java.lang.ref import SoftReference
from java.util.concurrent.locks import ReentrantLock


printService = Executors.newSingleThreadScheduledExecutor()
msgQueue = Collections.synchronizedList(LinkedList()) # synchronized

def printMsgQueue():
  while not msgQueue.isEmpty():
    try:
      print(msgQueue.pop())
    except:
      System.out.println(str(sys.exc_info()))

printService.scheduleWithFixedDelay(printMsgQueue, 500, 500, TimeUnit.MILLISECONDS)

def syncPrintQ(msg):
  """ Synchronized access to python's built-in print function.
      Messages are queued and printed every 0.5 seconds by a scheduled executor service.
  """
  msgQueue.insert(0, msg)


@make_synchronized
def syncPrint(msg):
  """ Synchronized access to python's built-in print function. """
  print(msg)

class Getter(Future):
  """ A simulated Future that is ready to deliver its result.
      Does not implement get(self, timeout, unit) as python
      does not support multiple method arity. """
  def __init__(self, ob):
    self.ob = ob
  def get(self):
    return self.ob
  def cancel(self, mayInterruptIfRunning):
    return True
  def isCancelled(self):
    return False
  def isDone():
    return True


class Task(Callable, Runnable):
  """ A wrapper for executing functions in concurrent threads. """
  def __init__(self, fn, *args, **kwargs):
    self.fn = fn
    self.args = args
    self.kwargs = kwargs
  def call(self):
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
      return None
    return self.fn(*self.args, **self.kwargs)
  def run(self):
    self.call()

class TimeItTask(Callable, Runnable):
  """ A wrapper for executing functions in concurrent threads,
      where the call method returns a tuple: the result, and the execution time in miliseconds;
      and the run method prints out the execution time. """
  def __init__(self, fn, *args, **kwargs):
    self.fn = fn
    self.args = args
    self.kwargs = kwargs
  def call(self):
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
      return None
    t0 = System.nanoTime()
    r = self.fn(*self.args, **self.kwargs)
    return r, (System.nanoTime() - t0) / 1000000.0
  def run(self):
    r, t = self.call()
    syncPrintQ("TimeItTask: %f ms" % t)
    

def ndarray(classtype, dimensions):
    """ E.g. for a two-dimensional native double array, use:
        
          arr = ndarray(Double.TYPE, [3, 4])
        
        which is equivalent to, using the jython jarray library:
            
          arr = array((zeros(4, 'd'), zeros(4, 'd'), zeros(4, 'd')), Class.forName("[D"))

        but here the native array is created via java.lang.reflect.Array.newInstance(class, dimensions).
        """ 
    return newArray(classtype, dimensions)


__nativeClass = {'c': Character, 'b': Byte, 's': Short, 'h': Short,
              'i': Integer, 'l': Long, 'f': Float, 'd': Double, 'z': Boolean}

def nativeArray(stype, dimensions):
    """ Create a native java array such as a double[3][4] like:
    arr = nativeArray('d', (3, 4))

    stype is one of:
    'c': char
    'b': byte
    's': short
    'h': short (like in the jarray package)
    'i': integer
    'l': long
    'f': float
    'd': double
    'z': boolean
    """
    return newArray(__nativeClass[stype].TYPE, dimensions)


class ThreadFactorySameGroup(ThreadFactory):
  def __init__(self, name):
    self.name = name
    self.group = Thread.currentThread().getThreadGroup()
    self.counter = AtomicInteger(0)
  def newThread(self, runnable):
    title = "%s-%i" % (self.name, self.counter.incrementAndGet())
    t = Thread(self.group, runnable, title)
    t.setPriority(Thread.NORM_PRIORITY)
    return t

def newFixedThreadPool(n_threads=0, name="jython-worker"):
  """ Return an ExecutorService whose Thread instances belong
      to the same group as the caller's Thread, and therefore will
      be interrupted when the caller is.
      n_threads: number of threads to use.
                 If zero, use as many as available CPUs.
                 If negative, use as many as available CPUs minus that number,
                 but at least one. """
  if n_threads <= 0:
    n_threads = max(1, Runtime.getRuntime().availableProcessors() + n_threads)
  return Executors.newFixedThreadPool(n_threads, ThreadFactorySameGroup(name))

def numCPUs():
  return Runtime.getRuntime().availableProcessors()

class ParallelTasks:
  def __init__(self, name, exe=None):
    self.exe = exe if exe else newFixedThreadPool(name=name)
    self.futures = []
  def add(self, fn, *args, **kwargs):
    future = self.exe.submit(Task(fn, *args, **kwargs))
    self.futures.append(future)
    return future
  def chunkConsume(self, chunk_size, tasks):
    """ 
    chunk_size: number of tasks to submit prior to start waiting and yielding their results.
    tasks: a generator (or an iterable) with Task instances.
    Returns a generator with the results.
    """
    for task in tasks:
      self.futures.append(self.exe.submit(task))
      if len(self.futures) > chunk_size:
        while len(self.futures) > 0:
          yield self.futures.pop(0).get()
  def awaitAll(self):
    while len(self.futures) > 0:
      self.futures.pop(0).get()
  def generateAll(self):
    while len(self.futures) > 0:
      yield self.futures.pop(0).get()
  def destroy(self):
    self.exe.shutdownNow()
    self.exe = None
    self.futures = None


def timeit(n_iterations, fn, *args, **kwargs):
  times = []
  for i in xrange(n_iterations):
    t0 = System.nanoTime()
    imp = fn(*args, **kwargs)
    t1 = System.nanoTime()
    times.append(t1 - t0)
  print("min: %.2f ms, max: %.2f ms, mean: %.2f ms" % (min(times) / 1000000.0, max(times) / 1000000.0, sum(times)/(len(times) * 1000000.0)))


def affine3D(matrix):
  aff = AffineTransform3D()
  aff.set(*matrix)
  return aff


def cropView(img, minCoords, maxCoords):
  return Views.zeroMin(Views.interval(img, minCoords, maxCoords))



class LRUCache(LinkedHashMap):
  def __init__(self, max_entries, eldestFn=None):
    # initialCapacity 16 (the default)
    # loadFactor 0.75 (the default)
    # accessOrder True (default is False)
    super(LinkedHashMap, self).__init__(10, 0.75, True)
    self.max_entries = max_entries
    self.eldestFn = eldestFn
  def removeEldestEntry(self, eldest):
    if self.size() > self.max_entries:
      if self.eldestFn:
        self.eldestFn(eldest.getValue())
      return True

class SoftMemoize:
  def __init__(self, fn, maxsize=30):
    self.fn = fn
    # Synchronize map to ensure correctness in a multi-threaded application:
    # (I.e. concurrent threads will wait on each other to access the cache)
    self.m = Collections.synchronizedMap(LRUCache(maxsize, eldestFn=lambda ref: ref.clear()))
    self.locks = Collections.synchronizedMap(HashMap())

  @make_synchronized
  def getOrMakeLock(self, key):
    lock = self.locks.get(key)
    if not lock:
      # Cleanup locks
      for key in self.locks.keys(): # copy of the list of keys
        if not self.m.containsKey(key):
          del self.locks[key]
      """
      # Proper cleanup, but unnecessary to query queued threads
      # and it is useful to keep locks for existing keys
      for key, lock in self.locks.items(): # a copy
        if not lock.hasQueuedThreads():
          del self.locks[key]
      """
      # Create new lock
      lock = ReentrantLock()
      self.locks[key] = lock
    return lock

  def __call__(self, key):
    """ Locks on the key, and waits, when needing to execute the memoized function. """
    # Either not present, or garbage collector discarded it
    lock = self.getOrMakeLock(key)
    try:
      lock.lockInterruptibly()
      softref = self.m.get(key) # self.m is a synchronized map
      o = softref.get() if softref else None
      if o:
        return o
      # Invoke the memoized function
      o = self.fn(key)
      # Store return value wrapped in a SoftReference
      self.m.put(key, SoftReference(o))
      return o
    finally:
      lock.unlock()
