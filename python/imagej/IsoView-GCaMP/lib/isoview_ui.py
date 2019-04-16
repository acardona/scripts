from ij import ImagePlus, IJ, ImageListener
from ij.gui import RoiListener, Roi
from ij.io import OpenDialog
from java.awt import Color
from java.awt.event import KeyEvent, KeyAdapter, MouseWheelListener, WindowAdapter
from javax.swing import JPanel, JLabel, JTextField, JButton, JOptionPane, JFrame, \
                        JSeparator, SwingUtilities, BorderFactory
from java.awt import Dimension, GridBagLayout, GridBagConstraints as GBC
from java.lang import System, Thread
from net.imglib2.util import Intervals, ImgUtil
from net.imglib2.view import Views
from net.imglib2.img import ImgView
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
import os, sys, csv
from itertools import izip, imap
from io import InRAMLoader
from util import numCPUs, affine3D, newFixedThreadPool, Task
from ui import showAsStack
from registration import transformedView, computeOptimizedTransforms, mergeTransforms
from java.util.concurrent import Executors, TimeUnit
from datetime import datetime


class MatrixTextFieldListener(KeyAdapter, MouseWheelListener, ImageListener):
  def __init__(self, affine, dimension, textfield, imp):
    self.affine = affine
    self.dimension = dimension
    self.textfield = textfield
    self.imp = imp
    self.refresh = False
    self.exe = Executors.newSingleThreadScheduledExecutor()
    def repaint():
      if self.refresh:
        self.refresh = False
        #self.imp.updateAndDraw() # fails for virtual stacks
        # A solution that works for virtual stacks, by Wayne Rasband:
        minimum, maximum = self.imp.getDisplayRangeMin(), self.imp.getDisplayRangeMax()
        self.imp.setProcessor(self.imp.getStack().getProcessor(self.imp.getCurrentSlice()))
        self.imp.setDisplayRange(minimum, maximum)
    #
    self.exe.scheduleAtFixedRate(repaint, 1000, 200, TimeUnit.MILLISECONDS)

  def translate(self, value):
    t = self.affine.getTranslation() # 3-slot double array, a copy
    t[self.dimension] = value
    try:
      self.affine.setTranslation(t) # will throw a RuntimeError when not invertible
    except:
      print sys.exc_info()
      return False
    self.refresh = True
    return True

  def parse(self):
    try:
      return float(self.textfield.getText())
    except:
      print sys.exc_info()
      raise ValueError("Can't parse number from: %s" % self.textfield.getText())

  def parseIncSet(self, inc):
    value = self.parse() + inc
    if self.translate(value):
      self.textfield.setText(str(value))

  def keyPressed(self, event):
    code = event.getKeyCode()
    if KeyEvent.VK_ENTER == code:
      self.translate(self.parse())
    elif KeyEvent.VK_UP == code or KeyEvent.VK_RIGHT == code:
      self.parseIncSet(1.0)
    elif KeyEvent.VK_DOWN == code or KeyEvent.VK_LEFT == code:
      self.parseIncSet(-1.0)
  
  def mouseWheelMoved(self, event):
    self.parseIncSet(-event.getWheelRotation())

  def imageUpdated(self, imp):
    pass
  def imageOpened(self, imp):
    pass
  def imageClosed(self, imp):
    if imp == self.imp:
      self.destroy()

  def destroy(self):
    if self.textfield:
      self.textfield.setEnabled(False)
      self.textfield = None
    if self.imp:
      self.imp.removeImageListener(self)
      self.imp = None # Release resources
    if self.exe:
      self.exe.shutdownNow()
      self.exe = None


class CloseControl(WindowAdapter):
  def __init__(self, destroyables=[]):
    self.destroyables = set(destroyables) # objects with a "destroy()" method, via duct typing
  def addDestroyables(self, destroyables):
   self.destroyables |= set(destroyables)
  def windowClosing(self, event):
    if JOptionPane.NO_OPTION == JOptionPane.showConfirmDialog(event.getSource(),
                                         "Are you sure you want to close?",
                                         "Confirm closing",
                                         JOptionPane.YES_NO_OPTION):
      # Prevent closing
      event.consume()
    else:
      for d in self.destroyables:
        d.destroy()
      event.getSource().dispose()
      self.destroyables = set()
      event.getSource().removeWindowListener(self)


