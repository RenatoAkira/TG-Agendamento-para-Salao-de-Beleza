import os
from datetime import datetime, date, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify, abort
from backend import db, bcrypt, login_manager
from flask import current_app as app
from backend.models import Cliente, Profissional, Administrador, Servico, ProfissionalServico, Agenda, Agendamento
from backend.forms import ClienteRegisterForm, LoginForm, CadastroProfissionalForm, CadastroServicoForm, AgendamentoForm, AgendaForm, AtribuirServicoForm
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith('admin-'):
        admin_id = user_id.split('-')[1]
        return Administrador.query.get(admin_id)
    elif user_id.startswith('prof-'):
        prof_id = user_id.split('-')[1]
        return Profissional.query.get(prof_id)
    else:
        return None
@app.route("/")
def index():
    return render_template("apresentacao.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        senha = form.senha.data

        user = Administrador.query.filter_by(email=email).first()
        if user and user.check_password(senha):
            login_user(user)
            return redirect(url_for('admin_inicio'))

        user = Profissional.query.filter_by(email=email).first()
        if user and user.check_password(senha):
            login_user(user)
            return redirect(url_for('profissional_inicio'))

        cliente = Cliente.query.filter_by(email=email).first()
        if cliente and cliente.check_password(senha):
            session['cliente_id'] = cliente.idCliente
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('cliente_inicio'))

        flash('Credenciais incorretas.', 'error')
        return redirect(url_for('index'))

    return render_template('login.html', form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = ClienteRegisterForm()
    if form.validate_on_submit():
        if Cliente.query.filter_by(email=form.email.data).first():
            flash('E-mail já cadastrado.', 'error')
            return redirect(url_for('register'))

        novo_cliente = Cliente(
            nome=form.nome.data,
            telefone=form.telefone.data,
            email=form.email.data
        )
        novo_cliente.set_password(form.senha.data)
        db.session.add(novo_cliente)
        db.session.commit()
        flash('Cadastro realizado com sucesso!', 'success')
        return redirect(url_for("login"))

    return render_template("register.html", form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/cliente/inicio')
@login_required
def cliente_inicio():
    # Só permite acesso se for cliente (não administrador nem profissional)
    if 'cliente_id' not in session:
        flash('Acesso restrito a clientes.', 'error')
        return redirect(url_for('login'))

    return render_template('inicio.html')

@app.route('/servicos')
def listar_servicos():
    servicos = Servico.query.all()
    return render_template('servicos.html', servicos=servicos)

@app.route('/escolher-profissional/<int:servico_id>')
def escolher_profissional(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    profissionais = db.session.query(Profissional).join(ProfissionalServico).filter(
        ProfissionalServico.idServico == servico_id
    ).all()
    return render_template('escolherProfissional.html', servico=servico, profissionais=profissionais)

@app.route('/horario/<int:profissional_id>/<int:servico_id>', methods=['GET'])
def selecionar_horario(profissional_id, servico_id):
    profissional = Profissional.query.get_or_404(profissional_id)
    servico = Servico.query.get_or_404(servico_id)

    data_str = request.args.get('data')
    horarios_disponiveis = []

    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
            dia_semana = data_selecionada.weekday()  # Segunda=0 ... Domingo=6

            # Busca os horários da Agenda para o profissional naquele dia da semana
            agendas = Agenda.query.filter_by(
                idProfissional=profissional_id,
                diaSemana=dia_semana,
                status='ativo'
            ).all()

            # Pega os horários já agendados naquela data
            agendados = (
                Agendamento.query
                .filter(
                    Agendamento.data == data_selecionada,
                    Agendamento.status.in_(["pendente", "realizado"])
                )
                .join(ProfissionalServico)
                .filter(ProfissionalServico.idProfissional == profissional_id)
                .with_entities(Agendamento.horaInicio)
                .all()
            )

            horarios_ocupados = [a.horaInicio for a in agendados]

            # Só adiciona na lista os horários que estão na agenda e ainda livres
            for agenda in agendas:
                if agenda.horaInicio not in horarios_ocupados:
                    horarios_disponiveis.append(agenda.horaInicio.strftime('%H:%M'))

        except ValueError:
            flash('Data inválida.', 'error')
            return redirect(url_for('listar_servicos'))

    return render_template(
        'horario.html',
        profissional=profissional,
        servico=servico,
        horarios=horarios_disponiveis,
        data_selecionada=data_str  # Para preencher o campo data no HTML
    )
    
@app.route('/confirmar-agendamento', methods=['POST'])
def confirmar_agendamento():
    cliente_nome = request.form.get('cliente_nome')
    cliente_telefone = request.form.get('cliente_telefone')
    cliente_email = request.form.get('cliente_email')
    data_str = request.form.get('data')
    horario_str = request.form.get('horario')
    servico_id = request.form.get('servico_id')
    profissional_id = request.form.get('profissional_id')

    if not all([cliente_nome, cliente_telefone, data_str, horario_str, servico_id, profissional_id]):
        flash('Todos os campos devem ser preenchidos.', 'error')
        return redirect(url_for('listar_servicos'))

    data_agendamento = datetime.strptime(data_str, '%Y-%m-%d').date()
    hora_inicio = datetime.strptime(horario_str, '%H:%M').time()

    cliente = Cliente.query.filter_by(telefone=cliente_telefone).first()
    if not cliente:
        cliente = Cliente(nome=cliente_nome, telefone=cliente_telefone, email=cliente_email)
        cliente.set_password("123456")
        db.session.add(cliente)
        db.session.flush()

    profissional_servico = ProfissionalServico.query.filter_by(
        idProfissional=profissional_id, idServico=servico_id).first()

    servico = Servico.query.get(servico_id)
    duracao = timedelta(minutes=servico.duracao)
    hora_fim = (datetime.combine(date.today(), hora_inicio) + duracao).time()

    agendamento = Agendamento(
        idCliente=cliente.idCliente,
        idProfissionalServico=profissional_servico.idProfissionalServico,
        data=data_agendamento,
        horaInicio=hora_inicio,
        horaFim=hora_fim
    )
    db.session.add(agendamento)
    db.session.commit()

    flash('Agendamento realizado com sucesso!', 'success')
    return redirect(url_for('cliente_inicio'))

@app.route('/historico')
@login_required
def historico():
    # Só permite acesso se for cliente (e não admin ou profissional)
    cliente_id = session.get('cliente_id')
    if not cliente_id:
        flash('Acesso restrito a clientes.', 'error')
        return redirect(url_for('login'))

    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        flash('Cliente não encontrado.', 'error')
        return redirect(url_for('login'))

    agendamentos = Agendamento.query.filter_by(idCliente=cliente.idCliente).all()
    return render_template('historico.html', agendamentos=agendamentos)

@app.route('/profissional/inicio')
@login_required
def profissional_inicio():
    if not isinstance(current_user._get_current_object(), Profissional):
        abort(403)
    return render_template('profissional-inicio.html')

@app.route('/profissional/agenda')
@login_required
def profissional_agenda():
    if not isinstance(current_user._get_current_object(), Profissional):
        abort(403)

    # Gera lista de datas: hoje + próximos 4 dias
    hoje = date.today()
    datas = [hoje + timedelta(days=i) for i in range(5)]

    # Captura a data selecionada pela URL, se houver
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Data inválida.', 'error')
            return redirect(url_for('profissional_agenda'))
    else:
        data_selecionada = hoje

    # Busca agendamentos para aquele profissional e para a data selecionada
    agendamentos = (
        Agendamento.query
        .join(ProfissionalServico)
        .filter(
            ProfissionalServico.idProfissional == current_user.idProfissional,
            Agendamento.data == data_selecionada
        )
        .all()
    )

    return render_template(
        'profissional-agenda.html',
        datas=datas,
        data_selecionada=data_selecionada,
        agendamentos=agendamentos
    )


@app.route('/admin/inicio')
@login_required
def admin_inicio():
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)
    return render_template('adm_Inicio.html')

@app.route('/admin/servicos')
@login_required
def admin_servicos():
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)
    servicos = Servico.query.all()
    return render_template('adm-servicos.html', servicos=servicos)

@app.route('/admin/profissionais')
@login_required
def admin_profissionais():
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)
    profissionais = Profissional.query.all()
    return render_template('profissionais.html', profissionais=profissionais)

