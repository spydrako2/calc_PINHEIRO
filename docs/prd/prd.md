# HoleritePRO — Product Requirements Document (PRD)

## 1. Goals and Background Context

### 1.1 Goals

- **Eliminar a digitacao manual** de dados de holerites em planilhas de calculo juridico
- **Reduzir erros humanos** na transcricao de verbas, valores e periodos de referencia
- **Acelerar a producao de calculos** para acoes judiciais contra o Estado de SP
- **Permitir escala** — novos estagiarios produzem calculos sem treinamento extensivo
- **Suportar multiplas teses juridicas** de forma modular (IAMSPE, Diferenca de Classe, Quinquenio/Sexta-Parte, e futuras)
- **Manter compatibilidade** com o fluxo existente (Excel → PDF → processo judicial)

### 1.2 Background Context

Um escritorio de advocacia ajuiza acoes judiciais em favor de servidores publicos do Estado de Sao Paulo. Cada acao requer uma planilha de calculo que demonstra os valores devidos ao servidor — essa planilha e preenchida manualmente a partir de dezenas ou centenas de holerites em PDF, um processo lento, tedioso e propenso a erros.

Os holerites sao emitidos por orgaos do Governo do Estado de SP em pelo menos 3 templates distintos (DDPE para ativos, SPPREV para aposentados, SPPREV para pensionistas). Cada template tem layout, codigos de verba e estrutura diferentes. Alem disso, um mesmo holerite pode conter verbas normais, atrasados, reposicoes e estornos referentes a periodos diferentes, e um mesmo PDF pode conter paginas com texto selecionavel misturadas com paginas escaneadas.

O software proposto automatiza a extracao dos dados dos PDFs e seu lancamento nas planilhas de calculo, respeitando as regras de alocacao temporal e as formulas especificas de cada tese juridica.

### 1.3 Change Log

