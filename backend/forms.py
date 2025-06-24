from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, TextAreaField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms.fields import SelectField

class ClienteRegisterForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    submit = SubmitField('Cadastrar')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class CadastroProfissionalForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    submit = SubmitField('Cadastrar Profissional')

class CadastroServicoForm(FlaskForm):
    nome = StringField('Nome do Serviço', validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    preco = DecimalField('Preço', validators=[DataRequired()])
    duracao = IntegerField('Duração (minutos)', validators=[DataRequired()])
    submit = SubmitField('Cadastrar Serviço')

class AgendamentoForm(FlaskForm):
    cliente_nome = StringField('Nome do Cliente', validators=[DataRequired()])
    cliente_telefone = StringField('Telefone do Cliente', validators=[DataRequired()])
    cliente_email = StringField('Email do Cliente', validators=[Email()])
    servico_id = SelectField('Serviço', coerce=int, validators=[DataRequired()])
    profissional_id = SelectField('Profissional', coerce=int, validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()])
    horario = SelectField('Horário', choices=[], coerce=str, validators=[DataRequired()])
    submit = SubmitField('Agendar')

class AgendaForm(FlaskForm):
    data = DateField('Data', validators=[DataRequired()])
    horario = TimeField('Horário de Início', validators=[DataRequired()])
    submit = SubmitField('Adicionar')

class AtribuirServicoForm(FlaskForm):
    servico_id = SelectField('Selecione o Serviço', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Atribuir Serviço')