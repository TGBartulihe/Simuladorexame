# Simulador de Exame Nacional — atualização (dados + UI)

Este pacote tem duas partes que se complementam:

1. **`scripts/`** — fecham as lacunas de dados encontradas na auditoria do
   banco (gabarito de escolha múltipla, cotações, tópicos por questão).
2. **`app/`** — UI completa (menu, simulação, correção, progresso),
   substituindo os arquivos mockados do projeto atual.

A UI já funciona com os dados de hoje (mostra estados vazios honestos onde
faltar gabarito/pontuação), mas só fica completa de verdade depois do
passo 2 abaixo.

---

## 1. Diagnóstico que motivou isto

Na auditoria do `simuladorexame.db`:

- 152 exames, 1.479 questões, 4 disciplinas (Português, Matemática A,
  Física e Química A, Biologia e Geologia), 2012–2025 — boa cobertura.
- **0%** das `choices` tinham `is_correct = 1` — nenhuma múltipla escolha
  tinha gabarito marcado na estrutura (só existia como texto livre dentro
  de `criteria.criteria_text`, em formatos inconsistentes).
- **0%** das `questions`/`criteria` tinham `max_points` preenchido — a
  cotação também só existia como texto livre ("10 pontos").
- **0%** das `questions` tinham `topic`/`subtopic`/`difficulty` — não
  havia nenhuma taxonomia de assunto, o que torna impossível dizer "você
  tem dificuldade em X" no nível de tópico (só no nível de disciplina).
- As 48 fases **EE** (Exame de Equivalência) têm **zero questões
  extraídas** em todas elas — não é falha pontual, é sistemático nessa
  fase. Fica fora do escopo deste pacote; é um problema de parsing de PDF,
  provavelmente porque o formato da fase EE é diferente.
- **22 questões** (quase todas `question_number = "1"`, em exames de
  Biologia e Geologia / Física e Química A) têm o `statement` corrompido:
  o parser capturou a tabela-resumo de cotações do início da prova
  ("Destes 8 itens, contam para a nota final os 4 com melhor pontuação")
  como se fosse o enunciado. A UI já filtra essas (`statementCorrompido`),
  mas a questão real provavelmente está perdida e precisa reextração do
  PDF original — fica registado aqui como item para o `process_parser_v2`.

## 2. Ordem de execução

Local: **todos os scripts em `scripts/` rodam na sua máquina**, não no
ambiente do Claude — o `02_extract_with_llm.py` depende do Ollama local
(`qwen2.5:7b`), que só existe no seu setup.

```bash
# a partir da raiz do repositório TGBartulihe/Simuladorexame

# Passo 1 — regex: resolve ~45% do gabarito de escolha múltipla sem custo
# de LLM. Roda em segundos, sem dependências externas.
python scripts/01_extract_mc_answers_regex.py --db caminho/simuladorexame.db --dry-run
# confira a saída, depois rode de verdade (sem --dry-run):
python scripts/01_extract_mc_answers_regex.py --db caminho/simuladorexame.db

# Passo 2 — LLM local: resolve o resto do gabarito + cotações + tópicos.
# Precisa do Ollama a correr (`ollama serve`) com qwen2.5:7b disponível.
pip install requests
python scripts/02_extract_with_llm.py --db caminho/simuladorexame.db --limit 20   # teste rápido primeiro
python scripts/02_extract_with_llm.py --db caminho/simuladorexame.db              # roda tudo

# Passo 3 — export: gera os JSON estáticos que a UI consome
python scripts/03_export_static_site_data.py --db caminho/simuladorexame.db --out app/public/data
```

Depois disso, `npm install && npm run dev` dentro de `app/` já mostra a UI
com os dados reais.

## 3. O que cada script faz e por que essa ordem

**`01_extract_mc_answers_regex.py`** — resolve com regex os casos
inequívocos: `"Opção (D)"`, `"Versão 1 – (C); Versão 2 – (B)"`, e um
padrão recorrente em que o parser original juntou o gabarito de várias
questões num único registro de `criteria` (`"Item 12. 13.\nVersão 1 (C)
(D)\nVersão 2 (D) (B)"`) — esse caso é resolvido por posição, casando os
números de item com as questões irmãs no mesmo exame. Cobre ~242 das 539
questões de escolha múltipla (45%) sem gastar nenhuma chamada de LLM.
Grava um log em `mc_answer_extraction_log` (tabela nova, criada pelo
script) para o script 02 saber o que já está resolvido.

