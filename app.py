import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import urllib.parse
import pandas as pd
import io
import traceback
import re
import hashlib

# --- CONFIGURAÇÕES MASTER DO DESENVOLVEDOR ---
try:
    EMAIL_DEV = st.secrets["EMAIL_DEV"]
    SENHA_DESENVOLVEDOR = st.secrets["SENHA_DESENVOLVEDOR"]
except Exception:
    EMAIL_DEV = "neemias123654@gmail.com"
    SENHA_DESENVOLVEDOR = "DEV_MASTER_2026"

def criptografar_senha(senha_pura):
    return hashlib.sha256(senha_pura.encode('utf-8')).hexdigest()

# --- ATUALIZAÇÃO E INICIALIZAÇÃO DO BANCO DE DADOS ---
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
            area_id INTEGER,
            status_aprovacao TEXT DEFAULT 'Aprovado'
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE funcionarios ADD COLUMN status_aprovacao TEXT DEFAULT 'Aprovado'")
    except sqlite3.OperationalError:
        pass 
    
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
        CREATE TABLE IF NOT EXISTS matriz_requisitos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cargo TEXT NOT NULL,
            curso_obrigatorio TEXT NOT NULL,
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
            status_pagamento INTEGER DEFAULT 1,
            permissao_uso INTEGER DEFAULT 1,
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
            rastro_tecnico TEXT,
            status TEXT DEFAULT 'Pendente'
        )
    ''')
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_func_email ON funcionarios(usuario_email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_func_area ON funcionarios(area_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cursos_email ON outros_cursos(usuario_email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matriz_email ON matriz_requisitos(usuario_email);")

    conn.commit()
    conn.close()

# --- FUNÇÕES DE CONTROLE DE LICENÇA (DEV) ---
def alterar_status_licenca(usuario_id, status_pagto, permissao):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios 
        SET status_pagamento = ?, permissao_uso = ? 
        WHERE id = ?
    """, (status_pagto, permissao, usuario_id))
    conn.commit()
    conn.close()

# --- FUNÇÕES DA MATRIZ DE REQUISITOS ---
def adicionar_requisito_matriz(cargo, curso, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO matriz_requisitos (cargo, curso_obrigatorio, usuario_email) VALUES (?, ?, ?)", 
                   (cargo.strip().upper(), curso.strip(), usuario_email))
    conn.commit()
    conn.close()

def listar_requisitos_matriz(usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, cargo, curso_obrigatorio FROM matriz_requisitos WHERE usuario_email = ?", (usuario_email,))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def delete_requisito_matriz(id_req, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matriz_requisitos WHERE id = ? AND usuario_email = ?", (id_req, usuario_email))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE FILA DE AUTOCADASTRO ---
def adicionar_funcionario_pendente(nome, cargo, validade_curso, validade_aso, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO funcionarios (nome, cargo, validade_curso, validade_aso, usuario_email, area_id, status_aprovacao) 
        VALUES (?, ?, ?, ?, ?, NULL, 'Pendente')
    """, (nome, cargo, validade_curso, validade_aso, usuario_email))
    ultimo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ultimo_id

def listar_funcionarios_por_status(usuario_email, status='Aprovado'):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, cargo, validade_curso, validade_aso, area_id FROM funcionarios WHERE usuario_email = ? AND status_aprovacao = ?", (usuario_email, status))
    resultados = cursor.fetchall()
    conn.close()
    return resultados

def alterar_status_aprovacao_funcionario(id_func, novo_status, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    if novo_status == 'Aprovado':
        cursor.execute("UPDATE funcionarios SET status_aprovacao = 'Aprovado' WHERE id = ? AND usuario_email = ?", (id_func, usuario_email))
    else:
        cursor.execute("DELETE FROM funcionarios WHERE id = ? AND usuario_email = ?", (id_func, usuario_email))
        cursor.execute("DELETE FROM outros_cursos WHERE funcionario_id = ? AND usuario_email = ?", (id_func, usuario_email))
    conn.commit()
    conn.close()

# --- AUTENTICAÇÃO ---
def verificar_login(email, senha):
    if email == EMAIL_DEV and senha == SENHA_DESENVOLVEDOR:
        return (EMAIL_DEV, "0000000000", 1, 1, "DEVELOPER MASTER")
        
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    senha_hash = criptografar_senha(senha)
    cursor.execute("SELECT email, telefone, status_pagamento, permissao_uso, nome_empresa FROM usuarios WHERE email = ? AND senha = ?", (email, senha_hash))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

def buscar_usuario_por_email(email):
    if email == EMAIL_DEV:
        return (EMAIL_DEV, "0000000000", 1, 1, "DEVELOPER MASTER")
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, telefone, status_pagamento, permissao_uso, nome_empresa FROM usuarios WHERE email = ?", (email,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario

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

def adicionar_funcionario(nome, cargo, validade_curso, validade_aso, usuario_email, area_id):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO funcionarios (nome, cargo, validade_curso, validade_aso, usuario_email, area_id, status_aprovacao) VALUES (?, ?, ?, ?, ?, ?, 'Aprovado')", 
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

def adicionar_outro_curso(funcionario_id, nome_curso, validade, usuario_email):
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO outros_cursos (funcionario_id, nome_curso, validade, usuario_email) VALUES (?, ?, ?, ?)", (funcionario_id, nome_curso, validade, usuario_email))
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
    try: data_validade = datetime.strptime(data_str.strip(), "%Y-%m-%d").date()
    except: return "🔴 VENCIDO"
    prazo_alerta = hoje + timedelta(days=30)
    if data_validade < hoje: return "🔴 VENCIDO"
    elif hoje <= data_validade <= prazo_alerta: return "🟡 ATENÇÃO"
    else: return "🟢 EM DIA"

# --- MODAL DE EDIÇÃO ISOLADA ---
@st.dialog("✏️ Gerenciamento do Colaborador")
def modal_editar_funcionario_isolado(f_id, email_usuario_logado, dicionario_areas):
    trabalhador = buscar_funcionario_por_id(f_id, email_usuario_logado)
    if not trabalhador:
        st.error("Erro ao carregar dados do funcionário.")
        return
        
    edit_nome = st.text_input("Nome Completo:", value=trabalhador[1])
    edit_cargo = st.text_input("Cargo Ocupacional:", value=trabalhador[2])
    
    opcoes_area_edit = {"Sem Área / Geral": None}
    for id_a, nome_a in dicionario_areas.items(): opcoes_area_edit[nome_a] = id_a
    area_atual_nome = dicionario_areas.get(trabalhador[5], "Sem Área / Geral")
    edit_area_nome = st.selectbox("Setor:", list(opcoes_area_edit.keys()), index=list(opcoes_area_edit.keys()).index(area_atual_nome))
    id_area_editado = opcoes_area_edit[edit_area_nome]
    
    try: data_curso_atual = datetime.strptime(trabalhador[3], "%Y-%m-%d").date()
    except: data_curso_atual = datetime.today().date()
    try: data_aso_atual = datetime.strptime(trabalhador[4], "%Y-%m-%d").date()
    except: data_aso_atual = datetime.today().date()
    
    col_ed1, col_ed2 = st.columns(2)
    with col_ed1: edit_curso = st.date_input("Vencimento Curso Técnico:", value=data_curso_atual)
    with col_ed2: edit_aso = st.date_input("Vencimento Exame ASO:", value=data_aso_atual)
    
    st.markdown("---")
    st.markdown("### 📜 Certificados Adicionais (NRs)")
    certificados_atuais = listar_outros_cursos_por_funcionario(f_id, email_usuario_logado)
    if certificados_atuais:
        for c_id, c_nome, c_val in certificados_atuais:
            col_c1, col_c2, col_c3 = st.columns([0.5, 0.3, 0.2])
            col_c1.write(f"• **{c_nome}**")
            col_c2.write(f"`{c_val}`")
            if col_c3.button("🗑️", key=f"del_c_{c_id}"):
                deletar_outro_curso(c_id, email_usuario_logado); st.rerun()
    
    st.markdown("**Vincular Novo Certificado:**")
    col_nc1, col_nc2 = st.columns([0.6, 0.4])
    novo_c_nome = col_nc1.text_input("Nome do Curso Extra:", key=f"nc_nome_{f_id}")
    novo_c_val = col_nc2.date_input("Validade:", key=f"nc_val_{f_id}")
    if st.button("➕ Adicionar Certificado Extra", use_container_width=True):
        if novo_c_nome.strip():
            adicionar_outro_curso(f_id, novo_c_nome.strip(), str(novo_c_val), email_usuario_logado)
            st.rerun()

    st.markdown("---")
    col_btn_salvar, col_btn_deletar = st.columns(2)
    with col_btn_salvar:
        if st.button("💾 Salvar Ficha", type="primary", use_container_width=True):
            atualizar_funcionario(f_id, edit_nome, edit_cargo, str(edit_curso), str(edit_aso), email_usuario_logado, id_area_editado)
            st.session_state.id_editando = None
            st.rerun()
    with col_btn_deletar:
        if st.button("🚨 REMOVER", type="secondary", use_container_width=True):
            deletar_funcionario(f_id, email_usuario_logado)
            st.session_state.id_editando = None
            st.rerun()

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="AlertaSafe Enterprise", layout="wide", page_icon="🛡️")
init_db()

if "logado" not in st.session_state: st.session_state.logado = False
if "dados_usuario" not in st.session_state: st.session_state.dados_usuario = None
if "id_editando" not in st.session_state: st.session_state.id_editando = None
if "cursos_temporarios_autocadastro" not in st.session_state: st.session_state.cursos_temporarios_autocadastro = []

params = st.query_params

# --- PORTAL DE AUTO-CADASTRO ---
if params.get("modo") == "auto_cadastro" and "empresa" in params:
    empresa_link = params.get("empresa")
    st.markdown(f"<h2 style='text-align: center; color: #1E3A8A;'>🛡️ AlertaSafe - Ficha de Admissão Digital</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>Preencha os seus dados técnicos para validação de entrada na empresa: <b>{empresa_link}</b></p>", unsafe_allow_html=True)
    
    with st.container(border=True):
        nome_worker = st.text_input("Seu Nome Completo:")
        cargo_worker = st.text_input("Cargo / Função Ocupacional:")
        
        st.markdown("<br><b>Insira as validades encontradas nos seus documentos impressos:</b>", unsafe_allow_html=True)
        col_w1, col_w2 = st.columns(2)
        val_curso_worker = col_w1.date_input("Validade do seu Curso Técnico Base:")
        val_aso_worker = col_w2.date_input("Validade do seu Exame Médico ASO:")
        
        # --- SEÇÃO COMPLETAMENTE INTERATIVA DE CURSOS EXTRAS ---
        st.markdown("---")
        st.markdown("### 📋 Seus Certificados Extras & NRs")
        st.caption("Adicione um por um abaixo. Os certificados salvos aparecerão em sequência.")
        
        # Container dinâmico para listar os cursos já adicionados em cartões sequenciais
        if st.session_state.cursos_temporarios_autocadastro:
            for idx, c_temp in enumerate(st.session_state.cursos_temporarios_autocadastro):
                with st.container(border=True):
                    col_i1, col_i2, col_i3 = st.columns([0.5, 0.3, 0.2])
                    col_i1.markdown(f"🏅 **Curso:** `{c_temp['nome']}`")
                    col_i2.markdown(f"📅 **Validade:** `{c_temp['validade']}`")
                    if col_i3.button("🗑️ Remover", key=f"del_temp_{idx}", use_container_width=True):
                        st.session_state.cursos_temporarios_autocadastro.pop(idx)
                        st.rerun()
            st.markdown("<p style='color: #10B981; font-weight: bold;'>⬇️ Adicione o próximo certificado na sequência abaixo:</p>", unsafe_allow_html=True)
        
        # Campos de entrada de dados (Limpam automaticamente após o clique devido ao st.rerun sem valor estático fixo)
        with st.container(border=True):
            col_add_c1, col_add_c2 = st.columns([0.6, 0.4])
            nome_curso_temp = col_add_c1.text_input("Nome do Curso Extra (Ex: NR-35, NR-10):", key="input_nome_extra_novo")
            validade_curso_temp = col_add_c2.date_input("Validade deste Certificado:", key="input_val_extra_novo")
            
            if st.button("➕ Adicionar Certificado à Sequência", type="secondary", use_container_width=True):
                if nome_curso_temp.strip():
                    st.session_state.cursos_temporarios_autocadastro.append({
                        "nome": nome_curso_temp.strip().upper(),
                        "validade": str(validade_curso_temp)
                    })
                    st.rerun()
                else:
                    st.warning("⚠️ Digite o nome do certificado antes de clicar em adicionar.")
                    
        st.markdown("---")
        if st.button("🚀 Finalizar e Enviar Ficha Completa", type="primary", use_container_width=True):
            if nome_worker and cargo_worker:
                id_novo_func = adicionar_funcionario_pendente(nome_worker, cargo_worker, str(val_curso_worker), str(val_aso_worker), empresa_link)
                
                for c_salvar in st.session_state.cursos_temporarios_autocadastro:
                    adicionar_outro_curso(id_novo_func, c_salvar['nome'], c_salvar['validade'], empresa_link)
                
                st.session_state.cursos_temporarios_autocadastro = []
                st.success("🎉 Perfeito! Seus dados pessoais e toda a sequência de cursos extras foram enviados para análise do RH.")
                st.stop()
            else: 
                st.error("Por favor, preencha o seu Nome Completo e Cargo na parte superior da página antes de enviar.")
    st.stop()

# --- FLUXO DE LOGIN ---
url_user = params.get("user_session", None)
if url_user and not st.session_state.logado:
    user_b = buscar_usuario_por_email(url_user)
    if user_b:
        if user_b[0] == EMAIL_DEV or (user_b[2] == 1 and user_b[3] == 1):
            st.session_state.logado = True
            st.session_state.dados_usuario = {"email": user_b[0], "telefone": user_b[1], "tipo": "dev" if user_b[0] == EMAIL_DEV else "cliente", "nome_empresa": user_b[4]}

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ AlertaSafe Enterprise</h1>", unsafe_allow_html=True)
    col_log1, col_log2, col_log3 = st.columns([1, 1.2, 1])
    with col_log2:
        with st.container(border=True):
            st.markdown("### 🔐 Autenticação Restrita")
            with st.form("formulario_login", clear_on_submit=False):
                email_login = st.text_input("E-mail Empresarial:")
                senha_login = st.text_input("Senha Governamental:", type="password")
                botao_entrar = st.form_submit_button("Entrar no Painel Seguro", type="primary", use_container_width=True)
                
                if botao_entrar:
                    usuario = verificar_login(email_login, senha_login)
                    if usuario:
                        if usuario[0] != EMAIL_DEV and (usuario[2] == 0 or usuario[3] == 0):
                            st.error("❌ Acesso Bloqueado. Sua conta encontra-se suspensa por falta de pagamento. Contacte o administrador.")
                        else:
                            st.session_state.logado = True
                            st.session_state.dados_usuario = {"email": usuario[0], "telefone": usuario[1], "tipo": "dev" if usuario[0] == EMAIL_DEV else "cliente", "nome_empresa": usuario[4]}
                            st.query_params["user_session"] = usuario[0]
                            st.rerun()
                    else: st.error("❌ Credenciais inválidas ou conta não localizada.")
else:
    email_usuario_logado = st.session_state.dados_usuario['email']
    tipo_usuario = st.session_state.dados_usuario.get('tipo', 'cliente')

    col_t1, col_sair = st.columns([0.85, 0.15])
    with col_t1: st.markdown(f"<h2 style='margin:0;'>🛡️ Painel AlertaSafe — {st.session_state.dados_usuario.get('nome_empresa', email_usuario_logado)}</h2>", unsafe_allow_html=True)
    with col_sair:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False; st.session_state.dados_usuario = None
            st.query_params.clear(); st.rerun()

    # =========================================================================
    # 👑 VISÃO EXCLUSIVA DO DESENVOLVEDOR MASTER (PAINEL DEV)
    # =========================================================================
    if email_usuario_logado == EMAIL_DEV or tipo_usuario == "dev":
        st.markdown("### 🎛️ Central de Governança do Desenvolvedor")
        
        aba_clientes, aba_logs = st.tabs(["👥 Gerenciamento de Clientes / Empresas", "🪵 Logs de Erros do Sistema"])
        
        with aba_clientes:
            st.subheader("Controle de Licenças e Permissões")
            
            with st.expander("➕ Cadastrar Novo Cliente / Empresa", expanded=False):
                with st.form("form_novo_usuario_dev", clear_on_submit=True):
                    col_u1, col_u2 = st.columns(2)
                    u_empresa = col_u1.text_input("Nome Comercial da Empresa:")
                    u_email = col_u2.text_input("E-mail de Login do Cliente:")
                    
                    col_u3, col_u4, col_u5 = st.columns(3)
                    u_senha = col_u3.text_input("Senha de Acesso:", type="password")
                    u_cpf = col_u4.text_input("CPF ou CNPJ:")
                    u_telefone = col_u5.text_input("Telefone:")
                    
                    if st.form_submit_button("🚀 Registrar Empresa e Ativar Licença", type="primary", use_container_width=True):
                        if u_email and u_senha and u_empresa:
                            try:
                                conn = sqlite3.connect('alerta_safe.db')
                                cursor = conn.cursor()
                                senha_criptografada = criptografar_senha(u_senha)
                                
                                cursor.execute("""
                                    INSERT INTO usuarios (email, senha, cpf, telefone, status_pagamento, permissao_uso, nome_empresa)
                                    VALUES (?, ?, ?, ?, 1, 1, ?)
                                """, (u_email.strip(), senha_criptografada, u_cpf.strip(), u_telefone.strip(), u_empresa.strip()))
                                conn.commit()
                                conn.close()
                                st.success(f"🎉 Empresa '{u_empresa}' cadastrada com sucesso!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                r = st.error("❌ Erro: Este e-mail já está cadastrado no banco de dados.")
                            except Exception as e:
                                st.error(f"Erro operacional: {e}")
                        else:
                            st.warning("⚠️ Preencha pelo menos Nome da Empresa, E-mail e Senha.")
            
            st.markdown("---")
            st.markdown("#### Empresas com Acesso Ativo")
            
            conn = sqlite3.connect('alerta_safe.db')
            df_usuarios = pd.read_sql_query("SELECT id, nome_empresa, email, cpf, status_pagamento, permissao_uso FROM usuarios", conn)
            conn.close()
            
            if not df_usuarios.empty:
                df_usuarios['status_pagamento'] = df_usuarios['status_pagamento'].apply(lambda x: "🟢 Pago" if x == 1 else "🔴 Inadimplente")
                df_usuarios['permissao_uso'] = df_usuarios['permissao_uso'].apply(lambda x: "🟢 Liberado" if x == 1 else "🔴 BLOQUEADO")
                st.dataframe(df_usuarios, use_container_width=True)
                
                st.markdown("#### ⚡ Ações Rápidas de Cobrança e Bloqueio")
                col_sel_emp, col_btn_ok, col_btn_block = st.columns([0.5, 0.25, 0.25])
                
                opcoes_empresas = {f"{row['nome_empresa']} ({row['email']})": row['id'] for _, row in df_usuarios.iterrows()}
                empresa_selecionada = col_sel_emp.selectbox("Selecione a empresa para alterar o acesso:", list(opcoes_empresas.keys()))
                
                if empresa_selecionada:
                    id_usuario_alt = opcoes_empresas[empresa_selecionada]
                    
                    if col_btn_ok.button("🟢 Permitir Acesso (Pago)", use_container_width=True):
                        alterar_status_licenca(id_usuario_alt, 1, 1)
                        st.success("Licença reativada e acesso liberado!")
                        st.rerun()
                        
                    if col_btn_block.button("🔴 Bloquear Acesso (Inadimplente)", use_container_width=True):
                        alterar_status_licenca(id_usuario_alt, 0, 0)
                        st.error("Acesso bloqueado por falta de pagamento!")
                        st.rerun()
            else: 
                st.info("Nenhum cliente cadastrado no banco de dados até o momento.")
                
        with aba_logs:
            st.subheader("Rastro de Erros em Tempo Real (Logs)")
            conn = sqlite3.connect('alerta_safe.db')
            df_erros = pd.read_sql_query("SELECT * FROM logs_erros ORDER BY id DESC", conn)
            conn.close()
            
            if not df_erros.empty:
                st.dataframe(df_erros, use_container_width=True)
            else: st.success("✅ Nenhum erro registrado! Sistema operando perfeitamente.")

    # =========================================================================
    # 🏢 VISÃO TRADICIONAL DOS CLIENTES DA PLATAFORMA (EMPRESAS)
    # =========================================================================
    else:
        lista_areas_cadastradas = listar_areas(email_usuario_logado)
        dicionario_areas = {a[0]: a[1] for a in lista_areas_cadastradas}
        
        requisitos_banco = listar_requisitos_matriz(email_usuario_logado)
        mapa_requisitos = {}
        for r_id, r_cargo, r_curso in requisitos_banco:
            if r_cargo not in mapa_requisitos: mapa_requisitos[r_cargo] = []
            mapa_requisitos[r_cargo].append(r_curso)

        if st.session_state.id_editando: modal_editar_funcionario_isolado(st.session_state.id_editando, email_usuario_logado, dicionario_areas)

        aba_dash, aba_fila_trabalhador, aba_cadastro, aba_matriz_trava, aba_config = st.tabs([
            "📊 Dashboard Operacional", "📥 Fila de Admissão Digital", "➕ Novo Registro Individual", "📋 Matriz de NRs por Função", "🏗️ Infraestrutura / Áreas"
        ])

        def renderizar_grid_funcionarios(funcionarios_lista):
            st.markdown("<hr style='margin:4px 0; border-color:#555;' />", unsafe_allow_html=True)
            for func in funcionarios_lista:
                f_id = func['ID']
                col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 1.8, 1.3, 1.3, 1.3, 2.5, 0.5])
                col1.write(f"`{f_id}`")
                col2.write(func['Nome'])
                col3.write(func['Cargo'])
                col4.write(f"{func['VCourses']}\n\n{func['StatC']}")
                col5.write(f"{func['VASO']}\n\n{func['StatA']}")
                
                if func['Irregularidades']:
                    col6.markdown(f"<span style='color:#EF4444;'><b>⚠️ BLOQUEADO EM OPERAÇÃO:</b><br>{func['Irregularidades']}</span>", unsafe_allow_html=True)
                else: col6.write(func['Extras'] if func['Extras'] else "Nenhum certificado anexo.")
                    
                if col7.button("✏️", key=f"btn_edit_{f_id}"):
                    st.session_state.id_editando = f_id
                    st.rerun()

        with aba_dash:
            lista_funcionarios = listar_funcionarios_por_status(email_usuario_logado, 'Aprovado')
            todos_certificados = listar_outros_cursos(email_usuario_logado)
            
            mapa_certificados = {}
            for cert in todos_certificados:
                func_id = cert[4]
                if func_id not in mapa_certificados: mapa_certificados[func_id] = {}
                mapa_certificados[func_id][cert[2].strip().upper()] = cert[3]

            funcionarios_processados = []
            for func in lista_funcionarios:
                f_id, f_nome, f_cargo, f_vcurso, f_vaso, f_area = func
                status_curso = calcular_status(f_vcurso)
                status_aso = calcular_status(f_vaso)
                certificados_do_cara = mapa_certificados.get(f_id, {})
                
                requisitos_do_cargo = mapa_requisitos.get(f_cargo.strip().upper(), [])
                falhas_encontradas = []
                for req_curso in requisitos_do_cargo:
                    req_curso_clean = req_curso.strip().upper()
                    if req_curso_clean not in certificados_do_cara: falhas_encontradas.append(f"Falta curso obrigatório: {req_curso}")
                    else:
                        validade_do_req = certificados_do_cara[req_curso_clean]
                        if "🔴" in calcular_status(validade_do_req): falhas_encontradas.append(f"{req_curso} está VENCIDO")

                texto_irregularidades = "; ".join(falhas_encontradas)
                funcionarios_processados.append({
                    "ID": f_id, "Nome": f_nome, "Cargo": f_cargo, "VCourses": f_vcurso, "StatC": status_curso, "VASO": f_vaso, "StatA": status_aso,
                    "Extras": ", ".join([f"{k} ({calcular_status(v)})" for k, v in certificados_do_cara.items()]), "Area_ID": f_area, "Irregularidades": texto_irregularidades
                })

            if lista_areas_cadastradas:
                for id_a, nome_a in lista_areas_cadastradas:
                    filtro_area = [f for f in funcionarios_processados if f["Area_ID"] == id_a]
                    if filtro_area:
                        with st.expander(f"📁 Setor: {nome_a} ({len(filtro_area)})", expanded=True): renderizar_grid_funcionarios(filtro_area)
                            
            sem_area = [f for f in funcionarios_processados if f["Area_ID"] is None]
            if sem_area:
                with st.expander(f"❓ Funcionários sem Setor Definido ({len(sem_area)})", expanded=True): renderizar_grid_funcionarios(sem_area)

        with aba_fila_trabalhador:
            st.subheader("📥 Central de Homologação de Admissão Remota")
            
            try:
                host_url = st.context.headers.get("Host", "localhost:8501")
                protocolo = "https" if "streamlit.app" in host_url else "http"
                host_atual = f"{protocolo}://{host_url}"
            except Exception:
                host_atual = "http://localhost:8501"

            link_autocadastro = f"{host_atual}/?modo=auto_cadastro&empresa={urllib.parse.quote(email_usuario_logado)}"
            st.info("💡 **Link de Recrutamento:** Copie o endereço abaixo e envie pelo WhatsApp para os novos colaboradores.")
            st.code(link_autocadastro, language="markdown")
            
            fila_pendentes = listar_funcionarios_por_status(email_usuario_logado, 'Pendente')
            todos_certificados = listar_outros_cursos(email_usuario_logado)
            
            mapa_certificados = {}
            for cert in todos_certificados:
                func_id = cert[4]
                if func_id not in mapa_certificados: mapa_certificados[func_id] = []
                mapa_certificados[func_id].append(f"{cert[2]} (Val: {cert[3]})")

            if not fila_pendentes: st.success("🎉 Nenhuma ficha pendente de revisão.")
            else:
                for p_id, p_nome, p_cargo, p_vcurso, p_vaso, _ in fila_pendentes:
                    with st.container(border=True):
                        col_p1, col_p2, col_p3 = st.columns([0.6, 0.2, 0.2])
                        with col_p1:
                            st.markdown(f"👤 **Nome:** {p_nome} | **Cargo:** {p_cargo}")
                            st.markdown(f"📅 *Vencimento Curso Base:* `{p_vcurso}` | *Vencimento ASO:* `{p_vaso}`")
                            
                            cursos_extras_func = mapa_certificados.get(p_id, [])
                            if cursos_extras_func:
                                st.markdown(f"📜 **Certificados Extras Vinculados:** {', '.join(cursos_extras_func)}")
                            else:
                                st.caption("Nenhum certificado adicional anexo.")
                                
                        with col_p2:
                            if st.button("✅ Aprovar Entrada", key=f"aprov_{p_id}", use_container_width=True):
                                alterar_status_aprovacao_funcionario(p_id, 'Aprovado', email_usuario_logado)
                                st.success("Funcionário admitido!"); st.rerun()
                        with col_p3:
                            if st.button("❌ Recusar Ficha", key=f"recus_{p_id}", use_container_width=True):
                                alterar_status_aprovacao_funcionario(p_id, 'Recusado', email_usuario_logado)
                                st.warning("Ficha descartada."); st.rerun()

        with aba_cadastro:
            st.subheader("➕ Cadastro Administrativo Direto")
            with st.form("form_cadastro_direto", clear_on_submit=True):
                n_nome = st.text_input("Nome Completo:")
                n_cargo = st.text_input("Cargo:")
                opcoes_c = {"Setor Geral": None}
                for id_a, nome_a in lista_areas_cadastradas: opcoes_c[nome_a] = id_a
                n_area = st.selectbox("Vincular ao Setor:", list(opcoes_c.keys()))
                n_vcurso = st.date_input("Validade do Curso Técnico:")
                n_vaso = st.date_input("Validade do Exame ASO:")
                if st.form_submit_button("Cadastrar e Homologar"):
                    if n_nome and n_cargo:
                        adicionar_funcionario(n_nome, n_cargo, str(n_vcurso), str(n_vaso), email_usuario_logado, opcoes_c[n_area])
                        st.success("Colaborador registrado com sucesso!"); st.rerun()

        with aba_matriz_trava:
            st.subheader("📋 Configuração de Matriz de Requisitos Mandatórios")
            with st.form("form_matriz"):
                m_cargo = st.text_input("Nome do Cargo Técnico (Ex: Soldador, Montador):")
                m_curso = st.text_input("Nome do Certificado Exigido por Lei (Ex: NR-35, NR-10):")
                if st.form_submit_button("🔨 Fixar Regra Regulatória"):
                    if m_cargo and m_curso:
                        adicionar_requisito_matriz(m_cargo, m_curso, email_usuario_logado)
                        st.success(f"Regra fixada: Todo {m_cargo} precisa de {m_curso} ativo!"); st.rerun()
                        
            st.markdown("### ⚠️ Regras Ativas na Empresa")
            if not requisitos_banco: st.caption("Nenhuma obrigatoriedade de cargo configurada atualmente.")
            else:
                for r_id, r_cargo, r_curso in requisitos_banco:
                    col_r1, col_r2 = st.columns([0.8, 0.2])
                    col_r1.write(f"• Profissionais no cargo de **{r_cargo}** precisam obrigatoriamente do certificado de **{r_curso}**.")
                    if col_r2.button("Deletar Regra", key=f"del_req_{r_id}"):
                        delete_requisito_matriz(r_id, email_usuario_logado); st.rerun()

        with aba_config:
            st.subheader("🏗️ Controle de Divisão Industrial")
            col_ar1, col_ar2 = st.columns(2)
            with col_ar1:
                nome_nova_area = st.text_input("Nome Comercial da Área / Frente de Trabalho:")
                if st.button("Criar Setor"):
                    if nome_nova_area: adicionar_area(nome_nova_area, email_usuario_logado); st.rerun()
