from net.imglib2.img.display.imagej import ImageJFunctions as IL, ImageJVirtualStackUnsignedShort
from net.imglib2.view import Views
from bdv.util import BdvFunctions, Bdv
from ij import ImagePlus, CompositeImage, VirtualStack, ImageListener
from java.awt.event import KeyEvent, KeyAdapter, MouseWheelListener, WindowAdapter
from javax.swing import JPanel, JLabel, JTextField, JButton, JOptionPane, JFrame
from java.awt import GridBagLayout, GridBagConstraints
from jarray import zeros
import sys


def wrap(img, title="", n_channels=1):
  """ Like ImageJFunctions.wrap but properly choosing the number of channels, slices and frames. """ 
  stack = ImageJVirtualStackUnsignedShort.wrap(img)
  imp = ImagePlus(title, stack)
  n = img.numDimensions()
  n_slices = img.dimension(2) / n_channels if n > 2 else 1
  n_frames = img.dimension(3) if n > 3 else 1
  imp.setDimensions(n_channels, n_slices, n_frames)
  imp.setOpenAsHyperStack(True)
  return imp
  

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


class MatrixTextFieldListener(KeyAdapter, MouseWheelListener, ImageListener):
  def __init__(self, affine, dimension, textfield, imp):
    self.affine = affine
    self.dimension = dimension
    self.textfield = textfield
    self.imp = imp

  def translate(self, value):
    t = self.affine.getTranslation() # 3-slot double array, a copy
    t[self.dimension] = value
    try:
      self.affine.setTranslation(t) # will throw a RuntimeError when not invertible
    except:
      print sys.exc_info()
      return False
    #self.imp.updateAndDraw() # fails for virtual stacks
    # A solution that works for virtual stacks, by Wayne Rasband:
    minimum, maximum = self.imp.getDisplayRangeMin(), self.imp.getDisplayRangeMax()
    self.imp.setProcessor(self.imp.getStack().getProcessor(self.imp.getCurrentSlice()))
    self.imp.setDisplayRange(minimum, maximum)
    return True

  def parse(self):
    try:
      return float(self.textfield.getText())
    except:
      print sys.exc_info()

  def keyPressed(self, event):
    print "KeyCode:", event.getKeyCode()
    if KeyEvent.VK_ENTER == event.getKeyCode():
      self.translate(self.parse())
  
  def mouseWheelMoved(self, event):
    value = self.parse() - event.getWheelRotation()
    if self.translate(value):
      self.textfield.setText(str(value))

  def imageUpdated(self, imp):
    pass
  def imageOpened(self, imp):
    pass
  def imageClosed(self, imp):
    if imp == self.imp:
      self.textfield.setEnabled(False)
      self.imp.removeImageListener(self)
      self.imp = None # Release resources


class CloseControl(WindowAdapter):
  def windowClosing(self, event):
    if JOptionPane.NO_OPTION == JOptionPane.showConfirmDialog(event.getSource(),
                                         "Are you sure you want to close the Translation UI?",
                                         "Confirm closing",
                                         JOptionPane.YES_NO_OPTION):
      # Prevent closing
      event.consume()
    else:
      event.getSource().dispose()


def makeTranslationUI(affines, imp, show=True):
  """ A GUI to control the translation components of a list of AffineTransform3D instances.
      When updated, the ImagePlus is refreshed.
      Returns the JFrame, the main JPanel and the lower JButton panel. """
  panel = JPanel()
  gb = GridBagLayout()
  panel.setLayout(gb)
  gc = GridBagConstraints()
  gc.anchor = GridBagConstraints.WEST
  gc.fill = GridBagConstraints.NONE

  # Column labels
  gc.gridy = 0
  for i, title in enumerate(["Camera", "translation X", "translation Y", "translation Z"]):
    gc.gridx = i
    gc.anchor = GridBagConstraints.CENTER
    label = JLabel(title)
    gb.setConstraints(label, gc)
    panel.add(label)

  gc.anchor = GridBagConstraints.WEST
  
  # One row per affine to control
  for i, affine in enumerate(affines):
    gc.gridx = 0
    gc.gridy += 1
    label = JLabel("CM0%i: " % (i + 1))
    gb.setConstraints(label, gc)
    panel.add(label)
    # One JTextField per dimension
    for dimension, translation in enumerate(affine.getTranslation()):
      tf = JTextField(str(translation), 10)
      listener = MatrixTextFieldListener(affine, dimension, tf, imp)
      imp.addImageListener(listener) # to disable the JTextField when closed
      tf.addKeyListener(listener)
      tf.addMouseWheelListener(listener)
      gc.gridx += 1
      gb.setConstraints(tf, gc)
      panel.add(tf)

  # Documentation for the user
  help_lines = ["Type a number and push enter,",
                "or use the scroll wheel."]
  gc.gridx = 0
  gc.gridwidth = 4
  for line in help_lines:
    gc.gridy += 1
    help = JLabel(line)
    gb.setConstraints(help, gc)
    panel.add(help)

  # Buttons
  printButton = JButton("Print transforms")
  
  def printTransforms(event):
    for i, aff in enumerate(affines):
      matrix = zeros(12, 'd')
      aff.toArray(matrix)
      print "affine matrix " + str(i) + ": "
      print "[%f, %f, %f, %f,\n %f, %f, %f, %f,\n %f, %f, %f, %f]" % tuple(matrix.tolist())
  
  printButton.addActionListener(printTransforms)
  gc.gridx = 0
  gc.gridy += 1
  gc.gridwidth = 4
  button_panel = JPanel()
  button_panel.add(printButton)
  gb.setConstraints(button_panel, gc)
  panel.add(button_panel)

  frame = JFrame("Translation control")
  frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE)
  frame.addWindowListener(CloseControl())
  frame.getContentPane().add(panel)
  frame.pack()
  frame.setVisible(show)

  return frame, panel, button_panel