def makeTranslationUI(affines, imp, show=True, print_button_text="Print transforms"):
  """
  A GUI to control the translation components of a list of AffineTransform3D instances.
  When updated, the ImagePlus is refreshed.

  affines: a list (will be read multiple times) of one affine transform per image.
  imp: the ImagePlus that hosts the virtual stack with the transformed images.
  show: defaults to True, whether to make the GUI visible.
  print_button_text: whatever you want the print button to read like, defaults to "Print transforms".
   
  Returns the JFrame, the main JPanel and the lower JButton panel.
  """
  panel = JPanel()
  panel.setBorder(BorderFactory.createEmptyBorder(10,10,10,10))
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
  listeners = []
  
  # One row per affine to control: skip the first
  for i, affine in enumerate(affines[1:]):
    gc.gridx = 0
    gc.gridy += 1
    label = JLabel("CM0%i: " % (i + 1))
    gb.setConstraints(label, gc)
    panel.add(label)
    # One JTextField per dimension
    for dimension, translation in enumerate(affine.getTranslation()):
      tf = JTextField(str(translation), 10)
      listener = MatrixTextFieldListener(affine, dimension, tf, imp)
      listeners.append(listener)
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
    for i, aff in enumerate(affines): # print all, including the first
      matrix = zeros(12, 'd')
      aff.toArray(matrix)
      msg = "# Coarse affine matrix " + str(i) + ": \n" + \
            "affine" + str(i) + ".set(*[%d, %d, %d, %d,\n %d, %d, %d, %d,\n %d, %d, %d, %d])" % tuple(matrix.tolist())
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
  frame.addWindowListener(CloseControl(destroyables=listeners))
  frame.getContentPane().add(panel)
  frame.pack()
  frame.setLocationRelativeTo(None) # center in the screen
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

  def parseIncSet(self, inc):
    value = self.parse() + inc
    self.textfields[self.index].setText(str(value))
    self.setRoi(value)

  def keyPressed(self, event):
    code = event.getKeyCode()
    if KeyEvent.VK_ENTER == code:
      self.setRoi(self.parse())
    elif KeyEvent.VK_UP == code or KeyEvent.VK_RIGHT == code:
      self.parseIncSet(1.0)
    elif KeyEvent.VK_DOWN == code or KeyEvent.VK_LEFT == code:
      self.parseIncSet(-1.0)
  
  def mouseWheelMoved(self, event):
    self.parseIncSet(- event.getWheelRotation())

  def destroy(self):
    if self.textfields:
      for tf in self.textfields:
        tf.setEnabled(False)
      self.textfields = None
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
    if self.textfields:
      for tf in self.textfields:
          tf.setEnabled(False)
    self.textfields = None
    Roi.removeRoiListener(self)
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
    if self.roifieldlistener and imp == self.roifieldlistener.imp:
      self.roifieldlistener.destroy()
      self.roifieldlistener = None
      if self.roimakers:
        for rm in self.roimakers:
          rm.destroy()
        self.roimakers = None
      ImagePlus.removeImageListener(self)


