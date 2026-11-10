# Redação e comparação do corpus

Plano de 2026-11-08: **81 068 entradas, em 406 lotes** — 405 de 200 e um de 68.
O [manifesto](batch-plan.json) identifica os intervalos de linhas e hashes dos
shards. O **lote 0001** foi tratado e comparado; os restantes 405 estão por
iniciar. Não existe processamento em segundo plano. As palavras já discutidas
não contam como lotes concluídos neste modelo.

O lote 0001 serviu para calibrar o formato e o esforço real. O tamanho é uma
escolha operacional inicial, não garantia de capacidade ou qualidade: entradas
polissémicas e técnicas podem exigir subdivisão. Lotes de 500 dariam 163 lotes,
mas concentrariam mais sentidos e dúvidas numa única revisão. O lote 0001 é
atípico: cobre o shard `_` e é composto quase todo por sufixos e símbolos, pelo
que não representa a distribuição lexical das 81 068 entradas.

## Trabalho por entrada

1. Redigir uma proposta PT-PT a partir do lema, antes de apresentar as definições
   atuais nessa etapa. Distinguir sentidos e classes gramaticais que se consigam
   sustentar, sem simplificação automática por idade.
2. Comparar a proposta com todas as aceções existentes, incluindo `original` e
   `curated`. Assinalar sentidos em falta em qualquer dos lados, divergências,
   regionalismos, problemas gramaticais e alterações apenas de redação.
3. Guardar a proposta e a comparação separadamente. Casos sem base suficiente
   ficam como `sem_proposta` ou `requer_fonte`, com a dúvida explícita. Não se
   preenchem lacunas com definições inventadas.
4. Avaliar o lote como conjunto e selecionar o que pode ser aproveitado. Uma
   comparação feita pelo mesmo modelo não é revisão independente, e concordar
   com a fonte não prova que ambos estejam corretos.

Uma entrada conta como tratada mesmo que termine com dúvida documentada e sem
definição proposta. Assim, a cobertura não esconde casos difíceis. O total de
entradas tratadas, propostas redigidas e propostas aprovadas deve ser separado.

## Estado

| Lote | Entradas | Aceções | Propostas | Sem proposta | Requer fonte | Estado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0001 | 200 | 288 | 191 | 0 | 9 | comparado |
| 0002 | 200 | 282 | 200 | 0 | 0 | comparado |
| 0003 | 200 | 235 | 200 | 0 | 0 | comparado |
| 0004 | 200 | 220 | 200 | 0 | 0 | comparado |
| 0005 | 200 | 221 | 200 | 0 | 0 | comparado |
| 0006 | 200 | 220 | 200 | 0 | 0 | comparado |
| 0007 | 200 | 246 | 200 | 0 | 0 | comparado |
| 0008–0406 | 79 668 | — | — | — | — | por iniciar |

Os lotes 0001–0007 estão em [`batches/`](batches/), validados contra
[`batch.schema.json`](batch.schema.json). **Comparado não significa revisto,
aprovado ou integrado.** A comparação foi feita pelo mesmo modelo que redigiu as
propostas; não é revisão independente.

## Registo do lote 0001

O lote cobre `data/_.json`, linhas 0–199, com hash
`f7665614683d8f9a69b9ded03f94b3464d2734f19f93b92e0c49042a2b8ee547`.
Tem 200 entradas e 288 aceções da fonte. Foram redigidas 191 propostas; 9
entradas ficaram como `requer_fonte`, sem proposta inventada. Não houve
`sem_proposta`.

Relações registadas: 187 equivalentes, 60 parciais, 12 omissões da fonte, 12
problemas gramaticais, 6 divergências, 6 erros da fonte, 2 artefactos não
aplicáveis, 1 acréscimo da proposta, 1 problema ortográfico e 1 marca regional.

Casos que justificam revisão prioritária:

- `'s Hertogenbosch` e `'s-Hertogenbosch` são duas entradas para a mesma cidade.
- `-eira` e `-eiro` repetem as mesmas seis aceções; `-ia` tem três aceções
  iniciais duplicadas e `-ismo` tem a definição truncada em «exprime a ideia de:».
