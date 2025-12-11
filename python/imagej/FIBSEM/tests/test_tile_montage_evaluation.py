import os, sys
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.montage2d import evaluateMontage

tilePaths = [
  "/net/fibserver1/raw/Nicolo_S9_02122024/Y2025/M01/D08/Merlin-WEMS_25-01-08_144312_0-0-0.dat",
  "/net/fibserver1/raw/Nicolo_S9_02122024/Y2025/M01/D08/Merlin-WEMS_25-01-08_144312_0-0-1.dat",
  "/net/fibserver1/raw/Nicolo_S9_02122024/Y2025/M01/D08/Merlin-WEMS_25-01-08_144312_0-1-0.dat",
  "/net/fibserver1/raw/Nicolo_S9_02122024/Y2025/M01/D08/Merlin-WEMS_25-01-08_144312_0-1-1.dat"
]

groupName = "Merlin-WEMS_25-01-08_144312_"
csvDir = "/net/fibserver1/raw/Nicolo_S9_02122024/registration/montage-csv/"
offset  =  80 # pixels The left margin of each image is severely elastically deformed.
overlap = 990 # pixels
params_pixels = {
  "invert": True,
  "CLAHE_params": [200, 255, 2.0], # blockRadius, n_bins, and slope in stdDevs
  "as8bit": True,
  "contrast": (500, 1000), # thresholds in pixel counts per histogram bin
  "roiFn": lambda sp: Roi(sp.width / 6, sp.height / 6, 2 * sp.width / 3, 2 * sp.height / 3), # middle 2/3rds to discard edges
  "interim_scale": 0.125, # for saving montaged snapshops to disk to be used for evaluation and serial alignment
}

print evaluateMontage(groupName, tilePaths, csvDir, overlap, offset, params_pixels)
