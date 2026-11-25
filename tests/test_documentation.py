"""Prevent missing evidence/reference files in the published readiness handoff."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_references_resolve(self):
        root = Path(__file__).resolve().parents[1]
        files = list((root / 'docs').rglob('*.md')) + [root / 'pilot/README.md', root / 'compat/v0.0/EVIDENCE_V0.0.2_BROWSER_ADDENDUM.md']
        for path in files:
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
                parsed = urlsplit(target.strip('<>'))
                if parsed.scheme or not parsed.path:
                    continue
                with self.subTest(document=str(path.relative_to(root)), target=target):
                    self.assertTrue((path.parent / unquote(parsed.path)).resolve().exists())
