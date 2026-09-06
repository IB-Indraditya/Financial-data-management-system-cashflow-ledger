# ACPL — Financial Management System & Cashflow Ledger (Python / Flask)

A full-stack admin platform built from your `acpl_*.sql` exports — rebuilt in Python
so it deploys cleanly on **Render**.

- **Public landing page** — light, trichromatic theme: white / dark green / gold, Bootstrap 5.
- **Admin dashboard** — business KPIs, cumulative MTM trend, cashflow chart, client leaderboard.
- **Full CRUD** for clients, trade data and the cash ledger (plain server-rendered forms).
- **Login / logout** — Flask-Login, hashed passwords (Werkzeug), protected routes.
- **AI assistant** — free, built-in rule-based engine (no API key needed) that answers
  questions and performs CRUD ("add client X", "delete client Y") in plain language,
  with an optional upgrade to Claude for open-ended Q&A.
- **Database** — SQLite by default (zero-config); Postgres via `DATABASE_URL` for Render.
- **Tested end-to-end**: every route, the seed script, and the assistant's CRUD actions
  were actually run against a live server during development — not just written.

---

## 1. What's in the data

Parsed directly from your uploaded dumps and included as JSON in `data/`:

| Table         | Rows  | What it holds                                                    |
|---------------|-------|---------------------------------------------------------------------|
| `clients`     | 10    | Client directory: name, email, login ID                             |
| `apricus`     | 1,074 | Combined daily ledger per client: investment, funds, MTM, cash      |
| `cash_record` | 1,074 | Daily cash movement: funds added/withdrawn, free cash balance       |
| `trade_data`  | 1,074 | Daily trade/MTM ledger: investment amount, MTM, cumulative MTM      |

All four are loaded automatically by `seed.py`.

## 2. Project structure

```
app.py                    Flask app factory + entry point
config.py                 Env-driven config (DB URL, secret key, seed creds)
extensions.py             SQLAlchemy + Flask-Login instances
models.py                 AdminUser, Client, Apricus, CashRecord, TradeData
analytics.py              KPI / chart aggregation queries
agent.py                  AI assistant: free local NLU + optional Claude upgrade
seed.py                   Loads data/*.json into the database + admin login
blueprints/
  main.py                  landing page
  auth.py                  login / logout
  dashboard.py             overview, clients, trades, cash, assistant page routes
  api.py                   /api/assistant JSON endpoint (used by the chat widget)
templates/
  base.html                shared HTML shell (Bootstrap 5 + Chart.js via CDN)
  landing.html, login.html
  dashboard/
    layout.html            sidebar + topbar shared by all dashboard pages
    overview.html, clients_list.html, client_form.html, client_detail.html,
    trades_list.html, cash_list.html, assistant.html
static/css/style.css       the white / dark-green / gold theme
data/*.json                your seed data, parsed from the SQL dumps
render.yaml                one-click Render Blueprint (web service + Postgres)
Procfile                   fallback start command for Render
requirements.txt
```

## 3. Run it locally

Requires Python 3.10+.

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # defaults already work as-is
python seed.py                # creates instance/acpl.db and loads all data
python app.py                 # dev server on http://localhost:5000
```

For a production-style run locally:

```bash
gunicorn app:app
```

Visit `http://localhost:5000`. Log in at `/login` with:

```
Email:    admin@acpl.com
Password: Admin@123
```

(Set `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` in `.env` before running `seed.py`
to change these, or edit the admin user afterwards.)

## 4. Deploying to Render

### Option A — one-click Blueprint (recommended)

1. Push this project to a GitHub repo.
2. In Render, choose **New → Blueprint** and point it at the repo.
   `render.yaml` provisions both the web service and a free Postgres database,
   and wires `DATABASE_URL` between them automatically.
3. Set the remaining env vars Render prompts for: `SEED_ADMIN_PASSWORD` and
   optionally `ANTHROPIC_API_KEY`.
4. After the first deploy, open the Render **Shell** for the web service and run:
   ```bash
   python seed.py
   ```
   This loads your data into the new Postgres database.

### Option B — manual web service

1. **New → Web Service**, connect your repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Add a Postgres instance (Render → **New → PostgreSQL**, free tier is fine),
   then copy its **Internal Connection String** into the web service's
   `DATABASE_URL` env var.
5. Also set `SECRET_KEY`, `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, and
   optionally `ANTHROPIC_API_KEY`.
6. Deploy, then run `python seed.py` from the Render Shell once to load data.

> **Why Postgres and not SQLite in production?** Render's free web service
> filesystem is ephemeral — it resets on every deploy/restart, so a SQLite
> file's CRUD writes wouldn't persist. Postgres (free tier available) keeps
> your data durable across deploys.

## 5. The AI assistant

The assistant at `/dashboard/assistant` works with **zero configuration**,
using a built-in, free rule-based engine (`agent.py`) verified to handle:

- "How many clients do we have?"
- "Who is the top / worst performer?"
- "What's the total AUM / total cash / total MTM?"
- "What's the cash balance for Rohit Sharma?"

and agentic CRUD commands:

- "Add client Priya Verma" — actually creates the row (tested)
- "Rename client acpl003 to Daniyal Nawab"
- "Delete client Prasam Kundu"

If you add `ANTHROPIC_API_KEY` to your environment, free-text questions that
don't match a known pattern are forwarded to Claude along with a live snapshot
of your KPIs, so answers stay grounded in real numbers. This is entirely
optional — the assistant is fully usable without any API key or cost.

## 6. Theme

The white / dark-green / gold theme lives in `static/css/style.css`, layered
on Bootstrap 5 via CSS variable overrides:

- `--acpl-offwhite` / `--acpl-white` — page and card backgrounds
- `--acpl-green-900` / `--acpl-green-800` — headings, nav, primary text accents
- `--acpl-gold` / `--acpl-gold-dark` — buttons, borders, highlights, badges

Adjust these variables to retheme the whole app in one place.

## 7. Known limitations / notes

- Templates use inline `<script>` blocks with Jinja `tojson` filters to feed
  Chart.js — this was tested and works, but if you rename any aggregation
  dict keys in `analytics.py`, avoid using `values`, `items`, or `keys` as key
  names (Jinja's attribute lookup collides with those built-in dict methods —
  this actually happened once during development and was fixed).
- CRUD forms use plain HTML forms + redirects (no JS framework), so they work
  without JavaScript enabled, at the cost of a full page reload per action.
