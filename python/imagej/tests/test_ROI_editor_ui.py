# Albert Cardona 2019-06-20
# Based on code written previously for lib/isoview_ui.py

from ij import IJ, ImagePlus, ImageListener
from ij.gui import RoiListener, Roi
from java.awt.event import KeyEvent, KeyAdapter, MouseWheelListener, WindowAdapter
from java.awt import Color, Rectangle, Dimension, GridBagLayout, GridBagConstraints as GBC
from javax.swing import JFrame, JPanel, JLabel, JTextField, BorderFactory, JOptionPane


class RoiMaker(KeyAdapter, MouseWheelListener):
  def __init__(self, textfields, index):
    """ textfields: the list of 4 textfields for x,y,width and height.
        index: of the textfields list, to chose the specific textfield to listen to. """
    self.textfields = textfields
    self.index = index
  
  def parse(self):
    """ Read the text in textfields[index] and parse it as a number.
        When not a number, fail gracefully, print the error and paint the field red. """
    try:
      return int(self.textfields[self.index].getText())
    except:
      print "Can't parse integer from text: '%s'" % self.textfields[self.index].getText()
      self.textfields[self.index].setBackground(Color.red)

  def update(self, inc):
    """ Set the rectangular ROI defined by the textfields values onto the active image. """
    value = self.parse()
    if value:
      self.textfields[self.index].setText(str(value + inc))
      imp = IJ.getImage()
      if imp:
        imp.setRoi(Roi(*[int(tf.getText()) for tf in self.textfields]))

  def keyReleased(self, event):
    """ If an arrow key is pressed, increase/decrese by 1.
        If text is entered, parse it as a number or fail gracefully. """
    self.textfields[self.index].setBackground(Color.white)
    code = event.getKeyCode()
    if KeyEvent.VK_UP == code or KeyEvent.VK_RIGHT == code:
      self.update(1)
    elif KeyEvent.VK_DOWN == code or KeyEvent.VK_LEFT == code:
      self.update(-1)
    else:
      self.update(0)
  
  def mouseWheelMoved(self, event):
    """ Increase/decrese value by 1 according to the direction of the mouse wheel rotation. """
    self.update(- event.getWheelRotation())


class RoiFieldListener(RoiListener):
  def __init__(self, textfields):
    self.textfields = textfields
  
  def roiModified(self, imp, ID):
    """ When the ROI of the active image changes, update the textfield values. """
    if imp != IJ.getImage():
      return # ignore if it's not the active image
    roi = imp.getRoi()
    if roi:
      bounds = roi.getBounds()
    if not roi or 0 == roi.getBounds().width + roi.getBounds().height:
      bounds = Rectangle(0, 0, imp.getWidth(), imp.getHeight())
    self.textfields[0].setText(str(bounds.x))
    self.textfields[1].setText(str(bounds.y))
    self.textfields[2].setText(str(bounds.width))
    self.textfields[3].setText(str(bounds.height))


class CloseControl(WindowAdapter):
  def __init__(self, roilistener):
    self.roilistener = roilistener
  
  def windowClosing(self, event):
    answer = JOptionPane.showConfirmDialog(event.getSource(),
                                          "Are you sure you want to close?",
                                          "Confirm closing",
                                          JOptionPane.YES_NO_OPTION)
    if JOptionPane.NO_OPTION == answer:
      event.consume() # Prevent closing
    else:
      Roi.removeRoiListener(self.roilistener)
      event.getSource().dispose() # close the JFrame


def specifyRoiUI(roi=Roi(0, 0, 0, 0)):
  # A panel in which to place UI elements
  panel = JPanel()
  panel.setBorder(BorderFactory.createEmptyBorder(10,10,10,10))
  gb = GridBagLayout()
  panel.setLayout(gb)
  gc = GBC()
  
  bounds = roi.getBounds() if roi else Rectangle()
  textfields = []
  roimakers = []

  # Basic properties of most UI elements, will edit when needed
  gc.gridx = 0 # can be any natural number
  gc.gridy = 0 # idem.
  gc.gridwidth = 1 # when e.g. 2, the UI element will occupy two horizontally adjacent grid cells 
  gc.gridheight = 1 # same but vertically
  gc.fill = GBC.NONE # can also be BOTH, VERTICAL and HORIZONTAL
  
  for title in ["x", "y", "width", "height"]:
    # label
    gc.gridx = 0
    gc.anchor = GBC.EAST
    label = JLabel(title + ": ")
    gb.setConstraints(label, gc) # copies the given constraints 'gc',
                                 # so we can modify and reuse gc later.
    panel.add(label)
    # text field, below the title
    gc.gridx = 1
    gc.anchor = GBC.WEST
    text = str(getattr(bounds, title)) # same as e.g. bounds.x, bounds.width, ...
    textfield = JTextField(text, 10) # 10 is the size of the field, in digits
    gb.setConstraints(textfield, gc)
    panel.add(textfield)
    textfields.append(textfield) # collect all 4 created textfields for the listeners
    # setup ROI and text field listeners
    listener = RoiMaker(textfields, len(textfields) -1) # second argument is the index of textfield
                                                        # in the list of textfields.
    roimakers.append(listener)
    textfield.addKeyListener(listener)
    textfield.addMouseWheelListener(listener)
    # Position next ROI property in a new row by increasing the Y coordinate of the layout grid
    gc.gridy += 1

  # User documentation (uses HTML to define line breaks)
  doc = JLabel("<html><body><br />Click on a field to active it, then:<br />"
            + "Type in integer numbers<br />"
            + "or use arrow keys to increase by 1<br />"
            + "or use the scroll wheel on a field.</body></html>")
  gc.gridx = 0 # start at the first column
  gc.gridwidth = 2 # Spans both columns
  gb.setConstraints(doc, gc)
  panel.add(doc)
  
  # Listen to changes in the ROI of imp
  roilistener = RoiFieldListener(textfields)
  Roi.addRoiListener(roilistener)

  # Show window
  frame = JFrame("Specify rectangular ROI")
  frame.getContentPane().add(panel)
  frame.pack()
  frame.setLocationRelativeTo(None) # center in the screen
  frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE) # prevent closing the window
  frame.addWindowListener(CloseControl(roilistener)) # handles closing the window
  frame.setVisible(True)


imp = IJ.getImage()
specifyRoiUI(roi=imp.getRoi() if imp else None)
