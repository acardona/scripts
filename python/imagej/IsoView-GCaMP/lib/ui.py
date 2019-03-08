from net.imglib2.img.display.imagej import ImageJFunctions as IL, ImageJVirtualStackUnsignedShort
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from bdv.util import BdvFunctions, Bdv
from ij import ImagePlus, CompositeImage, VirtualStack, ImageListener, IJ
from ij.gui import RoiListener, Roi
from java.awt.event import KeyEvent, KeyAdapter, MouseWheelListener, WindowAdapter
from javax.swing import JPanel, JLabel, JTextField, JButton, JOptionPane, JFrame
from java.awt import GridBagLayout, GridBagConstraints as GBC
from java.lang import System
from jarray import zeros
import sys
from itertools import izip


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
      raise ValueError("Can't parse number from: %s" % self.textfield.getText())

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


def makeTranslationUI(affines, imp, show=True, print_button_text="Print transforms"):
  """ A GUI to control the translation components of a list of AffineTransform3D instances.
      When updated, the ImagePlus is refreshed.
      Returns the JFrame, the main JPanel and the lower JButton panel. """
  panel = JPanel()
  gb = GridBagLayout()
  panel.setLayout(gb)
  gc = GBC()
  gc.anchor = GBC.WEST
  gc.fill = GBC.NONE

  # Column labels
  gc.gridy = 0
  for i, title in enumerate(["Camera", "translation X", "translation Y", "translation Z"]):
    gc.gridx = i
    gc.anchor = GBC.CENTER
    label = JLabel(title)
    gb.setConstraints(label, gc)
    panel.add(label)

  gc.anchor = GBC.WEST
  
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
  printButton = JButton(print_button_text)
  
  def printTransforms(event):
    for i, aff in enumerate(affines):
      matrix = zeros(12, 'd')
      aff.toArray(matrix)
      msg = "affine matrix " + str(i) + ": \n" + \
            "[%f, %f, %f, %f,\n %f, %f, %f, %f,\n %f, %f, %f, %f]" % tuple(matrix.tolist())
      # Print everywhere
      print msg
      IJ.log(msg)
      System.out.println(msg)
      
  
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


class RoiMaker(KeyAdapter, MouseWheelListener):
  def __init__(self, imp, textfields, index):
    self.imp = imp
    self.textfields = textfields
    self.index = index
  
  def parse(self):
    try:
      return float(self.textfields[self.index].getText())
    except:
      print sys.exc_info()
      raise ValueError("Can't parse number from: %s" % self.textfields[self.index].getText())

  def setRoi(self, value):
    c = [float(tf.getText()) for tf in self.textfields]
    self.imp.setRoi(Roi(int(c[0]), int(c[1]), int(c[3] - c[0] + 1), int(c[4] - c[1] + 1)))


  def keyPressed(self, event):
    if KeyEvent.VK_ENTER == event.getKeyCode():
      self.setRoi(self.parse())
  
  def mouseWheelMoved(self, event):
    value = self.parse() - event.getWheelRotation()
    self.textfields[self.index].setText(str(value))
    self.setRoi(value)

  def destroy(self):
    for tf in self.textfields:
      tf.setEnabled(False)
    self.imp = None


class RoiFieldListener(RoiListener):
  def __init__(self, imp, textfields):
    self.imp = imp
    self.textfields = textfields # 6
  def roiModified(self, imp, id):
    if imp == self.imp:
      # Whatever the id, do:
      roi = imp.getRoi()
      if roi:
        bounds = roi.getBounds()
        # Ignore 3rd and 6th fields, which are for Z
        self.textfields[0].setText(str(bounds.x))
        self.textfields[1].setText(str(bounds.y))
        self.textfields[3].setText(str(bounds.x + bounds.width - 1))
        self.textfields[4].setText(str(bounds.y + bounds.height - 1))
  def destroy(self):
    for tf in self.textfields:
        tf.setEnabled(False)
    self.textfields = None
    Roi.removeRoiListeners(self)
    self.imp = None
    

