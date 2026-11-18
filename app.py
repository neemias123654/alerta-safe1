import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import io
import json
import qrcode
import pandas as pd
import bcrypt
from google import genai
from google.genai import types

# ===================================================================
# --- CONFIGURAÇÃO DA PÁGINA E TRATAMENTO DE ERROS GLOBAL ---
# ===================================================================
st.set_page_config(
    page_title="AlertaSafe Enterprise",
    page_icon="🛡️",
    layout="padded"
)

st.config.set_option("client.showErrorDetails", False)

def exibir_erro_amigavel():
    st.error("⚠️ **Ocorreu um erro inesperado no sistema.**\n\nNossa equipe de suporte já foi notificada. Por favor, tente novamente mais tarde.")

# ===================================================================
# --- CONFIGURAÇÕES MASTER VIA st.secrets (SEGURO) ---
# ===================================================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINK_DA_SUA_VPS = st.secrets["LINK_DA_SUA_VPS"]
    SENHA_MESTRE_DEV = st.secrets["SENHA_MESTRE_DEV"]
except Exception:
    st.error("❌ Erro de Configuração: As chaves secretas não foram encontradas em `.streamlit/secrets.toml`.")
    st.stop()

# ===================================================================
# --- FUNÇÕES AUXILIARES DE SEGURANÇA E FORMATAÇÃO ---
# ===================================================================
def gerar_hash_senha(senha_plana: str) -> str:
    return bcrypt.hashpw(senha_plana.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha_plana.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception:
        return False

def limpar_cnpj(cnpj: str) -> str:
    return "".join(filter(str.isdigit, cnpj))

# ===================================================================
# --- INICIALIZAÇÃO DO BANCO DE DADOS (MULTI-TENANT & SAAS) ---
# ===================================================================
def init_db():
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        
        # Tabela de Empresas com CNPJ e Status Financeiro/Licença
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_empresa TEXT NOT NULL,
                cnpj TEXT UNIQUE NOT NULL,
                status_licenca TEXT DEFAULT 'pendente_dev',
                data_criacao TEXT
            )
        ''')
        
        # Tabela de Usuários com Perfil ('gerente' ou 'rh') e Status Individual
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                empresa_id INTEGER NOT NULL,
                perfil TEXT NOT NULL,
                status TEXT DEFAULT 'pendente',
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        ''')

        # Tabela de Funcionários isolada por empresa_id
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE,
                cargo TEXT,
                whatsapp TEXT,
                status TEXT DEFAULT 'aprovado',
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        ''')
        
        # Tabela de Certificados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_funcionario INTEGER,
                funcionario TEXT,
                nome_curso TEXT NOT NULL,
                data_emissao TEXT,
                data_validade TEXT NOT NULL,
                FOREIGN KEY (id_funcionario) REFERENCES funcionarios(id)
            )
        ''')
        
        # Tabela de Logs de Auditoria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                usuario TEXT,
                acao TEXT,
                detalhes TEXT,
                data_hora TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception:
        exibir_erro_amigavel()
        st.stop()

init_db()

