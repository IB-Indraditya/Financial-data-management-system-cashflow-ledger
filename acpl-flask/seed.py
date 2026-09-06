"""
Seeds the database from:
 - the original acpl_*.sql dumps (converted to JSON in data/)
 - a default admin login for the dashboard

Run with: python seed.py
"""
import json
import os
from datetime import datetime

from app import app
from extensions import db
from models import AdminUser, Client, Apricus, CashRecord, TradeData

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    with app.app_context():
        db.create_all()

        print("Seeding admin user...")
        admin_email = app.config["SEED_ADMIN_EMAIL"]
        admin_password = app.config["SEED_ADMIN_PASSWORD"]
        admin = AdminUser.query.filter_by(email=admin_email).first()
        if not admin:
            admin = AdminUser(name="ACPL Administrator", email=admin_email, role="admin")
            db.session.add(admin)
        admin.set_password(admin_password)
        db.session.commit()
        print(f"  -> admin login: {admin_email} / {admin_password}")

        print("Seeding clients...")
        Client.query.delete()
        clients = _load("clients.json")
        for c in clients:
            db.session.add(Client(client_id=c["client_id"], name=c["name"], mail_id=c["mail_id"], login_id=c["login_id"]))
        db.session.commit()
        print(f"  -> {len(clients)} clients")

        print("Seeding apricus (combined ledger)...")
        Apricus.query.delete()
        apricus_rows = _load("apricus.json")
        for r in apricus_rows:
            db.session.add(Apricus(
                date=_parse_date(r["date"]), client_code=r["id"], name=r["name"],
                investmt_amt=r.get("investmt_amt"), funds_added=r.get("funds_added"),
                funds_withdrawn=r.get("funds_withdrawn"), mtm=r.get("mtm"),
                prev_free_cash_bal=r.get("prev_free_cash_bal"), current_cash=r.get("current_cash"),
                difference=r.get("difference"), cumulative_mtm=r.get("cumulative_mtm"),
            ))
        db.session.commit()
        print(f"  -> {len(apricus_rows)} rows")

        print("Seeding cash_record...")
        CashRecord.query.delete()
        cash_rows = _load("cash_record.json")
        for r in cash_rows:
            db.session.add(CashRecord(
                date=_parse_date(r["date"]), client_code=r["id"], name=r["name"],
                funds_added=r.get("funds_added"), funds_withdrawn=r.get("funds_withdrawn"),
                prev_free_cash_bal=r.get("prev_free_cash_bal"), current_cash=r.get("current_cash"),
                difference=r.get("difference"),
            ))
        db.session.commit()
        print(f"  -> {len(cash_rows)} rows")

        print("Seeding trade_data...")
        TradeData.query.delete()
        trade_rows = _load("trade_data.json")
        for r in trade_rows:
            db.session.add(TradeData(
                date=_parse_date(r["date"]), client_code=r["id"], name=r["name"],
                investmt_amt=r.get("investmt_amt"), mtm=r.get("mtm"), cumulative_mtm=r.get("cumulative_mtm"),
            ))
        db.session.commit()
        print(f"  -> {len(trade_rows)} rows")

        print("Done.")


if __name__ == "__main__":
    main()
