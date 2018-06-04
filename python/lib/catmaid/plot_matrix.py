from lib.util.csv import parseLabeledMatrix
from lib.util.matrix import combineConsecutivePairs
from lib.plotting.matrix_plot import matrix_plot
import numpy as np

def plotMergedNormalized(matrix_csv_path, measurements_csv_path, single, joint, params):
    """
    Return the matplotlib 'fig, ax, c' instances of a matrix plot, created
    by merging the left-right homologous pairs in the matrix_csv_path
    and normalizing by the total amount of inputs as present in the measurements_csv_path.
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
    # Load
    row_names, column_names, matrix = parseLabeledMatrix(matrix_csv_path, cast=float, separator=',')

    # FANs are first, then FBNs. Reorder.
    # matrix: a list of lists, each inner list being a row.
    # First put the top 12*2 rows at the bottom
    matrix = matrix[24:] + matrix[:24]
    row_names = row_names[24:] + row_names[:24]
    # Second put the top 12*2 columns at the right
    matrix = [row[24:] + row[:24] for row in matrix]
    column_names = column_names[24:] + column_names[:24]

    # Load the table of measurements
    neuron_names, measurement_names, measurements = parseLabeledMatrix(measurements_csv_path, cast=float, separator=',')
    # Create map of neuron name vs amount of postsynaptic sites in its arbor
    # Index 4 (column 4) of measurements is "N inputs"
    n_inputs = {name: row[4] for name, row in zip(neuron_names, measurements)}

    # Normalize: divide each value by the total number of postsynaptic sites in the entire postsynaptic neuron.
    normalized = []
    for name, row in zip(neuron_names, matrix):
        b = n_inputs[name] # guaranteed to be above zero
        normalized.append([a/b for a in row])

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
    xticklabels = row_names
    yticklabels = column_names

    return matrix_plot(
            np.array(combined),
            title,
            xlabel, ylabel,
            xticklabels, yticklabels,
            **params)

