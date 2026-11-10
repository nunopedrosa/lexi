# Decisões editoriais propostas

Estado: **proposta para avaliação pelo utilizador**. Nenhuma proposta está aprovada ou aplicada à Lexi. O início desta preparação não altera os estados de revisão dos pilotos de origem.

A preferência por evitar nuances brasileiras nas respostas habituais está
registada na [revisão regional PT-PT](ptpt-regional-review.md). A boa receção
destas propostas não dispensa a revisão da variante por aceção e contexto.

## Critérios propostos

1. **Objetivo linguístico:** quando a Lexi responder sobre sílabas, distinguir a divisão baseada na pronúncia documentada da translineação. A translineação atual continua identificada como experimental.
2. **Âmbito da evidência:** uma separação gráfica exibida num dicionário e uma análise por soletração não se tornam automaticamente uma referência fonológica. Nesta amostra, só dez casos têm proposta de uso no perfil fonológico; doze análises únicas ficam no seu perfil gráfico/de soletração.
3. **Variantes:** conservar condições de pronúncia, ritmo, região ou modelo de análise. Não forçar uma contagem universal nem selecionar uma variante sem dizer qual é o critério.
4. **Lacunas:** manter o composto pendente; não expandir abreviaturas automaticamente para contar sílabas.
5. **Relações semânticas:** usar apenas o par, a classe gramatical e o contexto revistos. Pedir contexto quando faltar. Conservar a direção de «tipo de» e distinguir esta relação de sinonímia.
6. **Falta de resposta:** indisponibilidade de uma relação revista não significa que a relação linguística seja falsa. Não preencher lacunas por transitividade ou adivinhação.
7. **Conversa e proveniência:** manter a linguagem natural em PT-PT e os avisos de incerteza necessários. Fontes, licenças e identificadores ficam fora das respostas conversacionais normais.
8. **Publicação:** avaliar as propostas antes de qualquer alteração de dados, interface, cache ou versão. Não há nova release nesta etapa.

## Proposta por caso silábico

Resumo: **22 análises únicas para comparação no respetivo perfil, quatro casos com variantes, um caso pendente e uma abreviatura fora de âmbito**. As 22 análises não constituem uma aprovação conjunta para um dicionário fonológico.

| Caso | Palavra | Análise(s) documentada(s) | Perfil preservado | Proposta | Referência fonológica neste ensaio? |
| --- | --- | --- | --- | --- | --- |
| syl-01 | saúde | sa·ú·de | separação gráfica no dicionário | aceitar para comparação no perfil de origem | não |
| syl-02 | saída | sa·í·da | separação gráfica no dicionário | aceitar para comparação no perfil de origem | não |
| syl-03 | reunião | re·u·ni·ão | separação gráfica no dicionário | aceitar para comparação no perfil de origem | não |
| syl-04 | feudal | feu·dal | separação gráfica no dicionário | aceitar para comparação no perfil de origem | não |
| syl-05 | casa | ca·sa | separação gráfica no dicionário | aceitar para comparação no perfil de origem | não |
| syl-06 | cadeira | ca·dei·ra | separação gráfica no dicionário | aceitar para comparação no perfil de origem | não |
| syl-07 | país | pa·ís | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-08 | pais | pais | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-09 | pai | pai | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-10 | degraus | de·graus | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-11 | maior | mai·or | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-12 | lua | lu·a | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-13 | quando | quan·do | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-14 | guarda | guar·da | divisão silábica expressa | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-15 | rainha | ra·i·nha | soletração na referência | aceitar para comparação no perfil de origem | não |
| syl-16 | planícies | pla·ní·ci·es | soletração na referência | aceitar para comparação no perfil de origem | não |
| syl-17 | dormiam | dor·mi·am | soletração na referência | aceitar para comparação no perfil de origem | não |
| syl-18 | pneu | pneu | soletração na referência | aceitar para comparação no perfil de origem | não |
| syl-19 | psicologia | psi·co·lo·gi·a | soletração na referência | aceitar para comparação no perfil de origem | não |
| syl-20 | abstrato | abs·tra·to | soletração na referência | aceitar para comparação no perfil de origem | não |
| syl-21 | carro | ca·rro | consciência fonológica | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-22 | massa | ma·ssa | consciência fonológica | aceitar para comparação no perfil de origem | sim, sujeito a aprovação |
| syl-23 | água | á·gua / á·gu·a | modelo/pronúncia variável | conservar com ressalva | não |
| syl-24 | aquário | a·quá·rio / a·qu·á·ri·o | modelo/pronúncia variável | conservar com ressalva | não |
| syl-25 | habitual | ha·bi·tu·al / ha·bi·tual | modelo/pronúncia variável | conservar com ressalva | não |
| syl-26 | antiguidade | an·ti·gui·da·de / an·ti·gu·i·da·de | modelo/pronúncia variável | conservar com ressalva | não |
| syl-27 | guarda-chuva | — | composto por avaliar | deixar pendente | não |
| syl-28 | profª | — | controlo de âmbito | excluir das contagens automáticas | não |

