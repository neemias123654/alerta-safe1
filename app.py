import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import urllib.parse
import pandas as pd
import io
import traceback
import re  # Adicionado para limpeza de caracteres de texto e telefone

# --- CONFIGURAÇÕES MASTER DO DESENVOLVEDOR (PROTEÇÃO LOCAL/NUVEM) ---
try:
    # Tenta carregar do painel da Nuvem (Streamlit Cloud)
    EMAIL_DEV = st.secrets["EMAIL_DEV"]
    SENHA_DESENVOLVEDOR = st.secrets["SENHA_DESENVOLVEDOR"]
except Exception:
    # Se der erro ou estiver rodando localmente no PC, usa os padrões automáticos
    EMAIL_DEV = "neemias123654@gmail.com"
    SENHA_DESENVOLVEDOR = "DEV_MASTER_2026"

# --- CONFIGURAÇÃO DO BANCO DE DADOS ATUALIZADA ---
def init_db():
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cargo TEXT NOT NULL,
            validade_curso TEXT NOT NULL,
            validade_aso TEXT NOT NULL,
            usuario_email TEXT,
            area_id INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS areas_empresa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_area TEXT NOT NULL,
            usuario_email TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS outros_cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER,
            nome_curso TEXT NOT NULL,
            validade TEXT NOT NULL,
            usuario_email TEXT,
            FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            cpf TEXT NOT NULL,
            telefone TEXT NOT NULL,
            status_pagamento INTEGER DEFAULT 1,
            permissao_uso INTEGER DEFAULT 0,
            nome_empresa TEXT,
            acessos_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_erros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_email TEXT,
            data_hora TEXT,
            mensagem_erro TEXT,
            rastro_tecnico TEXT
        )
    ''')
    
    # Migrações de segurança para bancos legados
    try: cursor.execute("ALTER TABLE funcionarios ADD COLUMN area_id INTEGER")
    except sqlite3.OperationalError: pass

    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN permissao_uso INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN nome_empresa TEXT")
    except sqlite3.OperationalError: pass

    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN acessos_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()

# --- FUNÇÃO DE TELEMETRIA DE ERROS ---
def registrar_bug_sistema(usuario_email, erro_exception):
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_erro = str(erro_exception)
        rastro_completo = traceback.format_exc()
        
        cursor.execute("""
            INSERT INTO logs_erros (usuario_email, data_hora, message_erro, rastro_tecnico)
            VALUES (?, ?, ?, ?)
        """, (usuario_email, data_atual, msg_erro, rastro_completo))
        conn.commit()
        conn.close()
    except Exception:
        pass

def listar_bugs_sistema():
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario_email, data_hora, mensagem_erro, rastro_tecnico FROM logs_erros ORDER BY id DESC")
    erros = cursor.fetchall()
    conn.close()
    return erros

def limpar_historico_bugs():
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs_erros")
    conn.commit()
    conn.close()

# --- FUNÇÕES DO DESENVOLVEDOR ---
def dev_cadastrar_cliente(email, senha, cpf, telefone, nome_empresa):
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (email, senha, cpf, telefone, status_pagamento, permissao_uso, nome_empresa, acessos_count) 
            VALUES (?, ?, ?, ?, 1, 0, ?, 0)
        """, (email, senha, cpf, telefone, nome_empresa))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verificar_login(email, senha):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, telefone, status_pagamento, permissao_uso, nome_empresa FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def buscar_usuario_por_email(email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, telefone, status_pagamento, permissao_uso, nome_empresa FROM usuarios WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def listar_todos_usuarios_do_sistema():
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, cpf, telefone, status_pagamento, permissao_uso, nome_empresa, acessos_count FROM usuarios ORDER BY email ASC")
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios

def dev_alterar_pagamento(email_alvo, status):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status_pagamento = ? WHERE email = ?", (status, email_alvo))
    conn.commit()
    conn.close()

def dev_alterar_permissao(email_alvo, permissao):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET permissao_uso = ? WHERE email = ?", (permissao, email_alvo))
    conn.commit()
    conn.close()

def computar_acesso(email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET acessos_count = acessos_count + 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE ÁREAS CUSTOMIZADAS ---
def adicionar_area(nome_area, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO areas_empresa (nome_area, usuario_email) VALUES (?, ?)", (nome_area, usuario_email))
    conn.commit()
    conn.close()

def listar_areas(usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome_area FROM areas_empresa WHERE usuario_email = ?", (usuario_email,))
    areas = cursor.fetchall()
    conn.close()
    return areas

def deletar_area(id_area, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM areas_empresa WHERE id = ? AND usuario_email = ?", (id_area, usuario_email))
    cursor.execute("UPDATE funcionarios SET area_id = NULL WHERE area_id = ? AND usuario_email = ?", (id_area, usuario_email))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE FUNCIONÁRIOS ---
def adicionar_funcionario(nome, cargo, validade_curso, validade_aso, usuario_email, area_id):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO funcionarios (nome, cargo, validade_curso, validade_aso, usuario_email, area_id) VALUES (?, ?, ?, ?, ?, ?)", 
                   (nome, cargo, validade_curso, validade_aso, usuario_email, area_id))
    ultimo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ultimo_id

def buscar_funcionario_por_id(id_busca, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cargo, validade_curso, validade_aso, area_id FROM funcionarios WHERE id = ? AND usuario_email = ?", (id_busca, usuario_email))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

def listar_todos_funcionarios(usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cargo, validade_curso, validade_aso, area_id FROM funcionarios WHERE usuario_email = ?", (usuario_email,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def atualizar_funcionario(id_func, nome, cargo, validade_curso, validade_aso, usuario_email, area_id):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE funcionarios SET nome=?, cargo=?, validade_curso=?, validade_aso=?, area_id=? WHERE id=? AND usuario_email=?', 
                   (nome, cargo, validade_curso, validade_aso, area_id, id_func, usuario_email))
    conn.commit()
    conn.close()

def deletar_funcionario(id_func, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM funcionarios WHERE id = ? AND usuario_email = ?", (id_func, usuario_email))
    cursor.execute("DELETE FROM outros_cursos WHERE funcionario_id = ? AND usuario_email = ?", (id_func, usuario_email))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE OUTROS CURSOS ---
def adicionar_outro_curso(funcionario_id, nome_curso, validade, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO outros_cursos (funcionario_id, nome_curso, validade, usuario_email) VALUES (?, ?, ?, ?)", 
                   (funcionario_id, nome_curso, validade, usuario_email))
    conn.commit()
    conn.close()

def listar_outros_cursos(usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT oc.id, f.nome, oc.nome_curso, oc.validade, oc.funcionario_id 
        FROM outros_cursos oc 
        JOIN funcionarios f ON oc.funcionario_id = f.id 
        WHERE oc.usuario_email = ?
    ''', (usuario_email,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def listar_outros_cursos_por_funcionario(funcionario_id, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome_curso, validade FROM outros_cursos WHERE funcionario_id = ? AND usuario_email = ?', (funcionario_id, usuario_email))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def deletar_outro_curso(id_curso, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM outros_cursos WHERE id = ? AND usuario_email = ?", (id_curso, usuario_email))
    conn.commit()
    conn.close()

def calcular_status(data_str):
    hoje = datetime.today().date()
    data_validade = datetime.strptime(data_str, "%Y-%m-%d").date()
    prazo_alerta = hoje + timedelta(days=30)
    
    if data_validade < hoje:
        return "🔴 VENCIDO"
    elif hoje <= data_validade <= prazo_alerta:
        return "🟡 ATENÇÃO"
    else:
        return "🟢 EM DIA"

# --- INTERFACE MODAL DE EDIÇÃO INTEGRADA ---
@st.dialog("✏️ Opções de Gerenciamento e Edição")
def modal_editar_funcionario(trabalhador, email_usuario_logado, dicionario_areas):
    f_id = trabalhador[0]
    status_curso = calcular_status(trabalhador[3])
    status_aso = calcular_status(trabalhador[4])
    
    if "🔴" in status_curso or "🔴" in status_aso:
        st.error(f"❌ STATUS CRÍTICO: Documento Vencido Detectado.")
    elif "🟡" in status_curso or "🟡" in status_aso:
        st.warning(f"⚠️ STATUS ALERTA: Renovações pendentes em menos de 30 dias.")
    else:
        st.success(f"✅ STATUS REGULAR: Todos os prazos em dia.")

    edit_nome = st.text_input("Nome do Colaborador:", value=trabalhador[1])
    edit_cargo = st.text_input("Cargo Ocupacional:", value=trabalhador[2])
    
    opcoes_area_edit = {"Sem Área / Geral": None}
    for id_a, nome_a in dicionario_areas.items():
        opcoes_area_edit[nome_a] = id_a
        
    area_atual_nome = dicionario_areas.get(trabalhador[5], "Sem Área / Geral")
    edit_area_nome = st.selectbox("Setor Operacional:", list(opcoes_area_edit.keys()), index=list(opcoes_area_edit.keys()).index(area_atual_nome))
    id_area_editado = opcoes_area_edit[edit_area_nome]
    
    data_curso_atual = datetime.strptime(trabalhador[3], "%Y-%m-%d").date()
    data_aso_atual = datetime.strptime(trabalhador[4], "%Y-%m-%d").date()
    
    col_ed1, col_ed2 = st.columns(2)
    with col_ed1:
        edit_curso = st.date_input("Vencimento do Curso Técnico Base:", value=data_curso_atual)
    with col_ed2:
        edit_aso = st.date_input("Vencimento do Exame Médico ASO:", value=data_aso_atual)
    
    st.markdown("---")
    st.markdown("### 📜 Certificados Adicionais (NR-10, NR-35, etc.)")
    
    certificados_atuais = listar_outros_cursos_por_funcionario(f_id, email_usuario_logado)
    if certificados_atuais:
        for c_id, c_nome, c_val in certificados_atuais:
            col_c1, col_c2, col_c3 = st.columns([0.5, 0.3, 0.2])
            col_c1.write(f"• **{c_nome}**")
            col_c2.write(f"Validade: `{c_val}`")
            if col_c3.button("🗑️", key=f"del_cert_{c_id}"):
                deletar_outro_curso(c_id, email_usuario_logado)
                st.rerun()
    else:
        st.caption("Nenhum certificado adicional anexado a este colaborador.")
        
    st.markdown("**Adicionar Novo Certificado Extra:**")
    col_nc1, col_nc2 = st.columns([0.6, 0.4])
    novo_c_nome = col_nc1.text_input("Nome do Curso Extra:", key=f"nc_nome_{f_id}")
    novo_c_val = col_nc2.date_input("Data de Vencimento:", key=f"nc_val_{f_id}")
    
    if st.button("➕ Vincular Certificado", use_container_width=True):
        if novo_c_nome.strip():
            adicionar_outro_curso(f_id, novo_c_nome.strip(), str(novo_c_val), email_usuario_logado)
            st.success(f"Certificado {novo_c_nome} adicionado!")
            st.rerun()
        else:
            st.error("Digite o nome do curso para adicionar.")

    st.markdown("---")
    col_btn_salvar, col_btn_deletar = st.columns(2)
    with col_btn_salvar:
        if st.button("💾 Salvar Ficha Cadastral", type="primary", use_container_width=True):
            atualizar_funcionario(f_id, edit_nome, edit_cargo, str(edit_curso), str(edit_aso), email_usuario_logado, id_area_editado)
            st.success("Alterações salvas!")
            st.rerun()
    with col_btn_deletar:
        if st.button("🚨 REMOVER COLABORADOR", type="secondary", use_container_width=True):
            deletar_funcionario(f_id, email_usuario_logado)
            st.rerun()

# --- INTERFACE VISUAL PRINCIPAL ---
st.set_page_config(page_title="AlertaSafe Enterprise", layout="wide", page_icon="🛡️")
init_db()

# --- SISTEMA INSTANTÂNEO DE LOGIN VIA QUERY PARAMS ---
if "logado" not in st.session_state: st.session_state.logado = False
if "dados_usuario" not in st.session_state: st.session_state.dados_usuario = None
if "bloqueio_tipo" not in st.session_state: st.session_state.bloqueio_tipo = None
if "acesso_computado" not in st.session_state: st.session_state.acesso_computado = False

url_user = st.query_params.get("user_session", None)

if url_user and not st.session_state.logado:
    if url_user == EMAIL_DEV:
        st.session_state.logado = True
        st.session_state.dados_usuario = {"email": EMAIL_DEV, "tipo": "dev"}
    else:
        user_b = buscar_usuario_por_email(url_user)
        if user_b:
            if user_b[2] == 0: st.session_state.bloqueio_tipo = "pagamento"
            elif user_b[3] == 0: st.session_state.bloqueio_tipo = "permissao"
            else:
                st.session_state.logado = True
                st.session_state.dados_usuario = {"email": user_b[0], "telefone": user_b[1], "tipo": "cliente", "nome_empresa": user_b[4]}
                if not st.session_state.acesso_computado:
                    computar_acesso(user_b[0])
                    st.session_state.acesso_computado = True

# Tela de Bloqueios
if st.session_state.bloqueio_tipo:
    st.error("🛑 SISTEMA BLOQUEADO")
    st.info(f"✉️ Contato do Desenvolvedor: {EMAIL_DEV}")
    if st.button("↩️ Voltar para Tela de Login"):
        st.session_state.bloqueio_tipo = None
        st.session_state.logado = False
        st.session_state.dados_usuario = None
        st.session_state.acesso_computado = False
        st.query_params.clear()
        st.rerun()

# Tela de Login
elif not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ AlertaSafe Enterprise</h1>", unsafe_allow_html=True)
    
    col_log1, col_log2, col_log3 = st.columns([1, 1.2, 1])
    with col_log2:
        with st.container(border=True):
            st.markdown("### 🔐 Autenticação Restrita")
            email_login = st.text_input("E-mail Empresarial:")
            senha_login = st.text_input("Senha Governamental:", type="password")
            
            if st.button("Entrar no Painel Seguro", type="primary", use_container_width=True):
                if email_login == EMAIL_DEV and senha_login == SENHA_DESENVOLVEDOR:
                    st.session_state.logado = True
                    st.session_state.dados_usuario = {"email": EMAIL_DEV, "tipo": "dev"}
                    st.query_params["user_session"] = EMAIL_DEV
                    st.rerun()
                else:
                    usuario = verificar_login(email_login, senha_login)
                    if usuario:
                        if usuario[2] == 0:
                            st.session_state.bloqueio_tipo = "pagamento"
                            st.rerun()
                        elif usuario[3] == 0:
                            st.session_state.bloqueio_tipo = "permissao"
                            st.rerun()
                        else:
                            st.session_state.logado = True
                            st.session_state.dados_usuario = {"email": usuario[0], "telefone": usuario[1], "tipo": "cliente", "nome_empresa": usuario[4]}
                            computar_acesso(usuario[0])
                            st.session_state.acesso_computado = True
                            st.query_params["user_session"] = usuario[0]
                            st.rerun()
                    else:
                        st.error("❌ Credenciais inválidas.")

# Tela Principal do Sistema (Painel de Gerenciamento)
else:
    tipo_usuario = st.session_state.dados_usuario['tipo']
    
    col_tit, col_sair = st.columns([0.85, 0.15])
    with col_tit:
        if tipo_usuario == "dev":
            st.title("🛠️ CENTRAL MATRIX - Painel do Desenvolvedor")
        else:
            nome_exibicao = st.session_state.dados_usuario.get('nome_empresa') or st.session_state.dados_usuario['email']
            st.markdown(f"<h2 style='margin:0;'>🛡️ AlertaSafe — {nome_exibicao}</h2>", unsafe_allow_html=True)
            st.caption(f"Usuário Autenticado: **{st.session_state.dados_usuario['email']}**")
    with col_sair:
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.logado = False
            st.session_state.dados_usuario = None
            st.session_state.acesso_computado = False
            st.query_params.clear()
            st.rerun()
            
    st.write("---")

    if tipo_usuario == "dev":
        aba_cad_cliente, aba_gerenciar_licencas, aba_bugs = st.tabs(["➕ Autorizar Entrada", "🏢 Empresas", "🪲 Logs de Bugs"])
        
        with aba_cad_cliente:
            st.subheader("Configurar Credenciais de Acesso")
            with st.form("form_dev_cadastro"):
                c_nome_empresa = st.text_input("Nome Fantasia / Nome da Empresa:")
                c_email = st.text_input("E-mail da Empresa (Será o login):")
                c_senha = st.text_input("Senha de Acesso:")
                c_cpf = st.text_input("CNPJ ou CPF da Empresa:")
                
                # OPÇÃO 2 INTEGRADA: Tratamento preventivo no painel do dev
                c_tel_raw = st.text_input("Telefone com DDD (Apenas números):", help="Ex: 22999998888")
                
                if st.form_submit_button("Gerar Conta Ativa"):
                    # Aplica a limpeza de strings via Expressão Regular (Mantém apenas dígitos)
                    c_tel = re.sub(r'\D', '', c_tel_raw)
                    
                    if c_nome_empresa and c_email and c_senha and c_cpf and c_tel:
                        if len(c_tel) >= 10:  # Validação simples de tamanho de DDD + Número
                            if dev_cadastrar_cliente(c_email, c_senha, c_cpf, c_tel, c_nome_empresa):
                                st.success(f"Empresa '{c_nome_empresa}' cadastrada com sucesso!")
                                st.rerun()
                            else: st.error("Erro: Este e-mail já existe no banco.")
                        else:
                            st.error("❌ Formato de telefone inválido. Certifique-se de incluir o DDD e o número completo.")
                    else: st.error("Preencha todos os campos obrigatórios.")
                        
        with aba_gerenciar_licencas:
            st.subheader("🏢 Status de Licenciamento Global")
            lista_users = listar_todos_usuarios_do_sistema()
            if not lista_users:
                st.info("Nenhum cliente ativo encontrado.")
            else:
                df_usuarios = pd.DataFrame(lista_users, columns=["email", "cpf", "telefone", "status_pagamento", "permissao_uso", "nome_empresa", "acessos_count"])
                df_usuarios["nome_empresa"] = df_usuarios["nome_empresa"].fillna("Sem Nome Definido").str.strip()
                empresas_unicas = sorted(df_usuarios["nome_empresa"].unique())
                
                for nome_emp in empresas_unicas:
                    df_filtrado = df_usuarios[df_usuarios["nome_empresa"] == nome_emp]
                    with st.expander(f"🏢 Bloco: {nome_emp} ({len(df_filtrado)} conta(s))", expanded=True):
                        dados_tabela = []
                        for _, row in df_filtrado.iterrows():
                            dados_tabela.append({
                                "Login / E-mail": row["email"],
                                "CNPJ/CPF": row["cpf"],
                                "Telefone": row["telefone"],
                                "Total de Acessos": f"📊 {row['acessos_count']} login(s)",
                                "Status Financeiro": "🟢 PAGO / ATIVO" if row["status_pagamento"] == 1 else "🔴 INADIMPLENTE (Bloqueado)",
                                "Acesso ao Aplicativo": "✅ LIBERADO" if row["permissao_uso"] == 1 else "⏳ AGUARDANDO LIBERAÇÃO"
                            })
                        st.table(dados_tabela)
                
                st.write("---")
                st.markdown("### ⚡ Ações de Controle de Licença")
                email_modificar = st.selectbox("Selecione qual Empresa deseja gerenciar:", [u[0] for u in lista_users])
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    with st.container(border=True):
                        st.markdown("**Controle de Pagamentos**")
                        if st.button("🟢 Marcar como PAGO / Reativar", use_container_width=True):
                            dev_alterar_pagamento(email_modificar, 1); st.rerun()
                        if st.button("🚨 Bloquear por Inadimplência", use_container_width=True):
                            dev_alterar_pagamento(email_modificar, 0); st.rerun()
                with col_l2:
                    with st.container(border=True):
                        st.markdown("**Permissões de Uso Administrativo**")
                        if st.button("✅ Conceder PERMISSÃO LIVRE", use_container_width=True):
                            dev_alterar_permissao(email_modificar, 1); st.rerun()
                        if st.button("❌ Revogar Permissão", use_container_width=True):
                            dev_alterar_permissao(email_modificar, 0); st.rerun()

        with aba_bugs:
            st.subheader("🪲 Relatórios de Falhas em Tempo Real")
            st.write("Erros fatais disparados pelos clientes na produção são registrados automaticamente aqui:")
            
            lista_bugs = listar_bugs_sistema()
            if not lista_bugs:
                st.success("🎉 Nenhum bug ou falha crítica registrada! O sistema está estável.")
            else:
                if st.button("🗑️ Limpar Histórico de Erros", type="secondary"):
                    limpar_historico_bugs()
                    st.rerun()
                
                for b_id, b_user, b_data, b_msg, b_trace in lista_bugs:
                    with st.container(border=True):
                        st.markdown(f"🔴 **Erro #{b_id}** — disparado por `{b_user}` em `{b_data}`")
                        st.warning(f"**Mensagem do Erro:** {b_msg}")
                        with st.expander("🔍 Ver Rastro Técnico Completo (Traceback)"):
                            st.code(b_trace, language="python")
    else:
        email_usuario_logado = st.session_state.dados_usuario['email']
        
        try:
            lista_areas_cadastradas = listar_areas(email_usuario_logado)
            dicionario_areas = {a[0]: a[1] for a in lista_areas_cadastradas}
            
            aba_dash, aba_cadastro, aba_cadastro_massa, aba_config_areas, aba_notificacoes = st.tabs([
                "📊 Dashboard Geral por Áreas", "➕ Cadastrar Colaborador",
                "📥 Importar Planilha (Massa)", "🏗️ Criar/Editar Áreas da Empresa",
                "📲 Central de Alertas Automatizados"
            ])

            def renderizar_grid_funcionarios(funcionarios_lista):
                col_h1, col_h2, col_h3, col_h4, col_h5, col_h6, col_h7 = st.columns([0.6, 1.8, 1.3, 1.3, 1.3, 2.5, 0.6])
                col_h1.markdown("**ID**"); col_h2.markdown("**Nome**"); col_h3.markdown("**Cargo**")
                col_h4.markdown("**Curso Base**"); col_h5.markdown("**Status ASO**"); col_h6.markdown("**Certificados Extras**"); col_h7.markdown("**Editar**")
                st.markdown("<hr style='margin:4px 0px 12px 0px; border-color:#333;' />", unsafe_allow_html=True)
                
                for func in funcionarios_lista:
                    f_id = func['ID']
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([0.6, 1.8, 1.3, 1.3, 1.3, 2.5, 0.6])
                    col1.write(f"`{f_id}`")
                    col2.write(func['Nome Completo'])
                    col3.write(func['Cargo'])
                    col4.write(f"{func['Venc. Curso Base']}\n\n{func['Status Curso']}")
                    col5.write(f"{func['Venc. ASO']}\n\n{func['Status ASO']}")
                    col6.write(func['Certificados Extras (Status)'])
                    if col7.button("✏️", key=f"btn_edit_{f_id}"):
                        trabalhador_banco = buscar_funcionario_por_id(f_id, email_usuario_logado)
                        modal_editar_funcionario(trabalhador_banco, email_usuario_logado, dicionario_areas)

            with aba_dash:
                lista_funcionarios = listar_todos_funcionarios(email_usuario_logado)
                todos_certificados_banco = listar_outros_cursos(email_usuario_logado)
                
                st.markdown("### 🔍 Pesquisar Colaborador")
                termo_pesquisa = st.text_input("Digite o nome ou cargo do funcionário:", placeholder="Ex: João da Silva...").strip().lower()
                
                funcionarios_filtrados_busca = [f for f in lista_funcionarios if not termo_pesquisa or termo_pesquisa in f[1].lower() or termo_pesquisa in f[2].lower()]
                
                total_colab = len(funcionarios_filtrados_busca)
                vencidos, atencao = 0, 0
                
                mapa_certificados = {}
                for cert in todos_certificados_banco:
                    func_id = cert[4]
                    status_cert = calcular_status(cert[3])
                    if func_id in [f[0] for f in funcionarios_filtrados_busca]:
                        if "🔴" in status_cert: vencidos += 1
                        if "🟡" in status_cert: atencao += 1
                    if func_id not in mapa_certificados: mapa_certificados[func_id] = []
                    mapa_certificados[func_id].append(f"{cert[2]} ({status_cert})")

                for func in funcionarios_filtrados_busca:
                    if "🔴" in calcular_status(func[3]) or "🔴" in calcular_status(func[4]): vencidos += 1
                    if "🟡" in calcular_status(func[3]) or "🟡" in calcular_status(func[4]): atencao += 1

                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("👥 Colaboradores Listados", total_colab)
                col_m2.metric("🚨 Bloqueados / Vencidos", vencidos, delta="- Crítico" if vencidos > 0 else "Regularizado", delta_color="inverse")
                col_m3.metric("⚠️ Exige Atenção (30 dias)", atencao, delta="Atenção" if atencao > 0 else "Estável", delta_color="off")
                st.write("---")

                if not funcionarios_filtrados_busca:
                    if termo_pesquisa: st.warning(f"❌ Nenhum funcionário encontrado correspondente a '{termo_pesquisa}'.")
                    else: st.info("💡 Nenhum colaborador cadastrado.")
                else:
                    funcionarios_por_area = {a_nome: [] for a_nome in dicionario_areas.values()}
                    funcionarios_sem_area = []
                    
                    for func in funcionarios_filtrados_busca:
                        f_id = func[0]
                        lista_extras_func = mapa_certificados.get(f_id, ["-"])
                        f_dados = {
                            "ID": f_id, "Nome Completo": func[1], "Cargo": func[2],
                            "Venc. Curso Base": func[3], "Status Curso": calcular_status(func[3]),
                            "Venc. ASO": func[4], "Status ASO": calcular_status(func[4]),
                            "Certificados Extras (Status)": ", ".join(lista_extras_func)
                        }
                        if func[5] in dicionario_areas: funcionarios_por_area[dicionario_areas[func[5]]].append(f_dados)
                        else: funcionarios_sem_area.append(f_dados)
                    
                    if lista_areas_cadastradas:
                        for nome_da_area, lista_funcs in funcionarios_por_area.items():
                            deve_expandir = True if (termo_pesquisa and len(lista_funcs) > 0) else (not termo_pesquisa)
                            if len(lista_funcs) > 0 or not termo_pesquisa:
                                with st.expander(f"📁 Setor / Área: {nome_da_area} ({len(lista_funcs)})", expanded=deve_expandir):
                                    if not lista_funcs: st.caption("Nenhum colaborador alocado neste setor.")
                                    else: renderizar_grid_funcionarios(lista_funcs)
                    
                    if funcionarios_sem_area or (not lista_areas_cadastradas and funcionarios_sem_area):
                        deve_expandir_geral = True if (termo_pesquisa and len(funcionarios_sem_area) > 0) else (not termo_pesquisa)
                        with st.expander(f"❓ Sem Área Definida ({len(funcionarios_sem_area)})", expanded=deve_expandir_geral):
                            renderizar_grid_funcionarios(funcionarios_sem_area)

            with aba_cadastro:
                st.subheader("➕ Adicionar Novo Colaborador")
                with st.form("form_trab", clear_on_submit=True):
                    col_ins1, col_ins2 = st.columns(2)
                    nome_input = col_ins1.text_input("Nome Completo do Funcionário:")
                    cargo_input = col_ins1.text_input("Cargo / Função:")
                    opcoes_cadastro_area = {"Deixar em Setor Geral": None}
                    for id_a, nome_a in dicionario_areas.items(): opcoes_cadastro_area[nome_a] = id_a
                    area_selecionada_cadastro = col_ins2.selectbox("Vincular à Área:", list(opcoes_cadastro_area.keys()))
                    curso_input = col_ins1.date_input("Validade do Curso Técnico:")
                    aso_input = col_ins2.date_input("Validade do Exame Médico ASO:")
                    
                    if st.form_submit_button("Cadastrar Colaborador", type="primary", use_container_width=True):
                        if nome_input and cargo_input:
                            adicionar_funcionario(nome_input, cargo_input, str(curso_input), str(aso_input), email_usuario_logado, opcoes_cadastro_area[area_selecionada_cadastro])
                            st.success(f"{nome_input} cadastrado!")
                            st.rerun()

            with aba_cadastro_massa:
                st.subheader("📥 Cadastro de Funcionários em Lote")
                df_modelo = pd.DataFrame(columns=["Nome Completo", "Cargo", "Validade Curso (AAAA-MM-DD)", "Validade ASO (AAAA-MM-DD)"])
                df_modelo.loc[0] = ["João da Silva", "Alceador", "2026-12-15", "2027-01-20"]
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_modelo.to_excel(writer, sheet_name='Modelo_Importacao', index=False)
                st.download_button(label="📥 Baixar Planilha Modelo", data=buffer.getvalue(), file_name="modelo_importacao.xlsx")
                
                opcoes_lote_area = {"Vincular ao Setor Geral": None}
                for id_a, nome_a in dicionario_areas.items(): opcoes_lote_area[nome_a] = id_a
                area_selecionada_lote = st.selectbox("Setor de Destino do Lote:", list(opcoes_lote_area.keys()))
                arquivo_lote = st.file_uploader("Escolha o arquivo (.xlsx ou .csv):", type=["xlsx", "csv"])
                
                if arquivo_lote is not None:
                    df_carregado = pd.read_excel(arquivo_lote) if arquivo_lote.name.endswith('.xlsx') else pd.read_csv(arquivo_lote)
                    st.dataframe(df_carregado, use_container_width=True)
                    if st.button("🔥 Confirmar Importação Lote", type="primary"):
                        for _, row in df_carregado.iterrows():
                            if row["Nome Completo"] == "João da Silva": continue
                            try:
                                val_curso = pd.to_datetime(row["Validade Curso (AAAA-MM-DD)"]).strftime("%Y-%m-%d")
                                val_aso = pd.to_datetime(row["Validade ASO (AAAA-MM-DD)"]).strftime("%Y-%m-%d")
                                adicionar_funcionario(str(row["Nome Completo"]), str(row["Cargo"]), val_curso, val_aso, email_usuario_logado, opcoes_lote_area[area_selecionada_lote])
                            except Exception: pass
                        st.success("Lote importado!")
                        st.rerun()

            with aba_config_areas:
                st.subheader("🏗️ Controle de Setores")
                col_area1, col_area2 = st.columns(2)
                with col_area1:
                    nova_area_nome = st.text_input("Nome Comercial do Setor:")
                    if st.button("Criar Setor Agora"):
                        if nova_area_nome: adicionar_area(nova_area_nome, email_usuario_logado); st.rerun()
                with col_area2:
                    if lista_areas_cadastradas:
                        opcoes_deletar_area = {a[1]: a[0] for a in lista_areas_cadastradas}
                        area_deletar_nome = st.selectbox("Escolha o setor para remover:", list(opcoes_deletar_area.keys()))
                        if st.button("Remover Setor"): deletar_area(opcoes_deletar_area[area_deletar_nome], email_usuario_logado); st.rerun()

            with aba_notificacoes:
                st.subheader("📲 Central de Alertas Automatizados")
                alertas_encontrados = []
                if lista_funcionarios:
                    for func in lista_funcionarios:
                        if "🟡" in calcular_status(func[3]): alertas_encontrados.append({"nome": func[1], "item": "Curso Técnico Base", "venc": func[3]})
                        if "🟡" in calcular_status(func[4]): alertas_encontrados.append({"nome": func[1], "item": "Exame Médico ASO", "venc": func[4]})
                if not alertas_encontrados: st.success("🎉 Todos os prazos regularizados.")
                else:
                    # OPÇÃO 2 INTEGRADA: Garante que o telefone do cliente ativo está limpo antes de gerar o link
                    telefone_destino = re.sub(r'\D', '', str(st.session_state.dados_usuario['telefone']))
                    
                    for alerta in alertas_encontrados:
                        with st.container(border=True):
                            st.markdown(f"📌 **{alerta['nome']}** — *{alerta['item']}* expira em `{alerta['venc']}`.")
                            texto_url = urllib.parse.quote(f"AlertaSafe: {alerta['nome']} item {alerta['item']} vence em {alerta['venc']}.")
                            
                            # O link agora usa o telefone tratado de forma 100% segura
                            st.markdown(f'<a href="https://api.whatsapp.com/send?phone=55{telefone_destino}&text={texto_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:6px 10px; border-radius:4px; cursor:pointer;">💬 Disparar Zap</button></a>', unsafe_allow_html=True)
        
        except Exception as e:
            registrar_bug_sistema(email_usuario_logado, e)
            st.error("🛑 Ocorreu um erro interno de processamento.")
            st.info("💡 Fique tranquilo! O erro técnico foi mapeado de forma automática e enviado diretamente para a mesa do Desenvolvedor para correção imediata.")
