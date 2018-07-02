from lib.util.csv import parseLabeledMatrix
from lib.util.matrix import combineConsecutivePairs
from lib.plotting.matrix_plot import matrix_plot
from lib.catmaid.matrix.util import mergeNormalized
import numpy as np

def plotMergedNormalized(matrix_csv_path, measurements_csv_path, fix, single, joint, params):
    """
    Return the matplotlib 'fig, ax, c' instances of a matrix plot, created
    by merging the left-right homologous pairs in the matrix_csv_path
    according to rules involving the single and joint thresholds of synaptic counts,
    and normalizing by the total amount of inputs as present in the measurements_csv_path.
    'fix': (optional, can be None) a function that receives 3 arguments: row_names, column_names and matrix, and returns the same 3 arguments, fixing ordering etc. as necessary.
    'single': synapse count threshold for an individual connection. 3 can be a reasonable value.
    'joint': synapse count threshold for a joint left-right homologous pair of connections. 10 can be a reasonable value.
    'params': contains keyword arguments for the plot, with defaults:
        x_axis_at_top=True,
        cmap='Blues',
        with_values=True,
        fmt='%i', # can also be a function
        hideZeros=True,
        value_range=(0, 25),
        cm_dimensions=(30, 25))
    """
    combined, row_names, column_names = mergeNormalized(matrix_csv_path, measurements_csv_path, fix, single, joint)

    # Plot
    title = matrix_csv_path[:-4].replace('_', ' ')
    xlabel = None
    ylabel = None
    xticklabels = column_names
    yticklabels = row_names

    return matrix_plot(
            np.array(combined),
            title,
            xlabel, ylabel,
            xticklabels, yticklabels,
            **params)

