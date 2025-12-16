from ini.trakem2.display import Display
import os


front = Display.getFront()
current_layer = front.getLayer()
layer_set = front.getLayerSet()
layers = layer_set.getLayers()

for i in range(len(layers)):
	front.setLayer(layers.get(i))
	
	print "\n"
	print "Layer: ",1+i
	
	start=True
	outputstring = '"m00","m01","m02","m10","m11","m12"'
	for patch in Display.getFront().getLayer().getPatches(True):
		if start:
			fileroot = "_".join(patch.filePath.split("_")[0:3]) + "_"
			fileroot = fileroot.replace("tmp/", "")
			fileroot = "/net/fibserver1/raw/NGC-10/registration/montage-csv/" + os.path.split(fileroot)[1]
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
	if os.path.exists(imfile):
		os.remove(imfile)
		print "Removed:", imfile

	
