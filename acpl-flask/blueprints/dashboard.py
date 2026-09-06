from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required

from extensions import db

from models import (
    Client,
    TradeData,
    CashRecord,
    Apricus
)

from analytics import (
    get_kpis,
    get_cumulative_mtm_series,
    get_cash_flow_series,
    get_client_leaderboard
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _to_date(value):
    """
    Convert YYYY-MM-DD string to Python date object.
    """
    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()

    except (TypeError, ValueError):
        return None


def _to_float(value):
    """
    Convert form value to float.
    """
    if value in (None, ""):
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Dashboard Blueprint
# ---------------------------------------------------------------------------

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard"
)


# ===========================================================================
# Dashboard Overview
# ===========================================================================

@dashboard_bp.route("/")
@login_required
def overview():

    kpis = get_kpis()

    mtm_series = get_cumulative_mtm_series()

    cash_series = get_cash_flow_series()

    leaderboard = get_client_leaderboard()

    return render_template(
        "dashboard/overview.html",
        kpis=kpis,
        mtm_series=mtm_series,
        cash_series=cash_series,
        leaderboard=leaderboard
    )


# ===========================================================================
# Clients
# ===========================================================================

@dashboard_bp.route("/clients")
@login_required
def clients_list():

    q = request.args.get(
        "q",
        ""
    ).strip()

    query = Client.query

    if q:

        like = f"%{q}%"

        query = query.filter(
            db.or_(
                Client.name.ilike(like),
                Client.login_id.ilike(like),
                Client.mail_id.ilike(like)
            )
        )

    clients = (
        query
        .order_by(Client.client_id.asc())
        .all()
    )

    return render_template(
        "dashboard/clients_list.html",
        clients=clients,
        q=q
    )


# ---------------------------------------------------------------------------
# Create Client
# ---------------------------------------------------------------------------

@dashboard_bp.route(
    "/clients/new",
    methods=["GET", "POST"]
)
@login_required
def client_new():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        mail_id = request.form.get(
            "mail_id",
            ""
        ).strip()

        login_id = request.form.get(
            "login_id",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()

        # Validate required fields
        if not (
            name
            and mail_id
            and login_id
            and password
        ):

            flash(
                "All fields are required.",
                "danger"
            )

        # Check duplicate login ID
        elif Client.query.filter_by(
            login_id=login_id
        ).first():

            flash(
                "That login ID is already in use.",
                "danger"
            )

        else:

            client = Client(
                name=name,
                mail_id=mail_id,
                login_id=login_id,
                password=password
            )

            db.session.add(client)

            db.session.commit()

            flash(
                f'Client "{name}" created.',
                "success"
            )

            return redirect(
                url_for(
                    "dashboard.clients_list"
                )
            )

    return render_template(
        "dashboard/client_form.html",
        client=None
    )


# ---------------------------------------------------------------------------
# Client Details
# ---------------------------------------------------------------------------

@dashboard_bp.route(
    "/clients/<int:client_id>"
)
@login_required
def client_detail(client_id):

    client = Client.query.get_or_404(
        client_id
    )

    # Apricus table uses the database column `id`
    # which is mapped to Apricus.client_code
    apricus_rows = (
        Apricus.query
        .filter_by(
            client_code=client.login_id
        )
        .order_by(
            Apricus.date.asc()
        )
        .all()
    )

    return render_template(
        "dashboard/client_detail.html",
        client=client,
        apricus_rows=apricus_rows
    )


# ---------------------------------------------------------------------------
# Edit Client
# ---------------------------------------------------------------------------

@dashboard_bp.route(
    "/clients/<int:client_id>/edit",
    methods=["POST"]
)
@login_required
def client_edit(client_id):

    client = Client.query.get_or_404(
        client_id
    )

    client.name = request.form.get(
        "name",
        client.name
    ).strip()

    client.mail_id = request.form.get(
        "mail_id",
        client.mail_id
    ).strip()

    new_login_id = request.form.get(
        "login_id",
        client.login_id
    ).strip()

    # Check whether the new login ID already belongs
    # to another client.
    if (
        new_login_id != client.login_id
        and Client.query.filter_by(
            login_id=new_login_id
        ).first()
    ):

        flash(
            "That login ID is already in use.",
            "danger"
        )

    else:

        client.login_id = new_login_id

        db.session.commit()

        flash(
            "Client updated.",
            "success"
        )

    return redirect(
        url_for(
            "dashboard.client_detail",
            client_id=client_id
        )
    )


# ---------------------------------------------------------------------------
# Delete Client
# ---------------------------------------------------------------------------

@dashboard_bp.route(
    "/clients/<int:client_id>/delete",
    methods=["POST"]
)
@login_required
def client_delete(client_id):

    client = Client.query.get_or_404(
        client_id
    )

    name = client.name

    db.session.delete(client)

    db.session.commit()

    flash(
        f'Client "{name}" deleted.',
        "success"
    )

    return redirect(
        url_for(
            "dashboard.clients_list"
        )
    )


# ===========================================================================
# Trade Data
# ===========================================================================

@dashboard_bp.route(
    "/trades",
    methods=["GET", "POST"]
)
@login_required
def trades_list():

    # -----------------------------------------------------------------------
    # Add Trade Record
    # -----------------------------------------------------------------------

    if request.method == "POST":

        client_code = request.form.get(
            "client_code",
            ""
        ).strip()

        client = Client.query.filter_by(
            login_id=client_code
        ).first()

        if not client:

            flash(
                "Selected client was not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "dashboard.trades_list",
                    client_code=client_code
                )
            )

        # IMPORTANT:
        # TradeData model currently does NOT have a client_code field.
        #
        # Therefore we store the client login ID in TradeData.id.
        #
        # This assumes the existing trade_data.id column is intended
        # to contain the client code.

        row = TradeData(
            id=client.login_id,

            date=_to_date(
                request.form.get("date")
            ),

            name=client.name,

            investmt_amt=_to_float(
                request.form.get("investmt_amt")
            ),

            mtm=_to_float(
                request.form.get("mtm")
            ),

            cumulative_mtm=_to_float(
                request.form.get("cumulative_mtm")
            )
        )

        db.session.add(row)

        try:

            db.session.commit()

            flash(
                "Trade record added.",
                "success"
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to add trade record. "
                "The ID/date combination may already exist.",
                "danger"
            )

        return redirect(
            url_for(
                "dashboard.trades_list",
                client_code=client_code
            )
        )

    # -----------------------------------------------------------------------
    # Display Trade Records
    # -----------------------------------------------------------------------

    client_code = request.args.get(
        "client_code",
        ""
    ).strip()

    query = TradeData.query

    if client_code:

        # Since TradeData has no client_code column,
        # filter using the id column.
        query = query.filter(
            TradeData.id == client_code
        )

    trades = (
        query
        .order_by(
            TradeData.date.desc()
        )
        .limit(500)
        .all()
    )

    clients = (
        Client.query
        .order_by(
            Client.name.asc()
        )
        .all()
    )

    return render_template(
        "dashboard/trades_list.html",
        trades=trades,
        clients=clients,
        client_code=client_code
    )


