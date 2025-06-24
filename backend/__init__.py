from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login'

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SECRET_KEY'] = 'f58d9b42b530448d66e5df38d03a5ec0'

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    with app.app_context():
        from backend import views, models

        # Criar admin padrão se não existir
        from backend.models import Administrador
        if not Administrador.query.filter_by(email='admin@salao.com').first():
            novo_admin = Administrador(
                nome='Administrador',
                email='admin@salao.com'
            )
            novo_admin.set_password('admin123')
            db.session.add(novo_admin)
            db.session.commit()

    return app
