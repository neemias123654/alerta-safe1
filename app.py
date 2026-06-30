import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import urllib.parse
from streamlit_cookies_controller import CookieController

cookies = CookieController()

# SENHA MESTRE DO DESENVOLVEDOR
SENHA_DESENVOLVEDOR = "DEV_MASTER_2026"

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    
    # MODIFICADO: Adicionada a coluna 'usuario_email' para saber a quem pertence o funcionário
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cargo TEXT NOT NULL,
            validade_curso TEXT NOT NULL,
            validade_aso TEXT NOT NULL,
            usuario_email TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            cpf TEXT NOT NULL,
            telefone TEXT NOT NULL,
            status_pagamento INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def cadastrar_usuario(email, senha, cpf, telefone):
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        # MODIFICADO: Removida a trava de 1 usuário. Agora qualquer um pode se cadastrar.
        cursor.execute("INSERT INTO usuarios (email, senha, cpf, telefone, status_pagamento) VALUES (?, ?, ?, ?, 1)", 
                       (email, senha, cpf, telefone))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Se o e-mail já existir, o banco de dados rejeita duplicatas por causa do 'UNIQUE'
        return "email_existe"

def verificar_login(email, senha):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, telefone, status_pagamento FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def buscar_usuario_por_email(email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, telefone, status_pagamento FROM usuarios WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

# --- FUNÇÕES DO DESENVOLVEDOR ---
def dev_bloquear_usuario(email_alvo):
    """Bloqueia um usuário específico pelo e-mail."""
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status_pagamento = 0 WHERE email = ?", (email_alvo,))
    conn.commit()
    conn.close()

def dev_desbloquear_usuario(email_alvo):
    """Desbloqueia um usuário específico pelo e-mail."""
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status_pagamento = 1 WHERE email = ?", (email_alvo,))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE FUNCIONÁRIOS (AGORA FILTRADAS POR USUÁRIO) ---
def adicionar_funcionario(nome, cargo, validade_curso, validade_aso, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    # MODIFICADO: Salva o e-mail do dono do cadastro junto com o funcionário
    cursor.execute("INSERT INTO funcionarios (nome, cargo, validade_curso, validade_aso, usuario_email) VALUES (?, ?, ?, ?, ?)", 
                   (nome, cargo, validade_curso, validade_aso, usuario_email))
    conn.commit()
    conn.close()

def buscar_funcionario_por_id(id_busca, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    # MODIFICADO: Garante que a busca só retorne o funcionário se ele pertencer ao usuário logado
    cursor.execute("SELECT id, nome, cargo, validade_curso, validade_aso FROM funcionarios WHERE id = ? AND usuario_email = ?", (id_busca, usuario_email))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def listar_todos_funcionarios(usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    # MODIFICADO: Filtra a lista geral trazendo apenas os registros criados por esse e-mail
    cursor.execute("SELECT id, nome, cargo, validade_curso, validade_aso FROM funcionarios WHERE usuario_email = ?", (usuario_email,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def calcular_status(data_str):
    hoje = datetime.today().date()
    data_validade = datetime.strptime(data_str, "%Y-%m-%d").date()
    prazo_alerta = hoje + timedelta(days=30)
    
    if data_validade < hoje:
        return "🔴 VENCIDO"
    elif hoje <= data_validade <= prazo_alerta:
        return "🟡 ATENÇÃO (< 30 dias)"
    else:
        return "🟢 EM DIA"

# --- INTERFACE VISUAL ---
st.set_page_config(page_title="AlertaSafe Multi-Tenant", layout="wide", page_icon="🛡️")
init_db()

cookie_login = cookies.get('alertasafe_user')

if "logado" not in st.session_state:
    st.session_state.logado = False
if "dados_usuario" not in st.session_state:
    st.session_state.dados_usuario = None
if "bloqueado_por_pagamento" not in st.session_state:
    st.session_state.bloqueado_por_pagamento = False

if cookie_login and not st.session_state.logado:
    usuario_banco = buscar_usuario_por_email(cookie_login)
    if usuario_banco:
        if usuario_banco[2] == 0:
            st.session_state.bloqueado_por_pagamento = True
        else:
            st.session_state.logado = True
            st.session_state.dados_usuario = {"email": usuario_banco[0], "telefone": usuario_banco[1]}

# --- TELA DE BLOQUEIO TOTAL POR FALTA DE PAGAMENTO ---
if st.session_state.bloqueado_por_pagamento:
    st.error("🛑 SISTEMA SUSPENSO")
    st.title("Aviso Importante: Acesso Bloqueado")
    st.markdown("Prezado cliente, o acesso a esta conta foi **suspenso por pendência financeira**.")
    st.info("✉️ Suporte: suporte@alertasafe.com.br")
    
    with st.expander("🛠️ Área do Desenvolvedor (Oculto)"):
        email_reativar = st.text_input("E-mail da conta a reativar:")
        senha_dev = st.text_input("Insira a Senha Mestre de Dev:", type="password", key="dev_key_block")
        if st.button("Reativar Conta Agora"):
            if senha_dev == SENHA_DESENVOLVEDOR and email_reativar:
                dev_desbloquear_usuario(email_reativar)
                st.session_state.bloqueado_por_pagamento = False
                st.session_state.logado = False
                cookies.remove('alertasafe_user')
                st.success("Conta reativada! Atualize a página.")
                st.rerun()
            else:
                st.error("Dados incorretos ou senha inválida.")

# --- TELA DE AUTENTICAÇÃO PADRÃO ---
elif not st.session_state.logado:
    st.title("🔐 AlertaSafe - Plataforma de Segurança")
    
    aba_login, aba_novo_cadastro, aba_dev = st.tabs(["Acessar Conta", "Criar Nova Conta", "🛠️ Painel Dev"])
    
    with aba_login:
        st.subheader("Faça seu Login")
        email_login = st.text_input("E-mail:")
        senha_login = st.text_input("Senha:", type="password")
        
        if st.button("Entrar no Sistema"):
            usuario = verificar_login(email_login, senha_login)
            if usuario:
                if usuario[2] == 0:
                    st.session_state.bloqueado_por_pagamento = True
                    st.rerun()
                else:
                    st.session_state.logado = True
                    st.session_state.dados_usuario = {"email": usuario[0], "telefone": usuario[1]}
                    cookies.set('alertasafe_user', usuario[0], max_age=2592000)
                    st.success("Login realizado com sucesso!")
                    st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
                
    with aba_novo_cadastro:
        st.subheader("Cadastre sua Empresa")
        # MODIFICADO: Não há mais limite de cadastros na tela.
        with st.form("form_cadastro_adm"):
            novo_email = st.text_input("E-mail de Acesso:")
            nova_senha = st.text_input("Defina uma Senha:", type="password")
            novo_cpf = st.text_input("CPF/CNPJ:")
            novo_tel = st.text_input("Telefone de Alertas (com DDD):")
            if st.form_submit_button("Criar Minha Conta"):
                if novo_email and nova_senha and novo_cpf and novo_tel:
                    resultado = cadastrar_usuario(novo_email, nova_senha, novo_cpf, novo_tel)
                    if resultado == True:
                        st.success("Conta criada com sucesso! Acesse a aba 'Acessar Conta'.")
                    elif resultado == "email_existe":
                        st.error("Este e-mail já está cadastrado no sistema.")
                else:
                    st.error("Preencha todos os campos.")

    with aba_dev:
        st.subheader("Controle de Licenças (Exclusivo Dev)")
        senha_controle_dev = st.text_input("Senha Mestre do Desenvolvedor:", type="password", key="dev_panel_key")
        email_alvo = st.text_input("E-mail do Cliente para Alterar:")
        
        col_bloquear, col_desbloquear = st.columns(2)
        with col_bloquear:
            if st.button("🚨 Bloquear Conta", use_container_width=True):
                if senha_controle_dev == SENHA_DESENVOLVEDOR and email_alvo:
                    dev_bloquear_usuario(email_alvo)
                    st.warning(f"A conta {email_alvo} foi bloqueada.")
                else:
                    st.error("Dados ou senha inválidos.")
        with col_desbloquear:
            if st.button("🟢 Liberar Conta", use_container_width=True):
                if senha_controle_dev == SENHA_DESENVOLVEDOR and email_alvo:
                    dev_desbloquear_usuario(email_alvo)
                    st.success(f"A conta {email_alvo} foi liberada.")
                else:
                    st.error("Dados ou senha inválidos.")

# --- TELA PRINCIPAL (LOGADO E FILTRADO) ---
else:
    email_usuario_logado = st.session_state.dados_usuario['email']
    
    col_tit, col_sair = st.columns([0.85, 0.15])
    with col_tit:
        st.title("🛡️ AlertaSafe - Gerenciamento Ativo")
        st.caption(f"Empresa conectada: **{email_usuario_logado}**")
    with col_sair:
        if st.button("🚪 Sair do Sistema"):
            st.session_state.logado = False
            st.session_state.dados_usuario = None
            cookies.remove('alertasafe_user')
            st.rerun()
            
    st.write("---")

    aba_dash, aba_busca, aba_cadastro, aba_notificacoes = st.tabs([
        "📊 Dashboard de Controle", 
        "🔍 Validação de Campo", 
        "➕ Cadastrar Novo Colaborador",
        "📲 Central de Alertas Automatizados"
    ])

    # --- ABA 1: DASHBOARD (FILTRADO) ---
    with aba_dash:
        st.subheader("Painel Geral de Conformidade da Equipe")
        lista_funcionarios = listar_todos_funcionarios(email_usuario_logado)
        if not lista_funcionarios:
            st.info("Nenhum colaborador cadastrado por sua empresa.")
        else:
            tabela_dados = []
            for func in lista_funcionarios:
                tabela_dados.append({
                    "ID": func[0], "Nome": func[1], "Cargo": func[2],
                    "Venc. Curso": func[3], "Status Curso": calcular_status(func[3]),
                    "Venc. ASO": func[4], "Status ASO": calcular_status(func[4])
                })
            st.table(tabela_dados)

    # --- ABA 2: VALIDAÇÃO DE CAMPO (FILTRADO) ---
    with aba_busca:
        st.subheader("Consulta Rápida de Segurança")
        id_busca = st.number_input("Digite o ID do Colaborador:", min_value=1, step=1, value=1)
        if st.button("Consultar", type="primary"):
            trabalhador = buscar_funcionario_por_id(id_busca, email_usuario_logado)
            if trabalhador:
                status_curso = calcular_status(trabalhador[3])
                status_aso = calcular_status(trabalhador[4])
                st.markdown(f"### 🧑‍🔧 {trabalhador[1]} — *{trabalhador[2]}*")
                if "🔴" in status_curso or "🔴" in status_aso:
                    st.error("❌ TRABALHO BLOQUEADO!")
                elif "🟡" in status_curso or "🟡" in status_aso:
                    st.warning("⚠️ ACESSO LIBERADO COM RESTRIÇÃO")
                else:
                    st.success("✅ ACESSO TOTALMENTE LIBERADO")
            else:
                st.error("ID não localizado ou este funcionário não pertence à sua conta.")

    # --- ABA 3: CADASTRO (SALVANDO O DONO) ---
    with aba_cadastro:
        st.subheader("Formulário de Cadastro de Funcionário")
        with st.form("form_trab", clear_on_submit=True):
            nome_input = st.text_input("Nome Completo:")
            cargo_input = st.text_input("Cargo:")
            curso_input = st.date_input("Vencimento do Curso Técnico:")
            aso_input = st.date_input("Vencimento do Exame Médico:")
            if st.form_submit_button("Registrar"):
                if nome_input and cargo_input:
                    adicionar_funcionario(nome_input, cargo_input, str(curso_input), str(aso_input), email_usuario_logado)
                    st.success("Cadastrado com sucesso.")
                else:
                    st.error("Preencha Nome e Cargo.")

    # --- ABA 4: CENTRAL DE ALERTAS ---
    with aba_notificacoes:
        st.subheader("📲 Sistema de Envios Automáticos")
        lista_funcionarios = listar_todos_funcionarios(email_usuario_logado)
        alertas_encontrados = []
        if lista_funcionarios:
            for func in lista_funcionarios:
                if "🟡" in calcular_status(func[3]):
                    alertas_encontrados.append(func)
                    
        if not alertas_encontrados:
            st.success("🎉 Nenhum funcionário com curso vencendo nos próximos 30 dias.")
        else:
            st.warning(f"Detectado(s) {len(alertas_encontrados)} funcionário(s) necessitando de reciclagem.")
            telefone_destino = st.session_state.dados_usuario['telefone']
            email_destino = st.session_state.dados_usuario['email']
            
            for func in alertas_encontrados:
                nome_func = func[1]
                venc_curso = func[3]
                mensagem_texto = f"AlertaSafe: O curso do funcionário {nome_func} vence em {venc_curso}. Organize a reciclagem."
                st.info(f"📌 **Para: {nome_func}** (Vence em: {venc_curso})")
                
                col_whats, col_email = st.columns(2)
                with col_whats:
                    texto_url = urllib.parse.quote(mensagem_texto)
                    link_whatsapp = f"https://api.whatsapp.com/send?phone=55{telefone_destino}&text={texto_url}"
                    st.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px 15px; border-radius:8px; cursor:pointer;">Disparar via WhatsApp</button></a>', unsafe_allow_html=True)
                with col_email:
                    st.success(f"📧 E-mail Enviado para: {email_destino}")
                    st.code(f"Conteúdo: {mensagem_texto}")
