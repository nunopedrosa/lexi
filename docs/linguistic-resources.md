# Recursos linguísticos: avaliação e integração

Auditoria de 8 de novembro de 2026. Esta etapa prepara a integração; não altera
definições, formas, sílabas, interface, cache ou publicação. Os arquivos externos
foram guardados apenas em `/private/tmp/lexi-linguistic-review/` e não pertencem
ao inventário público. Os relatórios abaixo são inspeções, não certificação
lexicográfica. Não foram enviados dados para serviços de processamento externos.

## Licenças e versões verificadas

| Recurso | Evidência | Decisão nesta etapa |
| --- | --- | --- |
| LX-Syllabifier v1.1, arquivo oficial | `LICENSE` e cabeçalho de `silabificador.py`: licença de três cláusulas do tipo BSD-3-Clause, copyright 2015 dos autores NLX/Universidade de Lisboa. A página anuncia MIT e o texto separado tem copyright 2019. | Avaliar a distribuição local segundo os termos nela incluídos; conservar os avisos. Não atribuir automaticamente a licença MIT de 2019 ao arquivo de 2015. |
| Serviço LX no PORTULAN | Condições separadas com restrições de redistribuição, uso comercial e composição. | Não utilizar a API na Lexi nem nesta avaliação. |
| Onto.PT v0.6 | Página oficial e secção 5 do `LEIAME.txt` do arquivo: CC BY 3.0 Unported, Universidade de Coimbra. | Inspeção local permitida com atribuição. Qualquer extração futura deve identificar a versão, as transformações e a fonte; a licença não valida a qualidade linguística. |
| VOP / VOC | Consulta pública; VOP descreve ortografia, flexões e restrições geográficas. Não foi localizada autorização explícita para redistribuir a base nas páginas consultadas. | Sem transferência em massa, scraping, cópia de entradas ou incorporação. Esclarecer os termos de extração e redistribuição, incluindo resultados derivados, antes de preparar dados offline. |
| Pyphen / padrões `pt_PT` atuais | O README atual do dicionário de translineação LibreOffice declara GNU GPL. O repositório Lexi não conserva a versão/hash dos padrões que geraram os shards. | A proveniência/licença exata do artefacto original continua pendente. Não inventar uma versão nem estender a atribuição CC BY-SA do Wiktionary aos padrões. |

Fontes oficiais consultadas:

