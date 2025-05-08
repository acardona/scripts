#!/usr/bin/env python

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

rootpath = "/net/zstore1/FIBSEM/MR1.3-1/registration"

sectionlist = pd.read_csv(rootpath + "/csv/sections-list.csv")
sectionlist["time"] = [gn[12:-1] for gn in sectionlist["groupName"]]
sectionlist["time"] = pd.to_datetime(sectionlist.time, format="%y-%m-%d_%H%M%S")
sectionlist["dt"] = sectionlist["time"].diff().dt.total_seconds()

print(sectionlist[sectionlist["dt"] > 1000])

old = pd.read_csv(rootpath + "/matrices_smallgrid_20k.csv")
total = sectionlist.join(old)
total["magnitude"] = np.sqrt(total["m02"].diff()**2 + total["m12"].diff()**2)

# Filter out rows with NaN values in 'dt' and 'magnitude'
filtered_total = total.dropna(subset=["dt", "magnitude"])

# Create a log-log scatter plot
plt.figure(figsize=(10, 6))
plt.scatter(filtered_total["dt"], filtered_total["magnitude"], alpha=0.5, label="Data points")

# Perform linear regression on the log-transformed data
#log_dt = np.log(filtered_total["dt"])
#log_magnitude = np.log(filtered_total["magnitude"])
#slope, intercept = np.polyfit(log_dt, log_magnitude, 1)
#regression_line = slope * log_dt + intercept

# Plot the regression line
#plt.plot(filtered_total["dt"], np.exp(regression_line), color='red', label=f'Regression line: y = {np.exp(intercept):.2f} * x^{slope:.2f}')

# Set the scale to log
plt.xscale('log')
plt.yscale('log')

# Add labels and title
plt.xlabel('Time gap [s]')
plt.ylabel('Distance between consecutive translations [pixels]')
#plt.legend()

# Display the plot
plt.savefig("section_dt.png")