# Lexi — protótipo PWA

Dicionário conversacional PT-PT, sem backend e sem dependências JavaScript. Usa dados de KOReader/Wiktionary, com camada editorial limitada. Licenças em `LICENSE` e `ATTRIBUTION`.

## Executar

```sh
cd lexi-pwa
python3 -m http.server 8009
```

Abrir `http://localhost:8009/`. O service worker funciona em localhost ou HTTPS. Em Definições, usar **Preparar dicionário para uso offline** para colocar todos os blocos na cache do service worker. A permanência da cache depende do browser e do espaço disponível.

## Implementado

- Definições por palavra, com preferência para 14 entradas editoriais PT-PT.
- Listagens por letra inicial, final, número de letras e combinações.
- Continuação «mais» e manutenção parcial do contexto.
- Link opcional para Priberam.
- Interface PT-PT; sem API, sem servidor PHP.

## Limitações conhecidas

- A segmentação de sentidos e identificação regional é heurística; as definições não foram todas revistas.
- As 25 preferências regionais são associações de sentido, não equivalências universais.
- Divisão silábica, sinónimos, antónimos e categorias semânticas ainda não estão validados.
- A lista de formas flexionadas `.syn` ainda não está incorporada.
- A pesquisa por palavra é feita por lema e não corrige automaticamente flexões.
- Para produção: testar Safari iOS antigo, adicionar ícones PNG, validar acessibilidade e rever a cache offline.

## PT-PT filtering — v2

A apresentação de definições agora privilegia sentidos editoriais PT-PT, depois sentidos não marcados como Brasil sem alertas lexicais, depois sentidos com alertas, e finalmente sentidos exclusivamente marcados como Brasil. A camada de alertas assinala um conjunto limitado de expressões brasileiras inequívocas em certos contextos; **não traduz nem corrige** definições automaticamente. As entradas não revistas são identificadas como tal. A ausência de alerta **não garante** português europeu. A seleção considera apenas os sentidos presentes nos blocos exportados (até 4 ou 5 por entrada).

O relatório `ptpt_filter_audit.json`, distribuído separadamente, contém contagens e exemplos dos indicadores detetados. O filtro deve ser expandido apenas com revisão contextual, para não trocar significados de palavras polissémicas.


## PT-PT v3: correções conservadoras

Algumas definições incluem propostas automáticas de adaptação lexical ao português europeu, apenas em contextos específicos. O texto original permanece nos ficheiros JSON. As propostas **não foram revistas manualmente** e são assinaladas na interface. As aceções marcadas BR não são reescritas, para manter a explicação da variante regional. Relatório: `ptpt-v3-audit.json`.


## PT-PT v5

Added/revised 89 editorial PT-PT headword definitions. Original dictionary senses are preserved. These editorial entries are not independent lexicographic certification. See `ptpt-v5-audit.json`.

## PT-PT v6 — aceções e variantes

- A interface apresenta as aceções editoriais primeiro, seguidas de aceções não marcadas, suspeitas e marcadas Brasil.
- «Outros significados» percorre todas as aceções **incluídas na exportação**, sem apagar as variantes brasileiras.
- «Texto original» mostra as aceções não editoriais, para comparação.
- Rótulos distinguem redação editorial, uso de Portugal e uso do Brasil; ausência de rótulo não certifica PT-PT.
- Não foram feitas novas conversões automáticas nem alegada revisão humana de entradas.
- **Limite:** o exportador anterior conservou apenas parte das aceções originais por lema. Para cobertura integral é necessário reconstruir os blocos JSON a partir do StarDict.


## v7: source reconstruction and PT-PT adaptation

Rebuilt 133646 source senses for 81068 headwords from the uploaded StarDict-derived SQLite extraction. Applied 339 targeted automatic substitutions. Each changed sense preserves the exact original in the data and audit. These substitutions are not independently verified. See `ptpt-v7-audit.json`.


## v8 — regional awareness

`data/regional.json` contém equivalências editoriais **dependentes do sentido**, não traduções globais. A aplicação aceita perguntas como «Como se diz ônibus em Portugal?» e «Como se diz autocarro no Brasil?». Mostra equivalências apenas quando há uma entrada curada, mantém os sentidos originais e não altera automaticamente as definições. O conjunto é deliberadamente pequeno; não cobre todas as variantes.

## Publicação DreamHost

Colocar o conteúdo desta pasta na raiz do document root de `lexi.basecentral.link` (não a pasta envolvente). Configurar HTTPS no painel DreamHost. É uma aplicação estática: não requer PHP nem npm no servidor.


## v2: formas flexionadas

O índice original `pt-pt.syn` foi associado às 81 068 entradas na ordem de `pt-pt.idx`, sem inferir conjugações. Os ficheiros `data/forms/*.json` permitem reconhecer formas como plurais e verbos conjugados. Se uma forma tiver vários lemas, Lexi pede que se escolha a entrada pretendida. O índice é descarregado por letra, conforme necessário. O botão de transferência offline carrega as definições e as formas flexionadas.


## v3 — Pesquisa experimental por sílabas

Foram pré-calculadas sugestões de divisão com os padrões de translineação `pt_PT` do Pyphen. **Translineação não equivale a divisão silábica**; por isso, resultados com número de sílabas são explicitamente assinalados como experimentais e não devem ser tratados como factos linguísticos verificados. A pesquisa aceita combinações de letra inicial, final, número de letras e número aproximado de sílabas. Os dados estão em `data/syllables/`. O projeto Pyphen e os padrões incluídos têm licenças próprias; confirmar a licença dos padrões antes de redistribuir publicamente.

## v4 — motor de conversação

O módulo `conversation.js` reconhece intenções de forma determinística e sem dependências: saudações, ajuda, definições, equivalências regionais, pesquisas combinadas, continuação de resultados, outros significados, texto original e reinício de contexto. Mantém filtros entre perguntas como «Agora com quatro sílabas».

Teste rápido do interpretador: `node test-conversation.cjs`. O teste verifica o reconhecimento de intenções; não substitui testes completos de interface ou auditoria linguística. As limitações de definições e divisão silábica da v3 mantêm-se.

## v5 — apresentação das definições

A advertência sobre adaptações automáticas deixou de aparecer em cada resposta. A informação encontra-se nas Definições, e o comando «texto original» continua disponível. O cache do service worker foi atualizado para `lexi-v5`.


## Correção v6
- Pesquisa por inicial aceita «começadas por X» (e «pela letra X»), sem confundir «por» com a letra P.
- Cache do Service Worker atualizada para lexi-v6.


## Lexi v7
- Os resultados de pesquisas por palavras são botões clicáveis que abrem a definição na conversa.
- As pesquisas por palavras omitem entradas de uma só letra, entradas com pontuação, siglas em maiúsculas e abreviaturas identificadas na classe gramatical. As consultas diretas continuam a aceitar essas entradas.
- O filtro é conservador: entradas com abreviaturas não assinaladas na fonte poderão ainda aparecer.


## v8 — Explorar palavras na conversa

As palavras nas definições são botões que abrem a respetiva entrada sem reescrever a pergunta. O texto da definição não é alterado. O convite «Podes pedir «mais»» contém agora um botão «mais» para continuar a pesquisa.
