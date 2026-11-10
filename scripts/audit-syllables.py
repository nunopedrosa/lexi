#!/usr/bin/env python3
"""Compare a local candidate with shipped suggestions. Never fetch or write data."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import unicodedata


def normalized(text):
    return unicodedata.normalize('NFC', text).casefold()


def valid_parts(word, parts):
    return (isinstance(parts, list) and bool(parts)
            and all(isinstance(p, str) and p
                    and unicodedata.normalize('NFC', p).isalpha() for p in parts)
            and normalized(''.join(parts)) == normalized(word))


def compare(data_dir, candidate, limit=50):
    if not isinstance(candidate, dict) or candidate.get('schema') != 1:
        raise ValueError('candidate schema must be 1')
    source = candidate.get('source', {})
    if not isinstance(source, dict):
        raise ValueError('source must be an object')
    for field in ('id', 'version', 'license', 'artifact_sha256'):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise ValueError('missing source.' + field)
    if not re.fullmatch('[0-9a-f]{64}', source['artifact_sha256']):
        raise ValueError('source.artifact_sha256 must be a lowercase SHA-256')
    if not isinstance(candidate.get('rows'), list):
        raise ValueError('candidate rows must be an array')
    proposed = {}
    for row in candidate['rows']:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str):
            raise ValueError('candidate rows must be [headword, syllables] pairs')
        word = unicodedata.normalize('NFC', row[0])
        if word in proposed:
            raise ValueError('duplicate candidate: ' + word)
        proposed[word] = row[1]
    if not isinstance(limit, int) or limit < 0:
        raise ValueError('example limit must be nonnegative')
    counts = dict.fromkeys((
        'eligible_headwords', 'excluded_headwords', 'baseline_available',
        'baseline_invalid', 'candidate_available', 'candidate_invalid',
        'compared', 'same_boundaries', 'different_boundaries', 'different_counts',
        'newly_covered', 'missing_candidate', 'unexpected_candidates'), 0)
    report = {'schema': 1, 'linguistically_validated': False,
              'scope': 'Alphabetic headwords only; exact NFC keys, case-insensitive boundaries.',
              'caveat': 'Shipped data are hyphenation suggestions. Agreement is not linguistic validation.',
              'candidate_source': source, 'counts': counts,
              'differences': [], 'new_coverage': [], 'invalid': [], 'probes': []}
    hashes = {}

    def read(relative):
        raw = (data_dir / relative).read_bytes()
        hashes[relative] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    probe_words = {'saúde', 'saída', 'país', 'reunião', 'água', 'feudal',
                   'gaseificar', 'casa', 'açúcar', 'psicologia', 'aéreo'}
    eligible = set()
    for key in read('meta.json')['keys']:
        # One shipped definition/syllable shard at a time; no corpus regeneration.
        current = dict(read('syllables/' + key + '.json'))
        for row in read(key + '.json'):
            word = unicodedata.normalize('NFC', row[0])
            if not word.isalpha():
                counts['excluded_headwords'] += 1
                continue
            if word in eligible:
                raise ValueError('duplicate normalized headword: ' + word)
            eligible.add(word)
            counts['eligible_headwords'] += 1
            old = current.get(row[0])
            new = proposed.get(word)
            if old is not None:
                counts['baseline_available'] += 1
                if not valid_parts(word, old):
                    counts['baseline_invalid'] += 1
            if word in probe_words:
                report['probes'].append({'word': word, 'current': old, 'candidate': new})
            if word not in proposed:
                counts['missing_candidate'] += 1
                continue
            counts['candidate_available'] += 1
            item = {'word': word, 'current': old, 'candidate': new}
            if not valid_parts(word, new):
                counts['candidate_invalid'] += 1
                if len(report['invalid']) < limit:
                    report['invalid'].append(item)
                continue
            if old is None:
                counts['newly_covered'] += 1
                if len(report['new_coverage']) < limit:
                    report['new_coverage'].append(item)
                continue
            if not valid_parts(word, old):
                continue
            counts['compared'] += 1
            if [normalized(p) for p in old] == [normalized(p) for p in new]:
                counts['same_boundaries'] += 1
            else:
                counts['different_boundaries'] += 1
                if len(old) != len(new):
                    counts['different_counts'] += 1
                if len(report['differences']) < limit:
                    report['differences'].append(item)
    counts['unexpected_candidates'] = len(set(proposed) - eligible)
    report['baseline_sha256'] = hashes
    return report


def from_lx_archive(data_dir, archive):
    """Run only the exact official distribution inspected on 2026-11-08.

    Its CLI writes a log; the adapter calls the same exception/rule functions
    without the log or capitalization, which comparison ignores anyway.
    """
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != '29fe1e5f4434d44770c016bf184561433a8dc518e48f3553f2c8ccda07d94ba9':
        raise ValueError('LX archive does not match the reviewed SHA-256')
    with tempfile.TemporaryDirectory(prefix='lexi-lx-review-') as folder:
        with tarfile.open(archive) as package:
            for name in ('silabificador.py', 'dicionario_silabificado.py'):
                member = package.getmember(name)
                if not member.isfile():
                    raise ValueError('LX member must be a regular file: ' + name)
                Path(folder, name).write_bytes(package.extractfile(member).read())
        previous = sys.modules.get('dicionario_silabificado')
        old_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            modules = {}
            for name in ('dicionario_silabificado', 'silabificador'):
                spec = importlib.util.spec_from_file_location(name, Path(folder, name + '.py'))
                module = importlib.util.module_from_spec(spec)
                if name == 'dicionario_silabificado':
                    sys.modules[name] = module
                spec.loader.exec_module(module)
                modules[name] = module
            lx = modules['silabificador']
            rows = []
            meta = json.loads((data_dir / 'meta.json').read_text(encoding='utf-8'))
            for key in meta['keys']:
                for word, *_ in json.loads((data_dir / (key + '.json')).read_text(encoding='utf-8')):
                    if not unicodedata.normalize('NFC', word).isalpha():
                        continue
                    parts = modules['dicionario_silabificado'].check(word.lower())
                    if parts is False:
                        parts = word if len(word) == 1 else lx.silabifica(lx.minusculas(word))[1:-1]
                    rows.append([word, parts.split('|')])
        finally:
            sys.dont_write_bytecode = old_bytecode
            if previous is None:
                sys.modules.pop('dicionario_silabificado', None)
            else:
                sys.modules['dicionario_silabificado'] = previous
    return {'schema': 1, 'source': {
        'id': 'lx-syllabifier', 'version': '1.1', 'license': 'BSD-3-Clause (archive LICENSE)',
        'url': 'https://portulanclarin.net/static/downloads/lxsyllabifier/LX-Syllabifier.tar.gz',
        'attribution': 'Francisco Costa, João Rodrigues, João Silva and António Branco; NLX, Universidade de Lisboa',
        'artifact_sha256': digest}, 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path, nargs='?', help='Local JSON; schema described in docs/linguistic-resources.md')
    parser.add_argument('--lx-archive', type=Path, help='Reviewed official LX v1.1 tar.gz; no download')
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parent.parent / 'data')
    parser.add_argument('--limit', type=int, default=50, help='Maximum examples per category')
    args = parser.parse_args()
    if bool(args.candidate) == bool(args.lx_archive):
        parser.error('supply candidate JSON or --lx-archive, exclusively')
    try:
        if args.lx_archive:
            candidate = from_lx_archive(args.data, args.lx_archive)
            raw = json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode('utf-8')
        else:
            raw = args.candidate.read_bytes()
            candidate = json.loads(raw)
        result = compare(args.data, candidate, args.limit)
        result['candidate_json_sha256'] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, TypeError, OSError, KeyError) as error:
        print('Audit failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
