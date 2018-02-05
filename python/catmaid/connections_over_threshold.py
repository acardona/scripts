# Albert Cardona 2018-01-16
#
# Load CSV files exported from CATMAID's Connectivity Matrix widget
# that have been sorted by neuron name,
# then aggegate consecutive pairs of neurons (considered to be left-right homologs)
# by using the aggregate function specified below ('max', by default)
# and then print out the results
# and also export a CSV file with the results with 3 columns:
# presynaptic, postsynaptic, synaptic count

import sys
import os
from lib.util.csv import parseLabeledMatrix
from lib.util.string import commonSubstring
from lib.util.matrix import combineConsecutivePairs

# List of CSV files to process
# (Will export a results CSV file for each)
filenames = []

# Function to reduce four values (2 homologs onto 2 homologs) into one:
aggregate_fn = max
aggregate_fn_name = "max"

# Minimum number of synapses to consider per connection
threshold = 5

# Parse command line arguments
for arg in sys.argv[1:]:
    if arg.startswith("threshold="):
        try:
            threshold = int(arg[arg.rfind('=')+1:])
        except:
            print("ERROR: Invalid threshold value: " + arg)
            sys.exit(0)
    elif arg.startswith("aggregateFn="):
        fn_name = arg[arg.rfind('=')+1:]
        try:
            aggregate_fn = vars(__builtins__)[fn_name]
            aggregate_fn_name = fn_name
        except:
            print("ERROR: Function " + fn_name + " does not exist.")
            sys.exit(0)
    elif arg.endswith(".csv"):
        filenames.append(arg)
    else:
        print("WARNING: Ignoring argument: " + arg)

if 0 == len(filenames) or 1 == len(sys.argv):
    print("""
Usage:

$ python ./connections_over_threshold.py aggregateFn=max threshold=10 file1.csv file2.csv ... fileN.csv

Note aggregateFn is optional (defaults to sum), and so is threshold (defaults to 5).

""")
    sys.exit(0)

# The program
for filename in filenames:
    print("######################")
    print("For " + filename)
    print(" ")

    row_names, column_names, matrix = parseLabeledMatrix(filename, cast=int, separator=",")

    # Join consecutive pairs of rows and columns, which are the left and right homologs
    combined_matrix = combineConsecutivePairs(matrix, aggregateFn=aggregate_fn)

    # Construct the type name: the parts of the neuron names of two consecutive rows that are the same
    row_types = [commonSubstring(pair) for pair in zip(row_names[::2], row_names[1::2])]
    column_types = [commonSubstring(pair) for pair in zip(column_names[::2], column_names[1::2])]

    # Now find which connections have 5+ synapses
    found = []
    k = 1
    for j, row in enumerate(combined_matrix):
        for i, val in enumerate(row):
            if val >= threshold:
                print("[" + str(k) + "]: " + str(val) + " syn for " + row_types[j] + " -> " + column_types[i])
                found.append(",".join(['"' + row_types[j] + '"', '"' + column_types[i] + '"', str(val)]))
                k += 1

    # Export results as CSV, to the executing directory
    name = os.path.basename(filename)[:-4] + "_" + str(threshold) + "+.csv"
    with open(name, 'w') as f:
        f.write("\n".join(found))
        print("Saved this file in this directory: " + name)

