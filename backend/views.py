from flask import render_template, request, redirect, url_for, flash
from app import app, db, bcrypt
from backend.models import User


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        # Verifica o usuário e a senha
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.senha, senha):
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Credenciais incorretas. Tente novamente.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome") 
        email = request.form.get("email")
        senha = request.form.get("senha")
        confirmar_senha = request.form.get("confirmar_senha")

        if senha == confirmar_senha:
            hashed_senha = bcrypt.generate_password_hash(senha).decode("utf-8")
            novo_usuario = User(nome=nome, email=email, senha=hashed_senha)
            db.session.add(novo_usuario)
            db.session.commit()
            flash("Cadastro realizado com sucesso! Faça o login.", "success")
            return redirect(url_for("login"))
        else:
            flash("As senhas não coincidem. Tente novamente.", "danger")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return "Bem-vindo ao seu dashboard!"
