#!/usr/bin/env python

from tifffile import imread, imwrite
import numpy as np
import matplotlib.pyplot as plt
import os

rootpath = "/net/zstore1/FIBSEM/MR1.3-1/montages-400/"

box = [6750, 2630, 8440, 6950, 2830, 8640]

imsize = (2344, 2496)

scale = 6

x = int(6850/scale)
y = [int(2530/scale), int(2930/scale)]
z = [8490, 8590]

output = np.zeros((y[1]-y[0], z[1]-z[0]), dtype=np.uint8)

for slice in range(z[0], z[1]):
    path = os.path.join(rootpath, f"{slice}.tif")
    array = imread(path)
    output[:, slice-z[0]] = array[y[0]:y[1], x]
    array = None

# Scale up the image by a factor of 5
scale_factor = 5
output_scaled = np.kron(output, np.ones((scale_factor, scale_factor)))

# Update the output to the scaled version
output = output_scaled

# Convert to PNG and serve
png_path = "composite.png"

plt.imsave(png_path, output, cmap='gray')

import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        with open(png_path, 'rb') as f:
            self.set_header('Content-Type', 'image/png')
            self.write(f.read())

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(9100)
    tornado.ioloop.IOLoop.current().start()