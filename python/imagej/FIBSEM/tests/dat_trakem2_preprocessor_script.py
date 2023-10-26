import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readFIBSEMdat

# Variables "patch" and "imp" were injected by TrakEM2 preprocessor script engine
imp_dat = readFIBSEMdat(patch.getProperty("source_path"), channel_index=0, asImagePlus=True)[0]
imp.setProcessor(imp_dat.getProcessor())
