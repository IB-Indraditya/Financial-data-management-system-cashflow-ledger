from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

from models import AdminUser, Client


auth_bp = Blueprint(
    "auth",
    __name__
)


# ============================================================================
# Login
# ============================================================================

@auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # ------------------------------------------------------------------------
    # Already logged in
    # ------------------------------------------------------------------------

    if current_user.is_authenticated:

        if getattr(current_user, "role", None) == "client":

            return redirect(
                url_for(
                    "dashboard.client_detail",
                    client_id=current_user.client_id
                )
            )

        return redirect(
            url_for(
                "dashboard.overview"
            )
        )

    # ------------------------------------------------------------------------
    # Login request
    # ------------------------------------------------------------------------

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # ====================================================================
        # 1. CHECK ADMIN
        # ====================================================================

        admin = AdminUser.query.filter(
            AdminUser.email == email
        ).first()

        if admin:

            if admin.check_password(password):

                login_user(
                    admin,
                    remember=True
                )

                next_url = (
                    request.args.get("next")
                    or url_for("dashboard.overview")
                )

                return redirect(next_url)

        # ====================================================================
        # 2. CHECK CLIENT
        # ====================================================================

        client = Client.query.filter(
            Client.mail_id == email
        ).first()

        if client:

            if client.check_password(password):

                login_user(
                    client,
                    remember=True
                )

                return redirect(
                    url_for(
                        "dashboard.client_detail",
                        client_id=client.client_id
                    )
                )

        # ====================================================================
        # INVALID CREDENTIALS
        # ====================================================================

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# ============================================================================
# Logout
# ============================================================================

@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been signed out.",
        "success"
    )

    return redirect(
        url_for(
            "main.landing"
        )
    )