# Lexi — protótipo PWA

Dicionário conversacional PT-PT, sem backend e sem dependências JavaScript. Usa dados de KOReader/Wiktionary, com camada editorial limitada. Licenças em `LICENSE` e `ATTRIBUTION`.

## Executar

```sh
cd lexi
python3 -m http.server 8009
```

Abrir `http://localhost:8009/`. O service worker funciona em localhost ou HTTPS. Em Definições, usar **Preparar dicionário para uso offline** para colocar as definições, formas e sílabas na cache (cerca de 26 MB). A permanência da cache depende do browser e do espaço disponível.

## Implementado

- Definições por palavra, com preferência para 114 entradas editoriais PT-PT (117 aceções).
- Listagens por letra inicial, final, número de letras e combinações.
- Continuação «mais» e manutenção parcial do contexto.
- Link opcional para Priberam.
- Interface em português europeu e inglês, com seletor de idioma no cabeçalho e em Definições.
- Definições com seletor de idioma, cópia de segurança das preferências, instalação e verificação explícita de atualizações.
- Sem API, sem servidor PHP e sem dependências de runtime.

## Limitações conhecidas

- A segmentação de sentidos e identificação regional é heurística; as definições não foram todas revistas.
- As 57 equivalências regionais são associações dependentes do sentido, não equivalências universais; 7 remetem para formas que não têm entrada própria no dicionário.
- As substituições automáticas PT-PT não ajustam concordância nem distinguem todos os contextos. Exemplos por rever: «no casa de banho», «na ecrã», «sumo gástrico», «auto-autocarro» e «aplicação, aplicação». O texto original é preservado e a interface assinala estas adaptações.
- A camada editorial tem 117 aceções para 114 entradas, incluindo aceções duplicadas para «ecrã», «frigorífico» e «gelado» e variantes de maiúscula com o mesmo texto.
- As 9 819 entradas com várias palavras (por exemplo, «casa de banho») não são alcançáveis pela pesquisa conversacional atual, que interpreta uma palavra por vez.
- Algumas entradas usam a coluna gramatical para exemplos entre aspas, incluindo o artefacto de conversão «Títulos não suportados/reticências entre colchetes».
- Os dados silábicos cobrem 67 527 das 81 068 entradas (83,3%); a pesquisa por sílabas só encontra formas cobertas.
- 2 598 grafias normalizadas agrupam mais de uma entrada por diferenças de maiúsculas ou acentos; a aplicação prefere agora a correspondência exata.
- `meta.curated` (14) e `meta.preferences` (25) estão desatualizados face aos dados reais; a aplicação usa as entradas e `regional.json`.
- Divisão silábica, sinónimos, antónimos e categorias semânticas ainda não estão validados.
- As formas flexionadas vêm de `pt-pt.syn` (`data/forms/`); a cobertura e a desambiguação continuam limitadas.
- A pesquisa por palavra é feita por lema e não corrige automaticamente flexões.
- Para produção: testar iPhone 6 / Safari 12 em dispositivo real, validar acessibilidade com leitor de ecrã e rever a cache/preparação offline. A compatibilidade de sintaxe, o substituto de `<dialog>` e os ícones PNG já foram tratados, mas não há verificação em dispositivo neste repositório.

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

O site é estático. No host, a partir do checkout `~/lexi`, com o document root em `~/lexi.basecentral.link`:

```sh
bash scripts/deploy.sh --dry-run "$HOME/lexi.basecentral.link"
bash scripts/deploy.sh "$HOME/lexi.basecentral.link"
bash scripts/deploy.sh --verify "$HOME/lexi.basecentral.link"
```

O destino predefinido é `~/lexi.basecentral.link`, pelo que o argumento pode ser omitido. O script usa o motor comum BaseCentral (`scripts/deploy-core.sh`) e a lista de publicação em `scripts/deploy-profile.sh`:

- exige um checkout limpo, num ramo com upstream, e faz `git pull --ff-only`;
- publica apenas a lista revista de 105 ficheiros (HTML, scripts, manifest, ícones, `data/`, auditorias, licenças);
- não publica `README.md`, `AGENTS.md` nem testes, não corre builds, não apaga ficheiros alheios e não publica nada implicitamente;
- publica `sw.js` depois dos restantes ficheiros.

Antes de correr no host, fazer commit e push. O destino tem de existir, ser gravável e não ser um symlink. HTTPS é obrigatório para o service worker. `--dry-run` não faz fetch nem escreve; `--no-http` desativa a verificação HTTP final. Se os ficheiros públicos mudarem, atualizar `scripts/deploy-profile.sh` e `version.js`.


