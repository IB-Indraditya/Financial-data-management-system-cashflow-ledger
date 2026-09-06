from decimal import Decimal

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request
)

from flask_login import login_required

from extensions import db

from models import (
    Client,
    Apricus,
    TradeData,
    CashRecord
)


try:
    from google import genai
except ImportError:
    genai = None


api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)


# ============================================================================
# Helpers
# ============================================================================

def _number(value):
    """
    Convert Decimal / float / int / None into a normal float.
    """
    if value is None:
        return 0.0

    if isinstance(value, Decimal):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _money(value):
    """
    Format a number as a simple financial value.
    """
    return round(
        _number(value),
        2
    )


# ============================================================================
# Database Summary
# ============================================================================

def build_acpl_context():
    """
    Build a safe, read-only summary of the ACPL database.

    Gemini receives this summary instead of being given direct database
    access.
    """

    clients = (
        Client.query
        .order_by(Client.name.asc())
        .all()
    )

    # ------------------------------------------------------------------------
    # Basic client information
    # ------------------------------------------------------------------------

    client_data = []

    for client in clients:

        client_data.append({
            "client_id": client.client_id,
            "name": client.name,
            "login_id": client.login_id,
            "email": client.mail_id
        })

    # ------------------------------------------------------------------------
    # Apricus data
    # ------------------------------------------------------------------------

    apricus_rows = (
        Apricus.query
        .order_by(Apricus.date.desc())
        .limit(5000)
        .all()
    )

    total_aum = 0.0
    total_mtm = 0.0

    apricus_by_client = {}

    for row in apricus_rows:

        client_code = str(
            row.client_code
        )

        investment = _number(
            row.investmt_amt
        )

        mtm = _number(
            row.mtm
        )

        total_aum += investment
        total_mtm += mtm

        if client_code not in apricus_by_client:

            apricus_by_client[client_code] = {
                "investment": 0.0,
                "mtm": 0.0,
                "cumulative_mtm": 0.0,
                "latest_date": None
            }

        apricus_by_client[client_code]["investment"] += investment

        apricus_by_client[client_code]["mtm"] += mtm

        apricus_by_client[client_code]["cumulative_mtm"] += (
            _number(row.cumulative_mtm)
        )

        if (
            apricus_by_client[client_code]["latest_date"] is None
            or row.date > apricus_by_client[client_code]["latest_date"]
        ):

            apricus_by_client[client_code]["latest_date"] = row.date

    # ------------------------------------------------------------------------
    # Cash data
    # ------------------------------------------------------------------------

    cash_rows = (
        CashRecord.query
        .order_by(CashRecord.date.desc())
        .limit(5000)
        .all()
    )

    total_cash = 0.0
    total_funds_added = 0.0
    total_funds_withdrawn = 0.0

    cash_by_client = {}

    for row in cash_rows:

        client_code = str(
            row.id
        )

        funds_added = _number(
            row.funds_added
        )

        funds_withdrawn = _number(
            row.funds_withdrawn
        )

        current_cash = _number(
            row.current_cash
        )

        total_funds_added += funds_added

        total_funds_withdrawn += funds_withdrawn

        if client_code not in cash_by_client:

            cash_by_client[client_code] = {
                "funds_added": 0.0,
                "funds_withdrawn": 0.0,
                "current_cash": 0.0,
                "latest_date": None
            }

        cash_by_client[client_code]["funds_added"] += funds_added

        cash_by_client[client_code]["funds_withdrawn"] += funds_withdrawn

        # Use the latest current cash value for each client.
        if (
            cash_by_client[client_code]["latest_date"] is None
            or row.date > cash_by_client[client_code]["latest_date"]
        ):

            cash_by_client[client_code]["current_cash"] = current_cash

            cash_by_client[client_code]["latest_date"] = row.date

    for data in cash_by_client.values():

        total_cash += data["current_cash"]

    # ------------------------------------------------------------------------
    # Trade data
    # ------------------------------------------------------------------------

    trade_rows = (
        TradeData.query
        .order_by(TradeData.date.desc())
        .limit(5000)
        .all()
    )

    total_trade_mtm = 0.0

    for row in trade_rows:

        total_trade_mtm += _number(
            row.mtm
        )

    # ------------------------------------------------------------------------
    # Per-client performance
    # ------------------------------------------------------------------------

    performance = []

    for client in clients:

        login_id = str(
            client.login_id
        )

        apricus = apricus_by_client.get(
            login_id,
            {}
        )

        cash = cash_by_client.get(
            login_id,
            {}
        )

        performance.append({
            "client_id": client.client_id,
            "name": client.name,
            "login_id": login_id,
            "investment": _money(
                apricus.get("investment", 0)
            ),
            "mtm": _money(
                apricus.get("mtm", 0)
            ),
            "cumulative_mtm": _money(
                apricus.get("cumulative_mtm", 0)
            ),
            "current_cash": _money(
                cash.get("current_cash", 0)
            )
        })

    # Highest MTM first
    performance.sort(
        key=lambda item: item["mtm"],
        reverse=True
    )

    return {
        "summary": {
            "client_count": len(clients),
            "total_aum": _money(total_aum),
            "total_mtm": _money(total_mtm),
            "total_trade_mtm": _money(total_trade_mtm),
            "total_cash": _money(total_cash),
            "total_funds_added": _money(total_funds_added),
            "total_funds_withdrawn": _money(total_funds_withdrawn)
        },
        "clients": client_data,
        "performance": performance[:50]
    }


# ============================================================================
# Built-in financial command handling
# ============================================================================