def registrar_log(empresa_id, usuario, acao, detalhes):
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs_auditoria (empresa_id, usuario, acao, detalhes, data_hora) VALUES (?, ?, ?, ?, ?)",
            (empresa_id, usuario, acao, detalhes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ===================================================================
# PARTE 1: ROTEADORES DE URL PÚBLICOS (QR CODE E AUTO-CADASTRO)
# ===================================================================
try:
    query_params = st.query_params

    # ROTA A: Validação de Crachá via QR Code
    if "p" in query_params and query_params["p"] == "consultar":
        id_func = query_params.get("id_func")
        
        st.title("🛡️ AlertaSafe - Validação de Treinamentos")
        st.write("---")

        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.nome, f.cargo, f.status, e.status_licenca 
            FROM funcionarios f 
            LEFT JOIN empresas e ON f.empresa_id = e.id 
            WHERE f.id = ?
        ''', (id_func,))
        func = cursor.fetchone()
        
        if not func or func[2] == 'pendente':
            st.error("❌ Colaborador não localizado ou aguardando aprovação interna do RH.")
            conn.close()
            st.stop()

        if func[3] == 'bloqueada_pagamento':
            st.error("⛔ Consulta indisponível: A licença corporativa desta empresa encontra-se suspensa.")
            conn.close()
            st.stop()

        nome_colaborador, cargo_colaborador = func[0], func[1]
        st.subheader(f"Colaborador: **{nome_colaborador}**")
        st.caption(f"Função/Cargo: {cargo_colaborador}")

        cursor.execute("SELECT nome_curso, data_validade FROM certificados WHERE id_funcionario = ?", (id_func,))
        cursos = cursor.fetchall()
        conn.close()

        if not cursos:
            st.warning("⚠️ Este colaborador não possui nenhum curso registrado no sistema.")
            st.stop()

        hoje = datetime.now().date()
        trinta_dias_pra_frente = hoje + timedelta(days=30)
        
        status_geral = "🟢 REGULAR"
        lista_processada = []

        for nome_curso, validade_str in cursos:
            try:
                data_validade = datetime.strptime(validade_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if data_validade < hoje:
                status_linha = "🔴 VENCIDO"
                cor_linha = "red"
                status_geral = "🔴 BLOQUEADO"
            elif hoje <= data_validade <= trinta_dias_pra_frente:
                status_linha = "🟡 ALERTA"
                cor_linha = "orange"
                if status_geral != "🔴 BLOQUEADO":
                    status_geral = "🟡 ATENÇÃO"
            else:
                status_linha = "🟢 EM DIA"
                cor_linha = "green"

            lista_processada.append({
                "curso": nome_curso,
                "validade": data_validade.strftime("%d/%m/%Y"),
                "status": status_linha,
                "cor": cor_linha
            })

        if status_geral == "🟢 REGULAR":
            st.success("### 🟩 TRABALHO LIBERADO\nTodos os treinamentos obrigatórios (NRs) estão rigorosamente válidos.")
        elif status_geral == "🟡 ATENÇÃO":
            st.warning("### 🟨 ATENÇÃO EXIGIDA\nExiste treinamento próximo do vencimento (menos de 30 dias).")
        else:
            st.error("### 🟥 IMPEDIDO / ACESSO BLOQUEADO\nO colaborador possui treinamentos obrigatórios vencidos.")

        st.write("### Detalhes dos Cursos")
        for c in lista_processada:
            st.markdown(
                f'''
                <div style="padding:10px; border-radius:5px; margin-bottom:10px; border-left: 5px solid {c['cor']}; background-color: #f9f9f9; color: black;">
                    <strong style="font-size:16px;">{c['curso']}</strong><br>
                    <span>Válido até: {c['validade']}</span> | 
                    <span style="color:{c['cor']}; font-weight:bold;">{c['status']}</span>
                </div>
                ''', 
                unsafe_allow_html=True
            )
        st.stop()

    # ROTA B: Auto-Cadastro de Funcionário (vinculado à empresa pelo parâmetro emp_id)
    elif "p" in query_params and query_params["p"] == "cadastrar_func":
        emp_id_url = query_params.get("emp")
        st.title("📋 Portal de Cadastro do Colaborador")
        st.write("Insira suas informações abaixo para que o RH da empresa realize a validação.")
        
        with st.form("form_auto_cadastro"):
            nome_auto = st.text_input("Seu Nome Completo")
            cpf_auto = st.text_input("Seu CPF (Apenas números)")
            cargo_auto = st.text_input("Sua Função / Cargo Atual")
            whatsapp_auto = st.text_input("Seu WhatsApp com DDD (Ex: 5522999999999)")
            
            if st.form_submit_button("Enviar Cadastro para Análise"):
                if nome_auto and cpf_auto:
                    cpf_limpo = "".join(filter(str.isdigit, cpf_auto))
                    try:
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO funcionarios (empresa_id, nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, ?, 'pendente')",
                            (emp_id_url, nome_auto.strip(), cpf_limpo, cargo_auto.strip(), whatsapp_auto.strip())
                        )
                        conn.commit()
                        conn.close()
                        st.success("🎉 Seus dados foram transmitidos com sucesso! O RH analisará em breve.")
                    except sqlite3.IntegrityError:
                        st.error("❌ Este CPF já se encontra cadastrado no sistema.")
                else:
                    st.warning("Preencha Nome e CPF.")
        st.stop()

except Exception:
    exibir_erro_amigavel()
    st.stop()

# ===================================================================
# PARTE 2: TELA DE LOGIN E AUTO-CADASTRO DE CONTAS (GESTOR & RH)
# ===================================================================
try:
    if 'logado' not in st.session_state:
        st.session_state['logado'] = False

    if not st.session_state['logado']:
        st.title("🛡️ AlertaSafe Enterprise")
        
        aba_login, aba_cadastro = st.tabs(["🔐 Acessar Sistema", "✨ Criar Nova Conta"])
        
        with aba_login:
            st.subheader("Login de Clientes / Gestores")
            input_user = st.text_input("Usuário", key="login_user")
            input_pass = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Entrar no Painel"):
                conn = sqlite3.connect('alerta_safe.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.senha, u.status, u.perfil, u.empresa_id, e.nome_empresa, e.cnpj, e.status_licenca 
                    FROM usuarios u 
                    INNER JOIN empresas e ON u.empresa_id = e.id 
                    WHERE u.usuario = ?
                ''', (input_user,))
                resultado = cursor.fetchone()
                conn.close()
                
                if resultado and verificar_senha(input_pass, resultado[0]):
                    senha_hash_db, status_user, perfil_user, emp_id, nome_emp, cnpj_emp, status_licenca = resultado
                    
                    # 1. Verifica bloqueio financeiro/global da empresa pelo Dev
                    if status_licenca == 'bloqueada_pagamento':
                        st.error("⛔ **ACESSO SUSPENSO POR PENDÊNCIA FINANCEIRA**\n\nO acesso desta empresa está temporariamente bloqueado por ausência de pagamento. Entre em contato com o suporte comercial para regularizar.")
                    elif status_licenca == 'pendente_dev':
                        st.warning("⏳ O cadastro desta empresa ainda está aguardando aprovação inicial do administrador do sistema.")
                    # 2. Verifica aprovação individual do usuário
                    elif status_user == 'pendente_gestor':
                        st.warning("🔒 Sua conta de RH está **AGUARDANDO LIBERAÇÃO** do Gestor/Gerente da sua empresa.")
                    elif status_user == 'bloqueado':
                        st.error("🚫 Sua conta foi bloqueada pelo Gestor da sua empresa.")
                    elif status_user == 'aprovado':
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = input_user
                        st.session_state['perfil_atual'] = perfil_user
                        st.session_state['empresa_id'] = emp_id
                        st.session_state['empresa_atual'] = nome_emp
                        st.session_state['cnpj_atual'] = cnpj_emp
                        registrar_log(emp_id, input_user, "LOGIN", f"Login realizado ({perfil_user})")
                        st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
                    
        with aba_cadastro:
            st.subheader("Solicitar Acesso ao Sistema")
            
            tipo_conta = st.radio(
                "Selecione o Tipo de Conta:",
                ["👔 Gestor / Gerente (Conta Principal da Empresa)", "📋 Equipe de RH (Operacional)"],
                help="A primeira conta de cada empresa deve ser a do Gestor. Contas de RH precisam ser aprovadas pelo Gestor da empresa."
            )
            
            nova_empresa = st.text_input("Nome da Empresa / Razão Social", key="cad_empresa")
            novo_cnpj = st.text_input("CNPJ da Empresa (Apenas números)", key="cad_cnpj")
            novo_user = st.text_input("Escolha um Nome de Usuário", key="cad_user")
            nova_pass = st.text_input("Crie uma Senha", type="password", key="cad_pass")
            confirma_pass = st.text_input("Confirme a Senha", type="password", key="cad_pass_conf")
            
            if st.button("Finalizar Meu Cadastro"):
                cnpj_limpo = limpar_cnpj(novo_cnpj)
                if not (nova_empresa and cnpj_limpo and novo_user and nova_pass):
                    st.warning("⚠️ Por favor, preencha todos os campos obrigatórios.")
                elif len(cnpj_limpo) != 14:
                    st.error("❌ CNPJ inválido. Digite os 14 números do CNPJ.")
                elif nova_pass != confirma_pass:
                    st.error("❌ As senhas não coincidem!")
                else:
                    conn = sqlite3.connect('alerta_safe.db')
                    cursor = conn.cursor()
                    
                    # Verifica se o usuário já existe
                    cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (novo_user,))
                    if cursor.fetchone():
                        st.error("❌ Este nome de usuário já está em uso. Escolha outro.")
                        conn.close()
                    else:
                        cursor.execute("SELECT id, nome_empresa FROM empresas WHERE cnpj = ?", (cnpj_limpo,))
                        empresa_existente = cursor.fetchone()
                        senha_hash = gerar_hash_senha(nova_pass)
                        
                        # FLUXO 1: CADASTRO DE GESTOR (CONTA PRINCIPAL)
                        if "Gestor" in tipo_conta:
                            if empresa_existente:
                                st.error(f"❌ Já existe uma conta de Gestor principal registrada para o CNPJ **{cnpj_limpo}** ({empresa_existente[1]}). Se você faz parte da equipe, selecione a opção **Equipe de RH**.")
                            else:
                                cursor.execute(
                                    "INSERT INTO empresas (nome_empresa, cnpj, status_licenca, data_criacao) VALUES (?, ?, 'pendente_dev', ?)",
                                    (nova_empresa.strip(), cnpj_limpo, datetime.now().strftime("%Y-%m-%d"))
                                )
                                emp_id = cursor.lastrowid
                                cursor.execute(
                                    "INSERT INTO usuarios (usuario, senha, empresa_id, perfil, status) VALUES (?, ?, ?, 'gerente', 'aprovado')",
                                    (novo_user.strip(), senha_hash, emp_id)
                                )
                                conn.commit()
                                st.success(f"🎉 Solicitação da empresa **{nova_empresa}** enviada com sucesso!\n\nAguarde a liberação inicial pelo Desenvolvedor Master para acessar o painel de Gestor.")
                        
                        # FLUXO 2: CADASTRO DE EQUIPE DE RH (SUBORDINADA AO GESTOR)
                        else:
                            if not empresa_existente:
                                st.error("❌ Este CNPJ ainda não possui uma empresa ativa no sistema. Peça ao Gestor/Gerente responsável para criar a conta principal primeiro.")
                            else:
                                emp_id = empresa_existente[0]
                                cursor.execute(
                                    "INSERT INTO usuarios (usuario, senha, empresa_id, perfil, status) VALUES (?, ?, ?, 'rh', 'pendente_gestor')",
                                    (novo_user.strip(), senha_hash, emp_id)
                                )
                                conn.commit()
                                st.success(f"✅ Solicitação de acesso de **RH** enviada para a empresa **{empresa_existente[1]}**!\n\nO Gestor da sua empresa recebeu uma notificação para aprovar a sua conta.")
                        conn.close()
        st.stop()
