import os
from datetime import datetime, date, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify, abort
from backend import db, bcrypt, login_manager
from flask import current_app as app
from backend.models import Cliente, Profissional, Administrador, Servico, ProfissionalServico, Agenda, Agendamento
from backend.forms import ClienteAdminForm, ClientePerfilForm, ClienteRegisterForm, LoginForm, CadastroProfissionalForm, CadastroServicoForm, AgendamentoForm, AgendaForm, AtribuirServicoForm
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
    elif user_id.startswith('cliente-'):
        cliente_id = user_id.split('-')[1]
        return Cliente.query.get(cliente_id)
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

        print(f"Tentando login com email: {email}")

        user = Administrador.query.filter_by(email=email).first()
        if user and user.check_password(senha):
            print("Login como Administrador")
            login_user(user)
            return redirect(url_for('admin_inicio'))

        user = Profissional.query.filter_by(email=email).first()
        if user and user.check_password(senha):
            print("Login como Profissional")
            login_user(user)
            return redirect(url_for('profissional_inicio'))

        cliente = Cliente.query.filter_by(email=email).first()
        if cliente and cliente.check_password(senha):
            print("Login como Cliente")
            login_user(cliente)
            # flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('cliente_inicio'))

        print("Login falhou para todos os tipos.")
        flash('Credenciais incorretas.', 'error')
        return redirect(url_for('login'))

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
    if not isinstance(current_user._get_current_object(), Cliente):
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
    if not isinstance(current_user._get_current_object(), Cliente):
        flash('Acesso restrito a clientes.', 'error')
        return redirect(url_for('login'))

    agendamentos = Agendamento.query.filter_by(idCliente=current_user.idCliente).all()
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

    return render_template(
    'cadastrar-servico.html',
    form=form,
    titulo_pagina='Cadastrar Serviço',
    texto_botao='Cadastrar Serviço'
)


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

    return render_template(
    'cadastrar-servico.html',
    form=form,
    titulo_pagina='Editar Serviço',
    texto_botao='Salvar Alterações'
)


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

from datetime import datetime, timedelta
from flask import flash