def handle_builtin_question(question, context):
    """
    Handle common financial questions locally.

    Returns:
        string
        None when Gemini should handle the question.
    """

    q = question.lower().strip()

    summary = context["summary"]

    # ------------------------------------------------------------------------
    # Client count
    # ------------------------------------------------------------------------

    if (
        "how many clients" in q
        or "client count" in q
        or "number of clients" in q
    ):

        return (
            f"There are {summary['client_count']} clients "
            "in the ACPL database."
        )

    # ------------------------------------------------------------------------
    # AUM
    # ------------------------------------------------------------------------

    if (
        "total aum" in q
        or "aum" in q
        or "assets under management" in q
    ):

        return (
            f"Total AUM is "
            f"{summary['total_aum']:,.2f}."
        )

    # ------------------------------------------------------------------------
    # MTM
    # ------------------------------------------------------------------------

    if (
        "total mtm" in q
        or "mtm" in q
    ):

        return (
            f"Total MTM is "
            f"{summary['total_mtm']:,.2f}."
        )

    # ------------------------------------------------------------------------
    # Cash
    # ------------------------------------------------------------------------

    if (
        "total cash" in q
        or "cash balance" in q
        or "current cash" in q
    ):

        return (
            f"Total current cash is "
            f"{summary['total_cash']:,.2f}."
        )

    # ------------------------------------------------------------------------
    # Top performer
    # ------------------------------------------------------------------------

    if (
        "top performer" in q
        or "best performer" in q
        or "highest mtm" in q
        or "top performing" in q
    ):

        performance = context["performance"]

        if not performance:

            return "There is no performance data available."

        top = performance[0]

        return (
            f"The top performer by MTM is "
            f"{top['name']} ({top['login_id']}) "
            f"with MTM of {top['mtm']:,.2f}."
        )

    # ------------------------------------------------------------------------
    # Negative MTM
    # ------------------------------------------------------------------------

    if (
        "negative mtm" in q
        or "losing clients" in q
        or "loss making clients" in q
    ):

        negative = [
            item
            for item in context["performance"]
            if item["mtm"] < 0
        ]

        if not negative:

            return "There are currently no clients with negative MTM."

        lines = [
            "Clients with negative MTM:"
        ]

        for item in negative:

            lines.append(
                f"- {item['name']}: "
                f"{item['mtm']:,.2f}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------------
    # Client list
    # ------------------------------------------------------------------------

    if (
        "list clients" in q
        or "show clients" in q
        or "all clients" in q
    ):

        if not context["clients"]:

            return "There are no clients."

        lines = [
            "ACPL clients:"
        ]

        for client in context["clients"]:

            lines.append(
                f"- {client['name']} "
                f"({client['login_id']})"
            )

        return "\n".join(lines)

    return None


# ============================================================================
# Gemini
# ============================================================================

def ask_gemini(question, context):
    """
    Send the user's question plus verified ACPL database information
    to Gemini.
    """

    if genai is None:

        raise RuntimeError(
            "The google-genai package is not installed. "
            "Run: pip install -U google-genai"
        )

    api_key = current_app.config.get(
        "GEMINI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    model = current_app.config.get(
        "GEMINI_MODEL",
        "gemini-3.8-flash"
    )

    client = genai.Client(
        api_key=api_key
    )

    system_instruction = """
You are the ACPL Financial Dashboard Assistant.

You answer questions about the ACPL financial management system.

IMPORTANT RULES:

1. Use the supplied ACPL database context as the source of truth
   for ACPL financial figures.

2. Never invent financial numbers.

3. If the supplied database context does not contain enough information
   to answer a financial question, clearly say that the available data
   is insufficient.

4. You may explain, summarize, compare, and analyze the supplied data.

5. Keep answers concise and useful.

6. Monetary values should be displayed with two decimal places where
   appropriate.

7. Do not reveal passwords, API keys, database credentials, or other
   secrets.

8. Do not claim to have modified the database.

9. This request is read-only unless the application explicitly provides
   a CRUD operation.

10. Do not invent client records.
"""

    prompt = f"""
ACPL DATABASE CONTEXT:

{context}

USER QUESTION:

{question}

Answer the user's question using the ACPL database context above.
"""

    response = client.models.generate_content(
        model=model,
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            system_instruction
                            + "\n\n"
                            + prompt
                        )
                    }
                ]
            }
        ]
    )

    if not response or not response.text:

        return (
            "Gemini did not return an answer. "
            "Please try again."
        )

    return response.text.strip()


# ============================================================================
# Assistant API
# ============================================================================

@api_bp.route(
    "/assistant",
    methods=["POST"]
)
@login_required
def assistant():

    data = request.get_json(
        silent=True
    ) or {}

    question = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not question:

        return jsonify({
            "success": False,
            "error": "Please enter a question."
        }), 400

    try:

        # --------------------------------------------------------------------
        # Get real database data
        # --------------------------------------------------------------------

        context = build_acpl_context()

        # --------------------------------------------------------------------
        # Try built-in financial commands first
        # --------------------------------------------------------------------

        builtin_answer = handle_builtin_question(
            question,
            context
        )

        if builtin_answer:

            return jsonify({
                "success": True,
                "answer": builtin_answer,
                "source": "database"
            })

        # --------------------------------------------------------------------
        # Otherwise use Gemini
        # --------------------------------------------------------------------

        answer = ask_gemini(
            question,
            context
        )

        return jsonify({
            "success": True,
            "answer": answer,
            "source": "gemini"
        })

    except Exception as exc:

        current_app.logger.exception(
            "Assistant error"
        )

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500