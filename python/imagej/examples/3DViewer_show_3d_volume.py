from ij3d import Image3DUniverse
from org.scijava.java3d import View
from ij import IJ
from isosurface import SmoothControl

univ = Image3DUniverse(512, 512) # view size, not universe size
univ.getViewer().getView().setProjectionPolicy(View.PERSPECTIVE_PROJECTION)
univ.show()

#imp = IJ.openImage("/home/albert/lab/projects/20170112_small_animals/chameleon/Brookeesia-chameleon-sagital-flat.am")
#imp = IJ.getImage()
resample = 4
#univ.addVoltex(imp, None, imp.getTitle(), 0, [True, True, True], resample)

brain_hemisphere_left = "/home/albert/lab/projects/20170112_small_animals/chameleon/Brookesia-segmented-brain-volumes/brain-hemisphere-left.zip"
brain_hemisphere_right = "/home/albert/lab/projects/20170112_small_animals/chameleon/Brookesia-segmented-brain-volumes/brain-hemisphere-right.zip"
brain_rest = "/home/albert/lab/projects/20170112_small_animals/chameleon/Brookesia-segmented-brain-volumes/rest-of-brain.zip"

c1 = univ.addMesh(IJ.openImage(brain_hemisphere_left), resample)
c2 = univ.addMesh(IJ.openImage(brain_hemisphere_right), resample)
c3 = univ.addMesh(IJ.openImage(brain_rest), resample)

c1.setLocked(True)
c2.setLocked(True)
c3.setLocked(True)

sc = SmoothControl(univ)