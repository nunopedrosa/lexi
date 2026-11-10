#!/usr/bin/env python3
"""Executor não interativo dos lotes de revisão do corpus da Lexi.

Chama `opencode run` uma vez por lote, com o agente `corpus-review`, valida o
JSON produzido e só então atualiza `docs/corpus-review/batch-plan.json`.

Exemplos:
  python3 scripts/run-corpus-review.py --dry-run --from 0008 --to 0017
  python3 scripts/run-corpus-review.py --from 0008 --max-batches 10
  python3 scripts/run-corpus-review.py --check --from 0001 --to 0007

Não faz commit, push, deploy ou publicação.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = ROOT / "docs" / "corpus-review" / "batch-plan.json"
SCHEMA_PATH = ROOT / "docs" / "corpus-review" / "batch.schema.json"
BATCH_DIR = ROOT / "docs" / "corpus-review" / "batches"
WORK_DIR = ROOT / "docs" / "corpus-review" / ".work"
LOG_PATH = ROOT / "docs" / "corpus-review" / "run.log"
BATCH_RE = re.compile(r"^\d{4}$")
DEFAULT_MODEL = "pdm_ai/DeepSeek-V4.1-Flash-TP4"
RELATIONS = {
    "equivalente", "parcial", "divergente", "omissao_fonte",
    "acrescimo_proposta", "erro_fonte", "redacao", "regional",
    "gramatical", "ortografico", "nao_aplicavel",
}
STATUSES = {"proposta", "sem_proposta", "requer_fonte"}

# Tudo o que o agente não pode alterar. O executor atualiza o plano só depois
# de comparar estes hashes.
PROTECTED_EXCLUDE = {
    "docs/corpus-review/batches",
    "docs/corpus-review/.work",
    "docs/corpus-review/run.log",
    "docs/corpus-review/.run.lock",
    ".git",
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def shard_hash_map(plan: dict) -> dict[str, str]:
    return {s["path"]: s["sha256"] for s in plan["source_shards"]}


def expected_rows(plan: dict, batch: dict, cache: dict[str, list]):
    out = []
    for r in batch["ranges"]:
        path = r["path"]
        if path not in cache:
            cache[path] = load_json(ROOT / path)
        rows = cache[path][r["start_zero_based"]:r["end_exclusive"]]
        for offset, row in enumerate(rows):
            out.append((path, r["start_zero_based"] + offset, row))
    return out


def check_entry(entry: dict, path: str, row_index: int, row: list) -> list[str]:
    errors = []
    if entry.get("headword") != row[0]:
        errors.append("headword != fonte")
    if entry.get("shard") != path:
        errors.append("shard != range")
    if entry.get("row") != row_index:
        errors.append("row != posição")
    senses = row[2] or []
    got = entry.get("source_senses") or []
    if len(got) != len(senses):
        errors.append("nº de aceções != fonte")
    for j, (src, sense) in enumerate(zip(got, senses)):
        if len(sense) > 3 and isinstance(sense[3], dict):
            extra = sense[3]
        else:
            extra = {}
        expected = (
            sense[0],
            sense[1] if len(sense) > 1 else "unmarked",
            list(sense[2] or []) if len(sense) > 2 else [],
            extra.get("original"),
            list(extra.get("rules") or []),
        )
        actual = (
            src.get("text"),
            src.get("region"),
            src.get("flags"),
            src.get("original"),
            src.get("rules"),
        )
        if actual != expected:
            errors.append("aceção %d alterada" % (j + 1))
    comparison = entry.get("comparison") or []
    if len(comparison) != len(senses):
        errors.append("nº de comparações != aceções")
    for j, comp in enumerate(comparison):
        if comp.get("sense_index") != j + 1:
            errors.append("sense_index fora de ordem")
        if comp.get("relation") not in RELATIONS:
            errors.append("relação inválida: %r" % comp.get("relation"))
    if entry.get("status") not in STATUSES:
        errors.append("estado inválido: %r" % entry.get("status"))
    if (entry.get("proposal") is None) != (entry.get("status") != "proposta"):
        errors.append("proposal/status inconsistentes")
    return errors


def validate_batch(batch_id: str, plan: dict, cache: dict[str, list]) -> tuple[bool, dict, list[str]]:
    path = BATCH_DIR / (batch_id + ".json")
    errors: list[str] = []
    if not path.exists():
        return False, {}, ["ficheiro não existe"]
    try:
        doc = load_json(path)
    except Exception as exc:
        return False, {}, ["JSON inválido: %s" % exc]
    batch = next((b for b in plan["batches"] if b["id"] == batch_id), None)
    if batch is None:
        return False, {}, ["lote não existe no plano"]
    expected = expected_rows(plan, batch, cache)
    if len(doc.get("entries") or []) != len(expected):
        errors.append("nº de entradas != %d" % len(expected))
    if doc.get("schema") != 1:
        errors.append("schema != 1")
    if doc.get("batch_id") != batch_id:
        errors.append("batch_id != %s" % batch_id)
    if doc.get("status") not in ("compared", "reviewed"):
        errors.append("status do lote não é compared/reviewed")
    corpus = doc.get("corpus") or {}
    if corpus.get("entry_count") != len(expected):
        errors.append("corpus.entry_count != %d" % len(expected))
    shards = corpus.get("shards") or []
    hashes = shard_hash_map(plan)
    for r in batch["ranges"]:
        match = [s for s in shards if s.get("path") == r["path"]
                 and s.get("start_zero_based") == r["start_zero_based"]
                 and s.get("end_exclusive") == r["end_exclusive"]]
        if not match:
            errors.append("shard em falta no lote: %s %s-%s" % (r["path"], r["start_zero_based"], r["end_exclusive"]))
        elif match[0].get("sha256") != hashes.get(r["path"]):
            errors.append("hash do shard não coincide: %s" % r["path"])
    entries = doc.get("entries") or []
    for entry, (path_name, row_index, row) in zip(entries, expected):
        errors.extend(check_entry(entry, path_name, row_index, row))
    counts = doc.get("counts") or {}
    got = {
        "entries_total": len(entries),
        "entries_treated": len(entries),
        "proposals": sum(1 for e in entries if e.get("proposal") is not None),
        "sem_proposta": sum(1 for e in entries if e.get("status") == "sem_proposta"),
        "requer_fonte": sum(1 for e in entries if e.get("status") == "requer_fonte"),
        "source_senses": sum(len(e.get("source_senses") or []) for e in entries),
        "comparisons": sum(len(e.get("comparison") or []) for e in entries),
    }
    for key, value in got.items():
        if counts.get(key) != value:
            errors.append("counts.%s != %d" % (key, value))
    rel = {}
    for e in entries:
        for c in e.get("comparison") or []:
            rel[c.get("relation")] = rel.get(c.get("relation"), 0) + 1
    if counts.get("relation_counts") != dict(sorted(rel.items())):
        errors.append("counts.relation_counts não coincide")
    return not errors, got, errors


def hash_tree(base: Path, exclude: set[str]) -> dict[str, str]:
    out = {}
    for root, dirs, files in os.walk(base):
        rel_root = Path(root).relative_to(base)
        rel_root_s = str(rel_root)
        if rel_root_s == ".":
            rel_root_s = ""
        dirs[:] = [d for d in dirs if str(Path(rel_root_s) / d) not in exclude and d != ".git"]
        for name in files:
            p = Path(root) / name
            rel = str(p.relative_to(base))
            if rel in exclude or rel.endswith(".DS_Store"):
                continue
            if p.is_symlink():
                continue
            try:
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
            out[rel] = h
    return out


def protected_diff(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed = []
    for path in sorted(set(before) | set(after)):
        if before.get(path) != after.get(path):
            changed.append(path)
    return changed


def update_plan(plan: dict, batch_id: str, counts: dict) -> None:
    batch = next(b for b in plan["batches"] if b["id"] == batch_id)
    batch.update({
        "status": "compared",
        "prepared_on": date.today().isoformat(),
        "result_path": "docs/corpus-review/batches/%s.json" % batch_id,
        "counts": {
            "entries_treated": counts["entries_treated"],
            "proposals": counts["proposals"],
            "sem_proposta": counts["sem_proposta"],
            "requer_fonte": counts["requer_fonte"],
            "source_senses": counts["source_senses"],
            "comparisons": counts["comparisons"],
        },
    })
    done = [b for b in plan["batches"] if b.get("status") in ("compared", "reviewed") and b.get("counts")]
    plan["completed_batches"] = len(done)
    plan["reviewed_batches"] = sum(1 for b in plan["batches"] if b.get("status") == "reviewed")
    plan["progress"] = {
        "batches_compared": sum(1 for b in plan["batches"] if b.get("status") in ("compared", "reviewed")),
        "batches_reviewed": plan["reviewed_batches"],
        "entries_treated": sum(b["counts"]["entries_treated"] for b in done),
        "entries_with_proposal": sum(b["counts"]["proposals"] for b in done),
        "entries_without_proposal": sum(b["counts"]["sem_proposta"] + b["counts"]["requer_fonte"] for b in done),
        "source_senses_compared": sum(b["counts"]["source_senses"] for b in done),
        "last_batch": max(b["id"] for b in done) if done else None,
    }
    plan["status"] = "in_progress"
    tmp = PLAN_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, PLAN_PATH)


def build_prompt(batch_id: str, batch: dict) -> str:
    ranges = "; ".join(
        "%s linhas %d-%d" % (r["path"], r["start_zero_based"], r["end_exclusive"] - 1)
        for r in batch["ranges"]
    )
    return (
        "Processa apenas o lote %s do plano de redação e comparação do corpus da Lexi.\n\n"
        "Lê AGENTS.md, docs/corpus-review/README.md, docs/corpus-review/batch.schema.json "
        "e a entrada %s de docs/corpus-review/batch-plan.json.\n\n"
        "O lote tem %d entradas e cobre: %s.\n\n"
        "Podes usar os lotes 0001–0007 como exemplo de estrutura. Para 200 entradas, "
        "é aceitável escrever um script Python em docs/corpus-review/.work/ que leia "
        "o shard, aplique a tua tabela de propostas e escreva o JSON; valida o "
        "resultado antes de terminar.\n\n"
        "Segue o método do agente. Escreve docs/corpus-review/batches/%s.json com status "
        "\"compared\". Não alteres batch-plan.json, o corpus, o runtime, a documentação "
        "principal ou os scripts. Não faças commit, push, deploy, publicação ou pedidos "
        "externos. Se não conseguires redigir uma entrada, usa requer_fonte com dúvida "
        "explícita; não inventes.\n\n"
        "No fim, responde apenas com: %s entradas=... acoes=... propostas=... "
        "sem_proposta=... requer_fonte=..."
        % (batch_id, batch_id, batch["entries"], ranges, batch_id, batch_id)
    )


def log_line(text: str) -> None:
    line = "%s %s" % (now(), text)
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_agent(batch_id: str, batch: dict, args) -> int:
    prompt = build_prompt(batch_id, batch)
    cmd = [
        "opencode", "run",
        "--agent", args.agent,
        "--auto",
        "--title", "corpus-review-" + batch_id,
        "--format", "json",
    ]
    if args.model:
        cmd += ["--model", args.model]
    cmd.append(prompt)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    logs = WORK_DIR / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / (batch_id + ".jsonl")
    log_line("batch=%s status=start cmd=%s" % (batch_id, " ".join(cmd[:8])))
    start = time.monotonic()
    try:
        with log_path.open("ab") as out:
            proc = subprocess.run(
                cmd, cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT,
                timeout=args.timeout, check=False,
            )
        code = proc.returncode
    except subprocess.TimeoutExpired:
        log_line("batch=%s status=timeout timeout=%ss" % (batch_id, args.timeout))
        return 124
    except FileNotFoundError:
        log_line("batch=%s status=error opencode_not_found" % batch_id)
        return 127
    duration = round(time.monotonic() - start, 1)
    log_line("batch=%s status=agent_exit code=%s duration=%ss log=%s"
             % (batch_id, code, duration, log_path.relative_to(ROOT)))
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description="Executor não interativo dos lotes de revisão do corpus da Lexi.")
    parser.add_argument("--from", dest="start", default=None, help="primeiro lote (0001-0406)")
    parser.add_argument("--to", dest="end", default=None, help="último lote (0001-0406)")
    parser.add_argument("--max-batches", type=int, default=10, help="máximo de lotes nesta execução (0 = sem limite)")
    parser.add_argument("--timeout", type=int, default=3600, help="timeout por lote, em segundos")
    parser.add_argument("--retries", type=int, default=1, help="tentativas extra por lote")
    parser.add_argument("--stop-after-failures", type=int, default=2, help="parar após N lotes falhados")
    parser.add_argument("--max-runtime", type=int, default=0, help="parar após N segundos (0 = sem limite)")
    parser.add_argument("--sleep", type=float, default=5.0, help="pausa entre lotes, em segundos")
    parser.add_argument("--model", default=os.environ.get("REVIEW_MODEL", DEFAULT_MODEL), help="provider/modelo (ou REVIEW_MODEL)")
    parser.add_argument("--agent", default="corpus-review", help="agente OpenCode")
    parser.add_argument("--force", action="store_true", help="reprocessar mesmo que o lote já seja válido")
    parser.add_argument("--dry-run", action="store_true", help="listar sem executar")
    parser.add_argument("--check", action="store_true", help="validar lotes existentes e sair")
    args = parser.parse_args()

    plan = load_json(PLAN_PATH)
    ids = [b["id"] for b in plan["batches"]]
    if args.start and not BATCH_RE.match(args.start):
        parser.error("--from deve ter 4 dígitos")
    if args.end and not BATCH_RE.match(args.end):
        parser.error("--to deve ter 4 dígitos")
    start = args.start or next((b["id"] for b in plan["batches"] if b.get("status") not in ("compared", "reviewed")), ids[-1])
    end = args.end or ids[-1]
    selected = [i for i in ids if start <= i <= end]
    if args.max_batches and not args.check:
        selected = selected[:args.max_batches]

    if not selected:
        log_line("nada a fazer")
        return 0

    cache: dict[str, list] = {}
    if args.dry_run or args.check:
        bad = 0
        for batch_id in selected:
            ok, counts, errors = validate_batch(batch_id, plan, cache)
            batch = next(b for b in plan["batches"] if b["id"] == batch_id)
            if args.check:
                print("%s %s entries=%s senses=%s proposals=%s %s"
                      % (batch_id, "OK" if ok else "FAIL", counts.get("entries_treated", "?"),
                         counts.get("source_senses", "?"), counts.get("proposals", "?"),
                         "" if ok else "| " + "; ".join(errors[:3])))
                if not ok:
                    bad += 1
            else:
                state = "valid" if ok else "run"
                print("%s %s entries=%d ranges=%s" % (batch_id, state, batch["entries"], batch["ranges"]))
        return 1 if args.check and bad else 0

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = (WORK_DIR / ".run.lock").open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log_line("outro executor já está a correr; lock em %s" % (WORK_DIR / ".run.lock"))
        return 1

    before = hash_tree(ROOT, PROTECTED_EXCLUDE)
    started = time.monotonic()
    failures = 0
    for batch_id in selected:
        if args.max_runtime and (time.monotonic() - started) > args.max_runtime:
            log_line("paragem por max_runtime=%ss" % args.max_runtime)
            break
        ok, counts, errors = validate_batch(batch_id, plan, cache)
        if ok and not args.force:
            log_line("batch=%s status=skip reason=valid" % batch_id)
            continue
        batch = next(b for b in plan["batches"] if b["id"] == batch_id)
        log_line("batch=%s status=run entries=%d" % (batch_id, batch["entries"]))
        last_errors = errors
        for attempt in range(args.retries + 1):
            if attempt:
                log_line("batch=%s status=retry attempt=%d" % (batch_id, attempt))
            code = run_agent(batch_id, batch, args)
            after = hash_tree(ROOT, PROTECTED_EXCLUDE)
            changed = protected_diff(before, after)
            if changed:
                log_line("batch=%s status=abort protected_changed=%s" % (batch_id, ",".join(changed[:10])))
                return 2
            ok, counts, last_errors = validate_batch(batch_id, plan, cache)
            if ok:
                break
            log_line("batch=%s status=invalid errors=%s" % (batch_id, "; ".join(last_errors[:5])))
        if not ok:
            failures += 1
            log_line("batch=%s status=failed" % batch_id)
            if failures >= args.stop_after_failures:
                log_line("paragem após %d falhas" % failures)
                return 3
            continue
        failures = 0
        update_plan(plan, batch_id, counts)
        before = hash_tree(ROOT, PROTECTED_EXCLUDE)
        log_line("batch=%s status=ok entries=%d senses=%d proposals=%d sem_proposta=%d requer_fonte=%d"
                 % (batch_id, counts["entries_treated"], counts["source_senses"], counts["proposals"],
                    counts["sem_proposta"], counts["requer_fonte"]))
        if args.sleep:
            time.sleep(args.sleep)
    log_line("fim selected=%d" % len(selected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
