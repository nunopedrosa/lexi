# Execução não interativa dos lotes

O processo pode correr sem a tua interação direta, através de `opencode run`.
Há duas peças:

- [`.opencode/agents/corpus-review.md`](../../.opencode/agents/corpus-review.md) —
  agente restrito a `docs/corpus-review/`.
- [`scripts/run-corpus-review.py`](../../scripts/run-corpus-review.py) — executor
  que chama o agente uma vez por lote, valida o JSON e atualiza o plano.

O executor **não** faz commit, push, deploy ou publicação. O agente também não
tem permissão para o fazer.

## Pré-requisitos

- `opencode` V2 instalado e autenticado no modelo que queres usar.
- O agente é descoberto a partir de `.opencode/agents/corpus-review.md` quando o
  comando corre na raiz do repositório.
- Confirma o modelo disponível com `opencode models`. O executor usa por
  predefinição `pdm_ai/DeepSeek-V4.1-Flash-TP4`; se esse modelo não estiver
  disponível na tua região ou quiseres outro, define:

```sh
export REVIEW_MODEL='provider/modelo'
```

O modelo predefinido do OpenCode pode responder com um erro de região; o
`--model` explícito evita esse problema.

## Comandos

Validar os lotes já existentes, sem chamar o modelo:

```sh
python3 scripts/run-corpus-review.py --check --from 0001 --to 0007
```

Ver o que seria executado:

```sh
python3 scripts/run-corpus-review.py --dry-run --from 0008 --to 0017
```

Correr um único lote, para inspecionar a qualidade:

```sh
python3 scripts/run-corpus-review.py --from 0008 --max-batches 1 --timeout 3600
```

Correr dez lotes:

```sh
python3 scripts/run-corpus-review.py --from 0008 --max-batches 10 --timeout 3600
```

Correr durante a noite, sem bloquear o terminal (macOS):

```sh
mkdir -p docs/corpus-review/.work
nohup caffeinate -i python3 scripts/run-corpus-review.py \
  --from 0008 --max-batches 50 --timeout 3600 --max-runtime 28800 \
  > docs/corpus-review/.work/nohup.log 2>&1 &
```

O `--max-runtime 28800` pára ao fim de oito horas. O `--max-batches` limita o
número de lotes. Sem ambos, o executor tenta avançar até ao fim da seleção.

## O que o executor faz

1. Lê `batch-plan.json` e escolhe os lotes pedidos.
2. Salta lotes já válidos, salvo com `--force`.
3. Guarda hashes de todos os ficheiros protegidos (corpus, runtime, docs,
   scripts e o próprio plano).
4. Chama:

   ```sh
   opencode run --agent corpus-review --auto \
     --title corpus-review-0008 --format json '<prompt>'
   ```

5. Valida o JSON contra o esquema, contra as aceções da fonte e contra os
   hashes dos shards.
6. Compara os hashes protegidos. Se algo fora de
   `docs/corpus-review/batches/` ou `.work/` mudou, **aborta**.
7. Só depois atualiza `batch-plan.json` com o estado `compared` e as contagens.
8. Repete em caso de falha, até `--retries`; pára após
   `--stop-after-failures` lotes falhados.

O lock `docs/corpus-review/.work/.run.lock` impede duas execuções simultâneas.

## Limites

- **Qualidade:** o agente pode producir propostas piores do que as dos lotes
  0001–0007. O executor valida a estrutura e a preservação, não a qualidade
  lexicográfica. Um lote `compared` não é um lote `reviewed`.
- **Tamanho:** 200 entradas por chamada é muito. Se o agente começar a usar
  `requer_fonte` em excesso ou a cortar comparações, reduz o lote ou revê o
  prompt antes de continuar.
- **Custo e tempo:** não há limite de tokens no `opencode run`. O agente tem
  `steps: 100`, mas isso não limita o custo. Usa `--max-batches` e
  `--max-runtime`; começa por um lote e inspeciona.
- **Cobertura:** 399 lotes restantes não cabem numa noite. O executor foi feito
  para retomar: os lotes válidos são saltados.
- **Revisão:** revê uma amostra de cada execução e, sobretudo, os casos
  `requer_fonte`, `divergente`, `erro_fonte` e `regional`.

## Ficheiros de trabalho

- `docs/corpus-review/run.log` — uma linha por acontecimento.
- `docs/corpus-review/.work/logs/<lote>.jsonl` — saída JSON do `opencode run`.
- `docs/corpus-review/.work/.run.lock` — lock de execução.
- `docs/corpus-review/batches/<lote>.json` — resultado validado.

`.work/`, `run.log` e o lock estão no `.gitignore`; os lotes JSON não.

## Parar e retomar

`Ctrl-C` ou `kill` do processo. O lock é libertado quando o processo termina.
Volta a correr o mesmo comando; os lotes já válidos são saltados. Para forçar um
lote, usa `--force --from 0008 --max-batches 1`.

## Segurança

O agente tem permissões restritas:

- só escreve em `docs/corpus-review/batches/` e `.work/`;
- não tem `webfetch`, `websearch`, `question` nem `subagent`;
- só corre `python3`, `node`, `jq`, `git status/diff/log` e comandos de leitura;
- não pode `git add`, `commit`, `push` nem `deploy`.

O `python3` e o `node` continuam a poder escrever fora dessas pastas. Por isso, o
executor compara os hashes de todos os ficheiros protegidos antes e depois de
cada lote e aborta se algo mudou. Mesmo assim, revê `git status` e `git diff`
depois de uma execução longa.