As referências por palavra e as condições das variantes permanecem na [amostra documentada](README.md). As [propostas JSON](editorial-decisions.json) guardam os hashes das fontes locais usadas e os estados `user_approved: false` e `production_approved: false`.

**Pontos a decidir na avaliação:**

- Se o objetivo pedagógico será a representação fonológica documentada, mantendo um acesso separado à translineação.
- Se as dez referências fonológicas podem avançar para uma amostra maior e que revisão adicional exigir aos restantes perfis.
- Como apresentar as variantes de `água`, `aquário`, `habitual` e `antiguidade` sem misturar critérios diferentes. A proposta atual conserva as alternativas e as condições; não elege uma forma principal.
- Se o composto continua pendente e a abreviatura permanece excluída das contagens.

## Exemplos de resposta semântica

O [demonstrador local](demo/index.html) permite percorrer dez cenários fixos, sem pesquisa livre nem processamento do corpus. Mostra os seis pares retidos para avaliação, os contextos excluídos e os quatro casos rejeitados/adiados. Está em PT-PT e é material de revisão, não uma versão da interface bilingue da PWA.

As falas que se seguem são exemplos editoriais originais, não citações de dicionários. Os contextos escolhidos pelo utilizador são estímulos de teste. As relações e limites remetem para os IDs do [piloto semântico](semantic-pilot.json); nenhuma definição nova é produzida.

### Feliz: emoção e outros sentidos

**Pergunta:** Diz-me um sinónimo de feliz.

**Resposta inicial proposta:** Em que sentido usas «feliz»? Podes indicar uma frase?

| Contexto indicado | Resposta proposta |
| --- | --- |
| Ela ficou feliz com a notícia. | Nesse contexto, «contente» pode ser um sinónimo de «feliz». |
| Quero dizer que ela teve muita sorte. | Ainda não tenho um sinónimo revisto para esse sentido de «feliz». |

**Limite de revisão:** Retido apenas para o estado emocional. A resposta sobre sorte fica pendente.