def makeCropUI(imp, images, tgtDir, panel=None, cropContinuationFn=None):
  """ imp: the ImagePlus to work on.
      images: the list of ImgLib2 images, one per frame, not original but already isotropic.
              (These are views that use a nearest neighbor interpolation using the calibration to scale to isotropy.)
      tgtDir: the target directory where e.g. CSV files will be stored, for ROI, features, pointmatches.
      panel: optional, a JPanel controlled by a GridBagLayout.
      cropContinuationFn: optional, a function to execute after cropping,
                          which is given as arguments the original images,
                          minC, maxC (both define a ROI), and the cropped images. """
  independent = None == panel
  if not panel:
    panel = JPanel()
    panel.setBorder(BorderFactory.createEmptyBorder(10,10,10,10))
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

  # Load stored ROI if any
  roi_path = path = os.path.join(tgtDir, "crop-roi.csv")
  if os.path.exists(roi_path):
    with open(roi_path, 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
      reader.next() # header
      minC = map(int, reader.next()[1:])
      maxC = map(int, reader.next()[1:])
      # Place the ROI over the ImagePlus
      imp.setRoi(Roi(minC[0], minC[1], maxC[0] + 1 - minC[0], maxC[1] + 1 - minC[1]))
  else:
    # Use whole image dimensions
    minC = [0, 0, 0]
    maxC = [v -1 for v in Intervals.dimensionsAsLongArray(images[0])]

  # Text fields for the min and max coordinates
  for rowLabel, coords in izip(["min coords: ", "max coords: "],
                               [minC, maxC]):
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

  def storeRoi(minC, maxC):
    if os.path.exists(roi_path):
      # Load ROI
      with open(path, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar="\"")
        reader.next() # header
        same = True
        for a, b in izip(minC + maxC, map(int, reader.next()[1:] + reader.next()[1:])):
          if a != b:
            same = False
            # Invalidate any CSV files for features and pointmatches: different cropping
            for filename in os.listdir(tgtDir):
              if filename.endswith("features.csv") or filename.endswith("pointmatches.csv"):
                os.remove(os.path.join(tgtDir, filename))
            break
        if same:
          return
    # Store the ROI as crop-roi.csv
    with open(roi_path, 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=',', quotechar="\"", quoting=csv.QUOTE_NONNUMERIC)
      w.writerow(["coords", "x", "y", "z"])
      w.writerow(["min"] + map(int, minC))
      w.writerow(["max"] + map(int, maxC))
  
  def crop(event):
    global cropped, cropped_imp
    coords = [int(float(tf.getText())) for tf in textfields]
    minC = [max(0, c) for c in coords[0:3]]
    maxC = [min(d -1, c) for d, c in izip(Intervals.dimensionsAsLongArray(images[0]), coords[3:6])]
    storeRoi(minC, maxC)
    print "ROI min and max coordinates"
    print minC
    print maxC
    cropped = [Views.zeroMin(Views.interval(img, minC, maxC)) for img in images]
    cropped_imp = showAsStack(cropped, title="cropped")
    cropped_imp.setDisplayRange(imp.getDisplayRangeMin(), imp.getDisplayRangeMax())
    if cropContinuationFn:
      cropContinuationFn(images, minC, maxC, cropped, cropped_imp)

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
    frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE)
    frame.addWindowListener(CloseControl(destroyables=rms + [rfl]))
    frame.setVisible(True)
  else:
    # Re-pack the JFrame
    parent = panel.getParent()
    while not isinstance(parent, JFrame) and parent is not None:
      parent = parent.getParent()

    if parent:
      frame = parent
      frame.pack()
      found = False
      for wl in frame.getWindowListeners():
        if isinstance(wl, CloseControl):
          wl.addDestroyables(rms + [rfl])
          found = True
          break
      if not found:
        frame.addWindowListener(CloseControl(destroyables=rms + [rfl]))
      frame.setVisible(True)

  return panel


class NumberTextFieldListener(KeyAdapter):
  def __init__(self, key, params, parse=float):
    self.key = key
    self.params = params
    self.parse = parse
  def keyPressed(self, event):
    text = event.getSource().getText()
    try:
      # Attempt to parse number, will throw an error when not possible
      value = self.parse(text)
      # Update the params dictionary
      self.params[self.key] = value
      # Signal success
      event.getSource().setBackgroundColor(Color.white)
    except:
      print "Can't parse number from: %s" % text
      event.getSource().setBackgroundColor(Color(1.0, 82/255.0, 82/255.0))


def insertFloatFields(panel, gb, gc, params, strings):
  """
  strings: an array of arrays, which each array having at least 2 strings,
           with the first string being the title of the section,
           and subsequent strings being the label of the parameter
           as well as the key in the params dictionary to retrieve the value
           to show as default in the textfield.
  When a value is typed in and it is a valid float number, the entry in params is updated.
  When invalid, the text field background is turned red.
  """
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
      name = JLabel(param + ": ")
      gb.setConstraints(name, gc)
      panel.add(name)
      gc.gridx = 1
      gc.anchor = GBC.WEST
      tf = JTextField(str(params[param]), 10)
      tf.addKeyListener(NumberTextFieldListener(param, params, parse=float))
      gb.setConstraints(tf, gc)
      panel.add(tf)