Sobre **"Versão 1 / Versão 2"**: os exames nacionais costumam ter dois
cadernos com a ordem das alternativas trocada, para dificultar cola. O
schema atual (`exams.version`) está 100% NULL — não há registo de qual
caderno cada aluno real recebeu. Quando há duas versões, o script marca
**ambas** as letras como corretas. Isso é uma decisão deliberada: como a
simulação não sabe qual caderno está a reproduzir, o aluno deve poder
acertar com qualquer uma das duas. Se quiser distinguir os cadernos no
futuro, seria necessário voltar ao PDF original para saber qual versão é
qual.

**`02_extract_with_llm.py`** — usa o mesmo modelo que você já tinha
testado (`qwen2.5:7b` via Ollama, visto em `ai_exam_cache`) para três
tarefas que regex não cobre com segurança:
- gabarito das ~297 questões restantes (texto sem padrão reconhecível,
  glifos corrompidos de fonte simbólica, etc.);
- `max_points` a partir do texto livre de `criteria_text`;
- `topic`/`subtopic` por questão, contra uma **taxonomia fechada** por
  disciplina (8 tópicos cada, ver `TOPIC_TAXONOMY` no script). A lista é
  fechada de propósito — se o LLM pudesse inventar categorias livremente,
  a tela de progresso por tópico ficaria instável (uma categoria
  ligeiramente diferente a cada exame processado). **Revise essa lista
  antes de rodar em escala** — é um ponto de partida razoável, não a
  palavra final; você conhece o programa das disciplinas melhor do que eu.

Cada chamada ao modelo é cacheada numa tabela própria
(`llm_extraction_cache`, **não** reaproveita a tabela `ai_cache` existente
porque ela tem `question_id` como `UNIQUE` e não suporta guardar três
tipos de extração diferentes para a mesma questão sem um sobrescrever o
outro). É seguro interromper e retomar.

Use `--only-missing-answers`, `--only-points` ou `--only-topics` para
rodar uma parte por vez, e `--limit N` para testar rápido antes de rodar
tudo (1.479 questões × 3 prompts pode demorar, dependendo da sua máquina).

**`03_export_static_site_data.py`** — gera os JSON estáticos a partir do
SQLite, seguindo a arquitetura já descrita no README do repo (SQLite →
JSON → frontend). Marca explicitamente `gabaritoDisponivel`,
`pontuacaoDisponivel` e `statementCorrompido` em cada questão, para a UI
nunca fingir um dado que não existe.

## 4. UI — o que foi construído

- **Menu** (`ExamSelector.jsx`): disciplina → ano → fase, com aviso visual
  quando um exame tem dados incompletos (gabarito parcial, sem questões
  extraídas, etc.) em vez de deixar escolher algo que vai falhar
  silenciosamente. O botão "Simular um exame ao acaso" no `App.jsx` cobre
  o pedido de simulação direta sem escolher nada.
- **Simulação** (`ExamRunner.jsx`): agrupa por `GRUPO I/II/III` e por
  contexto compartilhado (texto-base, figura), exatamente como a prova
  impressa — um texto de apoio não se repete a cada questão que o usa.
- **Correção** (`ExamResult.jsx`): mostra todas as respostas ao final,
  com o gabarito ao lado de cada alternativa e uma grade de cotações
  (inspirada nas grades oficiais do IAVE) como resumo visual rápido.
  Questões sem gabarito/pontuação disponível aparecem como "para revisão",
  nunca como erradas por omissão.
- **Progresso** (`ProgressDashboard.jsx`): taxa de acerto por tópico,
  ordenada da maior dificuldade para a menor, com sugestão de outro exame
  da mesma disciplina que tenha questões do tópico mais frágil. Isto só
  fica útil depois do passo 2 (classificação de tópicos) — antes disso, a
  tela mostra um estado vazio explicando o motivo, não um gráfico vazio
  sem contexto.

O progresso é gravado em `localStorage` (`lib/progressStore.js`), espelhando
deliberadamente o schema de `student_attempts` / `student_answers` /
`student_statistics` do banco real — se um dia quiser sincronizar de volta
para o SQLite (multi-dispositivo, visão do professor sobre a turma), o
formato já está pronto, sem transformação.

## 5. PWA — instalável e funciona offline

Decisão tomada em conversa: baixar **todos** os dados (5.7MB hoje) na
instalação, em vez de cache progressivo por exame acessado. O aluno
instala uma vez (com internet) e depois usa qualquer exame sem rede.

