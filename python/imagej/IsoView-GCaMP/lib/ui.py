import os, sys
from time import time
from lib.util import syncPrintQ, printException, newFixedThreadPool
from lib.converter import createConverter, convert
from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.display.imagej import ImageJVirtualStack
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.util import ImgUtil
from net.imglib2.view import Views, TransformedRandomAccessible, MixedTransformView
from bdv.util import BdvFunctions, Bdv
from ij import ImagePlus, CompositeImage, VirtualStack
from ij.process import FloatProcessor
from java.awt import Dimension
from java.awt.event import KeyAdapter, KeyEvent, WindowAdapter, MouseAdapter
from java.lang import Number, Runtime, Thread
from java.util import Comparator
from java.util.concurrent import Callable, Future, Executors
from javax.swing import ListSelectionModel, JScrollPane, JFrame, JTable, JLabel, SwingUtilities, JPopupMenu, JMenuItem
from javax.swing.table import AbstractTableModel, TableRowSorter, DefaultTableCellRenderer
from javax.swing.event import ListSelectionListener
from ij import IJ, ImagePlus, ImageStack, VirtualStack
from ij.io import FileSaver
from net.imglib2.img.display.imagej import ImageJVirtualStackUnsignedByte
from net.imglib2.converter import TypeIdentity
from java.awt.event import ActionListener



def wrap(img, title="", n_channels=1):
  """ Like ImageJFunctions.wrap but, when n_channels=1 (the default),
      then a new dimension of size 1 is inserted at position 2 to prevent the Z axis
      from showing as the channels axis.
      To enable ImageJFunctions.wrap default behavior, set n_channels to a value other than 1. """
  if 1 == n_channels:
    # Append a dimension of size 1 at the end
    # and permute it iteratively so that it becomes the channels dimension (d=2)
    img = Views.addDimension(img, 1, 1)
    d = img.numDimensions() -1 # starts with the last: the new one of size 1
    while d > 2:
      img = Views.permute(img, d, d -1)
      d -= 1
  #
  return IL.wrap(img, title)


def grabImg(imp):
  """ Return the ImgLib2 image wrapped by the ImagePlus imp. """
  stack = imp.getStack() # an ImageJVirtualStackUnsignedShort or similar (for each pixel type) which extends ImageJVirtualStack which has a source field with the ImgLib2 RandomAccessibleInterval instance
  print type(stack)

  if isinstance(stack, ImageJVirtualStack):
    # Make the private field accessible
    f = ImageJVirtualStack.getDeclaredField("source")
    f.setAccessible(True)
    img = f.get(stack)
  else:
    img = stack
    
  while isinstance(img, TransformedRandomAccessible) or isinstance(img, MixedTransformView):
    img = img.getSource()
  
  return img


def showAsStack(images, title=None, show=True):
  if not title:
    title = "Stack of %i images" % len(images)
  imp = wrap(Views.stack(images), title)
  if show:
    imp.show()
  return imp


def showInBDV(images, names=None, bdv=None):
  if not names:
    names = ["img%i" % i for i in xrange(len(images))]
  if not bdv:
    bdv = BdvFunctions.show(images[0], names[0])
    images, names = images[1:], names[1:]
  for img, name in izip(images, names):
    BdvFunctions.show(img, name, Bdv.options().addTo(bdv))
  #
  return bdv


def showStack(img, title="", proper=True, n_channels=1):
  # IL.wrap fails: shows slices as channels, and channels as frames
  if not proper:
    imp = IL.wrap(img, title)
    imp.show()
    return imp
  # Proper sorting of slices, channels and frames
  imp = wrap(img, title=title, n_channels=n_channels)
  comp = CompositeImage(imp, CompositeImage.GRAYSCALE if 1 == n_channels else CompositeImage.COLOR)
  comp.show()
  return comp


def showBDV(img, title="", bdv=None):
  if bdv:
    BdvFunctions.show(img, title, Bdv.options().addTo(bdv))
    return bdv
  return BdvFunctions.show(img, title)


class StacksAsChannels(VirtualStack):
  def __init__(self, stacks):
    super(VirtualStack, self).__init__(stacks[0].getWidth(), stacks[0].getHeight(),
                                       max(stack.size() for stack in stacks) * len(stacks))
    self.stacks = stacks # one per channel
  def getPixels(self, i):
    return getProcessor(i).getPixels()
  def getProcessor(self, i):
    channel = (i-1) % len(self.stacks)
    z = (i-1) / len(self.stacks)
    stack = self.stacks[channel]
    return stack.getProcessor(min(z + 1, stack.size()))
    
