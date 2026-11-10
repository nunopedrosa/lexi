#!/usr/bin/env python3
"""Inspect the reviewed local Onto.PT archive; stdout only, no inference or conversion."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parent.parent / 'data')
    args = parser.parse_args()
    digest = hashlib.sha256(args.archive.read_bytes()).hexdigest()
    if digest != 'f89e7486b883c1a95166bb24874b18a581efc1c0187e88619659f4ff6b61f5a3':
        parser.error('archive does not match the reviewed Onto.PT v0.6 SHA-256')
    try:
        from rdflib import Graph, Namespace, RDF, Literal
        import rdflib
    except ImportError:
        parser.error('inspection requires the optional developer library RDFLib; the PWA does not use it')
    with zipfile.ZipFile(args.archive) as package:
        graph = Graph().parse(data=package.read('OntoPTv0.6.n3'), format='n3')
    ns = Namespace('http://ontopt.dei.uc.pt/OntoPT.owl#')
    synsets = set()
    classes = {}
    for name in ('NomeSynset', 'VerboSynset', 'AdjectivoSynset', 'AdverbioSynset'):
        items = set(graph.subjects(RDF.type, ns[name]))
        classes[name] = len(items)
        synsets.update(items)
    forms = {str(obj) for sub, obj in graph.subject_objects(ns.formaLexical) if sub in synsets}
    relations = Counter(str(pred).split('#')[-1] for sub, pred, obj in graph
                        if sub in synsets and obj in synsets)
    meta = json.loads((args.data / 'meta.json').read_text(encoding='utf-8'))
    words = {row[0] for key in meta['keys'] for row in
             json.loads((args.data / (key + '.json')).read_text(encoding='utf-8'))}
    queries = []
    for word in ('casa', 'casa de banho', 'feliz', 'bom', 'banco', 'autocarro'):
        ids = sorted(str(sub) for sub in graph.subjects(ns.formaLexical, Literal(word)) if sub in synsets)
        queries.append({'word': word, 'synset_ids': ids})
    # A small source example exposes regional mixtures/noise; it is not a synonym answer.
    sample_id = ns['26593']
    result = {
        'schema': 1, 'linguistically_validated': False,
        'source': {'id': 'ontopt', 'version': '0.6', 'license': 'CC-BY-3.0',
                   'attribution': 'Onto.PT, Universidade de Coimbra; Hugo Gonçalo Oliveira and Paulo Gomes',
                   'url': 'https://ontopt.dei.uc.pt/index.php?sec=downloads',
                   'archive_sha256': digest},
        'method': 'Explicit N3 triples only; exact case-sensitive overlap; no inference or sense alignment.',
        'rdflib_version': rdflib.__version__, 'triples': len(graph),
        'synset_classes': classes, 'lexical_forms': len(forms),
        'lexi_headwords': len(words), 'exact_lexi_overlap': len(forms & words),
        'explicit_relations_between_synsets': dict(sorted(relations.items())),
        'queries': queries,
        'unreviewed_source_example': {'synset_id': str(sample_id),
            'forms': sorted(str(obj) for obj in graph.objects(sample_id, ns.formaLexical)),
            'note': 'Source membership only; do not present as interchangeable PT-PT synonyms.'}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
