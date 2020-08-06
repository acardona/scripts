from ij import ImageListener, ImagePlus

# Function to be used for all methods of the implemented interface
def spyImageEvents(self, imp):
  print "Event on image:", imp

# New class definition
spying_class = type('Spying', # the name of the class
                    (ImageListener,), # the tuple of interfaces to implement
                    {"imageOpened": spyImageEvents, # the methods of the interfaces
                     "imageUpdated": spyImageEvents,
                     "imageClosed": spyImageEvents})

# Create a new instance
instance = spying_class()

ImagePlus.addImageListener(instance)