def makeRegistrationUI(original_images, original_calibration, coarse_affines, params, images, minC, maxC, cropped, cropped_imp):
  """
  Register cropped images either all to all or all to the first one,
  and print out a config file with the coarse affines,
  the ROI for cropping, and the refined affines post-crop.

  original_images: the original, raw images, with original dimensions.
  original_calibration: the calibration of the images as they are on disk.
  coarse_affines: list of AffineTransform3D, one per image, that specify the translation between images
                  as manually set using the makeTranslationUI.
  params: dictionary with parameters for registering the given cropped images.
          This includes a calibration that is likely [1.0, 1.0, 1.0] as the cropped images
          are expected to have been scaled to isotropy.
  images: the list of near-original images but scaled (by calibration) to isotropy.
          (These are really views of the original images, using nearest neighbor interpolation
           to scale them to isotropy.)
  minC, maxC: the minimum and maximum coordinates of a ROI with which the cropped images were made.
  cropped: the list of images that have been scaled to isotropy, translated and cropped by the ROI.
           (These are really interval views of the images, the latter using nearest neighbor interpolation.)
  cropped_imp: the ImagePlus holding the virtual stack of cropped image views.

  The computed registration will merge the scaling to isotropy + first transform (a translation)
   + roi cropping translation + the params["modelclass"] registration transform, to read directly
   from the original images using a nearest interpolation, for best performance (piling two nearest
   interpolations over one another would result in very slow access to pixel data).
  """

  panel = JPanel()
  panel.setBorder(BorderFactory.createEmptyBorder(10,10,10,10))
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
  # Insert all as fields, with values populated from the params dictionary
  # and updating dynamically the params dictionary
  params = dict(params) # copy, will be updated
  insertFloatFields(panel, gb, gc, params, strings)

  # Identity transforms prior to registration
  affines = [affine3D([1, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0]) for img in cropped]
  
  def run():
    exe = newFixedThreadPool(min(len(cropped), numCPUs()))
    try:
      # Dummy for in-RAM reading of isotropic images
      img_filenames = [str(i) for i in xrange(len(cropped))]
      loader = InRAMLoader(dict(zip(img_filenames, cropped)))
      getCalibration = params.get("getCalibration", None)
      if not getCalibration:
        getCalibration = lambda img: [1.0] * cropped[0].numDimensions()
      csv_dir = params["csv_dir"]
      modelclass = params["modelclass"]
      # Matrices describing the registration on the basis of the cropped images
      matrices = computeOptimizedTransforms(img_filenames, loader, getCalibration,
                                            csv_dir, exe, modelclass, params)
      # Store outside, so they can be e.g. printed, and used beyond here
      for matrix, affine in zip(matrices, affines):
        affine.set(*matrix)

      # Combine the transforms: scaling (by calibration)
      #                         + the coarse registration (i.e. manual translations)
      #                         + the translation introduced by the ROI cropping
      #                         + the affine matrices computed above over the cropped images.
      coarse_matrices = []
      for coarse_affine in coarse_affines:
        matrix = zeros(12, 'd')
        coarse_affine.toArray(matrix)
        coarse_matrices.append(matrix)

      # NOTE: both coarse_matrices and matrices are from the camera X to camera 0. No need to invert them.
      transforms = mergeTransforms([1.0, 1.0, 1.0], coarse_matrices, [minC, maxC], matrices, invert2=False)
      
      # Show registered images
      registered = [transformedView(img, transform, interval=cropped[0])
                    for img, transform in izip(original_images, transforms)]
      registered_imp = showAsStack(registered, title="Registered with %s" % params["modelclass"].getSimpleName())
      registered_imp.setDisplayRange(cropped_imp.getDisplayRangeMin(), cropped_imp.getDisplayRangeMax())

      """
      # TEST: same as above, but without merging the transforms. WORKS, same result
      # Copy into ArrayImg, otherwise they are rather slow to browse
      def copy(img1, affine):
        # Copy in two steps. Otherwise the nearest neighbor interpolation on top of another
        # nearest neighbor interpolation takes a huge amount of time
        dimensions = Intervals.dimensionsAsLongArray(img1)
        aimg1 = ArrayImgs.unsignedShorts(dimensions)
        ImgUtil.copy(ImgView.wrap(img1, aimg1.factory()), aimg1)
        img2 = transformedView(aimg1, affine)
        aimg2 = ArrayImgs.unsignedShorts(dimensions)
        ImgUtil.copy(ImgView.wrap(img2, aimg2.factory()), aimg2)
        return aimg2
      futures = [exe.submit(Task(copy, img, affine)) for img, affine in izip(cropped, affines)]
      aimgs = [f.get() for f in futures]
      showAsStack(aimgs, title="DEBUG Registered with %s" % params["modelclass"].getSimpleName())
      """
    except:
      print sys.exc_info()
    finally:
      exe.shutdown()
      SwingUtilities.invokeLater(lambda: run_button.setEnabled(True))

  def launchRun(event):
    # Runs on the event dispatch thread
    run_button.setEnabled(False) # will be re-enabled at the end of run()
    # Fork:
    Thread(run).start()


  def printAffines(event):
    for i, affine in enumerate(affines):
      matrix = zeros(12, 'd')
      affine.toArray(matrix)
      msg = "# Refined post-crop affine matrix " + str(i) + ": \n" + \
            "affine" + str(i) + ".set(*[%d, %d, %d, %d,\n %d, %d, %d, %d,\n %d, %d, %d, %d])" % tuple(matrix.tolist())
      # Print everywhere
      print msg
      IJ.log(msg)
      System.out.println(msg)

  def prepareDeconvolutionScriptUI(event):
    """
    # DEBUG generateDeconvolutionScriptUI: generate params as a loadable serialized file
    with open("/tmp/parameters.pickle", 'w') as f:
      import pickle
      def asArrays(affines):
        arrays = []
        for affine in affines:
          matrix = zeros(12, 'd')
          affine.toArray(matrix)
          arrays.append(matrix)
        return arrays
        
      pickle.dump([params["srcDir"], params["tgtDir"], calibration,
                   asArrays(coarse_affines), [minC, maxC], asArrays(affines)], f)
    """
    generateDeconvolutionScriptUI(params["srcDir"], params["tgtDir"], calibration,
                                  coarse_affines, [minC, maxC], affines)
  
  # Buttons
  panel_buttons = JPanel()
  gc.gridx = 0
  gc.gridy += 1
  gc.gridwidth = 2
  gb.setConstraints(panel_buttons, gc)
  panel.add(panel_buttons)
  
  run_button = JButton("Run")
  run_button.addActionListener(launchRun)
  gb.setConstraints(run_button, gc)
  panel_buttons.add(run_button)
  
  print_button = JButton("Print affines")
  print_button.addActionListener(printAffines)
  panel_buttons.add(print_button)

  prepare_button = JButton("Prepare deconvolution script")
  prepare_button.addActionListener(prepareDeconvolutionScriptUI)
  panel_buttons.add(prepare_button)

  frame = JFrame("Registration")
  frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE)
  frame.addWindowListener(CloseControl())
  frame.getContentPane().add(panel)
  frame.pack()
  frame.setLocationRelativeTo(None) # center in the screen
  frame.setVisible(True)


