import os

from flask import Flask

from dotenv import load_dotenv

from config import Config

from extensions import (
    db,
    login_manager
)


# ============================================================================
# Load .env
# ============================================================================

load_dotenv()


# ============================================================================
# Application Factory
# ============================================================================

def create_app():

    app = Flask(
        __name__,
        instance_relative_config=True
    )

    app.config.from_object(
        Config
    )

    os.makedirs(
        app.instance_path,
        exist_ok=True
    )

    # ------------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------------

    db.init_app(
        app
    )

    login_manager.init_app(
        app
    )

    # ------------------------------------------------------------------------
    # Flask-Login
    # ------------------------------------------------------------------------

    from models import (
        AdminUser,
        Client
    )

    @login_manager.user_loader
    def load_user(user_id):

        if not user_id:
            return None

        try:

            if user_id.startswith("admin:"):

                admin_id = int(
                    user_id.split(
                        ":",
                        1
                    )[1]
                )

                return AdminUser.query.get(
                    admin_id
                )

            if user_id.startswith("client:"):

                client_id = int(
                    user_id.split(
                        ":",
                        1
                    )[1]
                )

                return Client.query.get(
                    client_id
                )

        except (
            ValueError,
            TypeError,
            AttributeError
        ):

            return None

        return None

    # ------------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------------

    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.api import api_bp

    app.register_blueprint(
        main_bp
    )

    app.register_blueprint(
        auth_bp
    )

    app.register_blueprint(
        dashboard_bp
    )

    app.register_blueprint(
        api_bp
    )

    # ------------------------------------------------------------------------
    # Database / Admin seed
    # ------------------------------------------------------------------------

    with app.app_context():

        db.create_all()

        admin_email = app.config[
            "SEED_ADMIN_EMAIL"
        ]

        admin_password = app.config[
            "SEED_ADMIN_PASSWORD"
        ]

        admin = AdminUser.query.filter_by(
            email=admin_email
        ).first()

        if not admin:

            admin = AdminUser(
                name="ACPL Admin",
                email=admin_email,
                role="admin"
            )

            admin.set_password(
                admin_password
            )

            db.session.add(
                admin
            )

            db.session.commit()

    return app


# ============================================================================
# Application
# ============================================================================

app = create_app()


# ============================================================================
# Development server
# ============================================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )