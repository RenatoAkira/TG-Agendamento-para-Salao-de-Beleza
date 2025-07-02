from datetime import datetime, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from backend import db

class Cliente(db.Model, UserMixin):
    __tablename__ = 'clientes'

    idCliente = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)

    agendamentos = db.relationship('Agendamento', back_populates='cliente', lazy=True)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def get_id(self):
        return f"cliente-{self.idCliente}"

class Administrador(UserMixin, db.Model):
    __tablename__ = 'administradores'

    idAdministrador = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def get_id(self):
        return f"admin-{self.idAdministrador}"

class Profissional(UserMixin, db.Model):
    __tablename__ = 'profissionais'

    idProfissional = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)

    servicos = db.relationship('ProfissionalServico', back_populates='profissional', lazy=True)
    agendas = db.relationship('Agenda', back_populates='profissional', lazy=True)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def get_id(self):
        return f"prof-{self.idProfissional}"

class Servico(db.Model):
    __tablename__ = 'servicos'

    idServico = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    duracao = db.Column(db.Integer, nullable=False)

    profissional_servicos = db.relationship('ProfissionalServico', back_populates='servico', lazy=True)

class ProfissionalServico(db.Model):
    __tablename__ = 'profissional_servicos'

    idProfissionalServico = db.Column(db.Integer, primary_key=True)
    idProfissional = db.Column(db.Integer, db.ForeignKey('profissionais.idProfissional'), nullable=False)
    idServico = db.Column(db.Integer, db.ForeignKey('servicos.idServico'), nullable=False)

    profissional = db.relationship('Profissional', back_populates='servicos')
    servico = db.relationship('Servico', back_populates='profissional_servicos')
    agendamentos = db.relationship('Agendamento', back_populates='profissional_servico', lazy=True)

class Agenda(db.Model):
    __tablename__ = 'agendas'

    idAgenda = db.Column(db.Integer, primary_key=True)
    idProfissional = db.Column(db.Integer, db.ForeignKey('profissionais.idProfissional'), nullable=False)
    diaSemana = db.Column(db.Integer, nullable=False)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFim = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='ativo')

    profissional = db.relationship('Profissional', back_populates='agendas')

class Agendamento(db.Model):
    __tablename__ = 'agendamentos'

    idAgendamento = db.Column(db.Integer, primary_key=True)
    idCliente = db.Column(db.Integer, db.ForeignKey('clientes.idCliente'), nullable=False)
    idProfissionalServico = db.Column(db.Integer, db.ForeignKey('profissional_servicos.idProfissionalServico'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    horaInicio = db.Column(db.Time, nullable=False)
    horaFim = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='pendente')

    cliente = db.relationship('Cliente', back_populates='agendamentos')
    profissional_servico = db.relationship('ProfissionalServico', back_populates='agendamentos')
