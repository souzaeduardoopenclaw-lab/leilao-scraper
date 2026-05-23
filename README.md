# Leilao Scraper Agent

Autonomous agent that, given a URL from an auction website, navigates, extracts all available auctions, and saves the result as a well-formatted Markdown file. Built for researchers, investors, and curious people who want to compile auction information without manual copy-pasting.

**Stack:** LangGraph + Crawl4AI + LangChain

## Features

- 🌐 Renders SPA (JavaScript-heavy) pages via Crawl4AI
- 🤖 LLM-powered extraction (Gemini or OpenAI) with BeautifulSoup fallback
- 📄 Outputs Markdown with YAML frontmatter
- 🔄 Automatic retry on network failures
- 📑 Pagination support
- ⚙️ Fully configurable via environment variables

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd leilao-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `GEMINI_API_KEY` | — | Gemini API key |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `CRAWL_DELAY` | `1.0` | Delay between requests (seconds) |
| `MAX_PAGES` | `10` | Maximum pages per crawl |
| `OUTPUT_DIR` | `./output` | Output directory for `.md` files |
| `USER_AGENT` | Custom | Custom User-Agent string |

## Usage

```bash
# Basic usage
python -m cli https://www.example.com/leiloes

# With options
python -m cli https://www.example.com/leiloes --output my_auctions.md
python -m cli https://www.example.com/leiloes --max-pages 5
python -m cli https://www.example.com/leiloes --next-selector ".next-page" --verbose

# Or run directly
python cli.py <url> [options]
```

## Output Format

```markdown
---
url: https://example.com/leiloes
scraped_at: 2025-05-23T10:00:00Z
total_auctions: 42
source: example.com
---

# Leilões — example.com

## 1. Casa à Vista em Pinheiros
- **Data:** 15/06/2025
- **Local:** São Paulo, SP
- **Valor:** R$ 850.000,00
- **Descrição:** Imóvel de 3 dormitórios, 120m²...
- **Link:** https://example.com/leilao/123
- **Imagens:** 3 imagem(ns)

...
```

## Project Structure

```
leilao-scraper/
├── agent/
│   ├── __init__.py
│   ├── state.py          # LangGraph State
│   ├── nodes.py          # Graph nodes
│   ├── graph.py          # Graph compilation
│   └── models.py         # Pydantic models
├── crawlers/
│   ├── __init__.py
│   └── base.py           # Crawl4AI wrapper
├── parsers/
│   ├── __init__.py
│   ├── llm_parser.py     # LLM extraction
│   └── fallback.py       # BS4/regex fallback
├── renderers/
│   ├── __init__.py
│   └── markdown.py       # Auction → Markdown
├── cli.py                # Click CLI
├── config.py             # Settings
├── requirements.txt
├── .env.example
├── README.md
└── SPEC.md
```

## License

MIT