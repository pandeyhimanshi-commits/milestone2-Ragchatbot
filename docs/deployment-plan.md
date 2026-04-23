# Deployment Plan

This plan deploys the project as:
- **Scheduler:** GitHub Actions
- **Backend:** Streamlit
- **Frontend UI:** Vercel

---

## 1) Target Architecture

- **Ingestion scheduler (Phase 4.1):** GitHub Actions workflow (`.github/workflows/ingest-corpus.yml`)
  - Runs daily (09:15 IST via UTC cron already configured).
  - Executes scrape -> normalize -> chunk -> embed -> Chroma upsert.
- **Backend runtime:** Streamlit Cloud app
  - Runs a Streamlit app from the repository.
  - Handles chatbot query/response flow using the same retrieval + generation pipeline.
- **Frontend (Next.js):** Vercel
  - Deploys `frontend/`.
  - Uses `/api/chat` proxy route to reach backend.

---

## 2) Environments

Use two environments:

- **Staging**
  - Branch: `develop` (or equivalent)
  - Separate backend URL
  - Separate Chroma DB or collection for safe testing

- **Production**
  - Branch: `main`
  - Stable public backend + frontend URLs
  - Production Chroma Cloud credentials

---

## 3) Configuration & Secrets

## 3.1 GitHub Actions (Scheduler)

Repository secrets required:
- `CHROMA_CLOUD_TENANT`
- `CHROMA_CLOUD_DATABASE`
- `CHROMA_API_KEY`

Optional (if scheduler behavior is tuned later):
- scrape timeouts/retries via env in workflow
- notification webhook/token for failures

## 3.2 Streamlit (Backend)

Set these in Streamlit app secrets (`.streamlit/secrets.toml` on platform):
- `CHROMA_CLOUD_TENANT`
- `CHROMA_CLOUD_DATABASE`
- `CHROMA_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (optional; default exists in code)
- any rate-limit/runtime config vars used in `phase-7` / `phase-9`

## 3.3 Vercel (Frontend)

Set:
- `BACKEND_CHAT_URL=https://<streamlit-backend-domain>/chat`

The frontend proxy route (`frontend/app/api/chat/route.ts`) uses this value.

Note: Streamlit is primarily app-first (UI). If you need strict `/chat` API compatibility for Vercel, keep a thin API layer that forwards to the Streamlit-backed runtime logic.

---

## 4) Deployment Steps

## 4.1 Backend on Streamlit

1. Create a new **Streamlit app** from this repository.
2. Configure:
   - Branch: `main`
   - App file path: your Streamlit entrypoint (for example `ingestion/phase-9-security-ui/streamlit_app.py`)
   - Python dependencies: include required packages in `requirements.txt`
3. Add secrets listed in section 3.2.
4. Deploy and verify:
   - Streamlit app opens correctly.
   - Chatbot answers are generated from the same Chroma + Gemini pipeline.

## 4.2 Frontend on Vercel

1. Import repository in Vercel.
2. Configure:
   - Root directory: `frontend`
   - Framework: Next.js (auto-detected)
3. Add env var:
   - `BACKEND_CHAT_URL=https://<streamlit-backend-domain>/chat`
4. Deploy and verify:
   - Home page loads
   - Sending message reaches backend successfully
   - Source links render correctly.

## 4.3 Scheduler on GitHub Actions

1. Keep workflow file: `.github/workflows/ingest-corpus.yml`.
2. Ensure repository secrets in section 3.1 are present.
3. Trigger `workflow_dispatch` once for smoke test.
4. Validate artifacts:
   - scrape/normalize/chunk/embed/chroma outputs
   - scheduler logs (`scheduler-activity-log.jsonl`, `scheduler-last-run.json`).

---

## 5) CI/CD Strategy

- **Frontend (Vercel):**
  - Auto deploy on push to configured branch.
  - Preview deployments for PRs.

- **Backend (Streamlit):**
  - Auto deploy on push to configured branch.
  - Verify app health via Streamlit app availability and functional chat test.

- **Scheduler (GitHub Actions):**
  - Time-based cron + manual dispatch.
  - Artifacts retained for audit/debug.

---

## 6) Validation Checklist (Post Deploy)

- Backend
  - `/health` returns 200.
  - Refusal query returns exact refusal sentence configured.
  - Factual query returns 1 source link and last-updated line.

- Frontend
  - `/api/chat` returns backend response.
  - New Chat creates a new thread tab.
  - Thread switching preserves history per tab.

- Scheduler
  - Successful end-to-end run in Actions.
  - Chroma ingest report shows non-zero upserts.
  - Only latest ingest data retained as per workflow cleanup step.

---

## 7) Observability & Logs

- **Scheduler logs:** GitHub Actions logs + uploaded scheduler artifacts.
- **Backend logs:** Streamlit app logs + platform logs.
- **Frontend logs:** Vercel function logs (`/api/chat`) and browser console.

Recommended alerts:
- Scheduler failure alert (workflow failed).
- Backend health check failure alert.
- Elevated refusal/error rate alert (future enhancement).

---

## 8) Rollback Plan

- **Frontend rollback:** Redeploy prior successful Vercel deployment.
- **Backend rollback:** Redeploy prior Streamlit app commit/version.
- **Scheduler rollback:** Revert workflow commit, rerun manually.
- **Data rollback:** Re-run ingestion from stable commit + known good allowlist/config.

---

## 9) Security & Compliance Notes

- Keep all keys only in platform secrets (never commit to repo).
- Restrict CORS/host access on backend if needed.
- Preserve facts-only policy and refusal behavior in runtime checks.
- Do not log sensitive user data in plaintext.

---

## 10) Suggested Go-Live Sequence

1. Deploy backend to Streamlit and verify functional chatbot response.
2. Deploy frontend to Vercel with `BACKEND_CHAT_URL`.
3. Run manual scheduler workflow once.
4. Execute edge-case suite (`docs/edgecase.md`).
5. Go live after pass criteria on factual, refusal, and formatting checks.

