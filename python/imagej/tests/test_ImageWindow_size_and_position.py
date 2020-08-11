from ij import IJ

imp = IJ.getImage()

win = imp.getWindow()
win.setLocation(100, 100)

win.getCanvas().setMagnification(2.0)
win.getCanvas().setSize(1024, 1024)
win.pack()