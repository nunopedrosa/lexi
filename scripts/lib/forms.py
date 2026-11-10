"""Build a form-to-lemma index with the Hunspell command-line stemmer.

Hunspell is a build-time tool here. The PWA does not ship Hunspell or its
runtime; it only consumes the generated JSON index.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Dict, Iterable, List, Set


def hunspell_available() -> bool:
    return shutil.which("hunspell") is not None


def build_stem_index(
    words: Iterable[str],
    dic_base: str,
    allowed_stems: Set[str],
) -> Dict[str, List[str]]:
    """Return ``form -> [lemma, ...]`` using ``hunspell -s``.

    ``dic_base`` is the path to ``pt_PT`` (without the ``.dic`` suffix).
    Unknown words are returned by Hunspell as their own stem; those entries are
    discarded when the form is not itself an allowed lemma.
    """

    if not hunspell_available():
        raise RuntimeError(
            "hunspell is not installed; rerun with --no-forms or install it"
        )

    input_text = "\n".join(words) + "\n"
    process = subprocess.run(
        ["hunspell", "-d", dic_base, "-s"],
        input=input_text,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if process.returncode not in (0, 1):
        raise RuntimeError(
            "hunspell failed with exit code %s" % process.returncode
        )

    index: Dict[str, Set[str]] = {}
    for line in process.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        form, stem = parts
        stem_lower = stem.lower()
        if stem_lower not in allowed_stems:
            continue
        index.setdefault(form, set()).add(stem_lower)

    return {
        form: sorted(stems)
        for form, stems in index.items()
    }