class FieldDisabler(ImageListener):
  def __init__(self, roifieldlistener, roimakers):
    self.roifieldlistener = roifieldlistener
    self.roimakers = roimakers
  def imageUpdated(self, imp):
    pass
  def imageOpened(self, imp):
    pass
  def imageClosed(self, imp):
    if imp == self.roifieldlistener.imp:
      self.roifieldlistener.destroy()


def makeCropUI(imp, images, panel=None):
  """ imp: the ImagePlus to work on.
      images: the list of ImgLib2 images, one per frame.
      panel: optional, a JPanel controlled by a GridBagLayout. """
  independent = None == panel
  if not panel:
    panel = JPanel()
    gb = GridBagLayout()
    gc = GBC()
  else:
    gb = panel.getLayout()
    # Constraints of the last component
    gc = gb.getConstraints(panel.getComponent(panel.getComponentCount() - 1))

  # ROI UI header
  title = JLabel("ROI controls:")
  gc.gridy +=1
  gc.anchor = GBC.WEST
  gc.gridwidth = 4
  gb.setConstraints(title, gc)
  panel.add(title)

  # Column labels for the min and max coordinates
  gc.gridy += 1
  gc.gridwidth = 1
  for i, title in enumerate(["", "X", "Y", "Z"]):
    gc.gridx = i
    gc.anchor = GBC.CENTER
    label = JLabel(title)
    gb.setConstraints(label, gc)
    panel.add(label)

  textfields = []
  rms = []

  # Text fields for the min and max coordinates
  for rowLabel, coords in izip(["min coords", "max coords"],
                               [[0, 0, 0], [v -1 for v in Intervals.dimensionsAsLongArray(images[0])]]):
    gc.gridx = 0
    gc.gridy += 1
    label = JLabel(rowLabel)
    gb.setConstraints(label, gc)
    panel.add(label)
    for i in xrange(3):
      gc.gridx += 1
      tf = JTextField(str(coords[i]), 10)
      gb.setConstraints(tf, gc)
      panel.add(tf)
      textfields.append(tf)
      listener = RoiMaker(imp, textfields, len(textfields) -1)
      rms.append(listener)
      tf.addKeyListener(listener)
      tf.addMouseWheelListener(listener)

  # Listen to changes in the ROI of imp
  rfl = RoiFieldListener(imp, textfields)
  Roi.addRoiListener(rfl)
  # ... and enable cleanup
  ImagePlus.addImageListener(FieldDisabler(rfl, rms))

  # Functions for cropping images
  cropped = None
  cropped_imp = None
  
  def crop(event):
    global cropped, cropped_imp
    coords = [int(float(tf.getText())) for tf in textfields]
    minC = [max(0, c) for c in coords[0:3]]
    maxC = [min(d -1, c) for d, c in izip(Intervals.dimensionsAsLongArray(images[0]), coords[3:6])]
    print minC
    print maxC
    cropped = [Views.zeroMin(Views.interval(img, minC, maxC)) for img in images]
    cropped_img = showAsStack(cropped, title="cropped")

  # Buttons to create a ROI and to crop to ROI,
  # which when activated enables the fine registration buttons
  crop_button = JButton("Crop to ROI")
  crop_button.addActionListener(crop)
  gc.gridy +=1
  gc.gridwidth = 4
  gc.anchor = GBC.WEST
  buttons_panel = JPanel()
  buttons_panel.add(crop_button)
  gb.setConstraints(buttons_panel, gc)
  panel.add(buttons_panel)

  if independent:
    frame = JFrame("Crop by ROI")
    frame.getContentPane().add(panel)
    frame.pack()
    frame.setVisible(True)
  else:
    # Re-pack the JFrame
    parent = panel.getParent()
    while not isinstance(parent, JFrame) and parent is not None:
      parent = parent.getParent()

    if parent:
      parent.pack()
      parent.setVisible(True)

  return panel
  




