#!/usr/bin/env python3

import pandas as pd
import glob

slices = ["06-01_175524", "06-01_175617", "06-01_175709", "06-01_175801", "06-01_175853", "06-01_175946", "06-01_180038", "06-01_180130"]

rootpath = "/net/zstore1/FIBSEM/MR1.3-1/registration"

for slice in slices:
    csv = glob.glob(f"{rootpath}/csv/*{slice}*.csv")
    csvZ =sorted(glob.glob(f"{rootpath}/csvZ/*{slice}_.M*.csv"))
    print(csv,csvZ)