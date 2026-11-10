# Ensaio regional: legal, apelido e propina

**Estado posterior à avaliação:** o utilizador aprovou a integração das três
respostas iniciais na Lexi, sem publicação. Foram integradas na camada
`editorial.js` da versão local `2026.11.08.3`, com proveniência em
[editorial-audit.json](../../editorial-audit.json). Os cenários, o JSON e a
comparação abaixo conservam a proposta histórica; os restantes ramos não foram
integrados como novo interpretador de contexto. Todas as aceções originais
continuam nos shards e acessíveis na aplicação.

[Abrir os três exemplos interativos](regional-demo/index.html).

Esta etapa transforma a preferência PT-PT em três comportamentos concretos para avaliação. São cenários fixos, não um filtro implementado na Lexi. As falas são propostas editoriais originais, não transcrições de definições completas. Os originais do corpus e todas as aceções continuam intactos. Nenhuma resposta tem aprovação para produção.

## O que muda no ensaio

- A resposta inicial privilegia o contexto português selecionado, com evidência lexical e uso institucional em Portugal.
- Um pedido contextualizado pode obter a explicação de uma variante brasileira, explicitamente identificada.
- A ausência de rótulo regional não transforma um sentido em exclusivamente português ou brasileiro.
- Outros sentidos legítimos continuam preservados. Esta seleção breve não pretende substituir uma definição completa por uma definição abreviada.
- Não se faz pesquisa livre, adaptação automática, substituição de palavras ou reconstrução de aceções. Os nomes e frases de contexto são estímulos de teste.

## legal

**Problema observado:** Mistura de sentidos jurídicos e apreciativos; marca textual brasileira não refletida no campo regional de uma aceção.

**Pergunta de exemplo:** O que significa legal?

**Resposta inicial proposta:** Na aceção jurídica, «legal» diz respeito à lei ou ao que está de acordo com ela.

| Contexto pedido | Resposta proposta |
| --- | --- |
| Estou a falar de uma decisão legal. | Aqui, «legal» descreve uma decisão que está de acordo com a lei. |
| Ouvi no Brasil: «Que filme legal!». | Nesse uso informal do Brasil, «legal» é uma apreciação positiva, próxima de «fixe» ou «giro» em Portugal. |

**Limite:** Uso partilhado, com evidência de uso em Portugal; não é exclusivo de Portugal. O uso informal brasileiro só é explicado com contexto explícito.

**Comparação com o original:**
- Etiqueta `unmarked`: «lícito, bom, excelente, fixe, maravilhoso — de acordo com a lei».
- Etiqueta `unmarked`: «(Brazil, popular) interessante, agradável».

As etiquetas acima são as existentes, não correções propostas. A cópia integral da entrada original, com os seus campos e o hash do shard, fica em [regional-review.json](regional-review.json). Nenhum texto original foi sobrescrito.