except Exception:
    exibir_erro_amigavel()
    st.stop()

# ===================================================================
# PARTE 3: INTELIGÊNCIA ARTIFICIAL (GEMINI)
# ===================================================================
def analisar_certificado_com_ia(arquivo_bytes, mime_type):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        part_arquivo = types.Part.from_bytes(data=arquivo_bytes, mime_type=mime_type)
        prompt = (
            "Analise o documento anexado. Extraia o nome completo do funcionario, nome exato do curso (ex: NR-35, NR-10), "
            "data de emissao e data de validade no formato AAAA-MM-DD. Se a validade não estiver clara, "
            "calcule-a utilizando a regra padrão brasileira da NR. "
            "Retorne estritamente um objeto JSON puro com as chaves: nome_funcionario, nome_curso, data_emissao, data_validade. "
            "Não adicione blocos markdown nem texto adicional."
        )
        response = client.models.generate_content(model='gemini-2.5-flash', contents=[part_arquivo, prompt])
        return json.loads(response.text.strip())
    except Exception:
        return {"erro": "Falha de comunicação com o servidor de Inteligência Artificial."}

# ===================================================================
# PARTE 4: PAINEL ADMINISTRATIVO INTERNO (SEPARAÇÃO POR PERFIL)
# ===================================================================
try:
    emp_id_atual = st.session_state['empresa_id']
    perfil_atual = st.session_state['perfil_atual']
    usuario_atual = st.session_state['usuario_atual']

    st.sidebar.title(f"👤 {usuario_atual}")
    st.sidebar.caption(f"🏢 {st.session_state['empresa_atual']}")
    st.sidebar.caption(f"📄 CNPJ: {st.session_state['cnpj_atual']}")
    st.sidebar.caption(f"🔑 Perfil: {'Gestor / Gerente' if perfil_atual == 'gerente' else 'Equipe de RH'}")
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        registrar_log(emp_id_atual, usuario_atual, "LOGOUT", "Saiu do sistema")
        st.session_state['logado'] = False
        st.rerun()

    st.sidebar.write("---")

    # Verifica notificações pendentes para o Gestor
    qtd_notificacoes_rh = 0
    if perfil_atual == 'gerente':
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE empresa_id = ? AND status = 'pendente_gestor'", (emp_id_atual,))
        qtd_notificacoes_rh = cursor.fetchone()[0]
        conn.close()
        if qtd_notificacoes_rh > 0:
            st.sidebar.warning(f"🔔 Você tem **{qtd_notificacoes_rh}** solicitação(ões) de conta de RH aguardando aprovação!")

    st.sidebar.title("Navegação")
    
    # Monta o menu dinamicamente de acordo com o perfil do usuário
    menus_disponiveis = [
        "Painel Geral", 
        "Cadastrar Funcionário", 
        "📥 Aprovações de Funcionários", 
        "Leitura de Certificados (IA)", 
        "Gerenciar Crachás / QR Codes"
    ]
    
    if perfil_atual == 'gerente':
        label_gestao = f"👔 Gestão de Contas & Notificações ({qtd_notificacoes_rh})" if qtd_notificacoes_rh > 0 else "👔 Gestão de Contas da Empresa"
        menus_disponiveis.append(label_gestao)
        menus_disponiveis.append("📜 Logs de Auditoria")
        
    menus_disponiveis.append("⚙️ Painel do Dev (Master)")

    opcao = st.sidebar.radio("Selecione uma Tela", menus_disponiveis)

    # ---------------------------------------------------------------
    # TELA 1: PAINEL GERAL (ISOLADO POR EMPRESA)
    # ---------------------------------------------------------------
    if opcao == "Painel Geral":
        st.subheader(f"📊 Status Operacional — {st.session_state['empresa_atual']}")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM funcionarios WHERE empresa_id = ? AND status = 'aprovado'", (emp_id_atual,))
        total_func = cursor.fetchone()[0]
        cursor.execute('''
            SELECT COUNT(c.id) FROM certificados c 
            INNER JOIN funcionarios f ON c.id_funcionario = f.id 
            WHERE f.empresa_id = ?
        ''', (emp_id_atual,))
        total_cert = cursor.fetchone()[0]
        conn.close()
        
        col1, col2 = st.columns(2)
        col1.metric("Colaboradores Ativos da Empresa", total_func)
        col2.metric("Certificados Registrados", total_cert)

    # ---------------------------------------------------------------
    # TELA 2: CADASTRAR FUNCIONÁRIO (ISOLADO POR EMPRESA)
    # ---------------------------------------------------------------
    elif opcao == "Cadastrar Funcionário":
        st.subheader("👤 Cadastro de Colaboradores")
        link_auto_cadastro = f"{LINK_DA_SUA_VPS}/?p=cadastrar_func&emp={emp_id_atual}"
        st.info(f"🔗 **Link Exclusivo de Auto-Cadastro da Empresa:**\nEnvie para os funcionários se registrarem:\n\n`{link_auto_cadastro}`")
        
        aba_individual, aba_massa = st.tabs(["👤 Cadastro Individual", "🗂️ Cadastro em Massa (Planilha)"])
        
        with aba_individual:
            with st.form("form_func"):
                nome = st.text_input("Nome Completo")
                cpf = st.text_input("CPF")
                cargo = st.text_input("Cargo / Função")
                whatsapp = st.text_input("WhatsApp (com DDD)")
                if st.form_submit_button("Salvar Colaborador"):
                    if nome and cpf:
                        try:
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO funcionarios (empresa_id, nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, ?, 'aprovado')", 
                                (emp_id_atual, nome, "".join(filter(str.isdigit, cpf)), cargo, whatsapp)
                            )
                            conn.commit()
                            conn.close()
                            registrar_log(emp_id_atual, usuario_atual, "CADASTRO_FUNC", f"Cadastrou {nome}")
                            st.success(f"✅ {nome} cadastrado com sucesso!")
                        except sqlite3.IntegrityError:
                            st.error("❌ Este CPF já está cadastrado.")
                    else:
                        st.warning("Preencha Nome e CPF.")
                        
        with aba_massa:
            st.markdown("### 🗂️ Importação em Massa")
            modelo_dados = {"Nome Completo": ["Fulano de Tal"], "CPF": ["12345678901"], "Cargo": ["Soldador"], "WhatsApp (com DDD)": ["5522999999999"]}
            csv_modelo = pd.DataFrame(modelo_dados).to_csv(index=False, encoding='utf-8')
            st.download_button(label="📥 Baixar Modelo (.CSV)", data=csv_modelo, file_name="modelo_alertasafe.csv", mime="text/csv")
            
            arquivo_planilha = st.file_uploader("Suba a planilha preenchida", type=["csv", "xlsx"])
            if arquivo_planilha is not None:
                try:
                    df_importado = pd.read_csv(arquivo_planilha, dtype=str) if arquivo_planilha.name.endswith('.csv') else pd.read_excel(arquivo_planilha, dtype=str)
                    st.dataframe(df_importado)
                    if st.button("🚀 Confirmar e Importar"):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        sucessos = 0
                        for _, linha in df_importado.iterrows():
                            nm = str(linha.get("Nome Completo", "")).strip()
                            cp = "".join(filter(str.isdigit, str(linha.get("CPF", ""))))
                            cg = str(linha.get("Cargo", "")).strip()
                            wh = str(linha.get("WhatsApp (com DDD)", "")).strip()
                            if nm and cp and nm != "nan":
                                try:
                                    cursor.execute("INSERT INTO funcionarios (empresa_id, nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, ?, 'aprovado')", (emp_id_atual, nm, cp, cg, wh))
                                    sucessos += 1
                                except sqlite3.IntegrityError:
                                    pass
                        conn.commit()
                        conn.close()
                        registrar_log(emp_id_atual, usuario_atual, "IMPORTACAO_MASSA", f"Importou {sucessos} funcionários")
                        st.success(f"🎉 {sucessos} funcionários importados!")
                except Exception:
                    st.error("❌ Erro ao processar planilha.")

    # ---------------------------------------------------------------
    # TELA 3: APROVAÇÕES DE AUTO-CADASTRO DE FUNCIONÁRIOS
    # ---------------------------------------------------------------
    elif opcao == "📥 Aprovações de Funcionários":
        st.subheader("📥 Solicitações de Auto-Cadastro de Funcionários")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cpf, cargo, whatsapp FROM funcionarios WHERE empresa_id = ? AND status = 'pendente'", (emp_id_atual,))
        pendentes = cursor.fetchall()
        conn.close()
        
        if not pendentes:
            st.info("🟢 Nenhuma solicitação de funcionário pendente.")
        else:
            for f_id, f_nome, f_cpf, f_cargo, f_whats in pendentes:
                col1, col2 = st.columns([5, 2])
                with col1:
                    st.markdown(f"👤 **{f_nome}** | Cargo: `{f_cargo or 'N/I'}`")
                    st.caption(f"CPF: {f_cpf} | WhatsApp: {f_whats or 'N/I'}")
                with col2:
                    if st.button("✅ Confirmar", key=f"apr_{f_id}"):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE funcionarios SET status = 'aprovado' WHERE id = ?", (f_id,))
                        conn.commit()
                        conn.close()
                        registrar_log(emp_id_atual, usuario_atual, "APROVACAO_FUNC", f"Aprovou funcionário {f_nome}")
                        st.rerun()
                    if st.button("❌ Recusar", key=f"rec_{f_id}"):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM funcionarios WHERE id = ?", (f_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                st.markdown("---")

    # ---------------------------------------------------------------
    # TELA 4: LEITURA DE CERTIFICADOS (IA)
    # ---------------------------------------------------------------
    elif opcao == "Leitura de Certificados (IA)":
        st.subheader("🤖 Cadastro com Inteligência Artificial")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM funcionarios WHERE empresa_id = ? AND status = 'aprovado'", (emp_id_atual,))
        lista_funcs = cursor.fetchall()
        conn.close()
        
        if not lista_funcs:
            st.warning("⚠️ Cadastre funcionários ativos primeiro.")
        else:
            arquivo_enviado = st.file_uploader("Carregue o Certificado", type=["png", "jpg", "jpeg", "pdf"])
            if arquivo_enviado is not None:
                if arquivo_enviado.type in ["image/jpeg", "image/png"]:
                    st.image(arquivo_enviado, width=250)
                if st.button("✨ Analisar com Gemini IA"):
                    with st.spinner("Extraindo dados com IA..."):
                        resultado = analisar_certificado_com_ia(arquivo_enviado.read(), arquivo_enviado.type)
                        if "erro" in resultado:
                            st.error(resultado["erro"])
                        else:
                            st.session_state['ia_resultado'] = resultado
                            st.success("Análise concluída!")
                
                if 'ia_resultado' in st.session_state:
                    res = st.session_state['ia_resultado']
                    st.info(f"💡 Funcionário identificado: **{res.get('nome_funcionario')}**")
                    with st.form("confirmar_ia"):
                        dict_func = {f"{f[1]} (ID: {f[0]})": f[0] for f in lista_funcs}
                        id_sel_txt = st.selectbox("Vincular ao Funcionário:", list(dict_func.keys()))
                        id_final = dict_func[id_sel_txt]
                        curso = st.text_input("Curso / NR", value=res.get("nome_curso", ""))
                        emissao = st.text_input("Emissão (AAAA-MM-DD)", value=res.get("data_emissao", ""))
                        validade = st.text_input("Validade (AAAA-MM-DD)", value=res.get("data_validade", ""))
                        if st.form_submit_button("💾 Salvar no Banco"):
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO certificados (id_funcionario, funcionario, nome_curso, data_emissao, data_validade) VALUES (?, ?, ?, ?, ?)", (id_final, id_sel_txt.split(" (ID:")[0], curso, emissao, validade))
                            conn.commit()
                            conn.close()
                            registrar_log(emp_id_atual, usuario_atual, "CERTIFICADO_IA", f"Adicionou {curso} para ID {id_final}")
                            st.success("Salvo com sucesso!")
                            del st.session_state['ia_resultado']

    # ---------------------------------------------------------------
    # TELA 5: CRACHÁS / QR CODES
    # ---------------------------------------------------------------
    elif opcao == "Gerenciar Crachás / QR Codes":
        st.subheader("🪪 Emissão de Crachás Digitais")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cargo FROM funcionarios WHERE empresa_id = ? AND status = 'aprovado'", (emp_id_atual,))
        funcs = cursor.fetchall()
        conn.close()
        
        for f_id, f_nome, f_cargo in funcs:
            with st.expander(f"👤 {f_nome} ({f_cargo or 'Sem cargo'})"):
                url_consulta = f"{LINK_DA_SUA_VPS}/?p=consultar&id_func={f_id}"
                qr = qrcode.QRCode(version=1, box_size=8, border=4)
                qr.add_data(url_consulta)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                st.image(byte_im, width=150)
                st.download_button(label="📥 Baixar QR Code", data=byte_im, file_name=f"qr_{f_id}.png", mime="image/png")

    # ---------------------------------------------------------------
    # TELA 6: GESTÃO DE CONTAS E NOTIFICAÇÕES (EXCLUSIVA DO GESTOR)
    # ---------------------------------------------------------------
    elif "Gestão de Contas" in opcao and perfil_atual == 'gerente':
        st.subheader(f"👔 Gestão de Acessos — {st.session_state['empresa_atual']} (CNPJ: {st.session_state['cnpj_atual']})")
        
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        
        # BLOCO 1: NOTIFICAÇÕES DE NOVAS SOLICITAÇÕES DE RH
        cursor.execute("SELECT id, usuario, perfil FROM usuarios WHERE empresa_id = ? AND status = 'pendente_gestor'", (emp_id_atual,))
        solicitacoes_rh = cursor.fetchall()
        
        if solicitacoes_rh:
            st.warning(f"🔔 **Notificações Pendentes ({len(solicitacoes_rh)}):** Usuários solicitando acesso à equipe de RH desta empresa.")
            for u_id, u_nome, u_perf in solicitacoes_rh:
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.markdown(f"👤 Usuário: **{u_nome}** | Tipo: `Equipe de RH`")
                if c2.button("✅ Permitir", key=f"gest_apr_{u_id}"):
                    cursor.execute("UPDATE usuarios SET status = 'aprovado' WHERE id = ?", (u_id,))
                    conn.commit()
                    registrar_log(emp_id_atual, usuario_atual, "APROVACAO_RH", f"Gestor aprovou acesso de {u_nome}")
                    st.rerun()
                if c3.button("❌ Recusar", key=f"gest_rec_{u_id}"):
                    cursor.execute("DELETE FROM usuarios WHERE id = ?", (u_id,))
                    conn.commit()
                    registrar_log(emp_id_atual, usuario_atual, "RECUSA_RH", f"Gestor recusou acesso de {u_nome}")
                    st.rerun()
            st.write("---")

        # BLOCO 2: TODAS AS CONTAS DA EMPRESA (EDITAR / MUDAR SENHA / BLOQUEAR)
        st.markdown("### 👥 Contas Cadastradas nesta Empresa")
        cursor.execute("SELECT id, usuario, perfil, status FROM usuarios WHERE empresa_id = ? AND status != 'pendente_gestor'", (emp_id_atual,))
        contas_empresa = cursor.fetchall()
        
        for c_id, c_user, c_perf, c_stat in contas_empresa:
            badge_perfil = "👔 Gestor" if c_perf == 'gerente' else "📋 Equipe RH"
            badge_status = "🟢 Ativo" if c_stat == 'aprovado' else "🚫 Bloqueado"
            
            with st.expander(f"{badge_perfil} | Usuário: **{c_user}** — {badge_status}"):
                with st.form(f"edit_user_{c_id}"):
                    novo_nome_user = st.text_input("Editar Nome de Usuário", value=c_user)
                    nova_senha_user = st.text_input("Redefinir Senha (deixe em branco para manter a atual)", type="password")
                    
                    col_b1, col_b2 = st.columns(2)
                    salvar_edicao = col_b1.form_submit_button("💾 Salvar Alterações")
                    
                    if salvar_edicao:
                        try:
                            if nova_senha_user.strip():
                                hash_novo = gerar_hash_senha(nova_senha_user.strip())
                                cursor.execute("UPDATE usuarios SET usuario = ?, senha = ? WHERE id = ?", (novo_nome_user.strip(), hash_novo, c_id))
                            else:
                                cursor.execute("UPDATE usuarios SET usuario = ? WHERE id = ?", (novo_nome_user.strip(), c_id))
                            conn.commit()
                            registrar_log(emp_id_atual, usuario_atual, "EDICAO_CONTA", f"Editou credenciais do usuário ID {c_id}")
                            st.success("✅ Dados atualizados com sucesso!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Este nome de usuário já está em uso.")
                
                # Botão para bloquear/desbloquear contas subordinadas de RH
                if c_perf != 'gerente':
                    if c_stat == 'aprovado':
                        if st.button(f"🚫 Bloquear Acesso de {c_user}", key=f"blq_rh_{c_id}"):
                            cursor.execute("UPDATE usuarios SET status = 'bloqueado' WHERE id = ?", (c_id,))
                            conn.commit()
                            registrar_log(emp_id_atual, usuario_atual, "BLOQUEIO_RH", f"Bloqueou usuário {c_user}")
                            st.rerun()
                    else:
                        if st.button(f"🔓 Reativar Acesso de {c_user}", key=f"atv_rh_{c_id}"):
                            cursor.execute("UPDATE usuarios SET status = 'aprovado' WHERE id = ?", (c_id,))
                            conn.commit()
                            registrar_log(emp_id_atual, usuario_atual, "REATIVACAO_RH", f"Reativou usuário {c_user}")
                            st.rerun()
        conn.close()

    # ---------------------------------------------------------------
    # TELA 7: LOGS DE AUDITORIA (EXCLUSIVA DO GESTOR)
    # ---------------------------------------------------------------
    elif opcao == "📜 Logs de Auditoria" and perfil_atual == 'gerente':
        st.subheader("📜 Histórico de Auditoria da Empresa")
        conn = sqlite3.connect('alerta_safe.db')
        df_logs = pd.read_sql_query("SELECT data_hora AS 'Data/Hora', usuario AS 'Usuário', acao AS 'Ação', detalhes AS 'Detalhes' FROM logs_auditoria WHERE empresa_id = ? ORDER BY id DESC LIMIT 100", conn, params=(emp_id_atual,))
        conn.close()
        st.dataframe(df_logs, use_container_width=True)

    # ---------------------------------------------------------------
    # TELA 8: PAINEL DO DESENVOLVEDOR MASTER (CONTROLE DE LICENÇAS/EMPRESAS)
    # ---------------------------------------------------------------
    elif opcao == "⚙️ Painel do Dev (Master)":
        st.subheader("⚙️ Painel Master do Desenvolvedor — Controle de Empresas e Licenças")
        senha_dev = st.text_input("Digite a Senha Mestre do Desenvolvedor:", type="password")
        
        if senha_dev == SENHA_MESTRE_DEV:
            st.success("🔓 Acesso Master Liberado!")
            
            conn = sqlite3.connect('alerta_safe.db')
            cursor = conn.cursor()
            
            # Busca todas as empresas junto com o seu Gestor principal e total de usuários vinculados
            cursor.execute('''
                SELECT e.id, e.nome_empresa, e.cnpj, e.status_licenca, u.usuario,
                       (SELECT COUNT(*) FROM usuarios WHERE empresa_id = e.id) as total_contas
                FROM empresas e
                LEFT JOIN usuarios u ON u.empresa_id = e.id AND u.perfil = 'gerente'
                ORDER BY e.id DESC
            ''')
            empresas_lista = cursor.fetchall()
            
            st.markdown("### 🏢 Empresas Cadastradas na Plataforma")
            st.caption("Apenas as contas principais (Gestores) aparecem aqui para liberação inicial. O bloqueio financeiro suspende todas as contas vinculadas ao CNPJ.")
            st.write("---")
            
            for e_id, e_nome, e_cnpj, e_status, gestor_user, total_contas in empresas_lista:
                col1, col2, col3 = st.columns([4, 2, 3])
                
                with col1:
                    st.markdown(f"🏢 **{e_nome}**")
                    st.caption(f"📄 CNPJ: `{e_cnpj}` | 👔 Gestor Principal: **{gestor_user or 'N/A'}** ({total_contas} conta(s) vinculada(s))")
                
                with col2:
                    if e_status == 'pendente_dev':
                        st.warning("⏳ Aguardando Liberação")
                    elif e_status == 'ativa':
                        st.success("🟢 Licença Ativa")
                    elif e_status == 'bloqueada_pagamento':
                        st.error("⛔ Bloqueada (Pagamento)")
                
                with col3:
                    if e_status == 'pendente_dev':
                        if st.button("✅ Aprovar Primeira Conta (Gestor)", key=f"dev_apr_{e_id}"):
                            cursor.execute("UPDATE empresas SET status_licenca = 'ativa' WHERE id = ?", (e_id,))
                            conn.commit()
                            st.toast(f"Empresa {e_nome} liberada com sucesso!")
                            st.rerun()
                    elif e_status == 'ativa':
                        if st.button("⛔ Bloquear por Ausência de Pagamento", key=f"dev_blq_{e_id}"):
                            # Bloqueia a empresa E marca todas as contas associadas
                            cursor.execute("UPDATE empresas SET status_licenca = 'bloqueada_pagamento' WHERE id = ?", (e_id,))
                            conn.commit()
                            st.toast(f"Empresa {e_nome} (CNPJ: {e_cnpj}) e todas as suas {total_contas} contas foram bloqueadas!")
                            st.rerun()
                    elif e_status == 'bloqueada_pagamento':
                        if st.button("🔓 Regularizar Pagamento / Desbloquear", key=f"dev_desblq_{e_id}"):
                            cursor.execute("UPDATE empresas SET status_licenca = 'ativa' WHERE id = ?", (e_id,))
                            conn.commit()
                            st.toast(f"Acesso da empresa {e_nome} restabelecido!")
                            st.rerun()
                st.markdown("---")
            conn.close()
            
        elif senha_dev != "":
            st.error("❌ Senha Mestre incorreta.")
except Exception:
    exibir_erro_amigavel()
    st.stop()
    