### O que foi adicionado
- `public/manifest.json` — nome, ícones, cores, `display: standalone`
- `public/sw.js` — Service Worker: cacheia o app shell + todos os
  `data/*.json` na instalação; serve do cache primeiro depois disso
- `public/icons/` — 4 PNGs gerados por `scripts/generate_icons.py`
  (reaproveitando a paleta de `styles.css`; rode de novo se mudar a paleta)
- registo do Service Worker em `src/main.jsx` (só ativo em build de
  produção, não em `npm run dev`)

### ⚠️ Importante: o repositório não é `<user>.github.io`

Como `Simuladorexame` é um repo nomeado (não o repo especial
`tgbartulihe.github.io`), o GitHub Pages serve o site em
`https://tgbartulihe.github.io/Simuladorexame/` — um **subpath**, não a
raiz do domínio. Isso afeta onde o app busca seus próprios arquivos
(JS, CSS, manifest, ícones, e os JSON de dados).

Isso já está configurado em `vite.config.js` (`base: '/Simuladorexame/'`).
**Se o nome do repositório for outro**, edite o valor de `REPO_NAME` em
dois lugares — não há como evitar essa duplicação, porque
`manifest.json` é servido como arquivo estático puro, sem passar pelo
processamento de variáveis do Vite:
1. `app/vite.config.js` → `const REPO_NAME = 'Simuladorexame'`
2. `app/public/manifest.json` → `start_url`, `scope`, e cada `icons[].src`

`index.html` e `sw.js` **não** precisam de edição: o primeiro usa
`%BASE_URL%` (substituição nativa do Vite, funciona em qualquer tag,
diferente de um caminho absoluto que o Vite não reescreve em `<link>`);
o segundo deriva o caminho a partir de `self.location` em runtime.

### Testando localmente

Com `base` configurado como subpath absoluto, o dev server também serve
nesse subpath — **acesse `http://localhost:5173/Simuladorexame/`**, não
a raiz, ou vai parecer que o app não carregou nada.

```bash
cd app
npm install
npm run dev
# abra http://localhost:5173/Simuladorexame/
```

Para testar o comportamento de PWA de fato (instalação, offline), é
preciso um build de produção servido por HTTP (Service Workers não
funcionam em `npm run dev` por design, e exigem HTTPS ou localhost):

```bash
npm run build
npm run preview
# abra o endereço que o preview indicar, com o subpath /Simuladorexame/
```

No Chrome/Edge desktop: DevTools → Application → Manifest, para
confirmar que o navegador reconheceu o manifest e oferece "Instalar". Em
Application → Service Workers, confirme que o `sw.js` está `activated`
e veja em Cache Storage se `exame-data-v1` tem os ~152 arquivos.

Para forçar os PWAs já instalados a buscar uma nova versão dos dados
depois de você rodar os scripts 01/02/03 de novo, troque
`CACHE_VERSION` em `public/sw.js` (ex: `'v1'` → `'v2'`) antes de publicar
— isso invalida o cache antigo e dispara um novo download completo na
próxima visita de cada aluno.

## 6. O que eu NÃO consegui testar

Não tenho Node/npm com acesso à internet neste ambiente, então não rodei
um `npm run dev` de verdade num navegador. Testei o que pude sem rede:
- Sintaxe e bundling de todos os arquivos JS/JSX com `esbuild`.
- Renderização real dos componentes via `react-dom/server`
  (`renderToStaticMarkup`), com os dados reais exportados do seu banco.
- `correctionEngine.js` e `progressStore.js` com simulações ponta a ponta.

O que ainda vale verificar na sua máquina, num navegador de verdade:
- Comportamento visual/responsivo real (o CSS foi escrito mas não visto
  renderizado).
- Que as fontes do Google Fonts carregam corretamente (depende de rede no
  seu ambiente de build).
- O fluxo completo de clique (seleção de alternativa, submissão, etc.) —
  testei a lógica isoladamente, não a interação real do DOM.
- **A instalação real do PWA e o funcionamento offline.** Validei a
  sintaxe do `sw.js` e a lógica de caminhos (base path, `%BASE_URL%`,
  `self.location` no Service Worker) contra a documentação oficial do
  Vite, mas não tenho como abrir um Chrome real aqui, instalar o app, e
  testar offline de fato. Isso é o item de maior risco residual desta
  entrega — confirme com os passos da seção 5 antes de considerar o PWA
  pronto.