def showAsComposite(images, title="Composite", show=True):
  imps = []
  # Collect all images as ImagePlus, checking that they have the same XY dimensions.
  # (Z doesn't matter)
  dimensions = None
  for img in images:
    if isinstance(img, ImagePlus):
      imps.append(img)
    else:
      imps.append(IL.wrap(img, ""))
    if not dimensions:
      dimensions = [imps[-1].getWidth(), imps[-1].getHeight()]
    else:
      if imps[-1].width != dimensions[0] or imps[-1].getHeight() != dimensions[1]:
        print "asComposite: dimensions mistach."
        return
  imp = ImagePlus(title, StacksAsChannels([imp.getStack() for imp in imps]))
  imp.setDimensions(len(imps), max(imp.getStack().getSize() for imp in imps), 1)
  comp = CompositeImage(imp, CompositeImage.COMPOSITE)
  if show:
    comp.show()
  print imp.getNChannels(), imp.getNSlices(), imp.getNFrames(), "but imps: ", len(imps)
  return comp


class ViewFloatProcessor(FloatProcessor):
  """
  A 2D FloatProcessor whose float[] pixel array is populated from the pixels within
  an interval on a source 3D RandomAccessibleInterval at a specified indexZ (the section index).
  The interval and indexZ are editable via the translate method.
  """
  def __init__(self, img3D, interval2D, indexZ):
    self.img3D = img3D
    self.interval2D = interval2D
    self.indexZ = indexZ
    super(FloatProcessor, self).__init__(interval2D.dimension(0), interval2D.dimension(1))
    self.updatePixels()
    
  def translate(self, dx, dy, dz):
    # Z within bounds
    self.indexZ += dz
    self.indexZ = min(self.img3D.dimension(2) -1, max(0, self.indexZ))
    # X, Y can be beyond bounds
    self.interval2D = FinalInterval([self.interval2D.min(0) + dx,
                                     self.interval2D.min(1) + dy],
                                    [self.interval2D.max(0) + dx,
                                     self.interval2D.max(1) + dy])
    self.updatePixels()
    return self.interval2D.min(0), self.interval2D.min(1), self.indexZ
  
  def updatePixels(self):
    # Copy interval into pixels
    view = Views.interval(Views.extendZero(Views.hyperSlice(self.img3D, 2, self.indexZ)), self.interval2D)
    aimg = ArrayImgs.floats(self.getPixels(), [self.interval2D.dimension(0), self.interval2D.dimension(1)])
    ImgUtil.copy(view, aimg)


class SourceNavigation(KeyAdapter):
  def __init__(self, translatable, imp, shift=100, alt=10):
    """
      translatable: an object that has a "translate" method with 3 coordinates as arguments
      imp: the ImagePlus to update
      shift: defaults to 100, when the shift key is down, move by 100 pixels
      alt: defaults to 10, when the alt key is down, move by 10 pixels
      If both shift and alt are down, move by shift*alt = 1000 pixels by default.
    """
    self.translatable = translatable
    self.delta = {KeyEvent.VK_UP: (0, -1, 0),
                  KeyEvent.VK_DOWN: (0, 1, 0),
                  KeyEvent.VK_RIGHT: (1, 0, 0),
                  KeyEvent.VK_LEFT: (-1, 0, 0),
                  KeyEvent.VK_COMMA: (0, 0, -1),
                  KeyEvent.VK_PERIOD: (0, 0, 1),
                  KeyEvent.VK_LESS: (0, 0, -1),
                  KeyEvent.VK_GREATER: (0, 0, 1),
                  KeyEvent.VK_PAGE_DOWN: (0, 0, -1),
                  KeyEvent.VK_PAGE_UP: (0, 0, 1)}
    self.shift = shift
    self.alt = alt
    self.imp = imp
  
  def keyPressed(self, event):
    try:
      dx, dy, dz = self.delta.get(event.getKeyCode(), (0, 0, 0))
      if dx + dy + dz == 0:
        return
      syncPrintQ("Translating source")
      if event.isShiftDown():
        dx *= self.shift
        dy *= self.shift
        dz *= self.shift
      if event.isAltDown():
        dx *= self.alt
        dy *= self.alt
        dz *= self.alt
      syncPrintQ("... by x=%i, y=%i, z=%i" % (dx, dy, dz))
      x, y, z = self.translatable.translate(dx, dy, dz)
      IJ.showStatus("[x=%i y=%i z=%i]" % (x, y, z+1)) # 1-based stack index
      self.imp.updateAndDraw()
      event.consume()
    except:
      printException()
    

