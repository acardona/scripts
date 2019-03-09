from ij import ImagePlus, IJ, ImageListener
from ij.gui import RoiListener, Roi
from java.awt.event import KeyEvent, KeyAdapter, MouseWheelListener, WindowAdapter
from javax.swing import JPanel, JLabel, JTextField, JButton, JOptionPane, JFrame, JSeparator
from java.awt import Dimension, GridBagLayout, GridBagConstraints as GBC
from java.lang import System
from net.imglib2.util import Intervals
from net.imglib2.view import Views
from jarray import zeros
import sys
from itertools import izip
from io import InRAMLoader
from util import numCPUs, affine3D
from ui import showAsStack
from registration import transformedView


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
                                         "Are you sure you want to close?",
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


def makeCropUI(imp, images, panel=None, cropContinuationFn=None):
  """ imp: the ImagePlus to work on.
      images: the list of ImgLib2 images, one per frame.
      panel: optional, a JPanel controlled by a GridBagLayout.
      cropContinuationFn: optional, a function to execute after cropping,
                          which is given as arguments the original images,
                          minC, maxC (both define a ROI), and the cropped images. """
  independent = None == panel
  if not panel:
    panel = JPanel()
    gb = GridBagLayout()
    gc = GBC()
  else:
    gb = panel.getLayout()
    # Constraints of the last component
    gc = gb.getConstraints(panel.getComponent(panel.getComponentCount() - 1))
    
    # Horizontal line to separate prior UI components from crop UI
    gc.gridx = 0
    gc.gridy += 1
    gc.gridwidth = 4
    gc.anchor = GBC.WEST
    gc.fill = GBC.HORIZONTAL
    sep = JSeparator()
    sep.setMinimumSize(Dimension(200, 10))
    gb.setConstraints(sep, gc)
    panel.add(sep)

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
  for rowLabel, coords in izip(["min coords: ", "max coords: "],
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
    cropped_imp = showAsStack(cropped, title="cropped")
    if cropContinuationFn:
      cropContinuationFn(images, minC, maxC, cropped)

  # Buttons to create a ROI and to crop to ROI,
  # which when activated enables the fine registration buttons
  crop_button = JButton("Crop to ROI")
  crop_button.addActionListener(crop)
  gc.gridx = 0
  gc.gridy += 1
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
  

def makeRegistrationUI(params, images, minC, maxC, cropped):
  """ Register cropped images either all to all or all to the first one,
      and print out a config file with the coarse affines,
      the ROI for cropping, and the refined affines post-crop. """

  panel = JPanel()
  gb = GridBagLayout()
  panel.setLayout(gb)
  gc = GBC()

  calibration = params["calibration"]
  params["cal X"] = calibration[0]
  params["cal Y"] = calibration[1]
  params["cal Z"] = calibration[2]

  # Add a label and a text field for every parameter, with titles for every block
  strings = [["Calibration",
              "cal X", "cal Y", "cal Z"],
             ["Difference of Gaussian",
              "minPeakValue", "sigmaSmaller", "sigmaLarger"],
             ["Feature extraction",
              "radius", "min_angle", "max_per_peak",
              "angle_epsilon", "len_epsilon_sq",
              "pointmatches_nearby", "pointmatches_search_radius"],
             ["RANSAC parameters for the model",
              "maxEpsilon", "minInlierRatio", "minNumInliers",
              "n_iterations", "maxTrust"],
             ["All to all registration",
              "maxAllowedError", "maxPlateauwidth", "maxIterations", "damp"]]
  for block in strings:
    title = JLabel(block[0])
    gc.gridx = 0
    gc.gridy += 1
    gc.gridwidth = 2
    gc.anchor = GBC.WEST
    gb.setConstraints(title, gc)
    panel.add(title)
    for param in block[1:]:
      gc.gridy += 1
      gc.gridwidth = 1
      gc.gridx = 0
      gc.anchor = GBC.EAST
      name = JLabel(param)
      gb.setConstraints(name, gc)
      panel.add(name)
      gc.gridx = 1
      gc.anchor = GBC.WEST
      tf = JTextField(str(params[param]), 10)
      gb.setConstraints(tf, gc)
      panel.add(tf)

  # Identity transforms prior to registration
  affines = [affine3D([1, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0]) for img in cropped]
  
  def run(event):
    # Dummy for in-RAM reading of isotropic images
    img_filenames = [str(i) for i in xrange(len(cropped))]
    loader = InRAMLoader(dict(zip(img_filenames, cropped)))
    getCalibration = params.get("getCalibration", None)
    if not getCalibration:
      getCalibration = lambda img: [1.0] * len(cropped)
    csv_dir = params["csv_dir"]
    modelclass = params["modelclass"]
    exe = newFixedTheadPool(min(len(cropped), numCPUs()))
    try:
      affs = computeOptimizedTransforms(img_filenames, loader, getCalibration,
                                        csv_dir, exe, modelclass, params)
      # Store outside
      for aff, affine in zip(affs, affines):
        affine.set(aff)
      
      # Show registered images
      registered = [transformedView(img, aff) for img, aff in zip(cropped, affs)]
      dimensions = Intervals.dimensionsAsLongArray(cropped[0])
      # Copy into ArrayImg, otherwise they are rather slow to browse
      aimgs = [ArrayImgs.unsignedShorts(dimensions) for img in registered]
      for img, aimg in zip(registered, aimgs):
        ImgUtil.copy(img, aimg)
      showAsStack(aimgs, title="Registered with %s" % params["modelclass"].getClass().getSimpleName())
    finally:
      exe.shutdown()

  def printAffines(event):
    for i, affine in enumerate(affines):
      matrix = zeros(12, 'd')
      affine.toArray(matrix)
      msg = "affine matrix " + str(i) + ": \n" + \
            "[%f, %f, %f, %f,\n %f, %f, %f, %f,\n %f, %f, %f, %f]" % tuple(matrix.tolist())
      # Print everywhere
      print msg
      IJ.log(msg)
      System.out.println(msg)
  
  # Buttons
  panel_buttons = JPanel()
  gc.gridx = 0
  gc.gridy += 1
  gc.gridwidth = 2
  gb.setConstraints(panel_buttons, gc)
  panel.add(panel_buttons)
  
  run_button = JButton("Run")
  run_button.addActionListener(run)
  panel_buttons.add(run_button)
  
  print_button = JButton("Print affines")
  print_button.addActionListener(printAffines)
  panel_buttons.add(print_button)

  frame = JFrame("Registration")
  frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE)
  frame.addWindowListener(CloseControl())
  frame.getContentPane().add(panel)
  frame.pack()
  frame.setVisible(True)

  # TODO: missing button to print config file with coarse transforms, ROI, and refined transforms
  # for subsequent use in the next program

