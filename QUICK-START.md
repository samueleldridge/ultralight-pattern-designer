# AI Analytics Platform - Quick Start Guide

**Status:** Ready for setup | **Time to test:** 15 minutes

---

## What You Need Before Starting

1. **Kimi K2.5 API Key** — Get from https://platform.moonshot.cn/
2. **Supabase Account** — Free tier at https://supabase.com
3. **Docker Desktop** — Already installed on your Mac

---

## 3-Step Setup

### Step 1: Configure Environment (2 minutes)

```bash
cd ai-analytics-platform/backend

# Copy the environment template
cp .env.example .env

# Edit .env and paste your Kimi API key
# Replace: KIMI_API_KEY=your-key-here
# With:    KIMI_API_KEY=sk-your-actual-key
```

**Security note:** `.env` is in `.gitignore` and will never be committed.

### Step 2: Start Services (2 minutes)

```bash
# Start everything (Postgres, Redis, Backend, Frontend)
docker-compose up --build

# Wait for "Application startup complete" message
```

### Step 3: Test (10 minutes)

1. Open http://localhost:3000
2. Type: "What was revenue last month?"
3. Watch the streaming response
4. Add results to dashboard
5. Explore suggestions panel

---

## What's Already Configured

✅ **Kimi K2.5 Integration** — Primary model configured  
✅ **Demo Database** — 38 orders, 10 customers, 10 products  
✅ **Security** — API keys in .env, read-only SQL enforced  
✅ **Streaming** — Real-time agent step visualization  
✅ **Evaluation** — Accuracy testing framework ready  

---

## Troubleshooting

**If backend won't start:**
```bash
# Check logs
docker-compose logs backend

# Common fix: reset database
docker-compose down -v
docker-compose up -d postgres
sleep 10
docker-compose up backend
```

**If frontend shows errors:**
```bash
# Rebuild frontend
cd frontend && npm install && cd ..
docker-compose up --build frontend
```

**If Kimi API errors:**
- Verify API key in `backend/.env`
- Check key has credits at https://platform.moonshot.cn/
- Try: `curl -H "Authorization: Bearer YOUR_KEY" https://api.moonshot.cn/v1/models`

---

## Next Steps After Testing

### Deploy to Production (Optional)

1. **Create Supabase Project**
   - Go to https://app.supabase.com
   - New project → Copy connection string
   - Update `DATABASE_URL` in .env

2. **Deploy Backend**
   - AWS ECS, Railway, or Fly.io
   - Use Docker image
   - Set environment variables

3. **Deploy Frontend**
   - Vercel or Netlify
   - Connect GitHub repo
   - Set `NEXT_PUBLIC_API_URL`

### Get First Customer

1. Use research in `London-Market-Outreach-Plan.md`
2. Send LinkedIn messages using templates
3. Offer free pilot for feedback

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/.env` | API keys, database URLs |
| `docker-compose.yml` | Service orchestration |
| `PROACTIVE-FRAMEWORK.md` | Business strategy |
| `EVALUATION.md` | Testing your accuracy |
| `STREAMING.md` | How frontend-backend comm works |

---

## Support

**Questions?** Check these docs:
- `STATUS.md` — What's built
- `ARCHITECTURE.md` — System design
- `BUILD-SUMMARY.md` — Complete feature list

**Need help?** Message me with:
- Error logs
- What you were trying to do
- Expected vs actual behavior

---

**Ready to go! Just add your Kimi API key and run `docker-compose up`.**
