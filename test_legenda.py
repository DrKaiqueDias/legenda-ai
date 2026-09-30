from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
import numpy as np

from legenda import Cue, build_cues, milliseconds, parser, render, save_outputs, subtitle_lines, timestamp, transcribe


def segment(text=" Olá, mundo!", start=0, end=2, words=None):
    return NS(text=text, start=start, end=end, words=words)


class SubtitleTests(unittest.TestCase):
    def test_timestamp_carries_milliseconds(self):
        self.assertEqual(timestamp(milliseconds(59.9996)), "00:01:00,000")
        self.assertEqual(timestamp(3661234, True), "01:01:01.234")
        self.assertEqual(milliseconds(np.float64(1.25)), 1250)

    def test_invalid_time_rejected(self):
        for value in (-1, float("nan"), float("inf"), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                milliseconds(value)

    def test_srt_and_vtt_have_expected_syntax(self):
        cues = [Cue(0, 1234, "Olá, mundo!")]
        self.assertEqual(render(cues, "srt"), "1\n00:00:00,000 --> 00:00:01,234\nOlá, mundo!\n")
        self.assertEqual(render(cues, "vtt"), "WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.234\nOlá, mundo!\n")

    def test_payload_cannot_inject_subtitle_markup(self):
        output = render([Cue(0, 1000, "<b>Olá</b> & teste\n\nnovo --> trecho")], "vtt")
        self.assertIn("&lt;b&gt;Olá&lt;/b&gt; &amp; teste", output)
        self.assertIn("--&gt;", output)
        self.assertNotIn("\n\nnovo", output)

    def test_unicode_is_preserved(self):
        text = "Olá 日本語 العربية 한국어"
        self.assertIn(text, render([Cue(0, 1000, text)], "srt"))

    def test_two_lines_are_balanced(self):
        lines = subtitle_lines("And so my fellow Americans, ask not what your")
        self.assertEqual(lines, ["And so my fellow Americans,", "ask not what your"])

    def test_word_groups_use_real_word_times(self):
        words = [NS(word=" Olá", start=0.4, end=1), NS(word=" mundo", start=7, end=8)]
        self.assertEqual(build_cues([segment(words=words)]), [Cue(400, 1000, "Olá"), Cue(7000, 8000, "mundo")])

    def test_long_phrase_is_split_without_losing_words(self):
        words = [NS(word=" palavra", start=i, end=i + 0.5) for i in range(20)]
        cues = build_cues([segment(words=words)])
        self.assertGreater(len(cues), 1)
        self.assertEqual(" ".join(c.text for c in cues).split(), ["palavra"] * 20)

    def test_overlapping_cues_preserve_text(self):
        cues = build_cues([segment("A", 0, 2), segment("B", 1, 1.5), segment("C", 1.9, 3)])
        self.assertEqual(cues, [Cue(0, 2000, "A B"), Cue(2000, 3000, "C")])

    def test_translation_uses_segment_times(self):
        self.assertEqual(build_cues([segment("Hello", 1, 3, [NS(word="errado", start=0, end=1)])], True),
                         [Cue(1000, 3000, "Hello")])

    def test_empty_text_skipped_and_short_text_preserved(self):
        self.assertEqual(build_cues([segment(" "), segment("a", 1, 1)]), [Cue(1000, 1001, "a")])

    def test_inverted_interval_rejected(self):
        with self.assertRaises(ValueError):
            build_cues([segment("A", 2, 1)])

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sentinel = root / "keep.txt"
            sentinel.write_text("keep")
            with self.assertRaises(FileExistsError):
                save_outputs(root, [Cue(0, 1000, "A")], {})
            self.assertEqual(sentinel.read_text(), "keep")

    def test_no_speech_creates_no_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "output"
            with self.assertRaises(ValueError):
                save_outputs(target, [], {})
            self.assertFalse(target.exists())

    def test_outputs_are_utf8(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "output"
            save_outputs(target, [Cue(0, 1000, "ação 日本語")], {"idioma": "pt"})
            self.assertEqual(len(list(target.iterdir())), 4)
            self.assertEqual((target / "transcricao.txt").read_text(encoding="utf-8"), "ação 日本語\n")

    def test_invalid_metadata_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "output"
            with self.assertRaises(ValueError):
                save_outputs(target, [Cue(0, 1000, "A")], {"number": float("nan")})
            self.assertFalse(target.exists())

    def test_pipeline_consumes_lazy_segments_and_keeps_audio_local(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "audio.wav"
            source.write_bytes(b"test fixture for mocked decoder")
            model = Mock(supported_languages=["pt", "en"])
            model.transcribe.return_value = (iter([segment()]), NS(language="pt"))
            factory = Mock(return_value=model)
            args = parser().parse_args([str(source), "--idioma", "pt", "--offline"])
            output, info = transcribe(args, factory)
            self.assertEqual(info["trechos"], 1)
            self.assertTrue((output / "legendas.srt").exists())
            self.assertTrue(factory.call_args.kwargs["local_files_only"])
            self.assertEqual(model.transcribe.call_args.args, (str(source.resolve()),))
            self.assertTrue(model.transcribe.call_args.kwargs["vad_filter"])

    def test_missing_file_fails_before_model_download(self):
        with tempfile.TemporaryDirectory() as folder:
            factory = Mock()
            with self.assertRaises(ValueError):
                transcribe(parser().parse_args([str(Path(folder) / "absent.mp4")]), factory)
            factory.assert_not_called()

    def test_conflicting_language_options_fail_before_model_download(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "audio.wav"
            source.write_bytes(b"test")
            factory = Mock()
            with self.assertRaises(ValueError):
                transcribe(parser().parse_args([str(source), "--idioma", "pt", "--multilingue"]), factory)
            factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