def navigate2DROI(img, interval, indexZ=0, title="ROI"):
  """
     Use a FloatProcessor to visualize a 2D slice of a 3D image of any pixel type.
     Internally, uses a ViewFloatProcessor with an editable Interval.
     Here, a SourceNavigation (a KeyListener) enables editing the Interval
     and therefore the FloatProcessor merely shows that interval of the source img.
     
     img: the source 3D RandomAccessibleInterval.
     interval: the initial interval of img to view. Must be smaller than 2 GB.
     indexZ: the initial Z index to show.
     title: the name to give the ImagePlus.
  """
  img = convert(img, FloatType)
  vsp = ViewFloatProcessor(img, interval, indexZ)
  imp = ImagePlus(title, vsp)
  imp.show()
  canvas = imp.getWindow().getCanvas()
  # Place the SourceNavigation KeyListener at the top of the list of KeyListener instances
  kls = canvas.getKeyListeners()
  for kl in kls:
    canvas.removeKeyListener(kl)
  canvas.addKeyListener(SourceNavigation(vsp, imp))
  for kl in kls:
    canvas.addKeyListener(kl)
  return imp


class ExecutorCloser(WindowAdapter):
  def __init__(self, exe):
    self.exe = exe
  def windowClosing(self, event):
    try:
      self.exe.shutdownNow()
    except:
      printException()


class MenuItemListener(ActionListener):
  def __init__(self, fn, *args, **kwargs):
    self.fn = fn
    self.args = args
    self.kwargs = kwargs
  def actionPerformed(self, event):
    self.fn(*self.args, **self.kwargs)


class RowClickListener(MouseAdapter, ListSelectionListener):
  def __init__(self, table,
               right_click_fns={},
               double_click_fn=None):
    self.table = table
    self.right_click_fns = right_click_fns
    self.double_click_fn = double_click_fn
    self.firstIndex = -1
    self.lastIndex = -1
  
  def mousePressed(self, event):
    if 2 == event.getClickCount():
      # Open the raw images of the montage at that slice
      rowIndex = event.getSource().rowAtPoint(event.getPoint()) # TODO could use self.firstIndex or the whole range
      if self.double_click_fn:
        try:
          self.double_click_fn(self.table.getModel(), rowIndex)
        except:
          syncPrintQ(sys.exc_info())
  
  def mouseReleased(self, event):
    if 1 == event.getClickCount() and SwingUtilities.isRightMouseButton(event):
      popup = JPopupMenu()
      rowIndex = event.getSource().rowAtPoint(event.getPoint())
      
      for title, fn in self.right_click_fns:
        item = JMenuItem(title)
        item.addActionListener(MenuItemListener(fn, self.table.getModel(), rowIndex))
        popup.add(item)
      popup.show(event.getComponent(), event.getX(), event.getY())
  
  def valueChanged(self, event):
    if event.getValueIsAdjusting():
      return
    self.firstIndex = event.getFirstIndex()
    self.lastIndex = event.getLastIndex()
  

class DataTable(AbstractTableModel):
  """ Assumes all rows contain numbers. """
  def __init__(self, rows, column_names=None, dataType=Number, onCellClickFn=None, onRowClickFn=None):
    """
       rows: a list of lists of numbers.
       column_names: optional, one string per column.
       dataType: defaults to Number, can be a list of one class per column.
       onCellClickFn: a function that will be run when a cell is clicked, with 3 arguments: row index, column index, and the cell value.
       onRowClickFn: a function that will be run when a cell is clicked, with the entire row of values provided as arguments.
    """
    self.column_names = column_names if column_names is not None else map(str, xrange(1, len(rows[0]) + 1))
    self.rows = rows
    try:
      # Check if dataType is iterable, like a list
      iter(dataType)
      self.dataType = dataType
    except:
      # Not iterable: a Number, String, etc. so all columns have the same
      self.dataType = [dataType for _ in xrange(len(rows[0]))]
    self.onCellClickFn = onCellClickFn
    self.onRowClickFn = onRowClickFn
  def getColumnName(self, col):
    return self.column_names[col]
  def getColumnClass(self, col): # for e.g. proper numerical sorting
    return self.dataType[col]
  def getRowCount(self):
    return len(self.rows)
  def getColumnCount(self):
    return len(self.column_names)
  def getValueAt(self, row, col):
    return self.rows[row][col]
  def isCellEditable(self, row, col):
    # Activated on click
    if self.onCellClickFn:
      self.onCellClickFn(row, col, self.rows[row][col])
    if self.onRowClickFn:
      self.onRowClickFn(*self.rows[row])
    return False # none editable
  def setValueAt(self, value, row, col):
    pass # none editable


