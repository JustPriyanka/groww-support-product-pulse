# Deployment Plan

Backend → Railway · Frontend → Vercel (same split as the Zomato project). Deployed from GitHub
(`JustPriyanka/groww-support-product-pulse`) through each platform's GitHub integration.

---

## Architecture

```
Browser ─▶ Vercel (React, static)  ──HTTPS JSON──▶  Railway (FastAPI, 1 worker)
              │ in-browser Whisper (audio stays on device)      │  ├─ APScheduler weekly cron (Mon 09:00 IST)
              │                                                 │  ├─ stdio MCP workspace server (subprocess)
                                                                │  └─ SQLite on Railway volume /data
                                                                ▼
                                                      Groq (gpt-oss-120b / gpt-oss-20b)
```

### What changed versus the Zomato deployment, and why

| Concern | Zomato | This project |
|---|---|---|
| State | Stateless (dataset cache) | **Railway volume at `/data`** — approvals, drafts, canonical explainers and the MCP workspace must survive redeploys |
| Workers | default | **exactly 1 worker** — the in-process scheduler must fire once per week |
| Scheduled work | none | APScheduler cron + manual `POST /api/pulse/run` |
| Builder | Nixpacks, `pip install` into Nix Python | Nixpacks pinned in `railway.json`; deps installed into `/opt/venv` because Nix Python is read-only (PEP 668 — the first deploy failed with `externally-managed-environment`) |
| Secrets | `GROQ_API_KEY` | + `APPROVAL_SECRET` (HMAC for approval tokens) |
| Health check | `/api/health` | `/api/health` (corpus/reviews load in < 3 s, so no background loading needed) |

---

## Part 1 — Backend on Railway

1. **New project → Deploy from GitHub repo** → select `groww-support-product-pulse`. Root directory: repo root. `railway.json` sets the builder (Nixpacks), start command and health check.
2. **Add a volume:** service → *Settings → Volumes → New volume*, mount path **`/data`**.
3. **Variables** (service → *Variables*):

| Variable | Value | Notes |
|---|---|---|
| `GROQ_API_KEY` | `gsk_…` | Groq console |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | reasoning model |
| `GROQ_FAST_MODEL` | `openai/gpt-oss-20b` | clustering / compliance |
| `DATA_DIR` | `/data` | the volume |
| `APPROVAL_SECRET` | 64 random hex chars | `python -c "import secrets;print(secrets.token_hex(32))"` |
| `PULSE_CRON` | `0 9 * * mon` | Asia/Kolkata |
| `ALLOWED_ORIGINS` | `https://<vercel-app>.vercel.app` | add after Part 2 |
| `ENABLE_EVAL_HOOKS` | `true` while running evals, then `false` | fault injection + debug export |
| `REVIEWER_PASSCODE` | optional | if set, approve/edit/reject/run need it |

4. **Networking → Generate domain**, e.g. `https://groww-pulse.up.railway.app`.

## Part 2 — Frontend on Vercel

1. **Add New → Project → Import** the same repo.
2. Framework preset **Vite**, **Root directory `frontend`**, build `npm run build`, output `dist`.
3. Environment variable `VITE_API_URL` = Railway domain (no trailing slash), Production.
4. Deploy. `frontend/vercel.json` provides the SPA rewrite, immutable asset caching and `Permissions-Policy: microphone=(self)`.

## Part 3 — Wire CORS

Set `ALLOWED_ORIGINS` on Railway to the Vercel production URL (comma-separate extra domains). Railway redeploys automatically.

## Part 4 — Smoke test (through the public frontend)

```bash
B=https://<railway-domain>
curl -s $B/api/health                       # {"status":"ok","llm_configured":true,"llm_status":"ok",...}
                                            # llm_status turns "auth_error" after the first rejected LLM call
curl -s $B/api/meta | python3 -m json.tool  # 24 sources, 11,526 reviews
curl -s -X POST $B/api/questions -H 'Content-Type: application/json' \
     -d '{"text":"Why was a DP charge deducted when I sold my shares?"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['current_draft']['reply'])"
```
Then open the Vercel URL: Ask → submit a question → Queue shows the cited draft; Weekly pulse → Run pulse now → Approvals shows 4 pending actions; approve one → Workspace shows the entry. The browser's network tab must show calls going to the Railway domain (CORS OK).

## Part 5 — Evaluations against the deployed system

```bash
ENABLE_EVAL_HOOKS=true   # on Railway, temporarily
.venv/bin/python evals/run_evals.py --base-url https://<railway-domain>
```
Results: `evals/results/<timestamp>/` and `evals/results/latest.md`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Themes say `keyword_fallback`, replies are extractive, `/api/health` shows `llm_status: auth_error` | Groq rejects `GROQ_API_KEY` (401) — wrong value or a mistyped variable name such as `GROQ_API_KEY:` | re-paste the key under the exact name `GROQ_API_KEY`; health now reports `llm_last_error` |
| Requests go to `…railway.app%20/api` | trailing space in `VITE_API_URL` | value is trimmed in code; also clean it in Vercel |
| CORS error | `ALLOWED_ORIGINS` missing the Vercel URL | update Railway variable |
| Approvals vanish after redeploy | no volume / `DATA_DIR` not `/data` | add volume, set `DATA_DIR` |
| Pulse runs twice | more than one replica/worker | keep `numReplicas: 1`, `--workers 1` |
| Slow replies (20–60 s) | Groq free tier 8k tokens/min | expected; the client-side limiter queues calls instead of failing |
| “refresh_reviews: warn” in a run | Google Play blocks datacenter IPs | expected; falls back to committed snapshot |
| Vercel `npm install` fails in `onnxruntime-node` (CUDA download 404) | transformers.js pulls the Node runtime, whose Linux install script fetches CUDA binaries | `frontend/vercel.json` sets `installCommand` with `ONNXRUNTIME_NODE_INSTALL_CUDA=skip` (browser build never uses it) |
| Microphone button errors | browser without MediaRecorder / denied permission | type instead; see README voice limitations |
