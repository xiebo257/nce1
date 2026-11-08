"""Regression checks for source structures that previously caused silent speech errors."""
import json,unittest,os,tempfile
from pathlib import Path
from prepare_lessons import answer,fill,Lesson,OVERRIDES,PASSAGES,DATA,VOCAB,USAGE
from run_audio_queue import benign
from asr_text import align_digit_sequences,align_clock_sequences,normalize_year_words
class CompilerRegression(unittest.TestCase):
 def test_named_blank_keeps_sentence_and_assigns_actor(self):
  lesson=Lesson(71);lesson.part='practice'
  lesson.exercise({'id':'practice-a-1','data-prompt':"JANE: What's Ron Marston _____, Pauline?",'data-key':'like'},'Dialogue','Fill in the missing words.')
  self.assertEqual(lesson.s[0]['text'],"What's Ron Marston like, Pauline?")
  self.assertEqual(lesson.s[0]['role'],'jane')
 def test_year_words_keep_the_year(self):
  self.assertEqual(normalize_year_words('In nineteen seventy-five.'),'In 1975.')
  self.assertNotEqual(normalize_year_words('In nineteen seventy-five.'),'In 1957.')
 def test_clock_comparison_preserves_minutes(self):
  self.assertEqual(align_clock_sequences('eight oh five.','8.05'),'eight oh five')
  self.assertEqual(align_clock_sequences('eight oh five.','8.50'),'8.50')
  self.assertEqual(align_clock_sequences('eight oh five.','$8.05'),'$8.05')
 def test_printed_item_codes_are_not_spoken(self):
  lesson=Lesson(113);lesson.add('1e. David will go.')
  self.assertEqual(lesson.s[-1]['text'],'David will go.')
  lesson.add('2. b. Have they got a book?')
  self.assertEqual(lesson.s[-1]['text'],'Have they got a book?')
  lesson.add('1. finish my homework.')
  self.assertEqual(lesson.s[-1]['text'],'finish my homework.')
  lesson.add('c. Have they got a book?')
  self.assertEqual(lesson.s[-1]['text'],'Have they got a book?')
 def test_phone_asr_spelling_preserves_every_digit(self):
  expected='The number is five five five, zero one zero one.'
  self.assertEqual(align_digit_sequences(expected,'The number is 555-0101.'),expected)
  self.assertEqual(align_digit_sequences(expected,'The number is 555101.'),'The number is 555101.')
  self.assertEqual(align_digit_sequences(expected,'The number is 15550101.'),'The number is 15550101.')
 def test_leading_zero_phone_number_keeps_every_digit(self):
  lesson=Lesson(61);lesson.add("Yes. It's 09754.")
  self.assertEqual(lesson.s[-1]['text'],"Yes. It's zero, nine, seven, five, four.")
 def test_digit_sequence_must_not_lose_a_zero(self):
  self.assertFalse(benign(dict(text="Write two, zero, zero, zero, zero, zero.",heard="Write 20000.")))
  self.assertTrue(benign(dict(text="Write two, zero, zero, zero, zero, zero.",heard="Write 200000.")))
 def test_zero_article_is_silent(self):
  self.assertEqual(fill('She goes to ___ work in ___ morning.',answer('×, the')),'She goes to  work in the morning.')
 def test_matching_answer_letter_is_not_spoken(self):
  self.assertEqual(answer('h. What are the girls doing?'),'What are the girls doing?')
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
class PartialCompilerRegression(unittest.TestCase):
 def test_partial_compile_keeps_other_parts_and_explicit_dialogue(self):
  original=Path.cwd()
  with tempfile.TemporaryDirectory() as tmp:
   try:
    os.chdir(tmp)
    Path('html').mkdir();Path('lessons').mkdir()
    folder=Path('audio/scripts/099');folder.mkdir(parents=True)
    for part in ['lesson','practice']:(folder/f'{part}.json').write_text('previously reviewed '+part)
    roles={'answer':{'speaker':'Vivian','instructions':'Keep this voice.'},'existing_character':{'speaker':'Dylan'}}
    (folder/'roles.json').write_text(json.dumps(roles))
    Path('html/lesson-099.html').write_text('''<section id="grammar"><div id="grammar-ii"><article>
      <h3>Complete the conversation</h3><p class="instruction">Listen and answer.</p>
      <textarea id="g2" data-prompt="A: ___ B: ___" data-key="yes; yesterday"></textarea>
      </article></div></section>''')
    block={'id':'grammar-ii','audio_context':[{'text':'The bus arrived.','source':'fixed-opening','role':'narrator'}],
      'questions':[{'id':'g2','audio_segments':[{'text':'Did you see it?','role':'prompt','pause':1.7},
        {'text':'Yes, I saw it yesterday.','role':'answer','pause':1.2}]}]}
    Path('lessons/lesson-099.json').write_text(json.dumps({'sections':{'grammar':[block]}}))
    Lesson(99).compile(['grammar'])
    grammar=json.loads((folder/'grammar.json').read_text())
    segments=grammar['segments']
    self.assertEqual([s['text'] for s in segments[-3:]],['The bus arrived.','Did you see it?','Yes, I saw it yesterday.'])
    self.assertEqual([s['source_item'] for s in segments[-3:]],['fixed-opening','g2','g2'])
    self.assertEqual([s['role'] for s in segments[-2:]],['prompt','answer'])
    self.assertEqual(segments[-2]['pause_after'],1.7)
    segments[-1].update(generation_seed=123,generation_temperature=.45,instructions='Previously checked delivery.')
    (folder/'grammar.json').write_text(json.dumps(grammar))
    Lesson(99).compile(['grammar'])
    repaired=json.loads((folder/'grammar.json').read_text())['segments'][-1]
    self.assertEqual(repaired['generation_seed'],123)
    self.assertEqual(repaired['generation_temperature'],.45)
    self.assertEqual(repaired['instructions'],'Previously checked delivery.')
    for part in ['lesson','practice']:self.assertEqual((folder/f'{part}.json').read_text(),'previously reviewed '+part)
    saved=json.loads((folder/'roles.json').read_text())
    for key,value in roles.items():self.assertEqual(saved[key],value)
   finally:os.chdir(original)

if __name__=='__main__':unittest.main()