- [Documentação LX](https://portulanclarin.net/workbench/lx-syllabifier/),
  [texto MIT separado](https://portulanclarin.net/static/docs/lxsyllabifier/LICENSE.html),
  [arquivo avaliado](https://portulanclarin.net/static/downloads/lxsyllabifier/LX-Syllabifier.tar.gz)
  e [licença do serviço](https://portulanclarin.net/workbench/license/).
- [Onto.PT: distribuição e licença](https://ontopt.dei.uc.pt/index.php?sec=downloads),
  [arquivo v0.6 N3](https://ontopt.dei.uc.pt/recursos/OntoPTv0.6_n3.zip) e
  [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- [VOP: âmbito](https://www.portaldalinguaportuguesa.org/index.php?action=vop&page=agora)
  e [VOC: versões nacionais](https://voc.cplp.org/).
- [README dos padrões pt_PT no LibreOffice](https://raw.githubusercontent.com/LibreOffice/dictionaries/master/pt_PT/README_hyph_pt_PT.txt).

Hashes SHA-256 dos arquivos efetivamente avaliados:

```text
LX-Syllabifier.tar.gz  29fe1e5f4434d44770c016bf184561433a8dc518e48f3553f2c8ccda07d94ba9
OntoPTv0.6_n3.zip      f89e7486b883c1a95166bb24874b18a581efc1c0187e88619659f4ff6b61f5a3
```

O código LX foi inspecionado antes de execução. O adaptador só aceita esse hash,
extrai dois ficheiros de nomes fixos numa pasta temporária e chama as funções
de exceções e regras do programa original. Evita o log de texto escrito pelo CLI
original. Não corrige resultados do LX. Novos arquivos exigem nova inspeção;
os scripts não efetuam transferências.

## Resultado da avaliação silábica

Relatório: [lx-v1.1-comparison.json](linguistic-results/lx-v1.1-comparison.json).

O âmbito é de 67 538 lemas compostos apenas por letras; 13 530 entradas com
espaços, hífen, números ou outros caracteres ficam fora desta comparação.
Maiúsculas e normalização Unicode NFC são ignoradas ao comparar as divisões,
mas os lemas são associados por chave NFC exata, sem retirar acentos.

| Medida | Total |
| --- | ---: |
| Lemas no âmbito | 67 538 |
| Com sugestão atual de translineação | 67 527 |
| Resultados LX que não reconstituem a palavra | 340 |
| Comparações estruturalmente válidas | 67 190 |
| Divisões coincidentes | 48 927 |
| Divisões divergentes | 18 263 |
| Divergências também no número de segmentos | 18 199 |
| Resultados LX estruturalmente válidos sem sugestão atual | 8 |

São comparações entre métodos, não medidas de precisão. A maioria das 340
falhas de reconstituição ocorre em formas inteiramente maiúsculas (289);
há também abreviaturas e grafias estrangeiras. Por exemplo, o caminho normal
do CLI elimina a primeira letra de algumas formas sem vogais reconhecidas.
O adaptador conserva esse comportamento para tornar o problema observável.

| Palavra | Sugestão atual | LX v1.1 |
| --- | --- | --- |
| saúde | saú·de | sa·ú·de |
| saída | saí·da | sa·í·da |
| país | país | pa·ís |
| reunião | reu·nião | re·u·ni·ão |
| água | água | á·gua |
| feudal | feu·dal | feu·dal |

**Decisão:** manter a camada atual explicitamente experimental. O LX é um
candidato a substituir a geração de sugestões, sujeito a filtragem estrutural
e avaliação independente; concordância com o LX não constitui validação humana.
Não transformar automaticamente as 18 263 divergências em correções.

Antes de uma substituição, construir uma referência PT-PT com fontes e estado
de revisão por caso, cobrindo hiatos/ditongos, dígrafos, grupos consonânticos,
acentos, variantes de pronúncia, flexões e compostos. Amostrar também as
concordâncias e palavras sem cobertura para evitar avaliar apenas casos
favoráveis. Não usar as exceções do LX como único conjunto de referência.
Relatar fronteiras e contagens separadamente, aceitar variantes justificadas
e não forçar um resultado quando houver dúvida.

A etapa seguinte está preparada em [Amostra e piloto para avaliação](linguistic-pilots/README.md):
28 casos silábicos com referências, condições e comparação dos métodos; dez
casos semânticos com seis pares retidos e quatro rejeitados/adiados. A conferência
documental pelo Codex não equivale a certificação linguística; a revisão pelo
utilizador continua pendente. Estes ficheiros não alteram o corpus nem ativam
funcionalidades na aplicação.

## Onto.PT: estrutura e obstáculos observados

Relatório: [ontopt-v0.6-inspection.json](linguistic-results/ontopt-v0.6-inspection.json).

A leitura N3 com RDFLib encontrou 871 849 triplos, 117 450 synsets e 156 623
formas lexicais. 46 029 formas coincidem exatamente, incluindo maiúsculas e
acentos, com lemas atuais da Lexi. Isso mede sobreposição gráfica; não associa
aceções nem certifica PT-PT. RDFLib foi usado apenas como ferramenta local de
auditoria, não é uma dependência da aplicação.

- As formas estão em `OntoPT:formaLexical`; a sinonímia resulta da pertença ao
  mesmo synset, não de uma lista global de equivalências por palavra.
- Os synsets distinguem nome, verbo, adjetivo e advérbio.
- A antonímia tem predicados por classe: `antonimoNDe`, `antonimoVDe`,
  `antonimoAdjDe`, `antonimoAdvDe`. O arquivo contém 7 724 arcos desses tipos;
  não são necessariamente 7 724 pares distintos.
- As relações direcionais, como `hiperonimoDe` / `hiponimoDe` e `parteDe` /
  `temParte`, devem conservar predicado e direção. A inspeção não infere novos
  arcos por transitividade, simetria ou inversão.
- «casa» pertence a 12 synsets, «bom» a 13 e «feliz» a 7. Unir as formas de todos
  esses grupos perderia a distinção de sentidos.
- O synset de «autocarro» inclui variantes de várias regiões e também
  «possível». É um exemplo concreto de material que exige revisão; não deve
  originar uma resposta automática com todos os membros como sinónimos PT-PT.
- «casa de banho» não aparece como forma lexical exata, embora a expressão
  ocorra em texto de definições. Ocorrência no texto não autoriza criar uma relação.

**Decisão:** não ligar diretamente os grupos brutos à conversa. O primeiro
piloto deve conter um pequeno conjunto de relações revistas, organizadas por
synset/classe e com contexto suficiente. Os IDs Onto.PT ficam separados dos
IDs locais; uma coincidência de grafia não alinha uma aceção Wiktionary.

Contrato proposto para um futuro extrator:

```json
{
  "schema": 1,
  "source": {"id": "ontopt", "version": "0.6", "license": "CC-BY-3.0", "artifact_sha256": "..."},
  "synsets": [{"source_id": "URI original", "pos": "classe original", "forms": ["forma original"]}],
  "relations": [{"from": "URI original", "predicate": "URI original", "to": "URI original"}],
  "reviews": [{"source_id": "URI original", "status": "unreviewed", "lexi_sense_ids": []}]
}
```

É um contrato proposto, não dados de produção. A extração conserva os membros
originais; a seleção revista para apresentação deve ser uma camada separada.
Não descartar variantes nem reescrever definições existentes. Não inventar
rótulos de sentido para conseguir apresentar uma lista. Ausência de ligação
ou revisão deve produzir uma resposta honesta de indisponibilidade.

## VOP / VOC e próxima ordem de trabalho

VOP/VOC podem apoiar a verificação de grafias, lemas, flexões, rótulos nacionais
e, conforme a informação da entrada, segmentação. Não fornecem por si uma
validação semântica; presença no vocabulário não significa uso preferencial
em Portugal. Confirmar se uma separação exibida é translineação ou divisão
silábica antes de a usar como referência.

1. Recuperar a versão e licença dos padrões que geraram os dados atuais; se
   não for possível, documentar a perda de proveniência em vez de a adivinhar.
2. Preparar a amostra silábica revista e registar decisões nos casos ambíguos.
3. Preparar o piloto semântico Onto.PT com atribuição e revisão por sentido.
4. Esclarecer com os titulares do VOP/VOC a extração, armazenamento offline,
   redistribuição pública e uso de resultados derivados. Nenhum contacto foi
   enviado nesta etapa.
5. Só depois de revisão própria, preparar novos shards e uma release. Essa
   etapa deve atualizar auditorias, contagens, versão, preparação offline e
   inventário de publicação em conjunto, preservando todos os originais.

Na aplicação, apenas JSON local e consultas limitadas por shard; nada de
Python, RDFLib, RDF/N3, APIs ou novos serviços no browser. A avaliação do
tamanho/memória e os testes de atualização/offline precedem a integração.
Manter Safari 12/iPhone 6 como alvo; a verificação em dispositivo permanece
pendente. Licenças e proveniência ficam em Definições/documentação; avisos
breves de incerteza permanecem junto dos resultados experimentais.

## Reproduzir localmente

Após obter e verificar os arquivos oficiais, sem usar os serviços online:

```sh
python3 scripts/audit-syllables.py --lx-archive /caminho/LX-Syllabifier.tar.gz --limit 12
python3 scripts/inspect-ontopt.py /caminho/OntoPTv0.6_n3.zip
python3 test-syllables-audit.py
```

O primeiro script usa apenas a biblioteca padrão Python 3. O segundo precisa
da biblioteca de desenvolvimento opcional RDFLib (a versão usada consta do
relatório), lê o grafo na memória do computador de desenvolvimento e escreve
apenas JSON no stdout. Nenhum deles modifica `data/`, a cache ou preferências.
Os relatórios não incluem os arquivos externos completos.

Para outro silabificador, `audit-syllables.py /caminho/candidato.json` aceita:

```json
{
  "schema": 1,
  "source": {"id": "identificador", "version": "versão", "license": "licença verificada", "artifact_sha256": "64 dígitos hexadecimais minúsculos"},
  "rows": [["palavra", ["segmento", "segmento"]]]
}
```

O exemplo descreve a estrutura, não uma divisão linguística. A ferramenta
valida a estrutura e a reconstituição das palavras, recusa chaves duplicadas,
reporta falta/excesso de cobertura e limita os exemplos. Os metadados fornecidos
por quem chama a ferramenta não são uma verificação automática da licença.

Atribuição dos resultados Onto.PT: Universidade de Coimbra, Hugo Gonçalo
Oliveira e Paulo Gomes, CC BY 3.0; transformações nesta etapa: contagens,
interseção gráfica, IDs de exemplos e pequena amostra de membros de um synset,
sem inferência. Referência indicada pela distribuição: *Integrating
lexical-semantic knowledge to build a public lexical ontology for Portuguese*,
NLDB 2012. Para o LX: Francisco Costa, João Rodrigues, João Silva e António
Branco; licença do arquivo conservada em
[LX-Syllabifier-LICENSE.txt](linguistic-results/LX-Syllabifier-LICENSE.txt).
Os padrões/definições de origem mantêm as suas condições próprias.