def showTable(rows, title="Table", column_names=None, dataType=Number, width=400, height=500, showTable=True,
              windowClosing=None, onCellClickFn=None, onRowClickFn=None,
              singleBlockSelection=True,
              renderCenteredColumns=[], renderRightColumns=[]):
  """
     rows: list of lists of numbers.
     title: for the JFrame
     column_names: list of strings, or None
     width: defaults to 400 px
     height: defaults to 500 px
     showTable: whether to show the JFrame.
     windowClosing: an optional function to execute when the table's JFrame is closed.
     onClickCellFn: an optional function to execute when a table's cell is clicked, and receiving 3 args: row index, col index, cell value.
     onRowCellFn: an optinal function to execute when a table's row is clicked, and receiving as args the whole row.
     
     return: a tuple with the JTable and the JFrame
  """
  table_data = DataTable(rows, column_names=column_names, onCellClickFn=onCellClickFn, onRowClickFn=onRowClickFn)
  table = JTable(table_data)
  table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION)
  #table.setAutoCreateRowSorter(True) # to sort the view only, not the data in the underlying TableModel
  sorter = TableRowSorter(table_data)
  for i in xrange(len(column_names)):
    sorter.setComparator(i, Comparator.naturalOrder())
  table.setRowSorter(sorter)
  
  table.setAutoCreateRowSorter(True) # to sort the view only, not the data in the underlying TableModel
  
  if singleBlockSelection:
    table.setRowSelectionAllowed(True)
    table.setSelectionMode(ListSelectionModel.SINGLE_INTERVAL_SELECTION)
  
  centerRenderer = DefaultTableCellRenderer();
  for i in renderCenteredColumns:
    centerRenderer.setHorizontalAlignment(JLabel.CENTER)
    table.getColumnModel().getColumn(i).setCellRenderer(centerRenderer)
  for i in renderRightColumns:
    centerRenderer.setHorizontalAlignment(JLabel.RIGHT)
    table.getColumnModel().getColumn(i).setCellRenderer(centerRenderer)
  
  
  frame = JFrame(title) if windowClosing is None else JFrame(title, windowClosing=windowClosing)
  jsp = JScrollPane(table)
  jsp.setMinimumSize(Dimension(400, 500))
  jsp.setPreferredSize(Dimension(width, height))
  frame.getContentPane().add(jsp)
  
  def show():
    frame.pack()
    frame.setVisible(True)
    
  if showTable:
    SwingUtilities.invokeLater(show)

  return table, frame


def addWindowListener(window, fn, methods=["windowClosed"]):
  """ window: the java.awt.Window onto which add a WindowAdapter.
      fn: the function to run when any of the listener methods is triggered.
          Note it gets an event as argument.
      methods: defaults to a list with a single method name, "windowClosed".
               Add others like windowOpened, windowClosing, windowGainedFocus, etc.
               as defined in the convenience abstract class java.awt.WindowAdapter.
  """
  fnl = lambda self, event: fn(event)
  listenerClass = type("MyListenOnClose-%i" % int(time()*100), # unique class name
                       (WindowAdapter,),
                       {method: fnl for method in methods })
  listener = listenerClass()
  window.addWindowListener(listener)
  return listener



class CopyStackSlice(Callable):
  def __init__(self, stack, slice_index, shallow=False, scale=1.0, roi=None):
    self.stack = stack
    self.slice_index = slice_index # 1-based
    self.shallow = shallow
    self.scale = scale
    self.roi = roi
  def call(self):
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
      return None
    ip = self.stack.getProcessor(self.slice_index)
    if self.roi:
      ip.setRoi(self.roi)
      ip = ip.crop()
    if self.scale < 1.0:
      return ip.resize(int(ip.getWidth() * self.scale + 0.5),
                       int(ip.getHeight() * self.scale + 0.5),
                       True) # averaging
    return ip if self.shallow or self.roi else ip.duplicate()