@app.route('/admin/cadastrar-servico', methods=['GET', 'POST'])
@login_required
def cadastrar_servico():
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    form = CadastroServicoForm()
    if form.validate_on_submit():
        servico = Servico(
            nome=form.nome.data,
            descricao=form.descricao.data,
            preco=form.preco.data,
            duracao=form.duracao.data
        )
        db.session.add(servico)
        db.session.commit()
        flash('Serviço cadastrado com sucesso.', 'success')
        return redirect(url_for('admin_servicos'))

    return render_template('cadastrar-servico.html', form=form, titulo_pagina='Cadastrar Serviço')

@app.route('/admin/editar-servico/<int:servico_id>', methods=['GET', 'POST'])
@login_required
def editar_servico(servico_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    servico = Servico.query.get_or_404(servico_id)
    form = CadastroServicoForm(obj=servico)

    if form.validate_on_submit():
        servico.nome = form.nome.data
        servico.descricao = form.descricao.data
        servico.preco = form.preco.data
        servico.duracao = form.duracao.data
        db.session.commit()
        flash('Serviço atualizado com sucesso!', 'success')
        return redirect(url_for('admin_servicos'))

    return render_template('cadastrar-servico.html', form=form, titulo_pagina='Editar Serviço')

@app.route('/admin/cadastrar-profissional', methods=['GET', 'POST'])
@login_required
def cadastrar_profissional():
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    form = CadastroProfissionalForm()
    if form.validate_on_submit():
        profissional = Profissional(
            nome=form.nome.data,
            telefone=form.telefone.data,
            email=form.email.data
        )
        profissional.set_password(form.senha.data)
        db.session.add(profissional)
        db.session.commit()
        flash('Profissional cadastrado com sucesso.', 'success')
        return redirect(url_for('admin_profissionais'))

    return render_template('cadastrar-profissional.html', form=form, titulo_pagina='Cadastrar Profissional')

@app.route('/admin/profissional/<int:profissional_id>', methods=['GET', 'POST'])
@login_required
def servico_profissional(profissional_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    profissional = Profissional.query.get_or_404(profissional_id)
    form = AtribuirServicoForm()
    agenda_form = AgendaForm()

    # Preenche os serviços disponíveis para o select
    form.servico_id.choices = [(s.idServico, s.nome) for s in Servico.query.all()]

    if form.validate_on_submit():
        servico_id = form.servico_id.data

        # Verifica se já existe o vínculo antes de criar
        existente = ProfissionalServico.query.filter_by(
            idProfissional=profissional_id,
            idServico=servico_id
        ).first()

        if existente:
            flash('Este serviço já está atribuído ao profissional.', 'warning')
        else:
            novo_vinculo = ProfissionalServico(
                idProfissional=profissional_id,
                idServico=servico_id
            )
            db.session.add(novo_vinculo)
            db.session.commit()
            flash('Serviço atribuído ao profissional com sucesso!', 'success')

        return redirect(url_for('servico_profissional', profissional_id=profissional_id))

    return render_template('servico-profissional.html', profissional=profissional, form=form, agenda_form=agenda_form)



@app.route('/admin/atribuir-servico/<int:profissional_id>', methods=['POST'])
@login_required
def atribuir_servico(profissional_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    form = CadastroServicoForm()  # Se você tiver um form específico para isso, troque aqui
    servico_id = request.form.get('servico_id')

    if servico_id:
        # Verifica se o vínculo já existe
        existente = ProfissionalServico.query.filter_by(
            idProfissional=profissional_id,
            idServico=servico_id
        ).first()

        if not existente:
            novo_vinculo = ProfissionalServico(
                idProfissional=profissional_id,
                idServico=servico_id
            )
            db.session.add(novo_vinculo)
            db.session.commit()
            flash('Serviço atribuído ao profissional com sucesso!', 'success')
        else:
            flash('Este serviço já está vinculado ao profissional.', 'warning')

    return redirect(url_for('servico_profissional', profissional_id=profissional_id))



@app.route('/admin/profissional/<int:profissional_id>/adicionar-disponibilidade', methods=['POST'])
@login_required
def adicionar_disponibilidade(profissional_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    agenda_form = AgendaForm()
    if agenda_form.validate_on_submit():
        nova_agenda = Agenda(
            idProfissional=profissional_id,
            diaSemana=agenda_form.data.data.weekday(),
            horaInicio=agenda_form.horario.data,
            horaFim=(datetime.combine(date.today(), agenda_form.horario.data) + timedelta(minutes=60)).time(),
            status='ativo'
        )
        db.session.add(nova_agenda)
        db.session.commit()
        flash('Disponibilidade adicionada com sucesso!', 'success')

    return redirect(url_for('servico_profissional', profissional_id=profissional_id))


@app.route('/admin/editar-profissional/<int:profissional_id>', methods=['GET', 'POST'])
@login_required
def editar_profissional(profissional_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    profissional = Profissional.query.get_or_404(profissional_id)
    form = CadastroProfissionalForm(obj=profissional)

    if form.validate_on_submit():
        profissional.nome = form.nome.data
        profissional.telefone = form.telefone.data
        profissional.email = form.email.data
        if form.senha.data:
            profissional.set_password(form.senha.data)
        db.session.commit()
        flash('Profissional atualizado com sucesso!', 'success')
        return redirect(url_for('servico_profissional', profissional_id=profissional.idProfissional))

    return render_template('cadastrar-profissional.html', form=form, titulo_pagina='Editar Profissional')


@app.route('/profissional/agendar', methods=['GET', 'POST'])
@login_required
def profissional_agendar():
    if not isinstance(current_user._get_current_object(), Profissional):
        abort(403)

    form = AgendamentoForm()

    # Preenche os serviços que o profissional oferece
    servicos_profissional = db.session.query(Servico).join(ProfissionalServico).filter(
        ProfissionalServico.idProfissional == current_user.idProfissional
    ).all()
    form.servico_id.choices = [(s.idServico, s.nome) for s in servicos_profissional]
    form.profissional_id.choices = [(current_user.idProfissional, current_user.nome)]

    # Se o POST veio para carregar os horários da data escolhida
    if form.data.data and (request.method == 'POST' and request.form.get('carregar_horarios') == '1'):
        dia_semana = form.data.data.weekday()

        # Horários da agenda
        agendas = Agenda.query.filter_by(
            idProfissional=current_user.idProfissional,
            diaSemana=dia_semana,
            status='ativo'
        ).all()

        # Horários ocupados
        agendados = (
            Agendamento.query
            .join(ProfissionalServico)
            .filter(
                ProfissionalServico.idProfissional == current_user.idProfissional,
                Agendamento.data == form.data.data,
                Agendamento.status.in_(["pendente", "realizado"])
            )
            .with_entities(Agendamento.horaInicio)
            .all()
        )
        horarios_ocupados = [a.horaInicio for a in agendados]

        # Preenche os horários livres
        horarios_livres = []
        for agenda in agendas:
            if agenda.horaInicio not in horarios_ocupados:
                horarios_livres.append((agenda.horaInicio.strftime('%H:%M'), agenda.horaInicio.strftime('%H:%M')))

        form.horario.choices = horarios_livres

    # Se for um POST final (tentando agendar)
    if request.method == 'POST' and request.form.get('carregar_horarios') != '1':
        horario_str = request.form.get('horario')

        if not horario_str:
            flash('Por favor, selecione um horário antes de confirmar o agendamento.', 'error')
            return redirect(url_for('profissional_agendar'))

        try:
            horario_obj = datetime.strptime(horario_str, '%H:%M').time()
        except ValueError:
            flash('Horário inválido.', 'error')
            return redirect(url_for('profissional_agendar'))

        # Corrige manualmente o campo horario para o Flask-WTF aceitar
        form.horario.data = horario_obj

        if form.validate_on_submit():
            cliente_nome = form.cliente_nome.data
            cliente_telefone = form.cliente_telefone.data
            cliente_email = form.cliente_email.data
            data_agendamento = form.data.data
            servico_id = form.servico_id.data

            # Busca ou cria o cliente
            cliente = Cliente.query.filter_by(telefone=cliente_telefone).first()
            if not cliente:
                cliente = Cliente(nome=cliente_nome, telefone=cliente_telefone, email=cliente_email)
                cliente.set_password("123456")
                db.session.add(cliente)
                db.session.flush()

            profissional_servico = ProfissionalServico.query.filter_by(
                idProfissional=current_user.idProfissional,
                idServico=servico_id
            ).first()

            if not profissional_servico:
                flash('Este profissional não oferece o serviço selecionado.', 'error')
                return redirect(url_for('profissional_agendar'))

            servico = Servico.query.get(servico_id)
            duracao = timedelta(minutes=servico.duracao)
            hora_fim = (datetime.combine(date.today(), horario_obj) + duracao).time()

            novo_agendamento = Agendamento(
                idCliente=cliente.idCliente,
                idProfissionalServico=profissional_servico.idProfissionalServico,
                data=data_agendamento,
                horaInicio=horario_obj,
                horaFim=hora_fim,
                status='pendente'
            )

            db.session.add(novo_agendamento)
            db.session.commit()
            flash('Agendamento realizado com sucesso!', 'success')
            return redirect(url_for('profissional_inicio'))
        else:
            flash('Por favor, preencha todos os campos obrigatórios corretamente.', 'error')
            return redirect(url_for('profissional_agendar'))

    return render_template('profissional-agendar.html', form=form)

@app.route('/cancelar-agendamento/<int:agendamento_id>', methods=['POST'])
@login_required
def cancelar_agendamento(agendamento_id):
    cliente_id = session.get('cliente_id')
    if not cliente_id:
        flash('Acesso restrito a clientes.', 'error')
        return redirect(url_for('login'))

    agendamento = Agendamento.query.get_or_404(agendamento_id)

    # Verifica se o agendamento pertence ao cliente e está pendente
    if agendamento.idCliente != cliente_id:
        flash('Você não tem permissão para cancelar este agendamento.', 'error')
        return redirect(url_for('historico'))

    if agendamento.status != 'pendente':
        flash('Somente agendamentos pendentes podem ser cancelados.', 'error')
        return redirect(url_for('historico'))

    # Atualiza o status para cancelado
    agendamento.status = 'cancelado'
    db.session.commit()

    flash('Agendamento cancelado com sucesso.', 'success')
    return redirect(url_for('historico'))

@app.route('/profissional/agendamento/<int:agendamento_id>/realizado', methods=['POST'])
@login_required
def confirmar_realizacao(agendamento_id):
    if not isinstance(current_user._get_current_object(), Profissional):
        abort(403)

    agendamento = Agendamento.query.get_or_404(agendamento_id)

    # Verificar se o agendamento pertence ao profissional logado
    if agendamento.profissional_servico.profissional.idProfissional != current_user.idProfissional:
        abort(403)

    # Muda o status
    agendamento.status = 'realizado'
    db.session.commit()

    # Redireciona para a mesma data que o agendamento era
    data_str = agendamento.data.strftime('%Y-%m-%d')
    return redirect(url_for('profissional_agenda', data=data_str))