## v2: formas flexionadas

O índice original `pt-pt.syn` foi associado às 81 068 entradas na ordem de `pt-pt.idx`, sem inferir conjugações. Os ficheiros `data/forms/*.json` permitem reconhecer formas como plurais e verbos conjugados. Se uma forma tiver vários lemas, Lexi pede que se escolha a entrada pretendida. O índice é descarregado por letra, conforme necessário. O botão de transferência offline carrega as definições e as formas flexionadas.


## v3 — Pesquisa experimental por sílabas

Foram pré-calculadas sugestões de divisão com os padrões de translineação `pt_PT` do Pyphen. **Translineação não equivale a divisão silábica**; por isso, resultados com número de sílabas são explicitamente assinalados como experimentais e não devem ser tratados como factos linguísticos verificados. A pesquisa aceita combinações de letra inicial, final, número de letras e número aproximado de sílabas. Os dados estão em `data/syllables/`. O projeto Pyphen e os padrões incluídos têm licenças próprias; confirmar a licença dos padrões antes de redistribuir publicamente.

## v4 — motor de conversação

O módulo `conversation.js` reconhece intenções de forma determinística e sem dependências: saudações, ajuda, definições, equivalências regionais, pesquisas combinadas, continuação de resultados, outros significados, texto original e reinício de contexto. Mantém filtros entre perguntas como «Agora com quatro sílabas». Aceita perguntas plurais («O que são batatas?»), artigos plurais («as», «os»), texto sem acentos («o que sao batatas») e uma saudação antes da pergunta («Olá, o que são batatas?»); se o resto da frase não for reconhecido, a saudação mantém-se como resposta.

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

As palavras nas definições são botões que abrem a respetiva entrada sem reescrever a pergunta. O texto da definição não é alterado. O convite «Podes pedir «mais»» contém agora um botão «mais» para continuar a pesquisa. O aviso de que existem mais aceções apresenta «outros significados» como uma única ação que abre a página seguinte, em vez de dividir a expressão em duas ligações de palavras.


## v9 — idiomas, atualizações e compatibilidade

- `version.js` é a fonte única da versão da aplicação e do service worker. A cache chama-se `lexi-<versão>`; incrementar a versão é obrigatório em cada release que altere ficheiros em cache, para não sobrepor a cache ativa.
- O service worker já não ativa imediatamente uma versão nova. Em Definições, **Verificar atualizações** distingue a versão instalada de uma atualização pendente e **Atualizar aplicação** pede confirmação antes de recarregar.
- A interface está em português europeu e inglês. O seletor nativo de idioma aparece depois das Definições no cabeçalho e também dentro das Definições; a escolha explícita é guardada.
- A cópia de segurança é um JSON `lexi-backup` (schema 1) com as preferências de idioma e da ligação ao Priberam. A Lexi não guarda registos pessoais. A importação valida o ficheiro, mostra uma pré-visualização e permite cancelar.
- **Preparar dicionário para uso offline** transfere definições, formas e sílabas (cerca de 26 MB), verifica a escrita na cache, permite cancelar e distingue o shell offline do dicionário preparado.
- O `<dialog>` foi substituído por um painel compatível, foram removidos `?.`, `??` e `||=`, e foram adicionados ícones PNG, `apple-touch-icon` e fallbacks CSS para o alvo iPhone 6 / Safari 12.
- Continua a faltar validação em iPhone 6/Safari 12 e revisão de acessibilidade em dispositivo. `node test-conversation.cjs` cobre agora 52 asserções no interpretador, incluindo comandos em inglês.


## v10 — identidade visual

- Novo símbolo: um **L** branco (a lombada e a capa inferior do livro aberto) com três folhas em tons de turquesa a abrir a partir da lombada. Desenhado em `icons/icon.svg`, que continua a ser o ícone da aplicação, do manifest e do favicon.
- `icons/mark.svg` é o mesmo desenho sem a placa de fundo, usado no cabeçalho à esquerda de «Lexi». Está na pré-cache do service worker e na lista de publicação.
- `icons/icon-180.png` (apple-touch-icon) passou a ser de sangria total: o iOS aplica a sua própria máscara e os cantos transparentes apareciam a preto.
- Versão atualizada para `2026.11.08.1` porque a arte e o cabeçalho são ficheiros em cache.

