
# A library to analyze 4D volumes of neuronal activity imaging

Albert Cardona, 2018-2019

## Motivation

The Zlatic and Cardona labs set out to image and analyse neuronal activity in the whole central nervous system of the first instar _Drosophila_ larva. All work done in very close collaboration with Philipp Keller and his lab, in particular with Raghav Chhetri and Chen Wang, and with contributions from Burkhard Hoeckendorf and Leo Guignard.

The first data set analyzed, and for which this library was shaped, was acquired by Raghav Chhetri and Nadine Randel, using the [IsoView 4-camera lightsheet microscope]. The samples are dissected central nervous systems of first instar _Drosophila_ larvae, whose neurons express GCaMP6. Therefore, the neuronal activity is monitoring fictive behaviors, that can be read out by interpreting the temporal pattern of activity of e.g. motor neurons, as well as command neurons.


## The data to analyse

The data acquired consists in, per sample, a series of 5-minute intervals of imaging, interspersed with 5-minute intervals of recovery in the dark, for up to one hour.

Each time point consists of 4 camera views acquired over a total of 750 milliseconds. The first set of two cameras (CM00 and CM01) image the volume simultaneously by being mounted at 180-degree angle from each other and effectively imaging the same light sheet plane but from different sides, over the first 325 milliseconds. The second set of two cameras (CM02 and CM03) do exactly the same, over the last 325 milliseconds.

The goal is then to:
1. Register the 4 camera views to each other.
2. Fuse and deconvolve cameras CM00+CM01, and also CM02+CM03, reducing four views to only two 3D volumes per time point.
3. Register time points to each other, to correct for small spatial drift over time.
4. Detect all nuclei that are active at any time point.
5. Measure neuronal activity signal as deltaF/F, for all nuclei in all time points.


## The code

The library and programs are written in python for java: that is, [jython], which is an implementation of the [python 2.7] language for the java virtual machine. The code is meant to be run within [Fiji] with [java 8], using the [Script Editor].

For a general introduction to writing [python 2.7] programs for [Fiji] using all of [Fiji]'s libraries, see the [Fiji Scripting Tutorial]. In particular, check out the sections on [ImgLib2][scripting ImgLib2] and on [image registration][scripting image registration] with [custom features].

The code base is organized in 4 folders:

- **programs/** houses the python files to be executed.
- **util/** contains a number of secondary programs also as python files to be executed.
- **lib/** contains a number of python files declaring functions of various degrees of generality. It's use goes beyond the analsys of 4D volumes.
- **tests/** are python files that check the correctness of some library functions.


## Installation

Make sure you have [Fiji] installed and running, updated to the latest version (see its `Help - Update` menu).

Then open a terminal and type:

```
$ git clone https://github.com/acardona/scripts.git
```


## Running the programs

### Step 1: register views to each other

First we must discover the coarse transformations from all other cameras (CM01, CM02, CM03) to the first camera (CM00).

It is worth doing manually, as it is done only once per 4D data set: the transformations that relate views to each other are constant. To do so automatically would take a lot more time: volumes would have to be exhaustively cross-correlated to each other to find the translations, and there will be lots of error given the lack of deconvolution and the anisotropy of the volumes.

The coarse registration can be done in the [BigDataViewer] by loading all 4 views of a time point and rotating and translating each volume by pushing the arrow keys as appropriate. Then, read out the matrices from the saved XML file.

Here, instead I prefer to coarsely register all 4 volumes in the following way, using:

  **programs/register_IsoView_views_coarsely.py**

In this script, first we load all 4 3D volumes, then define an affine transform for each (as a matrix) that implements the expected rotation (plus appropriate translation that goes with it), and then load all 4 transformed views in an ImageJ hyperstack, where each channel is one of the 4 cameras. For simplicity, the first camera (CM00) has an identity transform. (The transforms are virtual thanks to [ImgLib2], no duplicated images are generated.)

By browsing the 4D stack across its "channels" and Z slices, you will notice that, despite the rotation being roughly right, there are still a number of translations pending.

A window will open with 3 rows, showing X, Y, Z text fields to edit the translation values of CM01, CM02, CM03 relative to CM00. Either type in a number and push return, or use the scroll wheel to adjust the values in each field.

This is how I do it: draw a rectangular ROI over a prominent feature, say the thickness of the nerve cord, in CM00 (the first frame). Then use the lower scroller in the image window to go to the CM01 (the second frame). Now adjust the X, Y position until the same recognized feature falls within the ROI.

Alternatively, run the script in "persistence" mode (it's a checkbox near the "Run" button in the [Script Editor] that must be ticked prior to pushing "Run"), and then you have access to the affine transforms `aff1`, `aff2`, and `aff3` to edit them directly: they are [AffineTransform3D] instances, with methods like e.g. `setTranslation(double[])` that you can call like e.g. `aff1.setTranslation([0.0, 10.5, 0.0])` to adjust the translation in the Y axis.


### Step 2: define a ROI for cropping

Once camera views are reasonably coarsely registered to the first view, draw a rectangular ROI to include only the parts of the XY plane that you want to include in further analysis. Reducing the amount of pixels to process downstream is a significant performance gain.

Write down the x, y, width, height of the rectangular ROI. Either read it from the "Edit - Selection - Specify..." dialog, or by typing into the python interpreter:

```
from ij import IJ
print IJ.getImage().getRoi()
```


### Step 3:

With these coarse transformation matrices, and the ROI, we now proceed to refine the registration of the camera views to each other, by using:

  **programs/register_IsoView_views_finely.py**

[//]: # (To be continued)




[jython]: https://www.jython.org/
[python 2.7]: https://docs.python.org/2.7/library/
[Fiji]: https://fiji.sc
[java 8]: https://docs.oracle.com/javase/8/docs/api/index.html
[Script Editor]: https://imagej.net/Using_the_Script_Editor
[Fiji Scripting Tutorial]: https://www.ini.uzh.ch/~acardona/fiji-tutorial/
[scripting ImgLib2]: https://www.ini.uzh.ch/~acardona/fiji-tutorial/#s11
[scripting image registration]: https://www.ini.uzh.ch/~acardona/fiji-tutorial/#s12
[custom features]: https://www.ini.uzh.ch/~acardona/fiji-tutorial/#custom-features
[IsoView 4-camera lightsheet microscope]: https://www.nature.com/articles/nmeth.3632
[BigDataViewer]: https://imagej.net/BigDataViewer
[AffineTransform3D]: https://github.com/imglib/imglib2-realtransform/blob/master/src/main/java/net/imglib2/realtransform/AffineTransform3D.java