| Date       | Version | Description                  | Author |
|------------|---------|------------------------------|--------|
| 2026-02-22 | 0.1     | Initial draft from gathering | Morgan |
| 2026-02-23 | 0.2     | Added FR-13a: auditability rule — decomposed formulas for composite values (=1000-200-200 instead of 600). Updated Stories 1.6, 2.5, 3.4 ACs | Morgan |
| 2026-02-23 | 0.3     | Added FR-18 (default 5-year period, adjustable), FR-19 (always generate new file, never edit existing). Updated Stories 2.7, 3.2 ACs | Morgan |
| 2026-02-23 | 0.4     | Added FR-20 (verba learning registry), FR-21 (semantic qualifier detection), FR-22 (alias support for verba identity). Added Story 2.1a. Updated Story 1.1 (qualificadores in data model), Story 2.1 (registry integration) | Morgan |
| 2026-02-23 | 0.5     | Corrected FR-01: extraction is selective (only fields needed by selected tese), not all-or-nothing. Updated FR-02: holerites can span multiple pages (continuação logic), and months without holerites generate no rows in final spreadsheet | Morgan |
| 2026-02-23 | 0.6     | Integrated Pinheiro Advocacia branding: updated Section 3.5 with official color palette (Azul Escuro #1a365d, Dourado #C7A76D, Branco, Vermelho, Verde). Defined application of branding to HoleritePRO UI elements | Morgan |

---

## 1.4 Casos de Uso Identificados em Referências

### 1.4.1 Múltiplos Cargos da Mesma Pessoa (Simultâneos)
**Exemplo Real:** CAROLINA BATISTA DOS SANTOS
- CARGO 01: Holerites 02/21 A 02/26 (professora ETEC?)
- CARGO 02: Holerites 02/21 A 02/26 (mesma pessoa, diferente cargo)
- **Requisito:** Deve gerar 2 planilhas separadas (uma por cargo), mesmo que seja mesma pessoa no mesmo período
- **Critério de Diferenciação:** Codigo do servidor (CPF é igual), mas código do cargo é diferente no holerite

### 1.4.2 Períodos Longos com Múltiplas Páginas
**Exemplos Reais:**
- FRANCISCA LUCIA OLIVEIRA LOPES: 04/22 A 10/25 (34 meses = ~15+ páginas)
- MARCIA LOPES DE OLIVEIRA MACHADO: 01/21 A 02/26 (13 meses = ~6+ páginas)
- **Característica:** Holerites que ocupam múltiplas páginas, especialmente com muitos atrasos

### 1.4.3 Atrasos Acumulados em Períodos Históricos
**Padrão Observado:**
- Períodos longos (5+ anos) frequentemente contêm: verbas normais + reposições + atrasos de períodos anteriores
- Exemplo: Holerite de 02/26 pode conter atrasados de 01/26, 12/25, 11/25, etc.
- **Impacto:** Aumenta complexidade da alocação temporal e necessidade de revisão visual

---

## 2. Requirements

### 2.1 Functional

- **FR-01:** O sistema deve ler arquivos PDF de holerites para localizar e entender sua estrutura (template, campos, layout). A extração é seletiva: extrai apenas os campos necessarios para a tese selecionada. Exemplo: a tese IAMSPE extrai codigo, denominacao, valor das 10 verbas IAMSPE + cabecalho (nome, CPF, competencia); a tese Quinquenio extrai apenas as 7 verbas de vantagens integrais. Isso reduz processamento e memoria sem perder precisao para o calculo juridico necessario.

- **FR-02:** O sistema deve auto-detectar o template do holerite, suportando no minimo: (a) DDPE — Departamento de Despesa de Pessoal do Estado (servidores ativos, codigos formato XX.XXX), (b) SPPREV Aposentados (layout detalhado, codigos formato XXXXXX), (c) SPPREV Pensionistas (layout 2 secoes: base de calculo + demonstrativo de pagamento). Um holerite pode ocupar uma ou multiplas paginas (ex: holerite com muitos atrasados pode estar dividido entre pagina 1 — cabecalho + primeiras verbas — e pagina 2 — continuacao de verbas + rodape). O sistema deve detectar continuacoes e agrupar como um unico holerite logico. Meses sem holerite (lacunas) nao geram linhas na planilha final.

- **FR-03:** O sistema deve processar PDFs com multiplas paginas, onde cada pagina e um holerite separado, extraindo todos os holerites do arquivo em lote.

- **FR-04:** O sistema deve implementar deteccao hibrida por pagina: texto selecionavel usa extracao direta (pdfplumber); paginas escaneadas usam OCR (Tesseract) como fallback. Ambos os tipos podem coexistir no mesmo PDF.

- **FR-05:** O sistema deve normalizar codigos de verba entre templates, permitindo mapear codigos equivalentes (ex: 70.006 do DDPE = 070006 do SPPREV).

- **FR-06:** O sistema deve classificar cada verba extraida por sua Natureza: N (Normal), A (Atrasado), R (Reposicao), D (Devolucao), E (Estorno).

- **FR-07:** O sistema deve aplicar a regra de alocacao temporal: cada verba e alocada na planilha no mes seguinte ao periodo de referencia. Se o periodo e 01/01/2024 a 31/01/2024, a verba e lancada na linha de 02/2024. Verbas normais (N) do mes corrente permanecem no proprio mes.

- **FR-08:** O sistema deve identificar e tratar separadamente os tipos de folha: Folha Normal, Folha Suplementar, e 13o Salario.

- **FR-09:** O sistema deve suportar teses juridicas como modulos independentes. Cada modulo define: (a) quais verbas extrair dos holerites (por codigo), (b) como mapear para colunas da planilha, (c) quais formulas aplicar, (d) quais linhas especiais gerar (13o proporcional, 1/3 ferias).

- **FR-10:** O sistema deve implementar o modulo da tese IAMSPE: extrair 10 verbas IAMSPE (codigos 70.006, 70.007, 70.037, 70.119, 70.120, 70.121, 70.122, 70.123, 70.124, 70.125), lancar por mes, calcular soma horizontal (VALOR DEVIDO = SUM de todas as verbas IAMSPE do mes) e soma vertical (TOTAL BRUTO).

- **FR-11:** O sistema deve implementar o modulo da tese Diferenca de Classe (Policial Civil): extrair salario base (01.001), quantidade de quinquenios (09.001 QTD), presenca de sexta-parte (10.001). Aceitar entrada externa de tabela salarial por classe de delegacia. Calcular: diferenca salarial, diferenca RETP, quinquenio (5% por quinquenio), sexta-parte (1/6 se aplicavel), total devido, 13o proporcional e 1/3 ferias.

- **FR-12:** O sistema deve implementar o modulo da tese Quinquenio e Sexta-Parte: extrair ate 7 verbas de vantagens integrais (Piso Salarial, Insalubridade, ALE, Art.133, AOL, GAP, GDAP — configuraveis por tese), quantidade de quinquenios, presenca de sexta-parte. Calcular: total vantagens, porcentagem quinquenal (5% x N), diferenca quinquenios, sexta-parte (1/6), total devido, 13o proporcional.

- **FR-13:** O sistema deve exportar planilhas XLSX com formulas ativas (nao apenas valores estaticos), seguindo o formato e estrutura das planilhas-modelo de cada tese.

- **FR-13a:** Quando multiplos lancamentos incidirem sobre a mesma verba no mesmo periodo de alocacao (ex: valor normal + reposicoes atrasadas), a celula do Excel deve conter uma formula decomposta que preserve cada componente individual (ex: `=1000-200-200`), e NAO o valor somado (ex: 600). Isso e obrigatorio para auditabilidade — o setor de liquidacao confere cada lancamento linha a linha na planilha final. A formula deve usar sinais de + para vencimentos e - para descontos/reposicoes, na ordem cronologica em que foram lancados nos holerites.

- **FR-14:** O sistema deve apresentar uma tela de revisao pos-extracao onde o usuario visualiza todos os dados extraidos organizados por mes, com destaque para: (a) verbas com Natureza diferente de Normal, (b) verbas realocadas temporalmente, (c) indicador de confianca da extracao (texto vs OCR), (d) celulas com valores compostos (multiplos lancamentos) mostrando a decomposicao. O usuario pode corrigir valores antes de exportar.

- **FR-15:** O sistema deve permitir adicionar novas teses sem alterar o core, fornecendo uma estrutura de plugin/modulo com interface definida (verbas de interesse, mapeamento de colunas, formulas, linhas especiais).

- **FR-16:** O sistema deve permitir importar e gerenciar tabelas salariais externas (ex: tabela de classes da Policia Civil), que sao atualizadas pelo Estado de SP periodicamente.

- **FR-17:** O sistema deve lidar com verbas que mudam de codigo ao longo do tempo por alteracao legislativa (ex: contribuicao previdenciaria 70.056 → 70.113 a partir de 2020), mantendo uma tabela de equivalencias configurable por tese.

- **FR-18:** O sistema deve aplicar um periodo padrao de 5 anos retroativos a partir da data atual (ex: se hoje e fev/2026, periodo padrao = mar/2021 a fev/2026). O usuario pode ajustar o periodo manualmente para casos excepcionais. Verbas extraidas fora do periodo selecionado sao filtradas e nao aparecem na planilha exportada, mas ficam visiveis na tela de revisao (em cinza/desabilitadas) para que o usuario possa incluir manualmente se necessario.

- **FR-19:** O sistema SEMPRE gera um arquivo XLSX novo a cada exportacao — nunca edita um arquivo existente. Isso elimina o risco de corromper planilhas-modelo compartilhadas. A planilha gerada e autonoma (contem todas as formulas necessarias), substituindo a necessidade de manter templates de planilha no drive.

- **FR-20:** O sistema deve manter um registro de aprendizado de verbas (verba registry) que armazena decisoes de classificacao feitas pelo usuario durante a revisao. Cada registro contem: codigo(s) da verba, denominacao(oes) conhecidas, natureza juridica (permanente, temporaria, incorporada, etc.), e quais teses a utilizam. O registro funciona como sugestao — ao encontrar uma verba ja conhecida, o sistema pre-classifica automaticamente, mas NUNCA impoe sem revisao humana. Verbas desconhecidas (nao presentes no registro) sao marcadas como "nao classificada" e exigem revisao obrigatoria.

- **FR-21:** O sistema deve detectar automaticamente qualificadores semanticos na denominacao da verba que indicam sua natureza juridica. Padroes conhecidos incluem: "ART.133" ou "ART. 133" (verba incorporada), "VPNI" (Vantagem Pessoal Nominalmente Identificada — verba incorporada), "PRO-LABORE" (verba permanente). A deteccao automatica serve como sugestao inicial na tela de revisao — o humano confirma, corrige ou complementa. Decisoes confirmadas alimentam o registro de aprendizado (FR-20).

- **FR-22:** O sistema deve reconhecer que uma mesma verba pode aparecer com codigos e/ou denominacoes diferentes entre processadores de folha (Fazenda vs SPPREV), entre periodos (mudancas legislativas), ou por incorporacao (ex: "GRAT. ATIVIDADES ESPECIAIS" → "VPNI - GRAT. ATIVIDADES ESPECIAIS"). O registro de aprendizado (FR-20) deve suportar aliases: multiplos codigos e denominacoes mapeados para a mesma verba logica. Aliases sao criados pelo usuario durante a revisao e replicados automaticamente em calculos futuros.

### 2.2 Non Functional

- **NFR-01:** Precisao de extracao >= 95% para PDFs com texto selecionavel em todos os templates suportados.

- **NFR-02:** Processar um PDF de 60+ paginas em menos de 120 segundos em hardware medio (i5, 8GB RAM).

- **NFR-03:** Funcionar em Windows 10/11 como aplicacao desktop standalone (.exe), sem necessidade de instalar Python, dependencias ou servidores.

- **NFR-04:** Interface intuitiva para usuarios nao-tecnicos (estagiarios de direito) — fluxo guiado com no maximo 4 passos: selecionar tese → importar PDFs → revisar dados → exportar planilha.

- **NFR-05:** O sistema deve funcionar 100% offline apos a instalacao (sem dependencia de APIs externas ou internet).

- **NFR-06:** O executavel final (.exe) deve ter tamanho maximo de 200MB incluindo Tesseract OCR embutido.

- **NFR-07:** O sistema deve suportar PDFs de ate 500 paginas sem crash ou memory overflow.

- **NFR-08:** Logs de extracao devem ser gerados para auditoria, incluindo: arquivo processado, template detectado, verbas extraidas, confianca, e quaisquer erros ou fallbacks para OCR.

---

## 3. User Interface Design Goals

### 3.1 Overall UX Vision

Interface limpa, profissional e guiada. O usuario nao precisa entender a estrutura dos holerites — o sistema faz a deteccao automatica. A experiencia e similar a um "assistente" (wizard) de 4 etapas. Paleta de cores profissional (tons neutros com acentos em azul escuro). Sem elementos gamificados ou visuais desnecessarios.

### 3.2 Key Interaction Paradigms

- **Wizard de 4 etapas** com progresso visual claro
- **Drag-and-drop** para importacao de PDFs
- **Tabela editavel** para revisao de dados extraidos com destaque visual por tipo de verba
- **Preview da planilha** antes de exportar
- **Barra de progresso** durante processamento de PDFs

### 3.3 Core Screens and Views

1. **Tela Inicial** — Selecao de tese (cards com nome e descricao curta de cada tese disponivel) + botao "Gerenciar Teses"
2. **Importacao de PDFs** — Area de drag-and-drop + lista de arquivos importados com status de processamento
3. **Revisao de Dados** — Tabela organizada por mes com dados extraidos, colunas da tese, indicadores visuais (confianca, natureza da verba, realocacoes temporais), edicao inline
4. **Exportacao** — Preview resumido + opcoes de exportacao (caminho do arquivo, nome) + botao exportar
5. **Gerenciador de Tabelas Externas** — Para importar/editar tabelas salariais (tese Diferenca de Classe)
6. **Configuracao de Teses** — Para usuarios avancados: criar/editar modulos de tese (verbas, mapeamento, formulas)

### 3.4 Accessibility

WCAG AA — contraste adequado, navegacao por teclado, labels em todos os campos.

### 3.5 Branding

**Identidade Visual:** Pinheiro Advocacia (vide `docs/referencias/BRANDING.png`)

**Paleta de Cores Pinheiro:**
- 🔵 **Azul Escuro** (#1a365d) — fundo, navegacao, texto primario
- 🏆 **Dourado/Ouro** (#C7A76D) — logo, botoes CTA, acentos visuais, indicadores de sucesso
- ⚪ **Branco** (#FFFFFF) — texto em fundo escuro, backgrounds secundarios
- 🔴 **Vermelho** (#E53E3E) — alertas, erros
- 🟢 **Verde** (#38A169) — confirmacoes, status OK

**Aplicacao no HoleritePRO:**
- Botoes principais (Importar, Exportar): fundo dourado com texto azul escuro
- Logo Pinheiro no topo de cada tela
- Abas do wizard: ativa = dourado, inativa = cinza
- Indicadores de confianca (texto vs OCR): verde = alta, amarelo = media, vermelho = baixa
- Checkmark de sucesso na tela de exportacao: icone dourado

### 3.6 Target Device and Platforms

Desktop Only — Windows 10/11. Resolucao minima: 1366x768.

---

## 4. Technical Assumptions

### 4.1 Repository Structure

**Monorepo** — projeto unico com todos os modulos.

### 4.2 Service Architecture

**Aplicacao Desktop Monolitica** em Python:

- **Linguagem:** Python 3.11+
- **GUI Framework:** CustomTkinter (leve, visual moderno, sem dependencias pesadas)
- **PDF Extraction (texto):** pdfplumber — extracao por coordenadas, suporte a tabelas posicionais
- **PDF Extraction (OCR):** pytesseract + Tesseract OCR 5.x embutido
- **XLSX Generation:** openpyxl — suporte a formulas, formatacao, multiplas abas
- **Persistencia:** JSON (verba_registry.json) — nao necessita banco de dados
- **Packaging:** PyInstaller para gerar .exe standalone para Windows
- **Deteccao hibrida:** por pagina (pdfplumber primeiro, OCR como fallback); fuzzy matching para template detection

```
holerite-pro/
├── src/
│   ├── core/                  # Engine principal
│   │   ├── pdf_reader.py      # Leitura de PDF (texto + OCR)
│   │   ├── template_detector.py # Auto-deteccao de template
│   │   ├── data_model.py      # Modelos de dados (Holerite, Verba, etc.)
│   │   ├── normalizer.py      # Normalizacao de codigos e periodos
│   │   └── verba_registry.py  # Registro de aprendizado de verbas (FR-20/21/22)
│   ├── parsers/               # 1 parser por template
│   │   ├── base_parser.py     # Interface abstrata
│   │   ├── ddpe_parser.py     # Template DDPE (ativos)
│   │   ├── spprev_apos_parser.py  # Template SPPREV aposentados
│   │   └── spprev_pens_parser.py  # Template SPPREV pensionistas
│   ├── teses/                 # 1 modulo por tese (plugin)
│   │   ├── base_tese.py       # Interface abstrata de tese
│   │   ├── iamspe.py          # Tese IAMSPE
│   │   ├── diferenca_classe.py # Tese Diferenca de Classe
│   │   └── quinquenio.py      # Tese Quinquenio/Sexta-Parte
│   ├── exporters/             # Geracao de XLSX
│   │   ├── base_exporter.py   # Interface abstrata
│   │   └── xlsx_exporter.py   # Exportador openpyxl
│   ├── tabelas/               # Tabelas externas (salariais)
│   │   └── tabela_manager.py  # CRUD de tabelas salariais
│   ├── registry/              # Dados persistidos
│   │   └── verba_registry.json # Registro de aprendizado de verbas
│   ├── ui/                    # Interface grafica
│   │   ├── main_window.py     # Janela principal
│   │   ├── tese_selector.py   # Tela 1: selecao de tese
│   │   ├── pdf_importer.py    # Tela 2: importacao
│   │   ├── data_reviewer.py   # Tela 3: revisao
│   │   └── exporter_view.py   # Tela 4: exportacao
│   └── utils/                 # Utilitarios
│       ├── logger.py          # Logging para auditoria
│       └── config.py          # Configuracoes
├── data/                      # Dados de referencia
│   ├── tabelas_salariais/     # Tabelas salariais importadas
│   └── tese_configs/          # Configuracoes de teses (YAML/JSON)
├── tests/                     # Testes automatizados
├── assets/                    # Icones, imagens
├── requirements.txt
├── pyproject.toml
└── build.spec                 # Config do PyInstaller
```

### 4.3 Testing Requirements

- **Unit tests** para parsers (cada template), normalizador, regra de alocacao temporal, e modulos de tese
- **Integration tests** com PDFs reais de referencia (anonimizados)
- **Framework:** pytest
- **Coverage minimo:** 80% no core e parsers

### 4.4 Additional Technical Assumptions

- Python foi escolhido por ter o melhor ecossistema para manipulacao de PDF (pdfplumber, pytesseract, camelot) e Excel (openpyxl), alem de packaging maduro para Windows (PyInstaller)
- Tesseract OCR sera embutido no .exe (nao requer instalacao separada)
- O sistema de teses usa uma interface abstrata (Strategy Pattern) que permite adicionar novas teses sem modificar o core
- Configuracoes de tese podem ser definidas em arquivos YAML para permitir que usuarios avancados criem teses sem programar (futuro)
- O formato de saida XLSX mantem formulas ativas para que o advogado possa auditar e ajustar no Excel antes de converter para PDF
- Equivalencia de verbas (mudancas legislativas) e configurada por tese em arquivo de dados, nao hardcoded

---

## 5. Epic List

### Epic 1: Core Engine — Extracao e Modelo de Dados
Estabelecer a infraestrutura do projeto, o engine de leitura de PDF (texto + OCR hibrido), deteccao automatica de template, parsers para os 3 templates identificados, modelo de dados normalizado, e regra de alocacao temporal. Entrega: CLI funcional que le PDFs e exibe dados extraidos.

### Epic 2: Sistema de Teses e Exportacao XLSX
Implementar a arquitetura de modulos de tese (plugin), os 3 modulos iniciais (IAMSPE, Diferenca de Classe, Quinquenio/Sexta-Parte), o exportador XLSX com formulas, e o gerenciador de tabelas externas. Entrega: pipeline completo de extracao → calculo → planilha via CLI.

### Epic 3: Interface Desktop e Experiencia do Usuario
Construir a interface grafica desktop (PyQt6) com as 4 telas do wizard (selecao de tese, importacao, revisao, exportacao), gerenciador de tabelas externas, e packaging como .exe standalone. Entrega: aplicacao desktop completa e distribuivel.

---

## 6. Epic Details

### Epic 1: Core Engine — Extracao e Modelo de Dados

**Objetivo:** Construir o coracao do sistema — a capacidade de ler qualquer holerite do Estado de SP em PDF, detectar automaticamente seu template, extrair todos os campos estruturados, normalizar os dados, e aplicar a regra de alocacao temporal. Ao final deste epic, o sistema processa PDFs e produz dados estruturados prontos para consumo pelos modulos de tese.

#### Story 1.1: Setup do Projeto e Modelo de Dados

Como desenvolvedor,
eu quero a estrutura do projeto Python configurada com o modelo de dados definido,
para que eu tenha a base sobre a qual construir todos os componentes.

**Acceptance Criteria:**
1. Projeto Python criado com pyproject.toml, estrutura de pastas conforme arquitetura, e dependencias iniciais (pdfplumber, pytesseract, openpyxl, pytest)
2. Modelo de dados implementado com dataclasses: Holerite (cabecalho + lista de verbas), CabecalhoHolerite (nome, cpf, cargo, unidade, competencia, tipo_folha, data_pagamento, template_type), Verba (codigo, denominacao, natureza, quantidade, unidade, periodo_inicio, periodo_fim, valor, qualificadores_detectados: list[str])
3. Enum para NaturezaVerba (NORMAL, ATRASADO, REPOSICAO, DEVOLUCAO, ESTORNO), TipoFolha (NORMAL, SUPLEMENTAR, DECIMO_TERCEIRO), TemplateType (DDPE, SPPREV_APOSENTADO, SPPREV_PENSIONISTA)
4. Normalizador de codigo de verba implementado: converte XX.XXX para XXXXXX e vice-versa, com tabela de equivalencias configurable
5. Funcao de alocacao temporal implementada: dado um periodo de referencia, retorna o mes de lancamento (periodo + 1 mes). Verbas normais do mes corrente permanecem no proprio mes
6. Testes unitarios para normalizador e alocacao temporal com cobertura >= 90%

#### Story 1.2: PDF Reader e Deteccao Hibrida (Texto vs OCR)

Como usuario,
eu quero que o sistema leia PDFs de holerites independente de serem texto selecionavel ou imagem escaneada,
para que eu possa processar qualquer holerite que eu receba.

**Acceptance Criteria:**
1. Modulo pdf_reader implementado que recebe um caminho de PDF e retorna uma lista de paginas com conteudo extraido
2. Deteccao hibrida por pagina: verifica se a pagina tem texto extraivel (pdfplumber); se o texto extraido for vazio ou abaixo de um limiar minimo de caracteres, aplica OCR (pytesseract) como fallback
3. Cada pagina retornada inclui metadados: numero da pagina, metodo de extracao usado (TEXTO ou OCR), e indicador de confianca (0.0-1.0)
4. Funciona com PDFs de ate 500 paginas sem memory overflow (processamento pagina a pagina, nao carregando tudo em memoria)
5. Deteccao de continuacao: identifica pages 2+ de um holerite (cabecalho vazio + tabela de verbas). Usa fuzzy matching (score >= 0.75) para template detection com OCR degradado
6. Testes com PDFs reais de referencia (pelo menos 1 texto selecionavel e 1 escaneado)

#### Story 1.3: Parser DDPE (Servidores Ativos)

Como usuario,
eu quero que o sistema extraia corretamente todos os dados de holerites do template DDPE,
para que eu possa processar holerites de servidores ativos do Estado de SP.

**Acceptance Criteria:**
1. Parser DDPE implementado que recebe o conteudo de uma pagina e retorna um objeto Holerite completo
2. Extrai campos do cabecalho: nome, CPF, cargo, tipo_folha, competencia (obrigatorios); outros campos opcionais
3. Extrai itens de linha com: codigo (XX.XXX), denominacao, natureza (N/A/R/D/E), valor
4. Extrai totais do rodape: total vencimentos, total descontos
5. Detecta versao do template (2020, 2024, etc.) e aplica coordenadas apropriadas (tolerancia ±15 pixels)
6. Template detector identifica pela presenca de "Departamento de Despesa" no cabecalho (fuzzy match >= 0.75)
7. Testes com 3+ holerites DDPE reais de diferentes versoes/servidores

#### Story 1.4: Parser SPPREV Aposentados

Como usuario,
eu quero que o sistema extraia corretamente todos os dados de holerites SPPREV de aposentados,
para que eu possa processar holerites de servidores aposentados.

**Acceptance Criteria:**
1. Parser SPPREV Aposentados implementado seguindo a interface base_parser
2. Extrai cabecalho especifico: nome, entidade, cargo, competencia, regime retribuicao, beneficio, percentual aposentadoria, CPF, numero beneficio, tipo folha, banco/agencia/conta, nivel
3. Extrai itens de linha com: codigo (formato XXXXXX sem ponto), denominacao, natureza, quantidade, unidade, periodo, e valores separados em colunas Vencimento e Descontos
4. Extrai totais do rodape: base IR, base redutor, base contrib prev, total vencimentos, total descontos, total liquido
5. Template detector identifica pela presenca de "DIRETORIA DE BENEFICIOS SERVIDORES" no cabecalho
6. Testes com holerites SPPREV aposentados reais

#### Story 1.5: Parser SPPREV Pensionistas

Como usuario,
eu quero que o sistema extraia corretamente dados de holerites SPPREV de pensionistas,
para que eu possa processar holerites de pensoes por morte.

**Acceptance Criteria:**
1. Parser SPPREV Pensionistas implementado seguindo a interface base_parser
2. Extrai cabecalho especifico: nome, CPF, cargo ex-servidor, beneficio, numero beneficio, dependentes IR, cota parte (%), banco/agencia, data pagamento, tipo folha, conta, competencia
3. Extrai as 2 secoes do corpo: (a) BASE DE CALCULO DO BENEFICIO com codigo, denominacao, total vencimentos/descontos, base calculo, (b) DEMONSTRATIVO DO PAGAMENTO com codigo, denominacao, periodo, vencimentos/descontos
4. Identifica creditos (-C) e debitos (-D) pelo sufixo na denominacao
5. Template detector identifica este template (SPPREV sem "DIRETORIA DE BENEFICIOS SERVIDORES" E com "COTA PARTE")
6. Testes com holerites SPPREV pensionistas reais

#### Story 1.6: Pipeline de Processamento em Lote

Como usuario,
eu quero importar um ou mais PDFs e obter todos os holerites processados, normalizados e ordenados cronologicamente,
para que eu tenha a visao completa dos dados de um servidor.

**Acceptance Criteria:**
1. Pipeline que recebe lista de PDFs e retorna lista unificada de Holerite objects
2. Cada pagina processada independentemente (detecta template → aplica parser)
3. Paginas de continuacao agrupadas no mesmo Holerite lógico (por CPF + competencia)
4. Holerites agrupados por CPF, ordenados por competencia
5. Verbas alocadas temporalmente (periodo + 1 mes)
6. Verbas com mesma alocacao e codigo mantidas separadas para formulas decompostas (ex: =1000-200-200)
7. Relatorio: total paginas, por template, com OCR, erros
8. CLI simples: `python -m holeritepro process --input pasta/ --output resultado.json`
9. Testes com 3+ PDFs reais

---

### Epic 2: Sistema de Teses e Exportacao XLSX

**Objetivo:** Implementar a camada de logica de negocios — o sistema modular de teses que transforma dados extraidos em planilhas de calculo. Cada tese e um modulo independente que define quais verbas buscar, como organizar os dados, e quais formulas aplicar. Ao final, o usuario executa via CLI: PDFs entram, planilha de calculo sai.

#### Story 2.1: Arquitetura de Teses (Plugin System)

Como desenvolvedor,
eu quero uma arquitetura de plugins para teses juridicas,
para que novas teses possam ser adicionadas sem modificar o core.

**Acceptance Criteria:**
1. Classe abstrata BaseTese definida com interface: verbas_de_interesse() → lista de codigos, mapear_colunas() → dict codigo→coluna, calcular_linha(dados_mes) → dict coluna→valor/formula, linhas_especiais() → config de 13o/ferias, validar_dados(holerites) → lista de avisos
2. Registry de teses que descobre automaticamente todas as teses disponiveis no diretorio teses/
3. Cada tese pode opcionalmente definir dados externos necessarios (ex: tabela salarial) via metodo dados_externos_requeridos()
4. Configuracao de equivalencia de verbas por tese (ex: 70.056 equivale a 70.113 a partir de 2020)
5. Integracao com o registro de verbas (FR-20): BaseTese consulta o registro para resolver aliases e classificacoes
6. Testes unitarios para registry e interface abstrata

#### Story 2.1a: Registro de Aprendizado de Verbas

Como advogado,
eu quero que o sistema lembre das classificacoes de verbas que eu ja revisei,
para que eu nao precise reclassificar as mesmas verbas em cada novo calculo.

**Acceptance Criteria:**
1. Modelo VerbaRegistrada com: id_logico (identificador unico da verba logica), codigos_conhecidos (lista de codigos que representam esta verba, ex: [70.006, 070006]), denominacoes_conhecidas (lista de nomes, ex: ["IAMSPE", "IAMSPE - LEI 17.293/2020"]), natureza_juridica (PERMANENTE, TEMPORARIA, INCORPORADA, NAO_CLASSIFICADA), qualificadores (lista: ["Art.133", "VPNI"], se aplicavel), teses_vinculadas (quais teses usam esta verba)
2. Armazenamento em arquivo JSON no diretorio data/verba_registry.json, persistido entre sessoes
3. Funcao de busca: dado um codigo e/ou denominacao, retorna a VerbaRegistrada correspondente (ou None se desconhecida). Busca por codigo exato, por codigo normalizado, e por similaridade de denominacao
4. Funcao de registro: usuario confirma/corrige classificacao na revisao → sistema salva no registry. Inclui campo "confirmado_por_humano: true/false"
5. Deteccao automatica de qualificadores na denominacao: padroes "ART.133", "ART. 133", "VPNI", "PRO-LABORE", "INCORPORAD" → sugere classificacao automatica (natureza = INCORPORADA). Classificacao automatica tem confirmado_por_humano = false
6. Funcao de alias: quando usuario identifica que duas verbas com codigos/nomes diferentes sao a mesma verba logica, cria alias no registry. Ex: "GRAT. ATIVIDADES ESPECIAIS" (cod 04.108) = "VPNI - GRAT. ATIVIDADES ESPECIAIS" (cod 04.250)
7. Verbas NAO presentes no registry sao retornadas como NAO_CLASSIFICADA e marcadas para revisao obrigatoria na tela de revisao
8. Testes unitarios para busca, registro, alias e deteccao de qualificadores

#### Story 2.2: Modulo Tese IAMSPE

Como advogado,
eu quero que o sistema gere automaticamente a planilha de calculo da tese IAMSPE,
para que eu nao precise digitar manualmente os valores de cada verba IAMSPE de cada holerite.

**Acceptance Criteria:**
1. Modulo IAMSPE implementado seguindo BaseTese
2. Verbas de interesse: 70.006, 70.007, 70.037, 70.119, 70.120, 70.121, 70.122, 70.123, 70.124, 70.125 (e equivalentes SPPREV: 070006, etc.)
3. Mapeamento de colunas: A=data, B-K=verbas IAMSPE (uma coluna por codigo), L=valor devido
4. Formula da coluna L: SUM(B:K) por linha
5. Total bruto: SUM vertical da coluna L
6. Trata verbas de 13o salario e ferias adequadamente (linhas separadas ou soma no mes)
7. Testes com dados extraidos dos PDFs de referencia, comparando com planilha-modelo existente

#### Story 2.3: Modulo Tese Diferenca de Classe

Como advogado,
eu quero que o sistema gere a planilha de Diferenca de Classe para policiais civis,
para que eu automatize o calculo mais complexo do escritorio.

**Acceptance Criteria:**
1. Modulo implementado seguindo BaseTese, declarando necessidade de tabela salarial externa
2. Verbas de interesse: 01.001 (salario base), 09.001 (quinquenio — extrai QTD), 10.001 (sexta-parte — detecta presenca)
3. Mapeamento: A=mes, B=classe delegacia (externo), C=classe cargo, D=salario delegacia (externo), E=salario base requerente, F-N=calculados
4. Formulas: F=D-E, G=F, H=F+G, J=I*5%, K=H*J, M=IF(L="Sim",(H+K)/6,0), N=H+K+M
5. Linhas especiais a cada 12 meses: 13o proporcional (SUM/12) e 1/3 ferias (13o/3)
6. Total final: SUM vertical da coluna N
7. Modulo aceita tabela salarial como input externo e faz lookup classe→salario por periodo
8. Testes com dados de referencia

#### Story 2.4: Modulo Tese Quinquenio e Sexta-Parte

Como advogado,
eu quero que o sistema gere a planilha de Quinquenio e Sexta-Parte,
para que eu automatize o recalculo de adicionais temporais.

**Acceptance Criteria:**
1. Modulo implementado seguindo BaseTese
2. Verbas de interesse configuraveis (default: Piso Salarial, Insalubridade, ALE, Art.133, AOL, GAP, GDAP — mas cada tese pode customizar a lista)
3. Mapeamento: A=data, B-H=verbas integrais, I=total vantagens, J=qtde quinquenios, K=porcentagem, L=diferenca quinquenios, M=tem 6a parte?, N=diferenca 6a parte, O=total devido
4. Formulas: I=SUM(B:H), K=J*5%, L=I*K, N=IF(M="Sim",(B+D+E+F+G+H+L)/6,0), O=L+N
5. Nota: coluna C (insalubridade) NAO entra no calculo da 6a parte (conforme planilha-modelo)
6. Linha especial a cada 12 meses: 13o salario proporcional (SUM/12)
7. Total bruto: SUM vertical da coluna O
8. Testes com dados de referencia

#### Story 2.5: Exportador XLSX com Formulas

Como advogado,
eu quero que a planilha exportada contenha formulas ativas do Excel,
para que eu possa auditar, ajustar valores e confiar no calculo.

**Acceptance Criteria:**
1. Exportador XLSX implementado usando openpyxl que recebe dados processados + definicao da tese e gera arquivo .xlsx
2. Cabecalho da planilha inclui: nome do requerente, CPF, tese, periodo coberto
3. Formulas sao inseridas como formulas do Excel (nao valores calculados) — ex: "=SUM(B4:K4)" na celula L4. Quando uma celula tem multiplos lancamentos para a mesma verba/periodo (ex: valor normal + reposicoes), a celula recebe formula decomposta preservando cada componente (ex: "=1000-200-200"), NAO o valor somado. Isso e obrigatorio para auditabilidade pelo setor de liquidacao que confere lancamento por lancamento
4. Formatacao: cabecalhos em negrito, colunas de valor com formato monetario brasileiro (R$ #.##0,00), datas formatadas
5. Linhas especiais (13o, ferias) sao inseridas automaticamente nos intervalos corretos
6. Linha de total no final com SUM vertical
7. O arquivo gerado abre corretamente no Excel e as formulas funcionam
8. Testes comparando estrutura do XLSX gerado com planilhas-modelo de referencia

#### Story 2.6: Gerenciador de Tabelas Externas

Como usuario,
eu quero importar e gerenciar tabelas salariais que sao usadas por teses como Diferenca de Classe,
para que o calculo use os valores corretos de cada periodo.

**Acceptance Criteria:**
1. Modulo tabela_manager que permite: importar tabela de XLSX/CSV, listar tabelas disponiveis, consultar valor por (classe, periodo)
2. Tabela armazenada em formato JSON no diretorio data/tabelas_salariais/
3. Suporta versionamento temporal: mesma classe pode ter valores diferentes por periodo (quando o Estado atualiza a tabela)
4. Funcao de lookup: dado uma classe e uma data, retorna o salario vigente naquele periodo
5. Testes unitarios para CRUD e lookup temporal

#### Story 2.7: Pipeline Completo CLI (Extracao → Calculo → Planilha)

Como advogado,
eu quero executar um comando que receba PDFs e uma tese e produza a planilha final,
para que eu valide o fluxo completo antes da interface grafica.

**Acceptance Criteria:**
1. Comando CLI: `python -m holeritepro generate --tese iamspe --input pasta_pdfs/ --output planilha.xlsx`
2. Pipeline: le PDFs → detecta templates → extrai dados → normaliza → aloca temporalmente → filtra periodo → aplica modulo da tese → exporta XLSX novo
3. Periodo padrao: ultimos 5 anos a partir da data atual. Parametro opcional: `--periodo-inicio 2019-01 --periodo-fim 2026-02` para exceções
4. Para teses que requerem dados externos: `--tabela tabela_salarial.xlsx --classe-delegacia "Classe Especial"`
4. Relatorio de execucao impresso no terminal: arquivos processados, paginas por template, verbas extraidas, avisos
5. Tratamento de erros robusto: paginas que falharam sao logadas mas nao interrompem o processamento
6. Teste end-to-end com PDFs de referencia, comparando planilha gerada com planilha-modelo

---

### Epic 3: Interface Desktop e Experiencia do Usuario

**Objetivo:** Construir a interface grafica que torna o sistema acessivel a estagiarios e advogados sem conhecimento tecnico. O wizard de 4 etapas guia o usuario do PDF a planilha. Ao final, o sistema e empacotado como .exe standalone distribuivel.

#### Story 3.1: Janela Principal e Navegacao por Wizard

Como usuario,
eu quero uma interface desktop com navegacao clara por etapas,
para que eu saiba exatamente onde estou no processo e o que fazer em seguida.

**Acceptance Criteria:**
1. Janela principal PyQt6 com barra de progresso do wizard (4 etapas) no topo
2. Navegacao entre etapas com botoes "Proximo" e "Voltar"
3. Etapas: 1-Selecionar Tese, 2-Importar PDFs, 3-Revisar Dados, 4-Exportar
4. Cada etapa so habilita avancar quando os dados obrigatorios estao preenchidos
5. Estilo visual limpo e profissional (paleta azul escuro / cinza / branco)
6. Icone da aplicacao e titulo "HoleritePRO"

#### Story 3.2: Tela de Selecao de Tese

Como usuario,
eu quero selecionar a tese juridica antes de importar os PDFs,
para que o sistema saiba quais dados extrair e como montar a planilha.

**Acceptance Criteria:**
1. Cards visuais para cada tese disponivel com: nome, descricao curta, icone
2. Card selecionado com destaque visual
3. As teses sao carregadas automaticamente do registry de plugins
4. Se a tese requer dados externos (ex: tabela salarial), informa o usuario antecipadamente
5. Seletor de periodo com default de 5 anos retroativos (ex: mar/2021 a fev/2026), editavel para exceções
6. Botao "Proximo" habilitado somente apos selecionar uma tese

#### Story 3.3: Tela de Importacao de PDFs

Como usuario,
eu quero arrastar PDFs para a aplicacao e ver o progresso do processamento,
para que eu saiba que o sistema esta trabalhando e quais arquivos foram processados com sucesso.

**Acceptance Criteria:**
1. Area de drag-and-drop grande e visivel + botao "Selecionar Arquivos" alternativo
2. Lista de arquivos importados com: nome, tamanho, numero de paginas, status (processando/concluido/erro)
3. Barra de progresso por arquivo e progresso geral
4. Processamento em thread separada (UI nao trava)
5. Ao concluir, exibe resumo: X holerites extraidos de Y paginas, Z paginas com OCR, W erros
6. Permite remover arquivos e adicionar mais antes de avancar

#### Story 3.4: Tela de Revisao de Dados (Simplificada)

Como usuario,
eu quero revisar e corrigir os dados extraidos antes de gerar a planilha,
para que eu tenha confianca na precisao do resultado.

**Acceptance Criteria:**
1. Tabela: Mês | Verbas (colunas da tese) | Status visual
2. Duplo-clique em celula = edit inline (input simples)
3. Status visual: 🟡 amarelo = tem alerta (atrasado/OCR baixo); ✅ verde = ok
4. Botao "Recalcular" atualiza campos calculados apos edicoes
5. Se tese requer dados externos (tabela salarial), campo para importar
6. Abaixo da tabela: seção "Verbas Desconhecidas (N)"
   - Lista simples: Código | Denominação | [Dropdown: PERMANENTE/TEMPORÁRIA/INCORPORADA] | [✅ Confirmar]
   - Verbas NAO_CLASSIFICADA bloqueiam exportacao
7. Classificacao salva em verba_registry.json (entre sessoes)
8. Botao "Exportar" (habilitado somente quando todas as verbas classificadas)
9. Suporte a "Criar Alias" (simples: [Código A] = [Código B] → salva no registry)

#### Story 3.5: Tela de Exportacao e Preview

Como usuario,
eu quero ver um resumo antes de exportar e escolher onde salvar a planilha,
para que eu tenha controle sobre o resultado final.

**Acceptance Criteria:**
1. Resumo antes de exportar: nome do requerente, tese, periodo coberto, total de meses, valor total calculado
2. Botao "Escolher Local" com dialogo de salvamento padrao do Windows
3. Nome sugerido: "PLANILHA DE CALCULO - {TESE} - {NOME_REQUERENTE}.xlsx"
4. Barra de progresso durante exportacao
5. Ao concluir: mensagem de sucesso com botao "Abrir Pasta" e botao "Novo Calculo" (volta a etapa 1)

#### Story 3.6: Packaging como .exe Standalone

Como usuario,
eu quero instalar o HoleritePRO como um programa normal do Windows,
para que eu nao precise instalar Python ou dependencias.

**Acceptance Criteria:**
1. Build com PyInstaller gerando .exe unico ou pasta dist/ para Windows
2. Tesseract OCR embutido no pacote (nao requer instalacao separada)
3. Tamanho do pacote final <= 200MB
4. Icone personalizado no .exe
5. Testado em Windows 10 e 11 em maquina sem Python instalado
6. Inclui arquivo README com instrucoes basicas de uso

---

## 7. Checklist Results Report

*Pendente — sera executado apos aprovacao do PRD.*

---

## 8. Next Steps

### 8.1 Architect Prompt

> @architect — Analise o PRD do HoleritePRO em `docs/prd/prd.md`. O projeto e uma aplicacao desktop Python que extrai dados de holerites (PDF) do Governo de SP e exporta para planilhas XLSX de calculo juridico. Foque em: (1) arquitetura do sistema de parsers por coordenadas/regioes do PDF, (2) design do plugin system de teses, (3) estrategia de deteccao hibrida texto/OCR por pagina, (4) modelo de dados e regras de alocacao temporal. Os PDFs de referencia estao em `docs/referencias/`.

### 8.2 UX Expert Prompt

> @ux-design-expert — Analise o PRD do HoleritePRO em `docs/prd/prd.md`, secao 3 (UI Design Goals). O publico-alvo sao estagiarios de direito sem conhecimento tecnico. Projete o wizard de 4 etapas para desktop Windows (PyQt6). Foco em: usabilidade extrema, fluxo guiado, e a tela de revisao de dados (a mais complexa). Os holerites de referencia estao em `docs/referencias/`.
