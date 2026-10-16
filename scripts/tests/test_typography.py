"""Lossless path compaction and editable typography metadata checks."""

from decimal import Decimal
import unittest
import xml.etree.ElementTree as ET

from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path

import typography


class TypographyTests(unittest.TestCase):
    def test_smooth_quadratics_preserve_q_t_q_geometry(self):
        source = "M0 0Q1 1 2 2Q3 3 4 4T6 6Q7 7 8 8"
        compact = typography.compact_quadratic_commands(source)
        self.assertEqual(compact, "M0 0Q1 1 2 2T4 4T6 6T8 8")
        before, after = RecordingPen(), RecordingPen()
        parse_path(source, before)
        parse_path(compact, after)
        self.assertEqual(before.value, after.value)

    def test_line_cubic_and_new_subpaths_reset_the_quadratic_control(self):
        source = ("M0 0Q1 1 2 2Q3 3 4 4L6 6Q8 8 9 9"
                  "C10 10 11 11 12 12Q13 13 14 14"
                  "M20 20Q25 25 30 30ZQ40 40 50 50")
        compact = typography.compact_quadratic_commands(source)
        self.assertIn("L6 6Q8 8 9 9", compact)
        self.assertIn("C10 10 11 11 12 12Q13 13 14 14", compact)
        self.assertIn("M20 20Q25 25 30 30ZQ40 40 50 50", compact)
        before, after = RecordingPen(), RecordingPen()
        parse_path(source, before)
        parse_path(compact, after)
        self.assertEqual(before.value, after.value)

    def test_close_decimal_controls_are_not_treated_as_exact_reflections(self):
        source = "M0 0Q.1 .1 .2 .2Q.30000000000000001 .3 .4 .4"
        self.assertEqual(typography.compact_quadratic_commands(source), source)

    def test_relative_artwork_and_arcs_are_left_intact(self):
        for source in ("M0 0q1 1 2 2q1 1 2 2", "M0 0A2 2 0 0 0 4 4"):
            self.assertEqual(typography.compact_quadratic_commands(source), source)

    def test_decimal_spellings_compact_without_removing_separators(self):
        source = "M10.0 0.50L-0.50+0.50Q2.500 3.0 4.0 5.0Z"
        self.assertEqual(typography.compact_path_numbers(source),
                         "M10 .5L-.5+0.5Q2.5 3 4 5Z")

    def test_every_numeric_value_is_preserved_including_exponents(self):
        source = "M-0.0 +0.000L0.500 100.000C1.250e-3 -2.0E+4 .500 1. 2 3Z"
        compact = typography.compact_path_numbers(source)
        numbers = lambda data: [Decimal(n) for n in typography.PATH_NUMBER.findall(data)]
        self.assertEqual(numbers(source), numbers(compact))
        self.assertIn("1.250e-3 -2.0E+4", compact)

    def test_absolute_relative_curves_and_arcs_keep_the_same_geometry(self):
        source = ("M10.0 20.0h0.50v-0.50l1.00 2.00Q3.0 4.0 5.0 6.0"
                  "C7.0 8.0 9.0 10.0 11.0 12.0a4.0 5.0 0.0 0 1 6.0 7.0Z")
        before, after = RecordingPen(), RecordingPen()
        parse_path(source, before)
        parse_path(typography.compact_path_numbers(source), after)
        self.assertEqual(before.value, after.value)

    def test_reoutlining_is_idempotent_and_preserves_editable_metadata(self):
        source = ('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="80">'
                  '<text x="160" y="35" font-size="16" font-weight="450" '
                  'font-family="Manrope" text-anchor="middle" fill="#e6edf3">'
                  'C++ / Python</text></svg>')
        outlined = typography.outline_svg(source)
        self.assertEqual(outlined, typography.outline_svg(outlined))
        root = ET.fromstring(outlined)
        group = next(g for g in root.iter() if "data-text" in g.attrib)
        self.assertEqual(group.attrib, {
            "data-text": "C++ / Python", "data-family": "sans", "data-size": "16.0",
            "data-weight": "450.0", "data-spacing": "0.0", "data-x": "160.0",
            "data-y": "35.0", "data-anchor": "middle", "fill": "#e6edf3",
        })
        original_path = typography.text_path("C++ / Python", 160, 35, 16, 450,
                                             "sans", 0, "middle")
        before, after = RecordingPen(), RecordingPen()
        parse_path(original_path, before)
        parse_path(group[0].get("d"), after)
        self.assertEqual([command for command, _ in before.value],
                         [command for command, _ in after.value])
        for (_, original_points), (_, compact_points) in zip(before.value, after.value):
            self.assertEqual(len(original_points), len(compact_points))
            for original, compact in zip(original_points, compact_points):
                for original_coordinate, compact_coordinate in zip(original, compact):
                    self.assertAlmostEqual(original_coordinate, compact_coordinate, places=10)
        self.assertLess(len(group[0].get("d")), len(original_path))


if __name__ == "__main__":
    unittest.main()
