# albert Cardona 2019-05-12
# A script to make multiple cuts of a movie and then concatenate them.
# Use like e.g.:
#
# import sys
# from lib.movie.ffmpeg import cutMovie
# cutMovie("/path/to/movie.mp4",
#          [("1.51.48", "2.15.50"),
#           ("2.18.25", "2.20.25"),
#           ("2.30.50", "2.34.00")]
#          extra="-an")
# 
# Will create, in the same folder as the input_filepath movie,
# the cuts as independent movie files, a .txt file listing their filenames,
# and then the final concatenated cuts as a new movie.

import subprocess, os

def cutMovie(input_filepath, intervals, vcodec="libx264", pix_fmt="yuv420p", extra="", cuts_txt="cuts.txt"):
    """
    intervals: a list of pairs of strings or floats defining the input to
               ffmpeg's -ss (start timestamp) and the end time (that can be None,
               signaling run till the end), which is then used for the -t
               (duration) parameter.
    vcodec: defaults to "libx264".
    pix_fmt: defaults to "yuv420p", which enables e.g. MacOSX to play the movie.
    extra: optional, additional ffmpeg parameters like e.g. "-an" to remove audio.
    Returns the link to the concatenated movie.
    """

    def parseTime(time):
        if str == type(time):
            count = time.count('.')
            if 0 == count or 1 == count:
                # e.g. "24" (seconds) or "24.56" (seconds and milliseconds)
                return time
            if 2 == count:
                # e.g. "3.24.56" (minutes, seconds and milliseconds)
                u = time.split('.')
                return "%i.%s" % (int(u[0]) * 60 + int(u[1]), u[2][:2])
        if int == type(time):
            # e.g. 24 (seconds)
            return str(time)
        if float == type(time):
            # e.g. 24.56 (seconds and milliseconds)
            return "%.2f" % time
        if None == time:
            # used for signaling "until the end of the movie"
            return None
        raise Exception("Unknown time format: " + str(time))

    def parseInterval(start, end):
        s = float(parseTime(start))
        if end:
            return s, "%.2f" % (float(parseTime(end)) - s)
        else:
            return s, None

    # Parse time intervals
    intervals = [parseInterval(start, end) for start, end in intervals]

    folder, filename = os.path.split(input_filepath)
    os.chdir(folder)

    i_ext = filename.rfind('.')
    name = filename[:i_ext]
    extension = filename[i_ext+1:]

    cuts = []

    for start, end in intervals:
        output_filename = "%s_%s-%s.%s" % (name, start, end, extension)

        if os.path.exists(os.path.join(folder, output_filename)):
            answer = input("overwrite %s? [y/n]" % output_filename)
            if not answer.startswith('y'):
                break

        command = "ffmpeg -ss %s %s -i %s -vcodec %s -strict -2 -pix_fmt %s %s %s" % (start,
    "-t %s" % end if end else "", # None would mean until the end
    input_filepath,
    vcodec,
    pix_fmt,
    extra,
    output_filename)

        subprocess.call(command, shell=True)

        cuts.append("file '%s'" % output_filename)
    
    try:
        cuts_txt_filename = check_exists(cuts_txt if cuts_txt else "cuts.txt")
    except KeyboardInterrupt:
        # User pressed control+C
        print("Your cuts:")
        for cut in cuts:
            print(cut)
        return

    with open(cuts_txt_filename, 'w') as f:
        f.write("\n".join(cuts))

    cuts_movie = "%s-%s.%s" % (name, cuts_txt_filename[:-4] if cuts_txt_filename.endswith(".txt") else cuts_txt_filename, extension)
    command = "ffmpeg -f concat -safe 0 -i %s -c copy %s" % (cuts_txt_filename, cuts_movie)
    subprocess.call(command, shell=True)
    print("Done!")

    return os.path.join(folder, cuts_movie)


def check_exists(filename):
    if os.path.exists(filename):
        answer = input("overwrite '%s'? [y/N]" % filename)
        if not answer.startswith('y'):
            filename = input("new name: ")
            return check_exists(filename)
    return filename

