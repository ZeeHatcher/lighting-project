from graphics import *

class VirtualLightstick:
    PADDING = 2
    PIXEL_SIZE = 8

    def __init__(self, num_pixels):
        self._num_pixels = num_pixels

        # Initialize window object
        win = GraphWin("Virtual Lightstick",
            ((VirtualLightstick.PADDING * 2) + num_pixels) * VirtualLightstick.PIXEL_SIZE, # width
            ((VirtualLightstick.PADDING * 2) + 1) * VirtualLightstick.PIXEL_SIZE # height
        )
        win.setBackground("black")
        win.autoflush = False
        self._win = win

        # Initialize "pixels"
        pixels = []
        y = VirtualLightstick.PADDING * VirtualLightstick.PIXEL_SIZE
        for i in range(num_pixels): 
            x = (VirtualLightstick.PADDING + i) * VirtualLightstick.PIXEL_SIZE
            p1 = Point(x, y)
            p2 = Point(x + VirtualLightstick.PIXEL_SIZE, y + VirtualLightstick.PIXEL_SIZE)

            pixels.append(Rectangle(p1, p2))
            pass
        
        self._pixels = pixels

    def update(self, c_r, c_g, c_b):
        for i in range(self._num_pixels):
            color = color_rgb(
                c_r[i],
                c_g[i],
                c_b[i]
            )

            pixel = self._pixels[i]
            pixel.undraw()
            pixel.setFill(color)
            pixel.draw(self._win)

        self._win.update()
