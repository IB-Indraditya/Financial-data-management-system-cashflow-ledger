from datetime import datetime

from flask_login import UserMixin

from extensions import db


# ============================================================================
# Admin User
# ============================================================================

class AdminUser(UserMixin, db.Model):
    __tablename__ = "AdminUser"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="admin"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ------------------------------------------------------------------------
    # Plain-text password handling
    # ------------------------------------------------------------------------

    def set_password(self, password: str):
        self.password_hash = password

    def check_password(self, password: str) -> bool:
        return self.password_hash == password

    # ------------------------------------------------------------------------
    # Flask-Login
    # ------------------------------------------------------------------------

    def get_id(self):
        """
        Prefix the ID so Flask-Login knows this is an admin user.
        Example: admin:1
        """
        return f"admin:{self.id}"


# ============================================================================
# Client
# ============================================================================

class Client(UserMixin, db.Model):
    __tablename__ = "clients"

    client_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    mail_id = db.Column(
        db.String(160),
        nullable=False
    )

    login_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    # ------------------------------------------------------------------------
    # Role
    # ------------------------------------------------------------------------

    @property
    def role(self):
        """
        This is a Python property only.
        It does NOT create or modify a database column.
        """
        return "client"

    # ------------------------------------------------------------------------
    # Plain-text password handling
    # ------------------------------------------------------------------------

    def set_password(self, password: str):
        self.password = password

    def check_password(self, password: str) -> bool:
        return self.password == password

    # ------------------------------------------------------------------------
    # Flask-Login
    # ------------------------------------------------------------------------

    def get_id(self):
        """
        Prefix the ID so Flask-Login knows this is a client.
        Example: client:1
        """
        return f"client:{self.client_id}"


# ============================================================================
# Apricus
# ============================================================================

class Apricus(db.Model):
    __tablename__ = "apricus"

    # Python attribute: client_code
    # Database column: id
    client_code = db.Column(
        "id",
        db.String(50),
        primary_key=True
    )

    date = db.Column(
        "Date",
        db.Date,
        primary_key=True
    )

    name = db.Column(
        "Name",
        db.String(255)
    )

    investmt_amt = db.Column(
        "Investmt_Amt",
        db.Numeric(15, 2)
    )

    funds_added = db.Column(
        "funds_added",
        db.Numeric(15, 2)
    )

    funds_withdrawn = db.Column(
        "funds_withdrawn",
        db.Numeric(15, 2)
    )

    mtm = db.Column(
        "MTM",
        db.Numeric(15, 2)
    )

    prev_free_cash_bal = db.Column(
        "prev_free_cash_bal",
        db.Numeric(15, 2)
    )

    current_cash = db.Column(
        "Current_Cash",
        db.Numeric(15, 2)
    )

    difference = db.Column(
        "Difference",
        db.Numeric(15, 2)
    )

    cumulative_mtm = db.Column(
        "Cumulative_MTM",
        db.Numeric(15, 2)
    )


# ============================================================================
# Cash Record
# ============================================================================

class CashRecord(db.Model):
    __tablename__ = "cash_record"

    id = db.Column(
        db.String(50),
        primary_key=True
    )

    date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    funds_added = db.Column(
        db.Float
    )

    funds_withdrawn = db.Column(
        db.Float
    )

    prev_free_cash_bal = db.Column(
        db.Float
    )

    current_cash = db.Column(
        db.Float
    )

    difference = db.Column(
        db.Float
    )


# ============================================================================
# Trade Data
# ============================================================================

class TradeData(db.Model):
    __tablename__ = "trade_data"

    id = db.Column(
        db.String(50),
        primary_key=True
    )

    date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    investmt_amt = db.Column(
        db.Float
    )

    mtm = db.Column(
        db.Float
    )

    cumulative_mtm = db.Column(
        db.Float
    )