# A library to manipulate matrix objects,
# defined as a list (of rows) of lists (the column values of each row).
# Albert Cardona 2018
#
# TODO: replace with functions from the pandas library, if these exist.

def combineConsecutivePairs(matrix, aggregateFn=sum):
    """
    Combine consecutive pairs of rows and of columns
    (a square of 4 values) using the aggregating function
    which is given all 4 values as arguments.
        
    Assumes the matrix has an even number of rows and columns.
    Assumes the matrix has the interface of a list of lists.

    Returns the matrix as a list (of rows) of lists (the column values of each row)
    """

    combined_matrix = []

    for row1, row2 in zip(matrix[::2], matrix[1::2]):
        row = []
        for i in range(0, len(row1), 2):
            row.append(aggregateFn(row1[i], row1[i+1],
                                   row2[i], row2[i+1]))
        combined_matrix.append(row)

    return combined_matrix

