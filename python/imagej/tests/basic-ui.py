from javax.swing import JFrame, JButton, JOptionPane
from ij import IJ, WindowManager as WM

def measure2(event):
  """ event: the ActionEvent that tells us about the button having been clicked. """
  imp = WM.getCurrentImage()
  print imp
  if imp:
    IJ.run(imp, "Measure", "")
  else:
    print "Open an image first."


def confirmWindowClosing(event):
  """ event: the WindowEvent that tells us what was done to the window. """
  answer = JOptionPane.showConfirmDialog(event.getSource(),  
                                         "Are you sure you want to close?",  
                                         "Confirm closing",  
                                         JOptionPane.YES_NO_OPTION)
  if JOptionPane.NO_OPTION == answer:
    event.consume() # prevent closing the window by cancelling the event
  else:
    event.getSource().dispose() # close the JFrame

frame = JFrame("Measure", visible=True, windowClosing=confirmWindowClosing)
button = JButton("Area", actionPerformed=measure2)
frame.getContentPane().add(button)
frame.pack()