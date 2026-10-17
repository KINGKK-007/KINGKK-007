"""Independent validation for README asset discovery and measured geometry."""

from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import unittest

from preview_profile import (desktop_payload, gradient_paint_is_visible, layout_issues,
                             local_asset, localize_images, readme_images,
                             rectangle_overlap, reusable_asset_evidence,
                             svg_issues, text_geometry_issues)


class ProfileLayoutTests(unittest.TestCase):
    def test_desktop_payload_deduplicates_fallbacks_and_excludes_picture_sources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets").mkdir()
            (root / "assets/shared.svg").write_bytes(b"12345")
            (root / "assets/phone.svg").write_bytes(b"123456789")
            html = '''<picture><source srcset="./assets/phone.svg">
              <img src="./assets/shared.svg?v=one"></picture>
              <img src="./assets/shared.svg?v=two">'''
            result = desktop_payload(html, root, baseline=100)
            self.assertEqual(result["unique_bytes"], 5)
            self.assertEqual(result["reference_bytes"], 10)
            self.assertEqual(result["maximum_bytes"], 110)
            self.assertEqual(result["unique_paths"], ["assets/shared.svg"])

    def test_asset_discovery_handles_queries_picture_sources_and_deduplication(self):
        document = '''<picture><source media="(max-width:480px)"
          srcset="./assets/mobile.svg?v=abc 1x, ./assets/mobile@2.svg 2x">
          <img src="./assets/desktop.svg?v=xyz" alt="An actual label"></picture>'''
        result = readme_images(document)
        self.assertEqual([item["path"] for item in result.references],
                         ["assets/mobile.svg", "assets/mobile@2.svg", "assets/desktop.svg"])
        self.assertEqual(result.images[0]["alt"], "An actual label")
        self.assertEqual(result.references[0]["media"], "(max-width:480px)")

    def test_asset_resolution_rejects_remote_unrelated_and_path_traversal(self):
        self.assertIsNone(local_asset("https://example.com/not-ours.svg"))
        self.assertIsNone(local_asset("./assets/../README.md"))
        self.assertIsNone(local_asset("./assets/%2e%2e/README.md"))
        self.assertEqual(local_asset("https://raw.githubusercontent.com/user/repo/main/assets/a.svg?v=1"),
                         "assets/a.svg")

    def test_localization_changes_only_asset_image_attributes(self):
        html = '<a href="https://example.com"><img src="./assets/a.svg?v=1"></a>'
        self.assertEqual(localize_images(html, "http://127.0.0.1:9876"),
                         '<a href="https://example.com"><img src="http://127.0.0.1:9876/assets/a.svg"></a>')

    def test_svg_validation_allows_local_glyph_and_gradient_references(self):
        source = '''<svg xmlns="http://www.w3.org/2000/svg"><defs><path id="glyph"/>
          <linearGradient id="surface"/></defs><use href="#glyph" fill="url(#surface)"/></svg>'''
        self.assertEqual(svg_issues(source), [])

    def test_svg_validation_rejects_runtime_dependencies(self):
        source = '''<svg xmlns="http://www.w3.org/2000/svg"><script/>
          <foreignObject/><text>not outlined</text><use href="other.svg#glyph"/>
          <style>@font-face {src:url(https://example.com/font.woff)}</style></svg>'''
        issues = svg_issues(source)
        self.assertIn("unexpected script element", issues)
        self.assertIn("unexpected foreignObject element", issues)
        self.assertIn("unexpected text element", issues)
        self.assertIn("external reference other.svg#glyph", issues)
        self.assertIn("external font/style dependency", issues)

    def test_geometry_flags_intersection_and_clipping_but_not_touching(self):
        def item(text, left, top, right, bottom):
            return {"text": text, "bounds": dict(left=left, top=top, right=right, bottom=bottom)}
        geometry = {"width": 100, "height": 100, "text": [
            item("first", 0, 0, 20, 10), item("touching", 20, 0, 40, 10),
            item("overlap", 5, 5, 15, 15), item("clipped", 90, 90, 110, 105)]}
        result = text_geometry_issues(geometry)
        self.assertEqual([value["text"] for value in result["clipped_text"]], ["clipped"])
        self.assertEqual(len(result["text_overlaps"]), 1)
        self.assertEqual(result["text_overlaps"][0]["intersection_area"], 50)
        self.assertEqual(rectangle_overlap(geometry["text"][0]["bounds"],
                                           geometry["text"][1]["bounds"]), 0)

    def test_gradient_requires_raster_evidence_even_with_valid_geometry(self):
        self.assertFalse(gradient_paint_is_visible({"painted_pixels": 0, "max_channel_delta": 0}))
        self.assertFalse(gradient_paint_is_visible({"painted_pixels": 2, "max_channel_delta": 50}))
        # A faint 1px gradient may change each covered pixel by only one channel
        # level; it still paints and should not require an arbitrary contrast.
        self.assertTrue(gradient_paint_is_visible({"painted_pixels": 40, "max_channel_delta": 1}))

    def test_evidence_reuse_requires_matching_svg_and_saved_png(self):
        with TemporaryDirectory() as directory:
            png = Path(directory) / "asset.png"
            png.write_bytes(b"saved PNG evidence")
            evidence = {"sha256": sha256(b"SVG source").hexdigest(),
                        "png_sha256": sha256(png.read_bytes()).hexdigest()}
            self.assertTrue(reusable_asset_evidence("SVG source", evidence, png))
            self.assertFalse(reusable_asset_evidence("changed source", evidence, png))
            png.write_bytes(b"changed PNG evidence")
            self.assertFalse(reusable_asset_evidence("SVG source", evidence, png))

    def test_desktop_grid_checks_alignment_equal_heights_and_sixteen_pixel_gap(self):
        def table(left, top, height=200):
            return dict(left=left, right=left + 334, top=top, bottom=top + height, height=height)
        good = {"tables": [table(0, 0), table(350, 0), table(0, 216), table(350, 216)],
                "social_rows": [{"count": 5}]}
        self.assertEqual(layout_issues("desktop-684", good), [])
        bad = {"tables": [table(0, 0), table(340, 10), table(0, 216), table(350, 216, 220)],
               "social_rows": [{"count": 5}]}
        problems = layout_issues("desktop-684", bad)
        self.assertTrue(any("aligned columns" in issue for issue in problems))
        self.assertTrue(any("expected 16px" in issue for issue in problems))
        self.assertTrue(any("unequal heights" in issue for issue in problems))
        # The compact breakpoint also requires a 16px gap after its card widths
        # are recalculated for a 600px column.
        self.assertEqual(layout_issues("compact-600", good), [])
        self.assertTrue(layout_issues("compact-600", bad))

    def test_phone_social_wrap_requires_three_then_two_in_both_usable_widths(self):
        tables = [dict(left=0, right=358, width=358, height=200,
                       top=index * 216, bottom=index * 216 + 200) for index in range(4)]
        for name in ("mobile-358", "mobile-390", "mobile-390-light"):
            with self.subTest(name=name):
                good = {"tables": tables, "social_rows": [{"count": 3}, {"count": 2}]}
                self.assertEqual(layout_issues(name, good), [])
                bad = {"tables": [], "social_rows": [{"count": 2}, {"count": 2}, {"count": 1}]}
                self.assertTrue(layout_issues(name, bad))

    def test_phone_project_cards_fill_the_usable_column_without_staggering(self):
        tables = [dict(left=0, right=358, width=358, height=200,
                       top=index * 216, bottom=index * 216 + 200) for index in range(4)]
        result = {"tables": tables, "social_rows": [{"count": 3}, {"count": 2}]}
        self.assertEqual(layout_issues("mobile-358", result), [])
        result["tables"][1] = dict(left=50, right=358, width=308, height=200, top=216, bottom=416)
        self.assertTrue(any("fill the 358px" in issue
                            for issue in layout_issues("mobile-358", result)))


if __name__ == "__main__":
    unittest.main()