@app.route('/admin/profissional/<int:profissional_id>/adicionar-disponibilidade', methods=['POST'])
@login_required
def adicionar_disponibilidade(profissional_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    profissional = Profissional.query.get_or_404(profissional_id)
    agenda_form = AgendaForm()

    if agenda_form.validate_on_submit():
        data = agenda_form.data.data
        hora_inicio = agenda_form.horario_inicio.data
        hora_fim = agenda_form.horario_fim.data

        if hora_inicio >= hora_fim:
            flash("A hora de início deve ser menor que a hora de fim.", "error")
            return redirect(url_for('servico_profissional', profissional_id=profissional.idProfissional))

        hora_atual = datetime.combine(data, hora_inicio)
        hora_fim_dt = datetime.combine(data, hora_fim)

        registros_criados = 0

        while hora_atual < hora_fim_dt:
            proxima_hora = hora_atual + timedelta(hours=1)

            nova_agenda = Agenda(
                idProfissional=profissional.idProfissional,
                diaSemana=data.weekday(),
                horaInicio=hora_atual.time(),
                horaFim=proxima_hora.time(),
                status='ativo'
            )
            db.session.add(nova_agenda)
            registros_criados += 1
            hora_atual = proxima_hora

        db.session.commit()
        flash(f"{registros_criados} horários cadastrados com sucesso!", "success")
    else:
        flash("Erro no formulário. Verifique os dados preenchidos.", "error")

    return redirect(url_for('servico_profissional', profissional_id=profissional.idProfissional))


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
    print("📥 Entrou na rota profissional_agendar com método:", request.method)
    print("📦 Dados recebidos:", request.form)

    if not isinstance(current_user._get_current_object(), Profissional):
        abort(403)

    form = AgendamentoForm()

    # Carrega os serviços do profissional logado
    servicos_profissional = db.session.query(Servico).join(ProfissionalServico).filter(
        ProfissionalServico.idProfissional == current_user.idProfissional
    ).all()
    form.servico_id.choices = [(s.idServico, s.nome) for s in servicos_profissional]

    # Se for apenas carregar os horários
    if request.method == 'POST' and request.form.get('carregar_horarios') == '1' and form.data.data:
        dia_semana = form.data.data.weekday()

        agendas = Agenda.query.filter_by(
            idProfissional=current_user.idProfissional,
            diaSemana=dia_semana,
            status='ativo'
        ).all()

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

        horarios_livres = []
        for agenda in agendas:
            if agenda.horaInicio not in horarios_ocupados:
                horarios_livres.append((agenda.horaInicio.strftime('%H:%M:%S'), agenda.horaInicio.strftime('%H:%M')))

        form.horario.choices = horarios_livres
        return render_template('profissional-agendar.html', form=form)

    # Se for o POST final de agendamento
    elif request.method == 'POST' and request.form.get('carregar_horarios') != '1':
        horario_str = request.form.get('horario')
        if not horario_str:
            flash('Por favor, selecione um horário.', 'error')
            return redirect(url_for('profissional_agendar'))

        # Corrigido: mantém como string, pois SelectField usa string
        form.horario.data = horario_str

        if not form.data.data:
            flash("Data não selecionada corretamente.", "error")
            return redirect(url_for("profissional_agendar"))

        dia_semana = form.data.data.weekday()
        agendas = Agenda.query.filter_by(
            idProfissional=current_user.idProfissional,
            diaSemana=dia_semana,
            status='ativo'
        ).all()

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

        horarios_livres = []
        for agenda in agendas:
            if agenda.horaInicio not in horarios_ocupados:
                horarios_livres.append((agenda.horaInicio.strftime('%H:%M:%S'), agenda.horaInicio.strftime('%H:%M')))

        form.horario.choices = horarios_livres

        # DEBUG
        print("🧪 DEBUG: form.cliente_nome.data =", form.cliente_nome.data)
        print("🧪 DEBUG: form.cliente_telefone.data =", form.cliente_telefone.data)
        print("🧪 DEBUG: form.cliente_email.data =", form.cliente_email.data)
        print("🧪 DEBUG: form.servico_id.data =", form.servico_id.data)
        print("🧪 DEBUG: form.data.data =", form.data.data)
        print("🧪 DEBUG: form.horario.data =", form.horario.data)
        print("🧪 DEBUG: form.errors =", form.errors)

        if form.validate():
            print("✅ Formulário validado com sucesso!")

            cliente = Cliente.query.filter_by(telefone=form.cliente_telefone.data).first()
            if not cliente:
                print("🆕 Criando novo cliente...")
                cliente = Cliente(
                    nome=form.cliente_nome.data,
                    telefone=form.cliente_telefone.data,
                    email=form.cliente_email.data
                )
                cliente.set_password("123456")
                db.session.add(cliente)
                db.session.flush()

            profissional_servico = ProfissionalServico.query.filter_by(
                idProfissional=current_user.idProfissional,
                idServico=form.servico_id.data
            ).first()

            if not profissional_servico:
                flash('Este profissional não oferece o serviço selecionado.', 'error')
                return redirect(url_for('profissional_agendar'))

            servico = Servico.query.get(form.servico_id.data)
            duracao = timedelta(minutes=servico.duracao)

            # Agora sim converte string para hora
            hora_inicio = datetime.strptime(form.horario.data, '%H:%M:%S').time()
            hora_fim = (datetime.combine(date.today(), hora_inicio) + duracao).time()

            novo_agendamento = Agendamento(
                idCliente=cliente.idCliente,
                idProfissionalServico=profissional_servico.idProfissionalServico,
                data=form.data.data,
                horaInicio=hora_inicio,
                horaFim=hora_fim,
                status='pendente'
            )

            db.session.add(novo_agendamento)
            db.session.commit()

            print("✅ Agendamento criado e salvo com sucesso.")
            flash('Agendamento realizado com sucesso!', 'success')
            return redirect(url_for('profissional_inicio'))

        else:
            print("❌ Erros de validação:", form.errors)
            flash('Erro ao validar os dados do formulário.', 'error')

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

@app.route('/perfil-cliente', methods=['GET', 'POST'])
@login_required
def perfil_cliente():
    if not isinstance(current_user._get_current_object(), Cliente):
        abort(403)

    form = ClientePerfilForm()

    if form.validate_on_submit():
        cliente = current_user._get_current_object()

        cliente.nome = form.nome.data
        cliente.telefone = form.telefone.data
        cliente.email = form.email.data

        if form.nova_senha.data:
            cliente.set_password(form.nova_senha.data)

        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil_cliente'))

    # Pré-preenche os campos com os dados atuais
    cliente = current_user._get_current_object()
    form.nome.data = cliente.nome
    form.telefone.data = cliente.telefone
    form.email.data = cliente.email

    return render_template('cliente-perfil.html', form=form, cliente=cliente)

@app.route('/admin/clientes')
@login_required
def admin_clientes():
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    clientes = Cliente.query.all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/admin/cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def admin_perfil_cliente(cliente_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    cliente = Cliente.query.get_or_404(cliente_id)
    form = ClienteAdminForm(obj=cliente)  # pré-preenche

    if form.validate_on_submit():
        cliente.nome = form.nome.data
        cliente.telefone = form.telefone.data
        cliente.email = form.email.data
        db.session.commit()
        flash('Dados do cliente atualizados com sucesso!', 'success')
        return redirect(url_for('admin_perfil_cliente', cliente_id=cliente.idCliente))

    return render_template('perfil-cliente.html', cliente=cliente, form=form)

@app.route('/admin/cliente/<int:cliente_id>/excluir', methods=['POST'])
@login_required
def admin_excluir_cliente(cliente_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    cliente = Cliente.query.get_or_404(cliente_id)

    # Exclui todos os agendamentos vinculados ao cliente
    Agendamento.query.filter_by(idCliente=cliente.idCliente).delete()

    # Remove o cliente
    db.session.delete(cliente)
    db.session.commit()

    flash('Cliente e seus agendamentos foram excluídos com sucesso.', 'success')
    return redirect(url_for('admin_inicio'))  # ou 'admin_clientes' se você tiver uma lista de clientes

@app.route('/admin/profissional/<int:profissional_id>/excluir', methods=['POST'])
@login_required
def excluir_profissional(profissional_id):
    if not isinstance(current_user._get_current_object(), Administrador):
        abort(403)

    profissional = Profissional.query.get_or_404(profissional_id)

    # 1. Buscar todos os vínculos de serviços com esse profissional
    prof_servicos = ProfissionalServico.query.filter_by(idProfissional=profissional.idProfissional).all()

    # 2. Para cada vínculo, excluir os agendamentos relacionados
    for ps in prof_servicos:
        Agendamento.query.filter_by(idProfissionalServico=ps.idProfissionalServico).delete()

    # 3. Excluir os vínculos com os serviços
    ProfissionalServico.query.filter_by(idProfissional=profissional.idProfissional).delete()

    # 4. Excluir as agendas do profissional
    Agenda.query.filter_by(idProfissional=profissional.idProfissional).delete()

    # 5. Excluir o próprio profissional
    db.session.delete(profissional)
    db.session.commit()

    flash("Profissional excluído com sucesso.", "success")
    return redirect(url_for('admin_profissionais'))

@app.route('/admin/servico/<int:servico_id>')
@login_required
def perfil_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    return render_template('perfil-servico.html', servico=servico)

@app.route('/admin/servico/<int:servico_id>/excluir', methods=['POST'])
@login_required
def excluir_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)

    # Você pode adicionar verificações aqui, como se é admin:
    if not current_user.get_id().startswith("admin-"):
        flash("Apenas administradores podem excluir serviços.", "error")
        return redirect(url_for("index"))

    try:
        db.session.delete(servico)
        db.session.commit()
        flash(f"Serviço '{servico.nome}' excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir serviço: {str(e)}", "error")

    return redirect(url_for('admin_servicos'))  # Redireciona para a lista de serviços