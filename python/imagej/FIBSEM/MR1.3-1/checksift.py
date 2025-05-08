#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import tifffile as tif

rootpath = "/net/zstore1/FIBSEM/MR1.3-1"
maxslice = 17367

if os.path.exists("pointcount.csv"):
    sectionlist = pd.read_csv("pointcount.csv")
else:
    sectionlist = pd.read_csv(rootpath + "/registration/csv/sections-list.csv")
    sectionlist["npoints"] = np.int32(np.zeros(len(sectionlist)))
    for i,row in sectionlist.iterrows():
        matchefiles = glob.glob(f"{rootpath}/registration/csvZ/{row.groupName}*.csv")
        npoints = 0
        for filename in matchefiles:
            pointmatches = pd.read_csv(filename, skiprows=2)
            npoints += len(pointmatches)
        sectionlist.loc[i,"npoints"] = npoints
    sectionlist.to_csv("pointcount.csv", index=False)

plt.plot(sectionlist.npoints)
plt.savefig("npoints.png")