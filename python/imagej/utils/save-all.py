from ij import IJ, WindowManager as WM

target = "/home/albert/Desktop/bread/"
prefix = "indulgence-"

for imp in map(WM.getImage, WM.getIDList()):
  IJ.save(imp, target + prefix + imp.getTitle()[:-4] + ".jpg")
