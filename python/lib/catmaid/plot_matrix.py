from lib.util.csv import parseLabeledMatrix
from lib.util.matrix import combineConsecutivePairs
from lib.plotting.matrix_plot import matrix_plot
import numpy as np

def plotMergedNormalized(matrix_csv_path, measurements_csv_path, fix, single, joint, params):
    """
    Return the matplotlib 'fig, ax, c' instances of a matrix plot, created
    by merging the left-right homologous pairs in the matrix_csv_path
    and normalizing by the total amount of inputs as present in the measurements_csv_path.
    'fix': (optional, can be None) a function that receives 3 arguments: row_names, column_names and matrix, and returns the same 3 arguments, fixing ordering etc. as necessary.
    'single': synapse count threshold for an individual connection. 3 can be a reasonable value.
    'joint': synapse count threshold for a joint left-right homologous pair of connections. 10 can be a reasonable value.
    'params': contains keyword arguments for the plot, with defaults:
        x_axis_at_top=True,
        cmap='Blues',
        with_values=True,
        fmt='%i',
        hideZeros=True,
        value_range=(0, 25),
        cm_dimensions=(30, 25))
    """
    if not fix:
        def fix(*args):
            return args
    # Load
    row_names, column_names, matrix = fix(*parseLabeledMatrix(matrix_csv_path, cast=float, separator=','))

    # Load the table of measurements
    neuron_names, measurement_names, measurements = parseLabeledMatrix(measurements_csv_path, cast=float, separator=',')
    # Create map of neuron name vs amount of postsynaptic sites in its arbor
    # Index 4 (column 4) of measurements is "N inputs"
    n_inputs = {name: row[4] for name, row in zip(neuron_names, measurements)}

    # Normalize: divide each value by the total number of postsynaptic sites in the entire postsynaptic neuron.
    normalized = []
    for row in matrix:
        normalized.append([a / n_inputs[name] for name, a in zip(column_names, row)])

    # Merge left and right partners:
    # Requires both left and right having at least 3 synapses, and the sum at least 10
    # Uses the matrix of synapse counts to filter, but returns values from the normalized matrix.
    def mergeFn(matrix, rowIndex1, rowIndex2, colIndex1, colIndex2):
        row11 = matrix[rowIndex1][colIndex1]
        row12 = matrix[rowIndex1][colIndex2]
        row21 = matrix[rowIndex2][colIndex1]
        row22 = matrix[rowIndex2][colIndex2]
        if (row11 >= single or row12 >= single) and (row21 >= single or row22 >= single) and row11 + row12 + row21 + row22 >= joint:
            n11 = normalized[rowIndex1][colIndex1]
            n12 = normalized[rowIndex1][colIndex2]
            n21 = normalized[rowIndex2][colIndex1]
            n22 = normalized[rowIndex2][colIndex2]
            s = 0.0
            count = 0
            for n_syn, norm in zip([row11, row12, row21, row22], \
                                   [  n11,   n12,   n21,   n22]):
                if n_syn >= 3:
                    s += norm
                    count += 1
            return (s / count) * 100 if count > 0 else 0
        return 0

    combined = combineConsecutivePairs(matrix, aggregateFn=mergeFn, withIndices=True)

    # Merge names: remove the " LEFT" and " RIGHT" suffixes
    row_names = [name[:name.rfind(' ')] for name in row_names[::2]]
    column_names = [name[:name.rfind(' ')] for name in column_names[::2]]

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

