from sqlalchemy import func
from extensions import db
from models import Client, Apricus, CashRecord


def get_kpis():
    client_count = db.session.query(func.count(Client.client_id)).scalar() or 0

    funds_added, funds_withdrawn, total_mtm = db.session.query(
        func.coalesce(func.sum(Apricus.funds_added), 0.0),
        func.coalesce(func.sum(Apricus.funds_withdrawn), 0.0),
        func.coalesce(func.sum(Apricus.mtm), 0.0),
    ).one()

    latest_rows = _latest_apricus_per_client()
    total_aum = sum((r.investmt_amt or 0) for r in latest_rows)
    total_cash = sum((r.current_cash or 0) for r in latest_rows)
    total_cumulative_mtm = sum((r.cumulative_mtm or 0) for r in latest_rows)

    return {
        "client_count": client_count,
        "total_aum": total_aum,
        "total_cash": total_cash,
        "total_cumulative_mtm": total_cumulative_mtm,
        "total_funds_added": funds_added,
        "total_funds_withdrawn": funds_withdrawn,
        "total_mtm": total_mtm,
    }


def _latest_apricus_per_client():
    subq = (
        db.session.query(Apricus.client_code, func.max(Apricus.date).label("max_date"))
        .group_by(Apricus.client_code)
        .subquery()
    )
    rows = (
        db.session.query(Apricus)
        .join(subq, (Apricus.client_code == subq.c.client_code) & (Apricus.date == subq.c.max_date))
        .all()
    )
    return rows


def get_cumulative_mtm_series():
    rows = (
        db.session.query(Apricus.date, func.coalesce(func.sum(Apricus.mtm), 0.0))
        .group_by(Apricus.date)
        .order_by(Apricus.date.asc())
        .all()
    )
    labels, totals = [], []
    running = 0.0
    for d, daily_mtm in rows:
        running += float(daily_mtm or 0)
        labels.append(d.isoformat())
        totals.append(round(running))
    return {"labels": labels, "totals": totals}


def get_cash_flow_series():
    rows = (
        db.session.query(
            CashRecord.date,
            func.coalesce(func.sum(CashRecord.funds_added), 0.0),
            func.coalesce(func.sum(CashRecord.funds_withdrawn), 0.0),
        )
        .group_by(CashRecord.date)
        .order_by(CashRecord.date.asc())
        .all()
    )
    return {
        "labels": [d.isoformat() for d, _, _ in rows],
        "added": [round(float(a or 0)) for _, a, _ in rows],
        "withdrawn": [round(float(w or 0)) for _, _, w in rows],
    }


def get_client_leaderboard():
    rows = _latest_apricus_per_client()
    rows.sort(key=lambda r: (r.cumulative_mtm or 0), reverse=True)
    return rows


def get_client_time_series(client_code: str):
    return (
        Apricus.query.filter_by(client_code=client_code)
        .order_by(Apricus.date.asc())
        .all()
    )
