# A reactive generic dialog that updates previews in the background

from ij.gui import GenericDialog
from ij import WindowManager as WM
from java.awt.event import AdjustmentListener, ItemListener
from java.util.concurrent import Executors, TimeUnit
from java.lang import Runnable
from javax.swing import SwingUtilities
from synchronize import make_synchronized

class ScalingPreviewer(AdjustmentListener, ItemListener, Runnable):
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
    # Scheduled preview update
    self.scheduled_executor = Executors.newSingleThreadScheduledExecutor()
    # Stored state
    self.state = {
      "restore": False, # whether to reset to the original
      "requested_scaling_factor": 1.0, # last submitted request
      "last_scaling_factor": 1.0, # last executed request
      "shutdown": False, # to request terminating the scheduled execution
    }
    # Update, if necessary, every 300 milliseconds
    time_offset_to_start = 1000 # one second
    time_between_runs = 300
    self.scheduled_executor.scheduleWithFixedDelay(self, \
      time_offset_to_start, time_between_runs, TimeUnit.MILLISECONDS)

  @make_synchronized
  def getState(self, *keys):
    """ Synchronized access to one or more keys.
        Returns a single value when given a single key, or a tuple of values when given multiple keys. """
    if 1 == len(keys):
      return self.state[keys[0]]
    return tuple(self.state[key] for key in keys)

  @make_synchronized
  def putState(self, key, value):
    self.state[key] = value
  
  def adjustmentValueChanged(self, event):
    """ event: an AdjustmentEvent with data on the state of the scroll bar. """
    preview = self.preview_checkbox.getState()
    if preview:
      if event.getValueIsAdjusting():
        return # there are more scrollbar adjustment events queued already
      self.scale()

  def itemStateChanged(self, event):
    """ event: an ItemEvent with data on what happened to the checkbox. """
    if event.getStateChange() == event.SELECTED:
      self.scale()
  
  def reset(self):
    """ Restore the original ImageProcessor """
    self.putState("restore", True)

  def scale(self):
    self.putState("requested_scaling_factor", self.slider.getValue() / 100.0)
  
  def run(self):
    """ Execute the in-place scaling of the ImagePlus,
        here playing the role of a costly operation. """
    if self.getState("restore"):
      print "Restoring original"
      ip = self.original_ip
      self.putState("restore", False)
    else:
      requested, last = self.getState("requested_scaling_factor", "last_scaling_factor")
      if requested == last:
        return # nothing to do
      print "Scaling to", requested
      new_width = int(self.original_ip.getWidth() * requested)
      ip = self.original_ip.resize(new_width)
      self.putState("last_scaling_factor", requested)
    
    # Request updating the ImageProcessor in the event dispatch thread,
    # given that the "setProcessor" method call will trigger
    # a change in the dimensions of the image window
    SwingUtilities.invokeAndWait(lambda: self.imp.setProcessor(ip))

    # Terminate recurrent execution if so requested
    if self.getState("shutdown"):
      self.scheduled_executor.shutdown()

  def destroy(self):
    self.putState("shutdown", True)

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

  previewer.destroy()

scaleImageUI()

