from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Configuração do banco de dados
app.config['SECRET_KEY'] = 'f58d9b42b530448d66e5df38d03a5ec0'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Importando rotas e modelos
from backend import views, models

if __name__ == '__main__':
    # Cria o contexto da aplicação para executar db.create_all()
    with app.app_context():
        db.create_all()  # Criando tabelas no banco de dados
    app.run(debug=True)