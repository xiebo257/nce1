"""Regression checks for source structures that previously caused silent speech errors."""
import json,unittest
from pathlib import Path
from prepare_lessons import fill,Lesson,OVERRIDES,PASSAGES,DATA,VOCAB,USAGE
class CompilerRegression(unittest.TestCase):
 def test_multiword_answer_is_not_two_unrelated_blanks(self):
  with self.assertRaises(ValueError):fill('While she ___ in the library, someone ___ a letter.','was sitting')
 def test_multiword_adjacent_blanks(self):
  self.assertEqual(fill('Try and ___ ___.','stand up'),'Try and stand up.')
 def test_partial_word_uses_whole_answer(self):
  self.assertEqual(fill('Fruit: p_____s','peaches'),'Fruit: peaches')
 def test_semicolon_separated_phrases(self):
  self.assertEqual(fill('Can you stand ___ the door? Then walk ___ it.','in front of; through'),'Can you stand in front of the door? Then walk through it.')
 def test_late_nested_sections_are_present(self):
  lesson=Lesson(144)
  self.assertTrue(lesson.root.xpath('//section[@id="grammar"]//article//*[@data-key]'))
 def test_completed_scripts_include_plain_prose(self):
  for n in [69,93,117,119,121,123,125,135,141,143]:
   d=json.loads(Path(f'audio/scripts/{n:03}/lesson.json').read_text())
   self.assertTrue(any(s['source_item'].startswith(('lesson-passage-','lesson-scan-')) for s in d['segments']),n)
 def test_progressive_verb_forms(self):
  d=json.loads(Path('audio/scripts/118/grammar.json').read_text())
  text=' '.join(s['text'] for s in d['segments'])
  self.assertIn('While she was sitting in the library, someone threw a letter',text)
  self.assertNotIn('someone sitting a letter',text)
 def test_no_spoken_role_prefixes(self):
  for n in [32,95,113,132,135,136]:
   for part in ['lesson','practice','grammar']:
    for s in json.loads(Path(f'audio/scripts/{n:03}/{part}.json').read_text())['segments']:
     self.assertNotRegex(s['text'],r'^(?:[ABC]|George|1st Tramp|2nd Tramp|Actress|Reporter):')
if __name__=='__main__':unittest.main()