def generateDeconvolutionScriptUI(srcDir,
                                  tgtDir,
                                  calibration,
                                  preCropAffines,
                                  ROI,
                                  postCropAffines):
  """
  Open an UI to automatically generate a script to:
  1. Register the views of each time point TM folder, and deconvolve them.
  2. Register deconvolved time points to each other, for a range of consecutive time points.

  Will ask for the file path to the kernel file,
  and also for the range of time points to process,
  and for the deconvolution iterations for CM00-CM01, and CM02-CM03.
  """

  template = """
# AUTOMATICALLY GENERATED - %s

import sys, os
sys.path.append("%s")
from lib.isoview import deconvolveTimePoints
from mpicbg.models import RigidModel3D, TranslationModel3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL

# The folder with the sequence of TM\d+ folders, one per time poi  nt in the 4D series.
# Each folder should contain 4 KLB files, one per camera view of the IsoView microscope.
srcDir = "%s"

# A folder to save deconvolved images in, and CSV files describing features, point matches and transformations
targetDir = "%s"

# Path to the volume describing the point spread function (PSF)
kernelPath = "%s"

calibration = [%s] # An array with 3 floats

# The transformations of each timepoint onto the camera at index zero.
def cameraTransformations(dims0, dims1, dims2, dims3, calibration):
  return {
    0: [1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0],
    1: [%s],
    2: [%s],
    3: [%s]
  }

# Deconvolution parameters
paramsDeconvolution = {
  "blockSizes": None, # None means the image size + kernel size. Otherwise specify like e.g. [[128, 128, 128]] for img in images]
  "CM_0_1_n_iterations": %i,
  "CM_2_3_n_iterations": %i,
}

# Joint dictionary of parameters
params = {}
params.update(paramsDeconvolution)

# A region of interest for each camera view, for cropping after registration but prior to deconvolution
roi = ([%s], # array of 3 integers, top-left coordinates
       [%s]) # array of 3 integers, bottom-right coordinates

# All 4 cameras relative to CM00
fineTransformsPostROICrop = \
   [[1, 0, 0, 0,
     0, 1, 0, 0,
     0, 0, 1, 0],
    [%s],
    [%s],
    [%s]]

deconvolveTimePoints(srcDir, targetDir, kernelPath, calibration,
                    cameraTransformations, fineTransformsPostROICrop,
                    params, roi, subrange=range(%i, %i))
  """

  od = OpenDialog("Choose kernel file", srcDir)
  kernel_path = od.getPath()
  if not kernel_path:
    JOptionPane.showMessageDialog(None, "Can't proceed without a filepath to the kernel", "Alert", JOptionPane.ERROR_MESSAGE)
    return

  panel = JPanel()
  panel.setBorder(BorderFactory.createEmptyBorder(10,10,10,10))
  gb = GridBagLayout()
  panel.setLayout(gb)
  gc = GBC()

  msg = ["Edit parameters, then push the button",
         "to generate a script that, when run,",
         "will execute the deconvolution for each time point",
         "saving two 3D stacks per time point as ZIP files",
         "in the target directory under subfolder 'deconvolved'.",
         "Find the script in a new Script Editor window.",
         " "]
  gc.gridy = -1 # init
  for line in msg:
    label = JLabel(line)
    gc.anchor = GBC.WEST
    gc.gridx = 0
    gc.gridy += 1
    gc.gridwidth = 2
    gc.gridheight = 1
    gb.setConstraints(label, gc)
    panel.add(label)

  strings = [["Deconvolution iterations",
              "CM_0_1_n_iterations", "CM_2_3_n_iterations"],
             ["Range",
              "First time point", "Last time point"]]
  params = {"CM_0_1_n_iterations": 5,
            "CM_2_3_n_iterations": 7,
            "First time point": 0,
            "Last time point": -1} # -1 means last
  insertFloatFields(panel, gb, gc, params, strings)

  def asString(affine):
    matrix = zeros(12, 'd')
    affine.toArray(matrix)
    return ",".join(imap(str, matrix))

  def generateScript(event):
    script = template % (str(datetime.now()),
                         filter(lambda path: path.endswith("IsoView-GCaMP"), sys.path)[-1],
                         srcDir,
                         tgtDir,
                         kernel_path,
                         ", ".join(imap(str, calibration)),
                         asString(preCropAffines[1]),
                         asString(preCropAffines[2]),
                         asString(preCropAffines[3]),
                         params["CM_0_1_n_iterations"],
                         params["CM_2_3_n_iterations"],
                         ", ".join(imap(str, ROI[0])),
                         ", ".join(imap(str, ROI[1])),
                         asString(postCropAffines[1]),
                         asString(postCropAffines[2]),
                         asString(postCropAffines[3]),
                         params["First time point"],
                         params["Last time point"])
    tab = None
    for frame in JFrame.getFrames():
      if str(frame).startswith("org.scijava.ui.swing.script.TextEditor["):
        try:
          tab = frame.newTab(script, "python")
          break
        except:
          print sys.exc_info()
    if not tab:
      try:
        now = datetime.now()
        with open(os.path.join(System.getProperty("java.io.tmpdir"),
                               "script-%i-%i-%i_%i:%i.py" % (now.year, now.month, now.day,
                                                             now.hour, now.minute)), 'w') as f:
          f.write(script)
      except:
        print sys.exc_info()
        print script
  

  gen = JButton("Generate script")
  gen.addActionListener(generateScript)
  gc.anchor = GBC.CENTER
  gc.gridx = 0
  gc.gridy += 1
  gc.gridwidth = 2
  gb.setConstraints(gen, gc)
  panel.add(gen)

  frame = JFrame("Generate deconvolution script")
  frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE)
  frame.getContentPane().add(panel)
  frame.pack()
  frame.setLocationRelativeTo(None) # center in the screen
  frame.setVisible(True)
