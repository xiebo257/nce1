#!/usr/bin/env python3
"""Renderer checks for source table structure, escaping and answer preservation."""
import copy
import json
from pathlib import Path
import unittest
from render_lessons import render

ROOT=Path(__file__).resolve().parents[3]

class SourceTableTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'lessons/lesson-144.json').read_text())
        self.table={'id':'source-test-table','type':'table','caption':'A < B & C',
                    'headers':['Earlier','Later'],'rows':[['one\ntwo','<script>bad</script>'],['','three']]}
        self.data['sections']['lesson'].insert(0,self.table)

    def test_columns_escape_and_answer_count(self):
        output,count=render(ROOT,self.data,set(range(1,145)))
        self.assertEqual(count,self.data['expected_answers'])
        self.assertIn('A &lt; B &amp; C',output)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;',output)
        self.assertIn('<td>one<br />\ntwo</td><td>',output)
        self.assertIn('<tr><td></td><td>three</td></tr>',output)

    def test_missing_column_rejected(self):
        self.table['rows'][0].pop()
        with self.assertRaisesRegex(ValueError,'Invalid table columns'):
            render(ROOT,self.data,set(range(1,145)))

if __name__=='__main__':unittest.main()
