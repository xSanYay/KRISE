# Krise Engine — Architecture

## What is Krise?

Krise is a **multi-agent AI commerce engine** that recommends products based on what you want to *achieve*, not what product you want. Instead of keyword search, you describe your goal ("I need a rugged phone for my dad under 25k"), and Krise:

1. Extracts your intent (use case, budget, constraints)
2. Asks clarification questions to fill gaps
3. Scrapes Amazon/Flipkart for real products
4. Scores and ranks them with sentiment analysis
5. Presents a swipe deck — swipe right to shortlist, left to skip

---

## Tech Stack

| Layer      | Technology                |
|------------|---------------------------|
| Frontend   | Vue 3, TypeScript, Vite   |
| Backend    | Python 3.12, FastAPI      |
| LLM        | AWS Bedrock (Amazon Nova) |
| Scraping   | httpx + BeautifulSoup     |
| Web Search | DuckDuckGo Search API     |
| State      | In-memory (dict)          |

---

## Project Structure

```
KRISE/
├── start.sh                  # Starts both backend + frontend
├── ARCHITECTURE.md           # This file
├── design.md                 # Original design spec
├── requirements.md           # Feature requirements
│
├── backend/
│   ├── requirements.txt
│   ├── .env                  # AWS keys, model config
│   └── app/
│       ├── main.py           # FastAPI app, lifespan, CORS
│       ├── config.py         # Settings (env vars, thresholds)
│       │
│       ├── agents/           # Multi-agent system
│       │   ├── orchestrator.py   # Central coordinator
│       │   ├── intent_mapper.py  # LLM-based intent extraction
│       │   ├── socratic.py       # Clarification question generator
│       │   └── scraper.py        # Product search coordinator
│       │
│       ├── llm/              # LLM providers
│       │   ├── base.py           # Abstract interface
│       │   ├── bedrock.py        # AWS Bedrock (Converse API)
│       │   ├── anthropic.py      # Direct Anthropic API
│       │   ├── gemini.py         # Google Gemini
│       │   └── prompts.py        # All prompt templates
│       │
│       ├── scraping/         # Product data fetching
│       │   ├── browser.py        # Playwright browser pool
│       │   ├── amazon.py         # Amazon India scraper
│       │   ├── flipkart.py       # Flipkart scraper
│       │   └── base.py           # Scraper interface
│       │
│       ├── scoring/          # Product ranking
│       │   └── engine.py         # Multi-factor scoring
│       │
│       ├── websearch/        # Review aggregation
│       │   └── search.py         # DuckDuckGo wrapper
│       │
│       ├── models/           # Pydantic data models
│       │   ├── session.py        # Session, phases, messages
│       │   ├── intent.py         # IntentProfile, constraints
│       │   ├── product.py        # Product, PriceInfo, Score
│       │   └── api.py            # Request/response schemas
│       │
│       ├── storage/          # Persistence
│       │   └── memory.py         # In-memory session store
│       │
│       └── api/              # HTTP layer
│           ├── routes.py         # REST endpoints
│           └── websocket.py      # WebSocket handler
│
└── frontend/
    ├── index.html
    ├── vite.config.ts        # Dev server + API proxy
    └── src/
        ├── main.ts           # Vue app entry
        ├── App.vue           # Root component + router
        ├── style.css         # Global styles + design tokens
        ├── lib/
        │   └── api.ts        # Backend API client
        ├── stores/
        │   └── session.ts    # Pinia store (state management)
        ├── views/
        │   ├── HomeView.vue      # Landing page
        │   └── SessionView.vue   # Chat + product deck
        └── components/
            ├── chat/
            │   ├── ChatMessage.vue
            │   └── ChatInput.vue
            ├── products/
            │   ├── ProductCard.vue
            │   └── SwipeDeck.vue
            └── layout/
                └── AppHeader.vue
```

---

## Data Flow

```
User types message
     │
     ▼
Frontend (SessionView.vue)
     │  POST /api/v1/sessions/{id}/message
     ▼
Orchestrator.process_message()
     │
     ├─► IntentMapperAgent.extract_intent()    ← LLM call
     │       Extracts: use case, category, budget, requirements
     │
     ├─► SocraticFrictionAgent.update_conviction()  ← LLM call
     │       Scores conviction 0.0 → 1.0
     │
     ├─ if conviction < 0.8 ─►  generate_question()  ← LLM call
     │       Returns clarification question to user
     │
     └─ if conviction >= 0.8 ─► _fetch_and_score_products()
              │
              ├─► ScraperAgent.fetch_products()
              │       ├─► LLM generates search queries
              │       ├─► AmazonScraper.search()     ← HTTP scrape
              │       ├─► FlipkartScraper.search()    ← HTTP scrape
              │       └─► WebSearcher.search_reviews() ← DuckDuckGo
              │
              └─► ScoringEngine.rank_products()
                      ├─► Technical match score
                      ├─► Sentiment score
                      ├─► Value-for-money score
                      └─► Availability score
                              │
                              ▼
                      Sorted ProductScore[]
                              │
                              ▼
                      Frontend SwipeDeck
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/v1/health` | Health check |
| POST   | `/api/v1/sessions` | Create new session |
| POST   | `/api/v1/sessions/{id}/message` | Send chat message |
| GET    | `/api/v1/sessions/{id}/profile` | Get intent profile |
| POST   | `/api/v1/sessions/{id}/swipe` | Swipe product |
| GET    | `/api/v1/sessions/{id}/products` | Get product deck |
| GET    | `/api/v1/sessions/{id}/progress` | SSE progress stream |

---

## Scoring Algorithm

Each product gets a **total score (0-100)** from 4 weighted factors:

| Factor | Default Weight | What it measures |
|--------|---------------|-------------------|
| Technical Match | 40% | How well specs match requirements |
| Sentiment | 30% | Reddit/YouTube review sentiment |
| Value for Money | 20% | Price vs budget ratio |
| Availability | 10% | In-stock status |

Weights are dynamically adjusted based on swipe feedback:
- Swipe left "too expensive" → increases VFM weight
- Swipe left "poor reviews" → increases sentiment weight
- Swipe right → boosts that brand's score

---

## Session Phases

```
INTENT_MAPPING → SOCRATIC_FRICTION → FETCHING_PRODUCTS → PRODUCT_RECOMMENDATION
```

The orchestrator transitions between phases automatically based on conviction score thresholds.

---

## Running

```bash
# First time setup
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # Add your AWS Bedrock keys

# Start both servers
cd /path/to/KRISE && bash start.sh
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```
