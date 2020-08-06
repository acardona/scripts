# A reactive generic dialog

from ij.gui import GenericDialog
from ij import WindowManager as WM
from java.awt.event import AdjustmentListener, ItemListener

class ScalingPreviewer(AdjustmentListener, ItemListener):
  def __init__(self, imp, slider, preview_checkbox):
    """
       imp: an ImagePlus
       slider: a java.awt.Scrollbar UI element
       preview_checkbox: a java.awt.Checkbox controlling whether to
                         dynamically update the ImagePlus as the
                         scrollbar is updated, or not.
    """
    self.imp = imp
    self.original_ip = imp.getProcessor().duplicate() # store a copy
    self.slider = slider
    self.preview_checkbox = preview_checkbox
  
  def adjustmentValueChanged(self, event):
    """ event: an AdjustmentEvent with data on the state of the scroll bar. """
    preview = self.preview_checkbox.getState()
    if preview:
      if event.getValueIsAdjusting():
        return # there are more scrollbar adjustment events queued already
      print "Scaling to", event.getValue() / 100.0
      
      self.scale()

  def itemStateChanged(self, event):
    """ event: an ItemEvent with data on what happened to the checkbox. """
    if event.getStateChange() == event.SELECTED:
      self.scale()
  
  def reset(self):
    """ Restore the original ImageProcessor """
    self.imp.setProcessor(self.original_ip)
  
  def scale(self):
    """ Execute the in-place scaling of the ImagePlus. """
    scale = self.slider.getValue() / 100.0
    new_width = int(self.original_ip.getWidth() * scale)
    new_ip = self.original_ip.resize(new_width)
    self.imp.setProcessor(new_ip)


def scaleImageUI():
  gd = GenericDialog("Scale")
  gd.addSlider("Scale", 1, 200, 100)
  gd.addCheckbox("Preview", True)
  # The UI elements for the above two inputs
  slider = gd.getSliders().get(0) # the only one
  checkbox = gd.getCheckboxes().get(0) # the only one

  imp = WM.getCurrentImage()
  if not imp:
    print "Open an image first!"
    return

  previewer = ScalingPreviewer(imp, slider, checkbox)
  slider.addAdjustmentListener(previewer)
  checkbox.addItemListener(previewer)
  
  gd.showDialog()

  if gd.wasCanceled():
    previewer.reset()
    print "User canceled dialog!"
  else:
    previewer.scale()

scaleImageUI()
