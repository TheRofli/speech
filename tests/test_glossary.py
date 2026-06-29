from __future__ import annotations

import unittest

from speech_app.glossary import apply_glossary, parse_glossary


class GlossaryTests(unittest.TestCase):
    def test_parses_canonical_terms_and_alias_mappings(self):
        terms = parse_glossary(
            "DeepSeek\nDeep-Seag -> DeepSeek\nContext Code -> ContextCode\n"
        )

        self.assertEqual(
            [(term.alias, term.canonical) for term in terms],
            [
                ("DeepSeek", "DeepSeek"),
                ("Deep-Seag", "DeepSeek"),
                ("Context Code", "ContextCode"),
            ],
        )

    def test_ignores_empty_malformed_and_duplicate_lines(self):
        terms = parse_glossary("\n-> missing\nDeepSeek ->\nDeepSeek\ndeepseek\n")

        self.assertEqual([(term.alias, term.canonical) for term in terms], [("DeepSeek", "DeepSeek")])

    def test_applies_explicit_aliases_without_replacing_inside_words(self):
        terms = parse_glossary("Deep-Seag -> DeepSeek\nDeepSeek")

        result = apply_glossary("Deep-Seag and deepseek, but NotDeep-SeagX.", terms)

        self.assertEqual(result, "DeepSeek and DeepSeek, but NotDeep-SeagX.")


if __name__ == "__main__":
    unittest.main()
