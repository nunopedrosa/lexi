"""Developer-tool tests: compare outputs without treating either as linguistic truth."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location(
    'audit_syllables', Path(__file__).parent / 'scripts' / 'audit-syllables.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SyllableAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name)
        (self.data / 'syllables').mkdir()
        self.write('meta.json', {'keys': ['c', 's']})
        self.write('c.json', [['casa', '', []], ['casa de banho', '', []]])
        self.write('s.json', [['saúde', '', []], ['saída', '', []]])
        self.write('syllables/c.json', [['casa', ['ca', 'sa']]])
        self.write('syllables/s.json', [['saúde', ['saú', 'de']]])
        self.candidate = {
            'schema': 1,
            'source': {'id': 'test-fixture', 'version': '1',
                       'license': 'test data', 'artifact_sha256': 'a' * 64},
            'rows': [['casa', ['ca', 'sa']], ['saúde', ['sa', 'ú', 'de']],
                     ['saída', ['sa', 'í', 'da']]]}

    def write(self, name, value):
        (self.data / name).write_text(json.dumps(value), encoding='utf-8')

    def test_reports_disagreement_and_new_coverage_without_changing_data(self):
        before = {p: p.read_bytes() for p in self.data.rglob('*.json')}
        result = audit.compare(self.data, self.candidate)
        self.assertEqual(result['counts']['eligible_headwords'], 3)
        self.assertEqual(result['counts']['excluded_headwords'], 1)
        self.assertEqual(result['counts']['compared'], 2)
        self.assertEqual(result['counts']['same_boundaries'], 1)
        self.assertEqual(result['counts']['different_boundaries'], 1)
        self.assertEqual(result['counts']['different_counts'], 1)
        self.assertEqual(result['counts']['newly_covered'], 1)
        self.assertEqual(result['differences'][0]['word'], 'saúde')
        self.assertFalse(result['linguistically_validated'])
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_rejects_duplicate_candidates_and_missing_provenance(self):
        self.candidate['rows'].append(['casa', ['cas', 'a']])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            audit.compare(self.data, self.candidate)
        self.candidate['rows'].pop()
        del self.candidate['source']['artifact_sha256']
        with self.assertRaisesRegex(ValueError, 'artifact_sha256'):
            audit.compare(self.data, self.candidate)

    def test_invalid_candidate_is_not_agreement_or_coverage(self):
        self.candidate['rows'] = [['casa', ['ca', 'za']], ['saúde', []],
                                  ['saída', 'sa|í|da'], ['fora', ['fo', 'ra']]]
        result = audit.compare(self.data, self.candidate)
        self.assertEqual(result['counts']['candidate_invalid'], 3)
        self.assertEqual(result['counts']['unexpected_candidates'], 1)
        self.assertEqual(result['counts']['compared'], 0)
        self.assertEqual(result['counts']['newly_covered'], 0)

    def test_matches_nfc_and_case_but_keeps_different_boundaries(self):
        self.candidate['rows'] = [['casa', ['CA', 'SA']],
                                  ['saúde', ['sau\u0301', 'de']]]
        result = audit.compare(self.data, self.candidate)
        self.assertEqual(result['counts']['same_boundaries'], 2)
        self.assertEqual(result['counts']['missing_candidate'], 1)

    def test_different_boundaries_can_have_the_same_count(self):
        self.candidate['rows'] = [['casa', ['cas', 'a']]]
        result = audit.compare(self.data, self.candidate, limit=0)
        self.assertEqual(result['counts']['different_boundaries'], 1)
        self.assertEqual(result['counts']['different_counts'], 0)
        self.assertEqual(result['differences'], [])

    def test_refuses_to_execute_an_unreviewed_lx_archive(self):
        archive = self.data / 'unreviewed.tar.gz'
        archive.write_bytes(b'not the reviewed distribution')
        with self.assertRaisesRegex(ValueError, 'reviewed SHA-256'):
            audit.from_lx_archive(self.data, archive)

    def test_rejects_malformed_source_metadata(self):
        self.candidate['source'] = []
        with self.assertRaisesRegex(ValueError, 'source must be an object'):
            audit.compare(self.data, self.candidate)


if __name__ == '__main__':
    unittest.main()
