#!/usr/bin/env python3
"""Unit tests for the meta.yaml subset parser.

The parser exists so `tse` has no dependencies. That trade is only safe if the
subset it accepts is pinned down, so these tests are the contract.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importlib.machinery
import importlib.util

_loader = importlib.machinery.SourceFileLoader("tse", str(Path(__file__).resolve().parents[1] / "tse"))
_spec = importlib.util.spec_from_loader("tse", _loader)
tse = importlib.util.module_from_spec(_spec)
# Registered before execution because @dataclass resolves annotations through
# sys.modules, and tse is loaded by path rather than imported normally.
sys.modules["tse"] = tse
_loader.exec_module(tse)
parse_meta = tse.parse_meta_subset  # always exercise the fallback


class ParseScalars(unittest.TestCase):
    def test_strings_ints_and_bools(self):
        meta = parse_meta("title: A ticket\nminutes: 25\ndraft: false\n", "t")
        self.assertEqual(meta["title"], "A ticket")
        self.assertEqual(meta["minutes"], 25)
        self.assertIs(meta["draft"], False)

    def test_quotes_are_stripped(self):
        self.assertEqual(parse_meta('title: "Quoted: with colon"\n', "t")["title"],
                         "Quoted: with colon")

    def test_inline_comment_is_removed(self):
        meta = parse_meta("stack: compose          # compose | kind | none\n", "t")
        self.assertEqual(meta["stack"], "compose")

    def test_hash_inside_quoted_value_survives(self):
        self.assertEqual(parse_meta('title: "issue #42"\n', "t")["title"], "issue #42")

    def test_empty_value_becomes_none(self):
        self.assertIsNone(parse_meta("notes:\n", "t")["notes"])


class ParseLists(unittest.TestCase):
    def test_block_list(self):
        meta = parse_meta("commands:\n  - docker ps\n  - docker logs\n", "t")
        self.assertEqual(meta["commands"], ["docker ps", "docker logs"])

    def test_empty_inline_list(self):
        self.assertEqual(parse_meta("prerequisites: []\n", "t")["prerequisites"], [])

    def test_populated_inline_list(self):
        self.assertEqual(parse_meta("tags: [a, b]\n", "t")["tags"], ["a", "b"])

    def test_list_then_next_key(self):
        meta = parse_meta("commands:\n  - one\n\ntier: core\n", "t")
        self.assertEqual(meta["commands"], ["one"])
        self.assertEqual(meta["tier"], "core")


class ParseFoldedBlocks(unittest.TestCase):
    def test_folded_block_joins_with_spaces(self):
        meta = parse_meta("teaches: >\n  first line\n  second line\n", "t")
        self.assertEqual(meta["teaches"], "first line second line\n")

    def test_literal_block_keeps_newlines(self):
        meta = parse_meta("teaches: |\n  first\n  second\n", "t")
        self.assertEqual(meta["teaches"], "first\nsecond\n")

    def test_block_terminates_at_next_top_level_key(self):
        meta = parse_meta("teaches: >\n  wrapped text\ntier: core\n", "t")
        self.assertEqual(meta["teaches"], "wrapped text\n")
        self.assertEqual(meta["tier"], "core")

    def test_clip_chomping_keeps_one_trailing_newline(self):
        """YAML's default. Missing it diverged from PyYAML on every meta file."""
        self.assertEqual(parse_meta("t: >\n  text\n", "t")["t"], "text\n")
        self.assertEqual(parse_meta("t: |\n  text\n", "t")["t"], "text\n")

    def test_strip_chomping_removes_it(self):
        self.assertEqual(parse_meta("t: >-\n  text\n", "t")["t"], "text")
        self.assertEqual(parse_meta("t: |-\n  text\n", "t")["t"], "text")


class RejectsUnsupported(unittest.TestCase):
    def test_nested_mapping_raises(self):
        with self.assertRaises(ValueError):
            parse_meta("limits:\n  cpu: 2\n", "t")

    def test_missing_colon_raises(self):
        with self.assertRaises(ValueError):
            parse_meta("this is not a mapping\n", "t")

    def test_comments_and_blank_lines_are_skipped(self):
        self.assertEqual(parse_meta("# a comment\n\ntier: core\n", "t"), {"tier": "core"})


class MatchesPyYAML(unittest.TestCase):
    """The subset must mean the same thing to a real YAML parser.

    Astro reads these files with a full YAML implementation, so a divergence
    here would show up as the site and the CLI disagreeing about an exercise.
    """

    def test_every_meta_file_agrees(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")

        root = Path(__file__).resolve().parents[2]
        files = sorted(root.glob("labs/*/*/meta.yaml"))
        self.assertGreater(len(files), 0, "no meta.yaml files found")

        for path in files:
            text = path.read_text()
            with self.subTest(path=str(path.relative_to(root))):
                self.assertEqual(
                    tse.parse_meta_subset(text, str(path)),
                    yaml.safe_load(text),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
