# Functions to manipulate and compare strings.
# Albert Cardona 2018

def commonSubstring(pair):
    """
    Given a pair of strings (tuple or list of 2),
    find the common substring starting at index 0.

    Returns the substring if found, else None.
    """

    s1, s2 = pair

    for i, c in enumerate(s1):
        if s2[i] == c:
            continue
        return s1[:i]
    else:
        # Fully identical
        return s1

    return None

