import unittest
import lighting

class TestColor(unittest.TestCase):

    def test_values(self):
        color = lighting.Color("FF0000")

        self.assertEqual(color.r, 255)
        self.assertEqual(color.g, 0)
        self.assertEqual(color.b, 0)

    def test_invalid_color(self):
        color = lighting.Color("0")

        self.assertEqual(color.r, 0)
        self.assertEqual(color.g, 0)
        self.assertEqual(color.b, 0)

class TestBasicMode(unittest.TestCase):

    def setUp(self):
        self.mode = lighting.BasicMode()
        self.patterns = {
            1: lighting.SolidPattern,
            2: lighting.DotPattern,
            3: lighting.BlinkPattern,
            4: lighting.BreathePattern,
            5: lighting.RainbowPattern,
            6: lighting.WavePattern,
        }

    def test_get_pattern(self):
        for i, pattern in self.patterns.items():
            lighting.locked_data.shadow_state["pattern"] = i
            self.mode._get_pattern()

            self.assertEqual(self.mode._pattern_id, i)
            self.assertIsInstance(self.mode._pattern, pattern)

    def test_output_length(self):
        for i in self.patterns:
            lighting.locked_data.shadow_state["pattern"] = i
            self.mode._get_pattern()

            c_r, c_g, c_b = self.mode.run()
            self.assertEqual(len(c_r), lighting.NUM_PIXELS)
            self.assertEqual(len(c_g), lighting.NUM_PIXELS)
            self.assertEqual(len(c_b), lighting.NUM_PIXELS)

    def test_solid_pattern(self):
        lighting.locked_data.shadow_state["pattern"] = 1
        lighting.locked_data.shadow_state["colors"].append("FF0000")

        colored = bytearray([255] * lighting.NUM_PIXELS)

        c_r, c_g, c_b = self.mode.run()
        self.assertEqual(c_r, colored)

    def test_dot_pattern(self):
        lighting.locked_data.shadow_state["pattern"] = 2
        lighting.locked_data.shadow_state["colors"].append("FF0000")

        for i in range(lighting.NUM_PIXELS):
            c_r, c_g, c_b = self.mode.run()
            if i > 0: # Behind dot
                for v in c_r[:i]:
                    self.assertEqual(v, 0)

            self.assertEqual(c_r[i], 255) # Dot

            if i < lighting.NUM_PIXELS - 1: # In front of dot
                for v in c_r[i+1:]:
                    self.assertEqual(v, 0)

    def test_blink_pattern(self):
        lighting.locked_data.shadow_state["pattern"] = 3
        lighting.locked_data.shadow_state["colors"].append("FF0000")

        colored = bytearray([255] * lighting.NUM_PIXELS)
        not_coloured = bytearray([0] * lighting.NUM_PIXELS)

        for i in range(6):
            c_r, c_g, c_b = self.mode.run()
            if i < 3:
                self.assertEqual(c_r, colored)
            else:
                self.assertEqual(c_r, not_coloured)

    def test_blink_pattern(self):
        lighting.locked_data.shadow_state["pattern"] = 4
        lighting.locked_data.shadow_state["colors"].append("FF0000")

        c_r, c_g, c_b = self.mode.run()
        prev = 0

        for i in range(20):
            c_r, c_g, c_b = self.mode.run()
            if i > 10: # Fade out
                self.assertLessEqual(c_r[0], prev)
            else: # Fade in
                self.assertGreaterEqual(c_r[0], prev)
            prev = c_r[0]

    def test_blink_pattern(self):
        lighting.locked_data.shadow_state["pattern"] = 6
        lighting.locked_data.shadow_state["colors"].append("FF0000")
        lighting.locked_data.shadow_state["colors"].append("00FF00")

        for i in range(lighting.NUM_PIXELS):
            c_r, c_g, c_b = self.mode.run()

            if i < lighting.NUM_PIXELS - 1: # Color 1
                for v in c_r[i:]:
                    self.assertEqual(v, 255)

            if i > 0: # Color 2
                for v in c_g[:i]:
                    self.assertEqual(v, 255)

    def test_invalid_pattern(self):
        lighting.locked_data.shadow_state["pattern"] = 0

        not_coloured = bytearray([0] * lighting.NUM_PIXELS)

        c_r, c_g, c_b = self.mode.run()
        self.assertEqual(c_r, not_coloured)

class TestImageMode(unittest.TestCase):

    def setUp(self):
        self.mode = lighting.ImageMode()

    def test_image_size(self):
        c_r, c_g, c_b = self.mode.run()
        self.assertEqual(len(c_r), lighting.NUM_PIXELS)
        self.assertEqual(len(c_g), lighting.NUM_PIXELS)
        self.assertEqual(len(c_b), lighting.NUM_PIXELS)

    def test_output(self):
        colored = bytearray([255] * 48)

        c_r, c_g, c_b = self.mode.run()

        self.assertEqual(c_r[:48], colored)
        self.assertEqual(c_g[48:96], colored)
        self.assertEqual(c_b[96:], colored)

if __name__ == '__main__':
    unittest.main()
