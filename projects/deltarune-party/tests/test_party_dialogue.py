from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'template'))

from party_dialogue import PartyDialogue, Reply, Speaker
from party_turns import BoardTurn, next_turn_start, turn_events
from reel_art import Text


class PartyDialogueTest(unittest.TestCase):
    def setUp(self):
        self.dialogue = PartyDialogue({
            'susie': Speaker('susie-face', '../cast/susie-text.wav', -.2),
            'lancer': Speaker('lancer-face', '../cast/lancer-text.wav', .2),
        })

    def test_board_exchange_holds_final_reply_and_then_hands_off(self):
        turn = BoardTurn('susie', 1.25, (2,), (2.5,), (3,), 3.25, .41, 0, 12)
        award = next(event for event in turn_events(turn, 3) if event['type'] == 'blue_coin')
        dialogue_end = self.dialogue.exchange(
            award, Reply('susie', '* Three coins!'), Reply('lancer', '* All three?', 'lancer-laugh-face'))
        call, response = self.dialogue.cues

        self.assertEqual(call['start'], round(award['t'] + .18, 6))
        self.assertEqual(response['start'], round(call['end'] + .12, 6))
        self.assertEqual(response['portrait'], 'lancer-laugh-face')
        self.assertEqual(dialogue_end, response['end'])
        self.assertAlmostEqual(dialogue_end - response['start'] -
                               (len(response['text']) - 1) / self.dialogue.text_rate, .58, places=5)
        self.assertEqual(next_turn_start(turn, dialogue_end=dialogue_end), round(dialogue_end + .82, 2))

    def test_rejects_truncated_or_overlapping_exchange_without_changing_cues(self):
        event = {'type': 'food_drop', 't': 7}
        replies = (Reply('susie', '* Food!'), Reply('lancer', '* Mine?'))
        with self.assertRaisesRegex(ValueError, 'deadline'):
            self.dialogue.exchange(event, *replies, until=8)
        self.assertEqual(self.dialogue.cues, ())
        self.dialogue.exchange(event, *replies, until=9)
        original = self.dialogue.cues
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            self.dialogue.exchange({'t': 8}, Reply('susie', '* Hey!'))
        self.assertEqual(self.dialogue.cues, original)

    def test_validates_text_fit_using_original_font_wrapping(self):
        font = Text.__new__(Text)
        font.glyphs = {glyph: (None, 10, 0) for glyph in ' *X'}
        for text, message in (
                ('* X?', 'unsupported glyph'), ('X' * 19, 'two-row'),
                (' '.join(['X' * 10] * 3), 'two-row')):
            with self.subTest(text=text):
                dialogue = PartyDialogue({'susie': Speaker('susie-face', 'susie-text.wav')})
                dialogue.exchange({'t': 1}, Reply('susie', text))
                with self.assertRaisesRegex(ValueError, message):
                    dialogue.validate_fit(font)

        self.dialogue.exchange({'t': 1}, Reply('susie', '* X'), Reply('lancer', 'X' * 18))
        self.dialogue.validate_fit(font)

    def test_cast_voices_follow_typewriter_and_duck_only_during_blips(self):
        self.dialogue.exchange({'t': 1}, Reply('susie', '* A!'), Reply('lancer', '* B?'))
        mixer = Mock()
        self.dialogue.mix(mixer)

        call, response = self.dialogue.cues
        self.assertEqual(len(mixer.add.call_args_list), 2)
        for cue, voice, pan, audio, duck in zip(
                (call, response), ('../cast/susie-text.wav', '../cast/lancer-text.wav'), (-.2, .2),
                mixer.add.call_args_list, mixer.duck.call_args_list, strict=True):
            at = cue['start'] + 2 / self.dialogue.text_rate
            self.assertEqual(audio.args[:3], ('voice', at, voice))
            self.assertEqual(audio.kwargs['pan'], pan)
            self.assertEqual(duck.args, (at, at + .15, .57))