- `-ation`, `-eichon` e `-men` não são sufixos portugueses correntes; `-ex` tem
  uma definição incompreensível; `-ingue`, `-ape`, `-aute`, `-eima`, `-mor` e
  `-lhar` não têm base suficiente para uma proposta.
- `-pata` inclui uma anotação em inglês e «crônica» em grafia brasileira;
  `-orama` conserva «espectáculo» na grafia anterior ao Acordo.
- Várias entradas tratam flexão como derivação (`-as`, `-es`, `-o`, `-s`) ou
  chamam «sufixo» a elementos de composição (`-cídio`, `-istão`).

Estes resultados são hipóteses de trabalho e dúvidas documentadas. Não
constituem certificação lexicográfica nem autorizam alterações ao corpus.

## Registo do lote 0002

O lote cobre `data/_.json`, linhas 200–260, e `data/a.json`, linhas 0–138.
Tem 200 entradas e 282 aceções. Foram redigidas 200 propostas; não houve
`sem_proposta` nem `requer_fonte`. Relações: 254 equivalentes, 9 regionais, 12
não aplicáveis, 5 parciais, 1 gramatical e 1 ortográfica.

O lote é quase todo de siglas, números e símbolos. Nas siglas, a proposta
identifica a expansão que a fonte já apresenta; não é uma redação independente.
A maioria das entradas 0074–0199 foi produzida por esse método e tem a dúvida
correspondente registada. Os símbolos e os números receberam descrições
próprias, mas continuam a depender da leitura da fonte.

Este lote não serve para calibrar o esforço de palavras comuns: as siglas têm
uma estrutura de definição muito diferente e a expansão já está na fonte. A
comparação também não é independente; serve para detetar duplicados,
regionalismos e artefactos, não para certificar as expansões.

## Registo do lote 0003

O lote cobre `data/a.json`, linhas 139–338. Tem 200 entradas e 235 aceções.
Foram redigidas 200 propostas; não houve `sem_proposta` nem `requer_fonte`.
Relações: 216 equivalentes, 13 parciais, 5 regionais e 1 não aplicável.

O lote começa com siglas e passa depois para nomes próprios: municípios
brasileiros, cidades, prenomes, personagens bíblicas e mitológicas. Nos nomes
próprios, a proposta normaliza a definição já presente na fonte; não é uma
redação independente. A maioria das entradas tem a dúvida correspondente.

Casos que justificam revisão:

- `Agamemnon`, `Agamenon`, `Agamémnon` e `Agamêmnon` são quatro entradas para a
  mesma figura mitológica, com variantes ortográficas.
- `Abadia dos Dourados` tem aceções truncadas na fonte; a população e parte da
  definição perderam-se na conversão.
- `Abissínia`, `Al-Qaeda` e `Adonai` usam formas brasileiras ou menos correntes
  em PT-PT («Eritréia», «Oriente Médio», «Velho Testamento»); a proposta
  assinala a variante, sem alterar o original.
- `Abel` e `Abner` usam «personagem bíblico»; em PT-PT, «personagem» é feminino.
- `Advento` tem uma lacuna na indicação das datas («entre 27 de novembro 3 de
  dezembro»).

Este lote também não serve para calibrar palavras comuns: é quase todo formado
por siglas e nomes próprios.

## Registo dos lotes 0004–0007

Os lotes 0004–0006 cobrem `data/a.json` 339–938 e são quase só nomes próprios.
O lote 0007 cobre 939–1138: 152 nomes próprios e 48 expressões comuns, redigidas
à mão. No total, 800 entradas e 907 aceções; 800 propostas, sem `sem_proposta`
nem `requer_fonte`.

Relações agregadas: 843 equivalentes, 49 parciais, 13 regionais, 1 erro da fonte
e 1 não aplicável. Os nomes próprios continuam a ser normalizações da definição
da fonte; as 48 expressões do 0007 são propostas editoriais mais próximas do
regime do lote 0001.

Casos que justificam revisão:

- Variantes no mesmo lote: `Allan`/`Alan`, `Alfa e Ómega`/`Alfa e Ômega`,
  `Arménia`/`Armênia`, `Azerbaidjão`/`Azerbaijão`, `Arena`/`ARENA`,
  `Avante`/`AVANTE`, `Antártida`/`Antárctida`/`Antárctica`,
  `Antigo Testamento`/`Velho Testamento`.
