# AI Analytics Platform — MVP

**Status:** Ready for testing  
**Time to run:** ~2 minutes

---

## Quick Start (3 Steps)

### 1. Set Up Environment

```bash
cd ai-analytics-platform
cp .env.mvp .env
# Edit .env and add your OPENAI_API_KEY
```

Get your API key: https://platform.openai.com/api-keys

### 2. Start Everything

```bash
docker-compose up --build
```

This starts:
- PostgreSQL with pgvector (database + demo data)
- Redis (caching)
- Backend API (FastAPI + LangGraph)
- Frontend (Next.js)

### 3. Test It

**Web UI:** http://localhost:3000

Try asking:
- "What was revenue last month?"
- "Show me top selling products"
- "Which customers spent the most?"

**API Docs:** http://localhost:8000/docs

---

## Demo Data Included

The MVP comes with synthetic e-commerce data:

- **10 customers** (premium/standard segments)
- **10 products** (Electronics, Furniture, Office Supplies)
- **38 orders** (Jan-June 2024, realistic patterns)
- **Views:** revenue_by_month, top_products, customer_summary

---

## Test the API

```bash
# Start a query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was total revenue by month?",
    "tenant_id": "demo",
    "user_id": "demo-user"
  }'

# Stream results (replace WORKFLOW_ID)
curl http://localhost:8000/api/stream/WORKFLOW_ID
```

Or run the test script:
```bash
python test_integration.py
```

---

## What Works

✅ Natural language → SQL (via GPT-4)  
✅ Real SQL execution on demo database  
✅ Streaming agent steps (SSE)  
✅ Auto chart type detection (line/bar/table)  
✅ Chat interface with streaming  
✅ Suggestions panel  

## What's Stubbed

⚠️ Authentication (Clerk not fully wired)  
⚠️ View persistence (no save to dashboard yet)  
⚠️ User profiles (pattern detection not active)  
⚠️ Proactive insights (anomaly detection not running)  

---

## Project Structure

```
ai-analytics-platform/
├── backend/
│   └── app/
│       ├── agent/          # LangGraph workflow (8 nodes)
│       │   ├── nodes/      # classify, generate, validate, execute, etc.
│       │   ├── state.py    # Agent state management
│       │   └── workflow.py # Graph composition
│       ├── api/            # REST endpoints
│       └── models.py       # Database models
├── frontend/
│   ├── app/                # Next.js pages
│   └── components/
│       ├── chat/           # ChatPanel (streaming UI)
│       ├── dashboard/      # DashboardCanvas
│       └── suggestions/    # SuggestionsPanel
├── docker-compose.yml      # Full stack
├── demo-data.sql           # Synthetic dataset
└── test_integration.py     # API tests
```

---

## Troubleshooting

### "No module named 'app'"
Make sure you're running from the `backend` directory or using Docker.

### "Connection refused" to database
Wait 10 seconds after `docker-compose up` for Postgres to initialize.

### OpenAI errors
Check your API key in `.env`. Needs GPT-4 access.

### Frontend can't connect
Make sure backend is on port 8000. Check `next.config.js` rewrites.

---

## Architecture

**Agent Flow:**
```
User Query → Classify Intent → Fetch Context → Generate SQL
                                          ↓
User ← Results ← Visualize ← Analyze ← Execute ← Validate
```

**Key Tech:**
- FastAPI + LangGraph (agentic workflows)
- PostgreSQL + pgvector (data + semantic search)
- OpenAI GPT-4 (NL→SQL)
- SSE streaming (real-time updates)

---

## Next Steps

1. **Test the flow** — Ask questions, see SQL, verify results
2. **Add persistence** — Save views to dashboard (Week 2 task)
3. **Add auth** — Wire up Clerk for real users
4. **Customer calls** — Get feedback on the experience

---

**Questions?** Check the full docs:
- `BUILD-COMPLETE.md` — What was built
- `QUICKSTART.md` — Detailed run instructions
- `Master-Build-Plan.md` — 4-week roadmap

---

**Ready to go?**

```bash
docker-compose up
```

Then open http://localhost:3000 and ask your first question.
