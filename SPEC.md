# SPEC: Leilão Scraper Agent

## 1. Conceito & Visão

Agente autônomo que, dado uma URL de um site de leiloeiro, navega, extrai todos os leilões disponíveis e salva o resultado como um arquivo Markdown bem formatado. Feito para pesquisadores, investidores e curiosos que querem compilar informações de leilões sem copiar-e-colar manualmente.

**Stack:** LangGraph + Crawl4AI + LangChain. O agente usa um grafo de estados para orchestrar crawl → parse → agregação → exportação.

## 2. Design do Agente (LangGraph)

### Grafo de Estados

```
State = {
  "url": str,
  "auctions": List[Auction],
  "markdown": str,
  "status": "idle" | "crawling" | "parsing" | "done" | "error",
  "error": str | None,
  "metadata": dict
}

Auction = {
  "title": str,
  "date": str | None,
  "location": str | None,
  "description": str,
  "url": str,
  "price": str | None,
  "images": List[str],
  "raw_data": dict
}
```

### Nós do Grafo

| Nó | Responsabilidade |
|----|-----------------|
| `start_node` | Valida URL, detecta tipo de site |
| `crawl_node` | Usa Crawl4AI para buscar HTML com JS rendering |
| `parse_node` | Extrai Auction records do HTML (LLM + regex fallback) |
| `aggregate_node` | Dedupe e consolida resultados |
| `render_node` | Converte lista de Auction → Markdown |
| `save_node` | Salva arquivo `.md` no disco |
| `error_node` | Captura falhas e tenta retry (1x) |

### Arestas

```
start → crawl (valid URL)
crawl → parse (HTML received)
parse → aggregate (auctions extracted)
aggregate → render (data cleaned)
render → save → end
any_error → error_node → retry? → crawl OR end
```

## 3. Funcionalidades

### 3.1 Input
- Aceita URL via CLI: `python -m agent.main https://example.com/leiloes`
- Parâmetros opcionais: `--output <path.md>` e `--max-pages <N>`

### 3.2 Crawl (Crawl4AI)
- Renderiza páginas SPA (JavaScript-heavy)
- Suporta paginação automática (próxima página via seletor CSS)
- Extrai metadata: título da página, data do leilão, localização
- Rate limiting respeitoso (1 req/s por padrão)
- User-Agent customizável

### 3.3 Parse (LangChain + LLM)
- Usa LLM (Gemini ou OpenAI) para extrair Auction records do HTML
- Fallback: regex + BeautifulSoup para campos conhecidos
- Schema de validação com Pydantic
- Detecta automaticamente se é página de lista ou detalhe individual

### 3.4 Output
- Arquivo `.md` com frontmatter YAML:
```markdown
---
url: https://example.com/leiloes
scraped_at: 2025-05-23T10:00:00Z
total_auctions: 42
source: Example Leiloeiro
---

# Leilões — Example Leiloeiro

## 1. Casa à Vista em Pinheiros
- **Data:** 15/06/2025
- **Local:** São Paulo, SP
- **Valor:** R$ 850.000,00
- **Descrição:** Imóvel de 3 dormitórios, 120m²...
- **Link:** https://example.com/leilao/123
```
- Nomenclatura: `{domain}-{date}.md` (ex: `example-2025-05-23.md`)

### 3.5 Erro e Retry
- Retry automático 1x em caso de falha de rede
- Erro final com mensagem clara e stack trace

## 4. Arquitetura de Diretórios

```
leilao-scraper/
├── agent/
│   ├── __init__.py
│   ├── state.py          # LangGraph State
│   ├── nodes.py          # Nós do grafo
│   ├── graph.py          # Compilação do grafo
│   └── models.py         # Pydantic models (Auction)
├── crawlers/
│   ├── __init__.py
│   └── base.py           # Crawl4AI wrapper
├── parsers/
│   ├── __init__.py
│   ├── llm_parser.py     # LLM-based extraction
│   └── fallback.py       # Regex/BS4 fallback
├── renderers/
│   ├── __init__.py
│   └── markdown.py       # Auction → Markdown
├── cli.py                # Click/Typer CLI
├── config.py             # Settings (env vars)
├── requirements.txt
├── .env.example
├── README.md
└── SPEC.md
```

## 5. Configuração (Environment Variables)

| Var | Default | Descrição |
|-----|---------|-----------|
| `LLM_PROVIDER` | `gemini` | `gemini` ou `openai` |
| `GEMINI_API_KEY` | — | API key do Gemini |
| `OPENAI_API_KEY` | — | API key da OpenAI |
| `CRAWL_DELAY` | `1.0` | Delay entre requests (segundos) |
| `MAX_PAGES` | `10` | Máximo de páginas por crawl |
| `OUTPUT_DIR` | `./output` | Diretório de saída dos `.md` |
| `USER_AGENT` | Custom | User-Agent customizado |

## 6. Fluxo de Execução (CLI)

```bash
# Instalar dependências
pip install -r requirements.txt

# Copiar e configurar env
cp .env.example .env
# editar .env com suas API keys

# Executar
python -m agent.main https://www.example.com/leiloes
python -m agent.main https://www.example.com/leiloes --output meus_leiloes.md
python -m agent.main https://www.example.com/leiloes --max-pages 5
```

## 7. Critérios de Aceitação

- [ ] Agente aceita URL e retorna arquivo `.md` com todos os leilões encontrados
- [ ] Renderiza páginas SPA via Crawl4AI
- [ ] Extrai no mínimo: título, data, localização, link, descrição
- [ ] Formata saída como Markdown com frontmatter YAML
- [ ] Lida com paginação (mais de uma página de resultados)
- [ ] Retry em caso de falha de rede
- [ ] CLI com `--help` funcional
- [ ] Arquivos salvos em `OUTPUT_DIR` com nomenclatura correta
- [ ] README.md com instruções de uso

## 8. Prazo / Prioridade

**MVP:** items marcados com [ ] no Critérios de Aceitação
**Nice-to-have (v2):** suporte a múltiplos sites, filtros por data/valor, exportação JSON/CSV