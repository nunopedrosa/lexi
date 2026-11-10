#!/usr/bin/env python3
"""Check isolated linguistic pilots and report reference agreement, without changing app data."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unicodedata
import zipfile

NS = 'http://ontopt.dei.uc.pt/OntoPT.owl#'
FORM = NS + 'formaLexical'
TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
CLASSES = {'noun': 'NomeSynset', 'verb': 'VerboSynset', 'adjective': 'AdjectivoSynset'}
ARCHIVE_SHA = 'f89e7486b883c1a95166bb24874b18a581efc1c0187e88619659f4ff6b61f5a3'


def norm(text):
    return unicodedata.normalize('NFC', text).casefold()


def reconstructs(word, segments):
    return (isinstance(segments, list) and bool(segments)
            and all(isinstance(s, str) and s for s in segments)
            and norm(''.join(segments)) == norm(word))


def validate_bundle(references, syllables, semantics):
    for bundle in (syllables, semantics):
        if bundle.get('schema') != 1 or bundle.get('production_approved') is not False:
            raise ValueError('pilot schema/production approval must remain explicit and disabled')
        ids = set()
        for case in bundle['cases']:
            if case['id'] in ids:
                raise ValueError('duplicate pilot case ID')
            ids.add(case['id'])
            if not case.get('references') or any(r not in references for r in case['references']):
                raise ValueError('missing pilot reference')
            if case.get('human_review') != 'pending':
                raise ValueError('this source-checked pilot must not claim completed human review')
    for case in syllables['cases']:
        analyses = case['analyses']
        if case['status'] not in ('source_checked', 'documented_variants', 'pending', 'not_applicable'):
            raise ValueError('unknown syllable review status')
        if case['status'] in ('pending', 'not_applicable'):
            if analyses:
                raise ValueError('unresolved syllable case must not carry accepted analyses')
        elif not analyses or any(not reconstructs(case['word'], a['segments']) for a in analyses):
            raise ValueError('syllable reference does not reconstruct the headword')
    if semantics['source']['artifact_sha256'] != ARCHIVE_SHA:
        raise ValueError('semantic pilot source is not the reviewed archive')
    for case in semantics['cases']:
        if case.get('production_approved') is not False or case.get('lexi_sense_alignment') is not None:
            raise ValueError('production or automatic sense alignment is not approved')
        if case['pos'] not in CLASSES or not case.get('scope') or not case.get('excluded_uses'):
            raise ValueError('semantic context and part of speech are required')
        if case['decision'] not in ('retain_in_pilot', 'reject_for_pilot', 'defer_no_direct_edge', 'defer_sense_review'):
            raise ValueError('unknown semantic review decision')
        if not case.get('source_locator') or not any(r != 'ontopt' for r in case['references']):
            raise ValueError('independent lexical reference and locator required')
        if case['decision'] == 'retain_in_pilot':
            evidence = case['ontopt_evidence']
            expected = {'synonym': 'same_synset', 'hyponym': NS+'hiponimoDe',
                        'antonym': NS+{'noun': 'antonimoNDe', 'verb': 'antonimoVDe',
                                      'adjective': 'antonimoAdjDe'}[case['pos']]}
            if (evidence['predicate'] != expected.get(case['relation'])
                    or evidence['relation_present'] is not True):
                raise ValueError('retained pair must preserve source relation type')


def evaluate_syllables(cases, methods):
    rows = []
    groups = {}
    for case in cases:
        analyses = [a['segments'] for a in case['analyses']]
        row = {'id': case['id'], 'word': case['word'], 'profile': case['profile'],
               'references': case.get('references', []), 'documented_analyses': case['analyses'], 'methods': {}}
        for method, words in methods.items():
            parts = words.get(case['word'])
            count_matches = None
            if case['status'] in ('pending', 'not_applicable'):
                status = 'not_scored'
            elif parts is None:
                status = 'missing'
            elif not reconstructs(case['word'], parts):
                status = 'invalid_reconstruction'
            else:
                count_matches = any(len(parts) == len(a) for a in analyses)
                matched = any([norm(p) for p in parts] == [norm(p) for p in a] for a in analyses)
                status = 'matches_documented_analysis' if matched else 'different_representation'
            row['methods'][method] = {'segments': parts, 'status': status, 'count_matches': count_matches}
            groups.setdefault(case['profile'], {}).setdefault(method, Counter())[status] += 1
        rows.append(row)
    return {'cases': rows, 'by_profile': groups,
            'caveat': 'Diagnostic, purposive sample; no global accuracy estimate. Reference display, phonology and pronunciation variants are distinct profiles.'}


def verify_semantics(cases, triples):
    """Require explicit triples; caller supplies all subjects containing the case words."""
    forms = {}
    for subject, predicate, obj in triples:
        if predicate == FORM:
            forms.setdefault(obj, set()).add(subject)
    checked = []
    for case in cases:
        pos = NS + CLASSES[case['pos']]
        left = {s for s in forms.get(case['left'], set()) if (s, TYPE, pos) in triples}
        right = {s for s in forms.get(case['right'], set()) if (s, TYPE, pos) in triples}
        e = case['ontopt_evidence']
        predicate = e['predicate']
        present = bool(left & right) if predicate == 'same_synset' else any(
            (s, predicate, t) in triples for s in left for t in right)
        if present != e['relation_present']:
            raise ValueError('source evidence presence differs: ' + case['id'])
        if present:
            s, t = e['subject_synset'], e['object_synset']
            valid = s in left and t in right
            valid = valid and (s == t if predicate == 'same_synset' else (s, predicate, t) in triples)
            if not valid:
                raise ValueError('source evidence IDs/direction differ: ' + case['id'])
        checked.append(case['id'])
    return checked


def read_ontopt_evidence(archive, cases):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError('Onto.PT archive hash differs from reviewed source')
    from rdflib import Graph, Namespace, Literal
    with zipfile.ZipFile(archive) as package:
        graph = Graph().parse(data=package.read('OntoPTv0.6.n3'), format='n3')
    subjects = set()
    for word in {c[k] for c in cases for k in ('left', 'right')}:
        subjects.update(graph.subjects(Namespace(NS).formaLexical, Literal(word)))
    # All synsets containing any queried word, across classes. No inferred triples.
    return {(str(s), str(p), str(o)) for s in subjects for p, o in graph.predicate_objects(s)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent.parent
    parser.add_argument('--pilots', type=Path, default=root/'docs/linguistic-pilots')
    parser.add_argument('--data', type=Path, default=root/'data')
    parser.add_argument('--lx-archive', type=Path, required=True)
    parser.add_argument('--ontopt-archive', type=Path, required=True)
    args = parser.parse_args()
    try:
        files = {name: (args.pilots/name).read_bytes() for name in
                 ('references.json', 'syllable-sample.json', 'semantic-pilot.json')}
        refs = json.loads(files['references.json'])['references']
        sample = json.loads(files['syllable-sample.json'])
        semantic = json.loads(files['semantic-pilot.json'])
        validate_bundle(refs, sample, semantic)
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('syllable_audit', Path(__file__).with_name('audit-syllables.py'))
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        # Evaluate the actual sample, including flexions absent from headword shards.
        # This tiny temporary input is not a regenerated Lexi corpus.
        with tempfile.TemporaryDirectory(prefix='lexi-pilot-input-') as folder:
            fixture = Path(folder)
            (fixture/'meta.json').write_text(json.dumps({'keys': ['sample']}), encoding='utf-8')
            (fixture/'sample.json').write_text(json.dumps(
                [[c['word'], '', []] for c in sample['cases']], ensure_ascii=False), encoding='utf-8')
            candidate = audit.from_lx_archive(fixture, args.lx_archive)
        current, hashes = {}, {}
        meta_path = args.data/'meta.json'
        hashes['meta.json'] = hashlib.sha256(meta_path.read_bytes()).hexdigest()
        for key in json.loads(meta_path.read_bytes())['keys']:
            path = args.data/'syllables'/(key+'.json')
            raw = path.read_bytes()
            hashes['syllables/'+key+'.json'] = hashlib.sha256(raw).hexdigest()
            current.update(json.loads(raw))
        verified = verify_semantics(semantic['cases'], read_ontopt_evidence(args.ontopt_archive, semantic['cases']))
        report = {'schema': 1, 'production_approved': False, 'expert_validated': False,
                  'pilot_sha256': {k: hashlib.sha256(v).hexdigest() for k, v in files.items()},
                  'baseline_sha256': hashes, 'lx_source': candidate['source'],
                  'lx_input_scope': 'Alphabetic sample strings, including flexions absent from headword shards.',
                  'semantic_source': semantic['source'],
                  'syllables': evaluate_syllables(sample['cases'], {'current_hyphenation': current, 'lx_v1.1': dict(candidate['rows'])}),
                  'semantics': {'source_evidence_verified': verified,
                      'decisions': dict(Counter(c['decision'] for c in semantic['cases'])),
                      'caveat': 'Only the selected pairs were source-checked. No whole-synset or Lexi-sense certification; user review pending.'}}
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError, OSError, ImportError) as error:
        print('Pilot evaluation failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
