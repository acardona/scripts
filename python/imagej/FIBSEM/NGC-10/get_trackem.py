from ini.trakem2.display import Display
import os

print "\n"
start=True
outputstring = '"m00","m01","m02","m10","m11","m12"'
for patch in Display.getFront().getLayer().getPatches(True):
  if start:
  	fileroot = "_".join(patch.filePath.split("_")[0:3]) + "_"
  	fileroot = fileroot.replace("tmp/", "")
  	print fileroot+".csv"
  	roottrans = patch.getAffineTransform()
  	rootx = roottrans.getTranslateX()
  	rooty = roottrans.getTranslateY()
  	print "Root tile:",rootx, rooty
  	start = False
  transform = patch.getAffineTransform()
  tx = transform.getTranslateX()
  ty = transform.getTranslateY()
  outputstring += "\n1.0,0.0,{0},0.0,1.0,{1}".format(tx-rootx, ty-rooty)
print(outputstring)

with open(fileroot+".csv", "w") as f:
	f.write(outputstring)
	
imfile = fileroot.replace("montage-csv", "montage-csv/scaled-montages")+".tif"
os.remove(imfile)
print "Removed:", imfile
	
