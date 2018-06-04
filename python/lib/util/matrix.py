# A library to manipulate matrix objects,
# defined as a list (of rows) of lists (the column values of each row).
# Albert Cardona 2018
#
# TODO: replace with functions from the pandas library, if these exist.

from PIL import Image
from itertools import chain
from lib.util.csv import parseLabeledMatrix
from lib.plotting.matrix_plot import matrix_plot
import numpy as np

def combineConsecutivePairs(matrix, aggregateFn=sum, withIndices=False):
    """
    Combine consecutive pairs of rows and of columns
    (a square of 4 values) using the aggregating function
    which is given all 4 values as arguments.
        
    Assumes the matrix has an even number of rows and columns.
    Assumes the matrix has the interface of a list of lists.

    The aggregate function is a function with 4 arguments (row1[i], row1[i+1], row2[i], row2[i+i] or, with withIndices is True, with arguments (matrix, rowIndex1, rowIndex2, columnIndex1, columnIndex2), and returns a single value.

    Returns the matrix as a list (of rows) of lists (the column values of each row)
    """

    combined_matrix = []

    if withIndices:
        for k in range(0, len(matrix), 2):
            row = []
            for i in range(0, len(matrix[0]), 2):
                row.append(aggregateFn(matrix, k, k+1, i, i+1))
            combined_matrix.append(row)
    else:
        for row1, row2 in zip(matrix[::2], matrix[1::2]):
            row = []
            for i in range(0, len(row1), 2):
                row.append(aggregateFn(row1[i], row1[i+1],
                                       row2[i], row2[i+1]))
            combined_matrix.append(row)

    return combined_matrix

def createIntImage(matrix):
    """
    Return a 2d 32-bit signed integer image from a matrix of numerical values
    that can be read as a list (of rows) of lists (the column values of each row.)

    To save the image, call its "save('data.png')" method with a name ending in a specific extension such as ".png".
    To see the image, call its "show()" method
    """

    # A 32-bit signed integer image ('I' mode). See: https://pillow.readthedocs.io/en/3.1.x/handbook/concepts.html
    # For reference, 'L' is 8-bit greyscale
    #                'F' is 32-bit floating point pixels
    #                '1' is with 1-bit pixels
    #                'P' is 8-bit colors, using a look-up table or "palette"
    #                'RGB', 'RGBA', 'CMYK', 'YCbCr', 'LAB', 'HSV' 
    # There's also 'LA' (8-bit with alpha) and 'RGBa' (alpha premultiplied)
    image = Image.new('I', (len(matrix[0]), len(matrix)))
    image.putdata(tuple(int(val) for val in chain.from_iterable(matrix)))
    return image

