"""
Virtual assistant for the ACPL dashboard.

Two tiers:
1. FREE, LOCAL ENGINE (always on, no API key, no cost) — a set of regex intent
   matchers that cover common questions and agentic CRUD commands.
2. OPTIONAL LLM UPGRADE (Claude, via ANTHROPIC_API_KEY) — free-text questions
   that don't match a known intent are forwarded to Claude with a snapshot of
   live KPIs as grounding context.
"""
import re
import requests
from flask import current_app
from extensions import db
from models import Client
from analytics import get_kpis, get_client_leaderboard, _latest_apricus_per_client


def _money(n):
    return f"{n:,.0f}"


def _title_case(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split() if w)


def _find_client(term: str):
    term = term.strip()
    compact = term.replace(" ", "")
    return (
        Client.query.filter(
            db.or_(
                Client.login_id.ilike(compact),
                Client.name.ilike(f"%{term}%"),
            )
        ).first()
    )


def _try_local_intents(message: str):
    m = message.strip().lower()

    if re.search(r"(how many|number of|count).*(client)", m):
        count = Client.query.count()
        return {"reply": f"There are currently {count} clients on the platform."}

    if re.search(r"(top|best).*(client|performer)", m):
        board = get_client_leaderboard()
        if not board:
            return {"reply": "I couldn't find any performance data yet."}
        top = board[0]
        return {
            "reply": f"{top.name} ({top.client_code}) is the top performer with a cumulative MTM of ₹{_money(top.cumulative_mtm or 0)}."
        }

    if re.search(r"(worst|lowest).*(client|performer)", m):
        board = get_client_leaderboard()
        if not board:
            return {"reply": "I couldn't find any performance data yet."}
        bottom = board[-1]
        return {
            "reply": f"{bottom.name} ({bottom.client_code}) currently has the lowest cumulative MTM at ₹{_money(bottom.cumulative_mtm or 0)}."
        }

    if re.search(r"(total|overall).*(aum|investment|invested)", m):
        kpis = get_kpis()
        return {"reply": f"Total assets under management: ₹{_money(kpis['total_aum'])}."}

    if re.search(r"(total|overall).*(cash)", m):
        kpis = get_kpis()
        return {"reply": f"Total free cash balance across all clients: ₹{_money(kpis['total_cash'])}."}

    if re.search(r"(net|total).*(mtm|p&l|pnl|profit)", m) or re.search(r"mtm.*(total|overall)", m):
        kpis = get_kpis()
        return {"reply": f"Total cumulative MTM across all clients: ₹{_money(kpis['total_cumulative_mtm'])}."}

    cash_bal_match = re.search(r"cash (?:balance|bal).*(?:for|of)\s+([a-z0-9\s]+)", m)
    if cash_bal_match:
        term = cash_bal_match.group(1).strip()
        client = _find_client(term)
        if not client:
            return {"reply": f'I couldn\'t find a client matching "{term}".'}
        latest = [r for r in _latest_apricus_per_client() if r.client_code == client.login_id]
        if not latest:
            return {"reply": f"No ledger entries found for {client.name} yet."}
        row = latest[0]
        return {
            "reply": f"{client.name}'s current free cash balance is ₹{_money(row.current_cash or 0)} as of {row.date.isoformat()}."
        }

    add_match = re.search(
        r"(add|create|register|new)\s+client\s+(?:named\s+|called\s+)?([a-z\s]+?)(?:\s+with\s+email\s+([\w.+-]+@[\w.-]+))?$",
        m,
    )
    if add_match:
        name = _title_case(add_match.group(2).strip())
        email = add_match.group(3) or f"{name.lower().replace(' ', '.')}@example.com"
        count = Client.query.count()
        login_id = f"acpl{count + 1:03d}"
        client = Client(name=name, mail_id=email, login_id=login_id)
        db.session.add(client)
        db.session.commit()
        return {
            "reply": f'Created client "{client.name}" with login ID {client.login_id} and email {client.mail_id}.',
            "action": {"type": "client_created", "payload": {"client_id": client.client_id}},
        }

    delete_match = re.search(r"(delete|remove)\s+client\s+([a-z0-9\s]+)", m)
    if delete_match:
        term = delete_match.group(2).strip()
        client = _find_client(term)
        if not client:
            return {"reply": f'I couldn\'t find a client matching "{term}" to delete.'}
        name, login_id = client.name, client.login_id
        db.session.delete(client)
        db.session.commit()
        return {
            "reply": f'Deleted client "{name}" ({login_id}).',
            "action": {"type": "client_deleted"},
        }

    rename_match = re.search(r"rename\s+client\s+([a-z0-9\s]+?)\s+to\s+([a-z\s]+)", m)
    if rename_match:
        term = rename_match.group(1).strip()
        new_name = _title_case(rename_match.group(2).strip())
        client = _find_client(term)
        if not client:
            return {"reply": f'I couldn\'t find a client matching "{term}".'}
        old_name = client.name
        client.name = new_name
        db.session.commit()
        return {
            "reply": f'Renamed "{old_name}" to "{client.name}".',
            "action": {"type": "client_updated", "payload": {"client_id": client.client_id}},
        }

    if re.match(r"^(hi|hello|hey)\b", m):
        return {
            "reply": "Hello! I'm your ACPL assistant. Ask me things like \"how many clients do we have\", "
            "\"who is the top performer\", \"total AUM\", or tell me to \"add client Priya Verma\"."
        }

    return None


def _try_claude(message: str):
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        kpis = get_kpis()
        board = get_client_leaderboard()[:10]
        context = {
            "clientCount": kpis["client_count"],
            "totalAUM": kpis["total_aum"],
            "totalCash": kpis["total_cash"],
            "totalCumulativeMtm": kpis["total_cumulative_mtm"],
            "totalFundsAdded": kpis["total_funds_added"],
            "totalFundsWithdrawn": kpis["total_funds_withdrawn"],
            "leaderboard": [
                {
                    "client_code": r.client_code,
                    "name": r.name,
                    "cumulative_mtm": r.cumulative_mtm,
                    "investmt_amt": r.investmt_amt,
                    "current_cash": r.current_cash,
                }
                for r in board
            ],
        }

        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "system": (
                    "You are a financial dashboard assistant for ACPL, a portfolio management firm. "
                    "Answer questions using ONLY the JSON snapshot of live data provided. "
                    "Be concise, use ₹ for currency, and never invent numbers not present in the data."
                ),
                "messages": [
                    {"role": "user", "content": f"Data snapshot: {context}\n\nQuestion: {message}"}
                ],
            },
            timeout=20,
        )
        if not res.ok:
            return None
        data = res.json()
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block.get("text")
        return None
    except Exception:
        return None


def run_assistant(message: str):
    local = _try_local_intents(message)
    if local:
        return local

    llm_reply = _try_claude(message)
    if llm_reply:
        return {"reply": llm_reply}

    return {
        "reply": "I didn't quite catch that with my built-in engine. Try asking about client counts, "
        "top performers, total AUM/cash/MTM, or a CRUD command like \"add client <name>\". "
        "Add an ANTHROPIC_API_KEY to unlock free-form Q&A."
    }
