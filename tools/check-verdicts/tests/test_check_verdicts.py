import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_verdicts as cv  # noqa: E402

GOOD_BLOCK = """\
## Verdict

Decision: PROCEED-WITH-CONSTRAINT

{gate}Criteria evaluated:
- cost under 30 % of revenue at 50k pages — PASS — see table
- pricing verified from primary source — FAIL — search-reported only

Unverified assumptions carried forward: list here

What would flip this verdict: a different number

{implication}"""


def doc(block: str, body: str = "# Title\n\nSome text.\n\n") -> str:
    return body + block


class CheckVerdicts(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def block(self, gate: str = "", implication: str = "") -> str:
        return GOOD_BLOCK.format(gate=gate, implication=implication)

    # -- happy paths ---------------------------------------------------------
    def test_well_formed_spike_without_extras_passes(self):
        p = self.write("04-x.md", doc(self.block(gate="GATE-S4: not fired\n\n")))
        self.assertEqual(cv.check_file(p), [])

    def test_s1_with_implication_last_passes(self):
        p = self.write("01-x.md", doc(self.block(implication="Implication for ADR-013: none yet\n")))
        self.assertEqual(cv.check_file(p), [])

    def test_s2_needs_gate_and_implication(self):
        ok = self.write(
            "02-x.md",
            doc(self.block(gate="GATE-S2: supports up to N pages\n\n", implication="Implication for ADR-013: x\n")),
        )
        self.assertEqual(cv.check_file(ok), [])

    def test_bold_labels_are_accepted(self):
        text = doc(
            "## Verdict\n\n**Decision:** KILL\n\n**GATE-S4:** fired\n\n**Criteria evaluated:**\n- a — FAIL — b\n\n"
            "**Unverified assumptions carried forward:** none\n\n**What would flip this verdict:** x\n"
        )
        self.assertEqual(cv.check_file(self.write("04-y.md", text)), [])

    # -- failures ------------------------------------------------------------
    def test_missing_verdict_heading(self):
        p = self.write("01-x.md", "# T\n\n## Findings\n\ntext\n")
        self.assertIn("must be '## Verdict'", cv.check_file(p)[0])

    def test_verdict_not_last_h2(self):
        p = self.write("01-x.md", doc(self.block(implication="Implication for ADR-013: x\n")) + "\n## Appendix\n\nmore\n")
        self.assertIn("must be '## Verdict'", cv.check_file(p)[0])

    def test_heading_inside_code_fence_is_ignored(self):
        text = doc(self.block(gate="GATE-S3: ok\n\n")) + "\n```\n## not a heading\n```\n"
        self.assertEqual(cv.check_file(self.write("03-x.md", text)), [])

    def test_bad_decision_value(self):
        text = doc(self.block(gate="GATE-S3: ok\n\n")).replace("PROCEED-WITH-CONSTRAINT", "MAYBE")
        problems = cv.check_file(self.write("03-x.md", text))
        self.assertTrue(any("'Decision:' must start with" in p for p in problems))

    def test_criterion_without_pass_or_fail(self):
        text = doc(self.block(gate="GATE-S3: ok\n\n")).replace("— PASS —", "— fine —")
        problems = cv.check_file(self.write("03-x.md", text))
        self.assertTrue(any("not marked PASS or FAIL" in p for p in problems))

    def test_missing_field(self):
        text = doc(self.block(gate="GATE-S3: ok\n\n")).replace(
            "What would flip this verdict: a different number\n", ""
        )
        problems = cv.check_file(self.write("03-x.md", text))
        self.assertTrue(any("missing 'What would flip this verdict:'" in p for p in problems))

    def test_fields_out_of_order(self):
        text = doc(
            "## Verdict\n\nCriteria evaluated:\n- a — PASS — b\n\nDecision: KILL\n\n"
            "Unverified assumptions carried forward: none\n\nWhat would flip this verdict: x\n"
        )
        problems = cv.check_file(self.write("04-x.md", text))
        self.assertTrue(any("out of order" in p for p in problems))

    def test_s2_missing_gate_line(self):
        p = self.write("02-x.md", doc(self.block(implication="Implication for ADR-013: x\n")))
        self.assertTrue(any("GATE-S2" in x for x in cv.check_file(p)))

    def test_s1_must_end_with_implication(self):
        p = self.write("01-x.md", doc(self.block()))
        self.assertTrue(any("Implication for ADR-013" in x for x in cv.check_file(p)))

    def test_s1_implication_not_last_line(self):
        text = doc(self.block(implication="Implication for ADR-013: x\n\nTrailing note.\n"))
        self.assertTrue(any("Implication for ADR-013" in x for x in cv.check_file(self.write("01-x.md", text))))

    # -- discovery / CLI -----------------------------------------------------
    def test_spike_docs_ignores_readme_and_unnumbered(self):
        self.write("README.md", "x")
        self.write("notes.md", "x")
        self.write("03-a.md", "x")
        self.assertEqual([p.name for p in cv.spike_docs(self.dir)], ["03-a.md"])

    def test_main_passes_on_empty_dir_and_fails_on_bad_doc(self):
        self.assertEqual(cv.main([str(self.dir)]), 0)
        self.write("03-bad.md", "# no verdict\n")
        self.assertEqual(cv.main([str(self.dir)]), 1)


if __name__ == "__main__":
    unittest.main()
