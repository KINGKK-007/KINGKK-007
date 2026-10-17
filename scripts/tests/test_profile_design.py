"""Regression checks for the v2 generator's layout contracts."""

from copy import deepcopy
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import profile_design as design

SVG = '{http://www.w3.org/2000/svg}'


class ProfileDesignTests(unittest.TestCase):
    def test_gradient_lines_use_user_space_so_zero_height_strokes_are_visible(self):
        root = ET.fromstring(design.start(320, 100, 'test') + design.card(320, 100)
                             + design.section_rule(0, 50, 100, 'rule') + '</svg>')
        gradients = {e.get('id'): e for e in root.iter(SVG+'linearGradient')}
        for identifier in ['card-edge', 'rule']:
            self.assertEqual(gradients[identifier].get('gradientUnits'), 'userSpaceOnUse')
        frame = next(e for e in root if e.get('data-card'))
        self.assertEqual((frame.get('x'), frame.get('width'), frame.get('rx')), ('.5', '319', '12'))

    def test_chip_flow_preserves_whole_technology_labels_and_never_crosses_rows(self):
        items = ['FastAPI', 'OpenEnv', 'TRL GRPO', 'Unsloth']
        placements, height = design.flow(items, 166)
        self.assertEqual([item[1] for item in placements], items)
        self.assertGreater(height, 32)
        for index, (_, label, x, y, width) in enumerate(placements):
            self.assertLessEqual(x+width, 166)
            for _, _, xx, yy, ww in placements[index+1:]:
                if y == yy:
                    self.assertGreaterEqual(xx-(x+width), 8)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            design.flow(['PostgreSQL'], 20)

    def test_half_action_has_clear_space_between_its_label_and_arrow(self):
        root = ET.fromstring(design.start(105, 60, 'test')
                            + design.action_pill('Live demo', 4, 12, 97) + '</svg>')
        label = root.find('.//'+SVG+'text')
        arrow = root.findall('.//'+SVG+'path')[-1]
        arrow_x = float(re.match(r'm([\d.]+)', arrow.get('d')).group(1))
        end = float(label.get('x')) + design.text_width(label.text, float(label.get('font-size')), 600)
        self.assertGreaterEqual(arrow_x-end, 8)

    def test_optional_availability_extends_the_card_in_every_hero_variant(self):
        generated = {}
        profile = deepcopy(design.PROFILE)
        profile['availability_text'] = 'Open to Summer 2027 SWE internships'
        with patch.object(design, 'PROFILE', profile), patch.object(design, 'write', side_effect=lambda p,s: generated.update({p:s+'</svg>'})):
            design.banners()
        self.assertEqual(len(generated), 6)
        for source in generated.values():
            root = ET.fromstring(source)
            frame = next(e for e in root if e.get('data-card'))
            self.assertEqual(float(frame.get('height')), float(root.get('height'))-1)
            self.assertTrue(any(e.text and 'internships' in e.text for e in root.iter(SVG+'text')))
            self.assertIn('prefers-reduced-motion', source)

    def test_asset_fingerprints_preserve_mobile_density_descriptors_and_are_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'assets/badges').mkdir(parents=True)
            (root/'assets/badges/a.svg').write_text('<svg/>')
            readme = root/'README.md'
            readme.write_text('<source srcset="./assets/badges/a.svg 1.07x" />')
            with patch.object(design, 'ROOT', root/'assets'):
                design.version_readme_assets()
                first = readme.read_text()
                design.version_readme_assets()
            self.assertIn(' 1.07x"', first)
            self.assertRegex(first, r'a\.svg\?v=[0-9a-f]{10} 1\.07x')
            self.assertEqual(first, readme.read_text())

    def test_shared_source_art_has_a_generic_alt_without_changing_repository_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'assets/projects').mkdir(parents=True)
            (root/'assets/projects/source.svg').write_text('<svg/>')
            readme = root/'README.md'
            targets = [entry[-1] for entry in design.PROFILE['projects']]
            readme.write_text(''.join(
                f'<a href="{target}"><img src="./assets/projects/source.svg" alt="stale" /></a>'
                for target in targets))
            with patch.object(design, 'ROOT', root/'assets'):
                design.version_readme_assets()
                first = readme.read_text()
                design.version_readme_assets()
            self.assertEqual(first, readme.read_text())
            for target in targets:
                self.assertIn(f'href="{target}"', first)
            self.assertEqual(first.count('alt="View source repository"'), len(targets))


if __name__ == '__main__':
    unittest.main()
