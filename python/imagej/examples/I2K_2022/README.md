### I2K 2022 ImgLib2 scripting tutorial in jython

See the instructions for the Fiji [Script Editor](https://imagej.net/scripting/script-editor).

Video recording of the workshop will follow soon.


### Further ImgLib2 scripting resources

See the [Python Scripting Tutorial for Fiji](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html), in jython. In particular these entries are most relevant:

- [ImgLib2: writing generic, high-performance image processing programs](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#s11)
- [Views of an image, with ImgLib2](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#imglib2-views)
- [Create images](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#imglib2-create-img)
- [Transform an image using ImgLib2](://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#imglib2-transform)
- [Rotating image volumes with ImgLib2](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#imglib2-rotations)
- On CellImg, see e.g., [Representing the whole 4D series as an ImgLib2 image](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#imglib2-vol4d)
- On [Visualizing the whole 4D series](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#imglib2-vol4d-visualization) as an ImageJ virtual stack with Z and time axes, or with the BigDataViewer.
- On cached CellImg for loading large volumes piece-wise on demand: [Browse large image stacks by loading them piece-wise with CachedCellImg](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#load-piece-wise-CachedCellImg)
 - [Express folder of 3D stacks as a 4D ImgLib2 volume](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#load-4D-as-cachedCellImg-N5), and export to N5 and compare loading from N5
- Mathematical operations between images: [ImgMath: a high-level library for composing low-level pixel-wise operations](https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial/index.html#ImgMath)

There are many more, search for "net.imglib2" or directly for ImgLib2 class names to find many example scripts.

### ImgLib2 core data structures

The published paper explains ImgLib2's core architecture and data structures:

Pietzsch T, Preibisch S, Tomančák P, Saalfeld S. [ImgLib2—generic image processing in Java](https://academic.oup.com/bioinformatics/article-abstract/28/22/3009/240540). Bioinformatics. 2012 Nov 15;28(22):3009-11.

See also the [ImgLib2](https://imagej.net/libs/imglib2/) entry in the Fiji wiki, with pointers to the [documentation](https://imagej.net/libs/imglib2/documentation) and [examples](https://imagej.net/libs/imglib2/examples) (in java).