**Referências pontuais:**
- [lexicographic_reference](https://dicionario.priberam.org/legal): aceções 1–2: jurídico; 3–5: Brasil, informal.
- [portuguese_institutional_usage](https://justica.gov.pt/Servicos/Pedir-e-consultar-registo-criminal-de-empresas-e-outras-entidades): uso de representante legal.

## apelido

**Problema observado:** Nome de família e alcunha aparecem reunidos no original.

**Pergunta de exemplo:** O que é um apelido?

**Resposta inicial proposta:** Em Portugal, «apelido» designa o nome de família.

| Contexto pedido | Resposta proposta |
| --- | --- |
| Estou a falar do nome de família de uma pessoa. | Nesse contexto, trata-se do apelido familiar. |
| Na frase, é o nome pelo qual os amigos tratam alguém. | Nesse contexto, trata-se de uma alcunha. Esse sentido deve ser distinguido do nome de família. |

**Limite:** Não classificar o sentido de alcunha como exclusivamente brasileiro com base na ausência de rótulo regional.

**Comparação com o original:**
- Etiqueta `unmarked`: «sobrenome, alcunha, cognome — nome pessoal que provém da tradição familiar; nome de família; sobrenome».

As etiquetas acima são as existentes, não correções propostas. A cópia integral da entrada original, com os seus campos e o hash do shard, fica em [regional-review.json](regional-review.json). Nenhum texto original foi sobrescrito.

**Referências pontuais:**
- [lexicographic_reference](https://dicionario.priberam.org/apelido): aceção 1 marcada Portugal; aceção 2 sem a mesma marca.
- [portuguese_institutional_usage](https://irn.justica.gov.pt/Servicos/Cidadao/Nascimento/Composicao-do-nome): composição do nome: nomes próprios e apelidos.

## propina

**Problema observado:** A palavra tem sentidos distintos; o original já conserva etiquetas PT e BR.

**Pergunta de exemplo:** O que é uma propina?

**Resposta inicial proposta:** No ensino superior, «propina» é a taxa devida pela inscrição no curso.

| Contexto pedido | Resposta proposta |
| --- | --- |
| Estou a falar da propina da universidade. | Neste contexto, a propina está ligada à inscrição no curso. |
| Ouvi numa notícia do Brasil: «receber propina». | Nesse contexto brasileiro, «propina» pode referir-se a um suborno. É um sentido diferente da taxa académica. |

**Limite:** Outros sentidos portugueses, incluindo gratificações, não são apagados nem declarados errados. O ensaio não é uma definição exaustiva.

**Comparação com o original:**
- Etiqueta `PT`: «quantia que se paga para se poderem realizar certos atos escolares».
- Etiqueta `PT`: «quantia paga pelos indivíduos admitidos numa agremiação».
- Etiqueta `unmarked`: «joia».
- Etiqueta `unmarked`: «gorjeta».
- Etiqueta `unmarked`: «gratificação».
- Etiqueta `BR`: «suborno».

As etiquetas acima são as existentes, não correções propostas. A cópia integral da entrada original, com os seus campos e o hash do shard, fica em [regional-review.json](regional-review.json). Nenhum texto original foi sobrescrito.

**Referências pontuais:**
- [lexicographic_reference](https://dicionario.priberam.org/propina): aceções 2–3: ensino; aceção 5: Brasil, informal.
- [portuguese_institutional_usage](https://www.iseg.ulisboa.pt/secretaria/informacoes-academicas/licenciaturas/propinas/): taxa de frequência devida pela inscrição; distinção entre inscrição e presença efetiva.

## Critérios de aceitação deste ensaio

| Verificação | Comportamento esperado |
| --- | --- |
| Pergunta simples | Prioridade ao contexto português selecionado, sem misturar sentidos regionais na mesma frase. |
| Contexto brasileiro explícito | Explicar a variante, mantendo a marca regional na resposta. |
| Apelido usado como alcunha | Distinguir os sentidos sem afirmar exclusividade brasileira. |
| Contexto desconhecido | Não escolher automaticamente a primeira aceção nem gerar uma resposta nova. |
| Outros sentidos portugueses | Não apagar nem declarar inválidos os sentidos que este ensaio não apresenta. |
| Preservação | `data/`, o runtime da PWA e os pilotos anteriores mantêm o conteúdo. |

A evidência institucional atesta usos concretos em Portugal; não demonstra exclusividade regional, frequência relativa ou todos os usos de cada palavra. A fonte académica consultada é o ISEG/Universidade de Lisboa. O antigo endereço DGES redirecionou para uma página de migração e não é usado como prova atual do conteúdo. Não foram importados artigos, verbetes ou bases externas; apenas se conservaram referências e anotações factuais.

## Verificação e estado

```sh
node test-regional-demo.cjs
node test-editorial-demo.cjs
```

O demonstrador regional reutiliza a apresentação do ensaio semântico anterior e define o seu próprio exemplo inicial. O ensaio anterior continua a iniciar no caso do banco de jardim. Os ficheiros podem abrir-se diretamente no browser: não há pedidos de dados, gravação de escolhas, service worker ou publicação. O protótipo está em PT-PT; não é uma release da interface bilingue.

Antes de qualquer integração na Lexi, avaliar a redação e a cobertura destes casos, definir o acesso aos restantes sentidos preservados e preparar uma camada editorial própria com proveniência. Não classificar todo o corpus nem ativar um filtro por extensão destes três exemplos.