Referências: [priberam-feliz](https://dicionario.priberam.org/feliz), [priberam-contente](https://dicionario.priberam.org/contente). Caso: `sem-01`.

### Veloz: velocidade de deslocação

**Pergunta:** Diz-me um sinónimo de veloz.

**Resposta inicial proposta:** Usas «veloz» para falar de algo que se desloca depressa?

| Contexto indicado | Resposta proposta |
| --- | --- |
| Estou a falar de um atleta veloz. | Para descrever a velocidade de deslocação, podes usar «rápido» como sinónimo de «veloz». |
| Estou a falar da conclusão veloz de uma tarefa. | Esse uso ainda não tem um sinónimo revisto nesta seleção. |

**Limite de revisão:** Só é ensaiada a relação adjetival no domínio da deslocação.

Referências: [priberam-veloz](https://dicionario.priberam.org/veloz). Caso: `sem-02`.

### Quente: temperatura e outros sentidos

**Pergunta:** Qual é o contrário de quente?

**Resposta inicial proposta:** Falas de temperatura ou de outro sentido de «quente»?

| Contexto indicado | Resposta proposta |
| --- | --- |
| Estou a falar da temperatura de uma bebida. | Ao falar da temperatura de uma bebida, «frio» é um contrário de «quente». |
| Quero dizer comida picante. | Ainda não tenho um contrário revisto para esse uso de «quente». |

**Limite de revisão:** Oposição escalar de temperatura. Não implica que tudo o que não é quente seja frio.

Referências: [priberam-frio](https://dicionario.priberam.org/frio). Caso: `sem-03`.

### Abrir: ação física

**Pergunta:** Qual é o contrário de abrir?

**Resposta inicial proposta:** O que estás a abrir?

| Contexto indicado | Resposta proposta |
| --- | --- |
| Uma janela. | Para uma janela, a ação contrária a «abrir» é «fechar». |
| Um buraco. | Ainda não tenho um contrário revisto para esse uso de «abrir». |

**Limite de revisão:** A resposta fica limitada ao contexto físico conferido. Não se aprovam os restantes usos do synset.

Referências: [priberam-abrir](https://dicionario.priberam.org/abrir). Caso: `sem-04`.

### Rosa: flor ou cor

**Pergunta:** Que relação há entre rosa e flor?

**Resposta inicial proposta:** Usas «rosa» para falar da flor ou de outro sentido?

| Contexto indicado | Resposta proposta |
| --- | --- |
| Estou a falar da flor da roseira. | Nesse sentido, uma rosa é um tipo de flor. |
| Estou a falar da cor de uma camisola. | A relação «tipo de flor» não se aplica a «rosa» enquanto cor. |

**Limite de revisão:** Conserva a direção rosa → flor. Não afirma que toda a flor seja uma rosa.

Referências: [priberam-rosa](https://dicionario.priberam.org/rosa). Caso: `sem-05`.

### Banco: objeto ou domínio financeiro

**Pergunta:** Que relação há entre banco e assento?

**Resposta inicial proposta:** Falas de um banco para sentar ou de outro sentido?

| Contexto indicado | Resposta proposta |
| --- | --- |
| Um banco de jardim. | No sentido de objeto para sentar, um banco é um tipo de assento. |
| Um banco financeiro. | A relação com «assento» não se aplica ao banco financeiro. |

**Limite de revisão:** Retida a hiponímia no contexto físico. Não se converte em sinonímia irrestrita.

Referências: [priberam-banco](https://dicionario.priberam.org/banco). Caso: `sem-06`.

### Equivalência rejeitada: autocarro / possível

**Pergunta:** «Possível» é sinónimo de «autocarro»?

**Resposta inicial proposta:** Não tenho essa equivalência confirmada para o sentido de transporte.

**Limite de revisão:** Rejeitado no piloto apesar da pertença ao mesmo grupo de origem. Não apagar nem corrigir o grupo original.

Referências: [priberam-autocarro](https://dicionario.priberam.org/autocarro), [priberam-possível](https://dicionario.priberam.org/poss%C3%ADvel). Caso: `sem-07`.

### Sinónimos gerais: banco / assento

**Pergunta:** «Banco» e «assento» são sempre sinónimos?

**Resposta inicial proposta:** Ainda não tenho uma equivalência geral revista entre «banco» e «assento».

**Limite de revisão:** A fonte contém hiponímia. Não promover esse arco a sinonímia geral; comparar com o exemplo do banco de jardim.

Referências: [priberam-banco](https://dicionario.priberam.org/banco). Caso: `sem-08`.

### Relação adiada: cão / animal

**Pergunta:** O cão é um tipo de animal?

**Resposta inicial proposta:** Esta relação ainda não está disponível nas respostas revistas.

**Limite de revisão:** Indisponibilidade da seleção, não dúvida sobre a classificação zoológica. Não foi extraído um arco direto para este piloto.

Referências: [priberam-cão](https://dicionario.priberam.org/c%C3%A3o), [priberam-animal](https://dicionario.priberam.org/animal). Caso: `sem-09`.

### Sentido por rever: roda / bicicleta

**Pergunta:** Posso usar «roda» como sinónimo de «bicicleta»?

**Resposta inicial proposta:** Ainda não tenho uma equivalência revista entre essas palavras para esse uso.

**Limite de revisão:** Adiado. Esclarecer sentido, metonímia e eventual uso regional ou histórico; não concluir ausência absoluta de tal uso.

Referências: [priberam-roda](https://dicionario.priberam.org/roda), [priberam-bicicleta](https://dicionario.priberam.org/bicicleta). Caso: `sem-10`.

## Limites e verificação

O demonstrador não interpreta texto livre, não procura aceções e não simula capacidade para além dos cenários fixos. Não guarda escolhas, não usa serviços externos, não carrega `data/` e não regista service worker. As ligações às fontes só navegam quando acionadas. Pode abrir-se `demo/index.html` diretamente no browser.

```sh
node test-editorial-demo.cjs
```

O teste verifica respostas em contextos autorizados, indisponibilidade sem contexto, usos excluídos, preservação do tipo de relação e propostas sem aprovação. A conferência das fontes já efetuada continua a ser documental, não certificação lexicográfica profissional. A compatibilidade real com Safari 12/iPhone 6 permanece por verificar.