# Duplicate a stack in parallel
def duplicateInParallel(imp=None, slices=None, n_threads=0, shallow=False, show=True, scale=1.0, roi=None):
  """ imp: defaults to None, meaning get the current image.
      slices: defaults to None, meaning all. Otherwise a list of 1-based indices.
      n_threads: defaults to 0, meaning as many as possible.
      shallow: defaults to False, meaning don't share the pixel data.
  """
  imp = imp if imp else IJ.getImage()
  slices = slices if slices else range(1, imp.getNSlices() + 1)
  stack = imp.getStack()
  exe = newFixedThreadPool(n_threads=n_threads if n_threads > 0 else min(Runtime.getRuntime().availableProcessors(), stack.getSize()), name="duplicate-stack")
  try:
    stack2 = ImageStack() # dimensions will be set by the first slice added
    futures = [(i, exe.submit(CopyStackSlice(stack, i, shallow=shallow, scale=scale, roi=roi))) for i in slices]
    for i, fu in futures:
      t = Thread.currentThread()
      if t.isInterrupted() or not t.isAlive():
        syncPrintQ("Interrupted duplicateInParallel.")
        return
      label = None
      try:
        label = stack.getSliceLabel(i)
      except:
        syncPrintQ("Failed to retrieve slice labet at section %i" % i)
      try:
        stack2.addSlice(label if label else str(i), fu.get())
      except:
        syncPrintQ("Failed to add slice for section %i" % i)
    imp = ImagePlus("%s - [%i, %i]" % (imp.getTitle(), slices[0], slices[-1]), stack2)
    if show:
      imp.show()
    return imp
  finally:
    exe.shutdown()

class SaveStackSlice(Callable):
  def __init__(self, stack, slice_index, targetDir, scale=1.0, incremental=True, parentThread=None):
    self.stack = stack
    self.slice_index = slice_index # 1-based
    self.targetDir = targetDir
    self.scale = scale
    self.incremental = incremental
    self.parentThread = parentThread
  def call(self):
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
      return False
    if self.parentThread.isInterrupted() or not self.parentThread.isAlive():
      self.parentThread = None
      return False
    path = os.path.join(self.targetDir, "%i.tif" % self.slice_index)
    if self.incremental and os.path.exists(path):
      return True
    ip = self.stack.getProcessor(self.slice_index)
    if self.scale < 1.0:
      ip = ip.resize(int(ip.getWidth() * self.scale + 0.5),
                     int(ip.getHeight() * self.scale + 0.5),
                     True) # averaging
    syncPrintQ("Saving slice %i" % self.slice_index)
    return FileSaver(ImagePlus(str(self.slice_index), ip)).saveAsTiff(path)

# Duplicate a stack in parallel
def saveInParallel(targetDir, imp=None, slices=None, n_threads=0, show=True, scale=1.0, incremental=True):
  """ imp: defaults to None, meaning get the current image.
      slices: defaults to None, meaning all. Otherwise a list of 1-based indices.
      n_threads: defaults to 0, meaning as many as possible.
      shallow: defaults to False, meaning don't share the pixel data.
  """
  if not os.path.exists(targetDir):
    os.makeDirs(targetDir)
  imp = imp if imp else IJ.getImage()
  slices = slices if slices else range(1, imp.getNSlices() + 1)
  stack = imp.getStack()
  exe = newFixedThreadPool(n_threads=n_threads if n_threads > 0 else min(Runtime.getRuntime().availableProcessors(), stack.getSize()), name="duplicate-stack")
  launcher_thread = Thread.currentThread()
  try:
    futures = [(i, exe.submit(SaveStackSlice(stack, i, targetDir, scale=scale, incremental=incremental, parentThread=launcher_thread))) for i in slices]
    for i, fu in futures:
      t = Thread.currentThread()
      if t.isInterrupted() or not t.isAlive():
        syncPrintQ("Interrupted saveInParallel.")
        return
      if not fu.get():
        syncPrint("Failed to save slice %i" % i)
    if show:
      vs = VirtualStack(int(imp.getWidth() * scale + 0.5),
                        int(imp.getHeight() * scale + 0.5),
                        None,
                        targetDir)
      for i in slices:
        vs.addSlice("%i.tif" % i)
      imp = ImagePlus(imp.getTitle() + " scale: " + str(scale), vs)
      imp.show()
      return imp
    return None
  finally:
    exe.shutdown()

# A VirtualStack view of an ImgLib2 8-bit img that supports stack labels
class VirtualStack8bit(ImageJVirtualStackUnsignedByte):
  def __init__(self, img3D, labelsFn=None):
    super(VirtualStack8bit, self).__init__(img3D, TypeIdentity())
    self.labels = {}
    self.labelsFn = labelsFn
  def setSliceLabel(self, label, n):
    self.labels[n] = label
  def getSliceLabel(self, n):
    if n in self.labels:
      return self.labels[n]
    if self.labelsFn:
      return self.labelsFn(n)
    return str(n)

def wrap8bit(img3D, title="", labelsFn=None):
  """ Return a 3D ImagePlus with a VirtualStack that reads from the 3-dimensional img3D. """
  return ImagePlus(title, VirtualStack8bit(img3D, labelsFn=labelsFn))

