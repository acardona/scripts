#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob

rootpath = "/net/zstore1/FIBSEM/MR1.3-1/registration"

new = pd.read_csv(rootpath + "/csvZ/matrices.csv")
old = pd.read_csv(rootpath + "/matrices_05-02-05b.csv")
section = pd.read_csv(rootpath + "/csvZ-section/matrices.csv")
tenk = pd.read_csv(rootpath + "/matrices_10k_40k.csv")
twentyk = pd.read_csv(rootpath + "/matrices_20k_40k.csv")
fortyk = pd.read_csv(rootpath + "/matrices_40k_40k.csv")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

start = 8400
end = 8600

start = 0
end = 17000

ax1.plot(new["m02"][start:end], label="new")
ax1.plot(old["m02"][start:end], label="old")
#ax1.plot(section["m02"][start:end], label="section")
#ax1.plot(tenk["m02"][start:end], label="10k")
#ax1.plot(twentyk["m02"][start:end], label="20k")
#ax1.plot(fortyk["m02"][start:end], label="40k")
ax1.legend()
ax1.set_title("m02")

ax2.plot(new["m12"][start:end], label="new")
ax2.plot(old["m12"][start:end], label="old")
#ax2.plot(section["m12"][start:end], label="section")
#ax2.plot(tenk["m12"][start:end], label="10k")
#ax2.plot(twentyk["m12"][start:end], label="20k")
#ax2.plot(fortyk["m12"][start:end], label="40k")
ax2.legend()
ax2.set_title("m12")

plt.tight_layout()
plt.savefig("alignplot.png")

lastx = 0
lasty = 0
indices = []
for n, row in new.iterrows():
    magnitude = np.sqrt((row["m02"]-lastx)**2 + (row["m12"]-lasty)**2)
    if magnitude > 100:
        print(n, magnitude)
        indices.append(n)
    lastx = row["m02"]
    lasty = row["m12"]

indices += [index+2 for index in indices]
indices += [index+1 for index in indices]
indices += [index-1 for index in indices]
indices += [index-2 for index in indices]

indices = sorted(list(set(indices)))

indices = [i for i in range(406,433)]
indices += [1870,1871,1872]

sectionlist = pd.read_csv(rootpath + "/csv/sections-list.csv")
sectionlist = sectionlist.iloc[indices]

answer = input(f"Remove these {len(sectionlist)} sections? (y/n) ")

placeholder = "maxCurvature,rod,scale,blockRadius,meshResolution,minR,searchRadius\n1000.0,0.9,0.5,200,30,0.1,50\nx1,y1,x2,y2\n1000,1000,1000,1000"

if answer == "y":
    answer2 = input("Replace with placeholder? (y/n)")
    for _, row in sectionlist.iterrows():
        print(row["groupName"])
        filenames = glob.glob(rootpath+"/csvZ/" + row["groupName"]+"*")
        for filename in filenames:
            print("   ", filename)
            os.remove(filename)
            if answer2 == "y":
                with open(filename, "w") as f:
                    f.write(placeholder)