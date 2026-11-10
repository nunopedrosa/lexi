# Prioridade PT-PT e nuances regionais

Preferência reforçada pelo utilizador em 8 de novembro de 2026: evitar nuances
brasileiras nas respostas habituais. As decisões editoriais anteriores foram
bem acolhidas; isso não aprova a publicação, a substituição dos dados nem todos
os casos individuais. Esta nota acrescenta um requisito de revisão regional.

O [ensaio dirigido a legal, apelido e propina](regional-review.md) já apresenta
os originais, as respostas editoriais propostas e as fontes de uso em Portugal.
O [demonstrador regional](regional-demo/index.html) permite avaliar os três
comportamentos separadamente da Lexi.

## Critério para a apresentação futura

- Privilegiar grafia, vocabulário, construções e sentidos documentados em
  português europeu. Uma grafia portuguesa não basta se o sentido for regional.
- Rever palavra **e aceção/contexto/registo**. Não banir uma palavra inteira
  por ter também um uso brasileiro; palavras partilhadas pelas variedades
  continuam a ser elegíveis nos sentidos sustentados em PT-PT.
- Não interpretar a ausência de rótulo regional como certificação de PT-PT.
  A presença num vocabulário ortográfico também não prova preferência de uso.
- Nas novas sugestões semânticas, exigir evidência positiva de uso em Portugal
  no contexto proposto antes da aprovação regional. Conferir uma relação de
  sinonímia não equivale a concluir esta revisão de variante.
- Não apresentar automaticamente os restantes membros de um synset. A revisão
  de um par não se estende às outras palavras, grafias ou sentidos do grupo.
- Manter os originais e as variantes na camada de origem. Uma futura seleção
  de apresentação pode deixar variantes brasileiras fora das sugestões
  habituais, sem apagar informação. Consultas diretas e pedidos explícitos
  sobre o Brasil devem permitir explicar a variante e distingui-la do uso em
  Portugal, quando houver evidência suficiente.
- Não substituir palavras ou expressões em massa para fazer uma definição
  parecer portuguesa. Uma alternativa editorial precisa de revisão de sentido,
  concordância e registo; o original continua preservado.

Estados úteis para a revisão: uso PT-PT sustentado; uso partilhado sustentado
em Portugal; uso brasileiro identificado no contexto; outra variante
identificada; por esclarecer. Estes estados são uma proposta de organização,
não campos já implementados nem uma classificação automática do corpus.

## Inspeção dirigida ao estado atual

Foram consultadas algumas entradas, não realizada uma auditoria regional completa.

| Caso | Observação local | Consequência para a revisão |
| --- | --- | --- |
| `legal` | `data/l.json` mistura termos de apreciação com o sentido relativo à lei na primeira aceção. Outra aceção conserva a indicação textual `(Brazil, popular)`, mas o campo regional é `unmarked`. | Prioridade alta: mistura de sentidos e marca regional não refletida na estrutura. Uma simples ordenação de aceções não separa o texto já misturado. |
| `apelido` | `data/a.json` reúne nome de família, alcunha e cognome numa única aceção não marcada. | Rever a separação e a prioridade dos sentidos, sem assumir que todo o uso de «alcunha» nesta entrada é exclusivamente brasileiro. |
| `propina` | `data/p.json` já distingue aceções PT e uma aceção BR para suborno. | Conservar a distinção; não uniformizar os sentidos nem remover a entrada inteira. |
| Grupo de `autocarro` no Onto.PT | A inspeção anterior encontrou grafias de várias regiões e ruído no mesmo grupo. | Não aproveitar o grupo completo como lista de sinónimos PT-PT. |
| Grupo de `feliz` no Onto.PT | A inspeção anterior encontrou, entre outros membros, a grafia `boêmio`. | A retenção contextual de «feliz» / «contente» não aprova essa grafia nem os outros membros do grupo. |

O código em `app.js`, nas funções `senseList` e `displaySenses`, ordena e mostra
aceções já exportadas. Essa heurística não certifica as aceções não marcadas e
não consegue desfazer, por si, a mistura interna da primeira aceção de `legal`.
Não foi aplicado um novo filtro nesta etapa.

## Referências pontuais conferidas

Anotações factuais mínimas; não foram importadas definições nem bases externas.

- [Priberam: legal](https://dicionario.priberam.org/legal), aceções 1–2 e 3–5:
  distingue o domínio jurídico dos usos informais identificados como brasileiros.
- [Priberam: apelido](https://dicionario.priberam.org/apelido), aceção 1:
  identifica o sentido de nome de família como uso de Portugal; também apresenta
  a aceção de alcunha sem a mesma marca. Não concluir exclusividade brasileira
  para esta última com base nesta consulta.
- [Priberam: propina](https://dicionario.priberam.org/propina), aceções 2–3 e 5:
  separa pagamentos escolares do uso informal brasileiro associado a suborno.
- [Priberam: boêmio](https://dicionario.priberam.org/bo%C3%AAmio), notas de grafia:
  distingue `boémio` em Portugal de `boêmio` no Brasil.
- [Priberam: contente](https://dicionario.priberam.org/contente) e
  [veloz](https://dicionario.priberam.org/veloz): sustentam os pares contextuais
  retidos. A consulta desses verbetes, sem uma revisão regional própria, não
  deve ser transformada numa certificação completa de variante ou preferência.

## Efeito nos trabalhos em preparação

Os seis pares retidos continuam candidatos com revisão de contexto, sujeitos
também à revisão regional. Não passam a «brasileiros» por esta ressalva e não
recebem aprovação automática de PT-PT por ausência de rótulo BR.

Antes de integrar os recursos, priorizar uma amostra de colisões de sentido e
marcas regionais: começar por `legal`, `apelido` e `propina`, acrescentando
outros casos com evidência explícita. Avaliar depois a apresentação preferencial
PT-PT e o acesso separado às variantes, com testes que preservem os originais.
As condições de redistribuição de novas fontes continuam a aplicar-se.

`data/`, o demonstrador, os pilotos JSON e o funcionamento da aplicação ficam
intactos. A revisão editorial por fontes continua distinta da certificação
lexicográfica profissional; não se afirma que o dicionário já esteja livre de
brasileirismos ou de sentidos regionais mal identificados.
