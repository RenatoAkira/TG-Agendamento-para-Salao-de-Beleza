from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, TextAreaField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, Optional
from wtforms.fields import SelectField

class ClienteRegisterForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    submit = SubmitField('Cadastrar')
    

class ClientePerfilForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    nova_senha = PasswordField('Nova Senha', validators=[Optional()])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[EqualTo('nova_senha', message='As senhas não coincidem')])
    submit = SubmitField('Salvar Alterações')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class BaseProfissionalForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField()

class CadastroProfissionalForm(BaseProfissionalForm):
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    submit = SubmitField('Cadastrar Profissional')

class EdicaoProfissionalForm(BaseProfissionalForm):
    senha = PasswordField('Senha', validators=[Optional(), Length(min=6)])
    confirmar_senha = PasswordField('Confirmar Senha', validators=[Optional(), EqualTo('senha')])
    submit = SubmitField('Salvar Alterações')

class CadastroServicoForm(FlaskForm):
    nome = StringField('Nome do Serviço', validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[DataRequired()])
    preco = DecimalField('Preço', validators=[DataRequired()])
    duracao = IntegerField('Duração (minutos)', validators=[DataRequired()])
    submit = SubmitField('Cadastrar Serviço')

class AgendamentoForm(FlaskForm):
    cliente_nome = StringField('Nome do Cliente', validators=[DataRequired()])
    cliente_telefone = StringField(
        'Telefone do Cliente',
        validators=[
            DataRequired(),
            Regexp(r'^\d{8,15}$', message="Digite um número de telefone válido, com apenas dígitos.")
        ]
    )
    cliente_email = StringField('Email do Cliente', validators=[Email()])
    servico_id = SelectField('Serviço', coerce=int, validators=[DataRequired()])
    data = DateField('Data', validators=[DataRequired()])
    horario = SelectField('Horário', choices=[], coerce=str, validators=[DataRequired()])
    submit = SubmitField('Agendar')

class AgendaForm(FlaskForm):
    data = DateField('Data', validators=[DataRequired()])
    horario_inicio = TimeField('Horário Início', validators=[DataRequired()])
    horario_fim = TimeField('Horário Fim', validators=[DataRequired()])
    submit = SubmitField('Adicionar Horário')

class AtribuirServicoForm(FlaskForm):
    servico_id = SelectField('Selecione o Serviço', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Atribuir Serviço')
    
class ClienteAdminForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    telefone = StringField('Telefone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])