- Várias entradas de países e estados estão truncadas na fonte: `Alasca`,
  `Albânia`, `Amapá`, `Amazonas`, `Amazônia Azul`, `América do Norte`, `Andes`,
  `Andorra`, `Antigo Regime`, `Arizona`, `Arábia Saudita`, `Arménia`.
- Correções PT-PT assinaladas sem alterar o original: `Arménia`, `Génesis`,
  `Antigo Testamento`, `Médio Oriente`, `Ómega`, `personagem`, `de facto`.
- `a cerca de` está assinalado como possível erro: em PT-PT, «cerca de» é a
  forma corrente para «aproximadamente»; «a cerca de» significa «a uma distância
  de».
- `a capella` e `a cappella` são duas entradas para a mesma expressão.
- As expressões marcadas `(Galicia)` foram identificadas como uso galego, não
  português: `a atoutinhadelas`, `a canchapernas`, `a carranchapernas`,
  `a carão`, `a cotio`.

## Formato do registo

Cada lote é um JSON validável por [`batch.schema.json`](batch.schema.json). Por
entrada, conserva o lema, a classe, o shard/linha, a proposta (texto, âmbito e
confiança), o estado, a comparação por aceção (índice, relação e nota), as
dúvidas e **todas as aceções da fonte**, incluindo `text`, `region`, `flags`,
`original` e `rules`. `original` e `rules` só existem quando a fonte os tem.

Relações permitidas: `equivalente`, `parcial`, `divergente`, `omissao_fonte`,
`acrescimo_proposta`, `erro_fonte`, `redacao`, `regional`, `gramatical`,
`ortografico` e `nao_aplicavel`. A relação descreve a comparação, não aprova a
fonte nem a proposta.

O lote 0001 não usa `redacao` porque as diferenças de redação foram absorvidas
por `equivalente` ou `parcial`; o campo fica disponível para lotes seguintes.

O lote 0001 ocupa cerca de 220 KB porque copia integralmente as 288 aceções da
fonte. A 406 lotes, este formato poderia aproximar-se de 90 MB. Se o volume for
um problema, os lotes seguintes podem referenciar `shard`/`linha`/`índice` e
conservar um hash da aceção, mas essa alteração exige uma nova versão do esquema
e não deve ser feita silenciosamente.

## Execução não interativa

O processo pode ser executado por um agente restrito, com validação do JSON e
verificação dos hashes do corpus, através de
[`scripts/run-corpus-review.py`](../../scripts/run-corpus-review.py). As
instruções, os limites e os exemplos estão em [AUTOMATION.md](AUTOMATION.md).
O executor não substitui revisão humana e não publica.

## Limites

- O corpus, os originais e as 36 respostas aprovadas permanecem intactos.
- O lote 0001 foi comparado pelo mesmo modelo que redigiu as propostas; não
  houve revisão independente. A concordância com a fonte não certifica a fonte
  nem a proposta.
- No lote 0002, as propostas de siglas derivam da expansão já presente na fonte;
  não são redações independentes e não devem ser lidas como certificação.
- Os lotes 0001–0007 são atípicos (sufixos, símbolos, siglas, números, nomes
  próprios e expressões fixas); nenhum serve para estimar a qualidade média do
  corpus nem para fixar o esforço dos restantes lotes.
- A ordem dos lotes garante cobertura; não representa frequência ou importância
  para a Laura. Esse critério poderá orientar uma seleção posterior para uso.
- A ordem começa com símbolos, sufixos, siglas e nomes próprios; os primeiros
  lotes não são representativos do vocabulário comum. Uma calibração de palavras
  comuns exige uma amostra fora desta sequência.
- O plano não acrescenta backend, API, dependências, build ou pedidos à PWA.
- Não autoriza regeneração, integração de propostas, commit, push ou publicação.
- Se os shards mudarem, conferir os hashes e reconciliar os intervalos antes de
  continuar. Não usar posições antigas sobre dados diferentes.

O resultado pretendido é um conjunto de propostas comparadas que possamos
avaliar, não a declaração automática de que as 81 mil entradas foram validadas.
Os lotes 0001–0007 são os primeiros registos; não são uma amostra
representativa.
