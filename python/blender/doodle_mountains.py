# Albert Cardona 2022-01-21
# Using Blender 2.82a
import bpy
from mathutils import Matrix
from math import sin, pi, pow

# Clear the scene
# doesn't work:
#bpy.ops.object.select_all()
#bpy.ops.object.delete()
# So remove objects one by one
for o in bpy.context.collection.objects:
    bpy.context.collection.objects.unlink(o)


# Create a cube from scratch

# Make a new cube
bpy.ops.mesh.primitive_cube_add()
# New cube is automatically selected
cube = bpy.context.selected_objects[0]
cube.name = "block" # rename
# Place object center at 0, 0, 0
cube.data.transform(Matrix.Translation([1.0, 1.0, 1.0]))
# Make the sides be 1.0
cube.scale = (0.5, 0.5, 0.5)
cube.location = (0.0, 0.0, 0.0)

# Clone the cube: make a shallow copy, i.e. a new object that shares the mesh and other details
def clone(x, y, height):
    copy = cube.copy() # shallow
    copy.location = (x, y, 0.0)
    copy.scale.z *= height
    bpy.context.collection.objects.link(copy) # add to scene

def getZ(i, j):  
    z = 0  
    z += pow( sin( i / pi ) + 1, 2 )  
    z += ( sin( j / pi ) + 1 )  
    z += ( sin( j / pi ) + 1 )  
    return z

n = 100
m = 100
for i in range(n):
    for j in range(m):
        clone(i, j, getZ(i, j))

# Remove the template
bpy.context.collection.objects.unlink(cube)
