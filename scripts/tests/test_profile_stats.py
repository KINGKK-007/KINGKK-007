"""Regression checks for truthful, non-empty profile snapshots."""

from collections import Counter
from datetime import date,timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import profile_stats as stats

SVG='{http://www.w3.org/2000/svg}'
ROOT=Path(__file__).resolve().parents[2]


class ProfileStatsTests(unittest.TestCase):
    def setUp(self):
        self.today=date(2026,10,9)
        self.days={self.today-timedelta(days=i):0 for i in range(365)}
        for i in range(12):self.days[self.today-timedelta(days=i)]=3
        self.totals=Counter({'Python':7500,'C':1400,'TypeScript':550,'Java':300,'CSS':150,'Makefile':100})

    def test_calendar_parses_singular_plural_and_zero(self):
        p=stats.ContributionCalendar()
        p.feed('<td id="a" data-date="2026-10-09"></td><tool-tip for="a">1 contribution on October 9th.</tool-tip>'
               '<td id="b" data-date="2026-10-08"></td><tool-tip for="b">12 contributions on October 8th.</tool-tip>'
               '<td id="c" data-date="2026-10-07"></td><tool-tip for="c">No contributions on October 7th.</tool-tip>')
        self.assertEqual(list(p.counts.values()),[1,12,0])

    def test_window_counts_do_not_include_old_or_future_days(self):
        self.days[self.today-timedelta(days=500)]=1000
        self.days[self.today+timedelta(days=1)]=1000
        s=stats.summarize(self.days,self.today,self.totals)
        self.assertEqual(s['contributions'],36)
        self.assertEqual(s['active_days'],12)

    def test_small_language_shares_are_hidden_without_renormalizing(self):
        s=stats.summarize(self.days,self.today,self.totals)
        self.assertEqual([n for n,_ in s['languages']],['Python','C','TypeScript','Java'])
        self.assertEqual(s['languages'][0][1],.75)
        self.assertLess(sum(v for _,v in s['languages']),1)

    def test_sparse_headline_metrics_do_not_leave_an_empty_activity_card(self):
        s=stats.summarize(self.days,self.today,self.totals)
        s.update(contributions=2,active_days=1)
        svg=ET.fromstring(stats.overview(s))
        labels=[g.get('data-text') for g in svg.iter() if g.get('data-text')]
        self.assertNotIn('Contributions',labels)
        self.assertNotIn('Active days',labels)
        self.assertIn('Repository languages',labels)

    def test_failed_fetch_leaves_previous_snapshot_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'overview.svg';p.write_text('previous valid snapshot')
            with patch('sys.argv',['profile_stats.py','--output',folder]),patch.object(stats,'fetch',side_effect=RuntimeError('simulated API failure')):
                with self.assertRaises(RuntimeError):stats.main()
            self.assertEqual(p.read_text(),'previous valid snapshot')

    def test_missing_data_cannot_be_published(self):
        with self.assertRaises(ValueError):stats.summarize({},self.today,self.totals)
        with self.assertRaises(ValueError):stats.summarize(self.days,self.today,Counter())

    def test_profile_and_forks_are_excluded_from_language_data(self):
        repos=[{'name':'KINGKK-007','fork':False,'size':10,'languages_url':'profile'},
               {'name':'fork','fork':True,'size':10,'languages_url':'fork'},
               {'name':'project','fork':False,'size':10,'languages_url':'project'}]
        with patch.object(stats,'fetch',return_value='{"C":42}') as fetch:
            result=stats.language_totals(repos,None,'KINGKK-007')
        self.assertEqual(result,Counter({'C':42}))
        fetch.assert_called_once_with('project',None)

    def test_framing_preserves_the_real_contribution_cells(self):
        source=(ROOT/'assets/snake.svg').read_text()
        original=ET.fromstring(source)
        framed=ET.fromstring(stats.contribution_frame(source,date(2025,10,5),self.today))
        def cells(root):
            return [tuple(e.get(k) for k in ['x','y','width','height','class']) for e in root.iter(SVG+'rect') if 'c' in e.get('class','').split()]
        self.assertEqual(cells(original),cells(framed))
        self.assertIn('prefers-reduced-motion:reduce',ET.tostring(framed,encoding='unicode'))


if __name__=='__main__':unittest.main()
