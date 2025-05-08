#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
import tifffile as tif


def cosine_sim(im1, im2):
    return np.dot(im1.flatten()/np.linalg.norm(im1), im2.flatten()/np.linalg.norm(im2))

rootpath = "/net/zstore1/FIBSEM/MR1.3-1"
maxslice = 17367

result = pd.DataFrame(columns=["slice", "cossim"])

threshold = 0.999

lastimage = tif.imread(f"{rootpath}/montages-400/1.tif")
indices = []
for slice in range(1,maxslice):  
    filename = f"{rootpath}/montages-400/{slice}.tif"
    if not os.path.exists(filename):
        continue
    image = tif.imread(filename)

    # Find the boundaries of the black border
    non_black_pixels = np.argwhere(image > 0)
    top_left = non_black_pixels.min(axis=0)
    bottom_right = non_black_pixels.max(axis=0)

    # Repeat for last image
    non_black_pixels = np.argwhere(lastimage > 0)
    top_left_last = non_black_pixels.min(axis=0)
    bottom_right_last = non_black_pixels.max(axis=0)
    
    # Get the intersection of the two
    top_left = np.maximum(top_left, top_left_last)
    bottom_right = np.minimum(bottom_right, bottom_right_last)

    cs = cosine_sim(lastimage[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]], image[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]])
    #result = result.append({"slice": slice, "cossim": cs}, ignore_index=True)
    if cs < threshold:
        #plt.imshow(image)
        #plt.savefig("{rootpath}/montages-400/cos_{slice}.png")
        print(slice, cosine_sim(lastimage, image))
        indices.append(slice)
#    plt.savefig(f"{rootpath}/coscheck/{slice}.png")
    lastimage = image

#indices = [1874,3611,6574,6575,7820,7821,9946,9948,9949,9950,9951,9952,10958,10959,10960,11292,11293,11294,11296,11297,11298,11299,11300,12226,12227,12228,15289,15814,15816,15817,15818,15819,15820,15821]
indices = [7813,7814,7815,7816,7817,7820,7821]

full_indices = [index-1 for index in indices]
full_indices += [index-2 for index in indices]
full_indices += [index-3 for index in indices]
full_indices += [index-4 for index in indices]
full_indices += [index-5 for index in indices]
full_indices += [index-6 for index in indices]
full_indices += [index-7 for index in indices]

indices = list(set(full_indices))

sectionlist = pd.read_csv(rootpath + "/registration/csv/sections-list.csv")
sectionlist = sectionlist.iloc[indices]


placeholder = "maxCurvature,rod,scale,blockRadius,meshResolution,minR,searchRadius\n1000.0,0.9,0.5,200,30,0.1,50\nx1,y1,x2,y2\n1000,1000,1000,1000"

answer = input(f"Remove these {len(sectionlist)} sections? (y/n) ")

if answer == "y":
    answer2 = input("Replace with placeholder? (y/n)")
    for i in indices:
        try:
            os.remove(f"{rootpath}/montages-400/{i}.tif")
        except:
            pass
    for _, row in sectionlist.iterrows():
        print(row["groupName"])
        filenames = glob.glob(rootpath+"/registration/csvZ/" + row["groupName"]+"*")
        for filename in filenames:
            print("   ", filename)
            try:
                os.remove(filename)
            except:
                pass
            if answer2 == "y":
                with open(filename, "w") as f:
                    f.write(placeholder)

