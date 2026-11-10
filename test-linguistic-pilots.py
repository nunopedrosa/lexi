import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('pilots', Path(__file__).parent / 'scripts/evaluate-pilots.py')
pilots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilots)


class PilotTests(unittest.TestCase):
    def test_variants_missing_and_pending_are_separate(self):
        cases = [
            {'id': 'a', 'word': 'habitual', 'profile': 'variant', 'status': 'documented_variants',
             'analyses': [{'segments': ['ha', 'bi', 'tu', 'al']}, {'segments': ['ha', 'bi', 'tual']}]},
            {'id': 'b', 'word': 'saúde', 'profile': 'display', 'status': 'source_checked',
             'analyses': [{'segments': ['sa', 'ú', 'de']}]},
            {'id': 'c', 'word': 'profª', 'profile': 'coverage', 'status': 'not_applicable', 'analyses': []}]
        report = pilots.evaluate_syllables(cases, {'method': {'habitual': ['ha', 'bi', 'tual'], 'profª': ['profª']}})
        self.assertEqual([r['methods']['method']['status'] for r in report['cases']],
                         ['matches_documented_analysis', 'missing', 'not_scored'])
        self.assertNotIn('accuracy', report)

    def test_equal_count_does_not_hide_different_boundaries(self):
        case = {'id': 'x', 'word': 'carro', 'profile': 'phonological_awareness',
                'status': 'source_checked', 'analyses': [{'segments': ['ca', 'rro']}]}
        result = pilots.evaluate_syllables([case], {'method': {'carro': ['car', 'ro']}})['cases'][0]['methods']['method']
        self.assertEqual(result['status'], 'different_representation')
        self.assertTrue(result['count_matches'])

    def test_invalid_reconstruction_is_not_scored_as_a_simple_disagreement(self):
        case = {'id': 'x', 'word': 'saúde', 'profile': 'display', 'status': 'source_checked',
                'analyses': [{'segments': ['sa', 'ú', 'de']}]}
        result = pilots.evaluate_syllables([case], {'method': {'saúde': ['sau', 'de']}})
        self.assertEqual(result['cases'][0]['methods']['method']['status'], 'invalid_reconstruction')
        result = pilots.evaluate_syllables([case], {'method': {'saúde': ['SA', 'U\u0301', 'DE']}})
        self.assertEqual(result['cases'][0]['methods']['method']['status'], 'matches_documented_analysis')

    def test_source_edges_keep_their_direction(self):
        n = pilots.NS
        triples = {('s', pilots.FORM, 'rosa'), ('t', pilots.FORM, 'flor'),
                   ('s', pilots.TYPE, n+'NomeSynset'), ('t', pilots.TYPE, n+'NomeSynset'),
                   ('s', n+'hiponimoDe', 't')}
        case = {'id': 'x', 'left': 'rosa', 'right': 'flor', 'pos': 'noun',
                'ontopt_evidence': {'subject_synset': 's', 'object_synset': 't',
                    'predicate': n+'hiponimoDe', 'relation_present': True}}
        self.assertEqual(pilots.verify_semantics([case], triples), ['x'])
        changed = copy.deepcopy(case)
        changed['ontopt_evidence']['subject_synset'] = 't'
        changed['ontopt_evidence']['object_synset'] = 's'
        with self.assertRaisesRegex(ValueError, 'source evidence'):
            pilots.verify_semantics([changed], triples)

    def test_no_transitive_edges_are_invented(self):
        n = pilots.NS
        triples = {('s', pilots.FORM, 'cão'), ('t', pilots.FORM, 'animal'),
                   ('s', pilots.TYPE, n+'NomeSynset'), ('t', pilots.TYPE, n+'NomeSynset'),
                   ('s', n+'hiponimoDe', 'middle'), ('middle', n+'hiponimoDe', 't')}
        case = {'id': 'x', 'left': 'cão', 'right': 'animal', 'pos': 'noun',
                'ontopt_evidence': {'subject_synset': None, 'object_synset': None,
                    'predicate': n+'hiponimoDe', 'relation_present': False}}
        self.assertEqual(pilots.verify_semantics([case], triples), ['x'])
        case['ontopt_evidence']['relation_present'] = True
        with self.assertRaisesRegex(ValueError, 'source evidence'):
            pilots.verify_semantics([case], triples)

    def test_bundle_cannot_silently_become_production_or_lose_references(self):
        root = Path(__file__).parent / 'docs/linguistic-pilots'
        import json
        refs = json.loads((root/'references.json').read_text())['references']
        syllables = json.loads((root/'syllable-sample.json').read_text())
        semantics = json.loads((root/'semantic-pilot.json').read_text())
        pilots.validate_bundle(refs, syllables, semantics)
        semantics['production_approved'] = True
        with self.assertRaisesRegex(ValueError, 'production'):
            pilots.validate_bundle(refs, syllables, semantics)
        semantics['production_approved'] = False
        del refs['priberam-feliz']
        with self.assertRaisesRegex(ValueError, 'reference'):
            pilots.validate_bundle(refs, syllables, semantics)

    def test_retaining_a_hyponym_as_a_synonym_is_rejected(self):
        import json
        root = Path(__file__).parent / 'docs/linguistic-pilots'
        refs = json.loads((root/'references.json').read_text())['references']
        sample = json.loads((root/'syllable-sample.json').read_text())
        semantic = json.loads((root/'semantic-pilot.json').read_text())
        # The real withheld banco/assento synonym proposal has only a hyponym edge.
        proposal = next(c for c in semantic['cases'] if c['id'] == 'sem-08')
        proposal['decision'] = 'retain_in_pilot'
        with self.assertRaisesRegex(ValueError, 'source relation type'):
            pilots.validate_bundle(refs, sample, semantic)


if __name__ == '__main__':
    unittest.main()