# ---------------------------------------------------------------------------
# Delete Trade Record
# ---------------------------------------------------------------------------

@dashboard_bp.route(
    "/trades/<string:row_id>/delete",
    methods=["POST"]
)
@login_required
def trade_delete(row_id):

    # TradeData.id is String, not Integer.
    row = TradeData.query.get_or_404(
        row_id
    )

    db.session.delete(row)

    db.session.commit()

    flash(
        "Trade record deleted.",
        "success"
    )

    return redirect(
        url_for(
            "dashboard.trades_list"
        )
    )


# ===========================================================================
# Cash Ledger
# ===========================================================================

@dashboard_bp.route(
    "/cash",
    methods=["GET", "POST"]
)
@login_required
def cash_list():

    # -----------------------------------------------------------------------
    # Add Cash Record
    # -----------------------------------------------------------------------

    if request.method == "POST":

        client_code = request.form.get(
            "client_code",
            ""
        ).strip()

        client = Client.query.filter_by(
            login_id=client_code
        ).first()

        if not client:

            flash(
                "Selected client was not found.",
                "danger"
            )

            return redirect(
                url_for(
                    "dashboard.cash_list",
                    client_code=client_code
                )
            )

        # IMPORTANT:
        # CashRecord currently has:
        #
        # id
        # date
        # name
        # funds_added
        # funds_withdrawn
        # prev_free_cash_bal
        # current_cash
        # difference
        #
        # It does NOT have a client_code column.
        #
        # Therefore the client login ID is stored in id.

        row = CashRecord(
            id=client.login_id,

            date=_to_date(
                request.form.get("date")
            ),

            name=client.name,

            funds_added=_to_float(
                request.form.get("funds_added")
            ),

            funds_withdrawn=_to_float(
                request.form.get("funds_withdrawn")
            ),

            prev_free_cash_bal=_to_float(
                request.form.get("prev_free_cash_bal")
            ),

            current_cash=_to_float(
                request.form.get("current_cash")
            ),

            difference=_to_float(
                request.form.get("difference")
            )
        )

        db.session.add(row)

        try:

            db.session.commit()

            flash(
                "Cash entry added.",
                "success"
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to add cash entry. "
                "The ID may already exist.",
                "danger"
            )

        return redirect(
            url_for(
                "dashboard.cash_list",
                client_code=client_code
            )
        )

    # -----------------------------------------------------------------------
    # Display Cash Records
    # -----------------------------------------------------------------------

    client_code = request.args.get(
        "client_code",
        ""
    ).strip()

    query = CashRecord.query

    if client_code:

        # Since CashRecord has no client_code column,
        # filter using the id column.
        query = query.filter(
            CashRecord.id == client_code
        )

    rows = (
        query
        .order_by(
            CashRecord.date.desc()
        )
        .limit(500)
        .all()
    )

    clients = (
        Client.query
        .order_by(
            Client.name.asc()
        )
        .all()
    )

    return render_template(
        "dashboard/cash_list.html",
        rows=rows,
        clients=clients,
        client_code=client_code
    )


# ---------------------------------------------------------------------------
# Delete Cash Record
# ---------------------------------------------------------------------------

@dashboard_bp.route(
    "/cash/<string:row_id>/delete",
    methods=["POST"]
)
@login_required
def cash_delete(row_id):

    # CashRecord.id is String, so the route parameter
    # must also be a string.
    row = CashRecord.query.get_or_404(
        row_id
    )

    db.session.delete(row)

    db.session.commit()

    flash(
        "Cash entry deleted.",
        "success"
    )

    return redirect(
        url_for(
            "dashboard.cash_list"
        )
    )


# ===========================================================================
# AI Assistant
# ===========================================================================

@dashboard_bp.route("/assistant")
@login_required
def assistant():

    return render_template(
        "dashboard/assistant.html"
    )