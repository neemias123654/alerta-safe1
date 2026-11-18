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

# Esconde tracebacks técnicos do cliente final
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
    st.error("❌ Erro de Configuração: As chaves secretas não foram encontradas no arquivo `.streamlit/secrets.toml`. Configure-as antes de iniciar.")
    st.stop()

# ===================================================================
# --- FUNÇÕES AUXILIARES DE SEGURANÇA (HASH DE SENHAS) ---
# ===================================================================
def gerar_hash_senha(senha_plana: str) -> str:
    return bcrypt.hashpw(senha_plana.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha_plana.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception:
        return False

# ===================================================================
# --- INICIALIZAÇÃO DO BANCO DE DADOS (SQLITE COM AUDITORIA) ---
# ===================================================================
def init_db():
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        
        # Tabela de empresas / tenants
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_empresa TEXT UNIQUE NOT NULL,
                data_criacao TEXT
            )
        ''')
        
        # Tabela de usuários com vínculo de empresa e hash seguro
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                empresa_id INTEGER,
                status TEXT DEFAULT 'bloqueado',
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            )
        ''')

        # Tabela de funcionários vinculada por empresa
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
        
        # Tabela de certificados
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

def registrar_log(usuario, acao, detalhes):
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs_auditoria (usuario, acao, detalhes, data_hora) VALUES (?, ?, ?, ?)",
            (usuario, acao, detalhes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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

    if "p" in query_params and query_params["p"] == "consultar":
        id_func = query_params.get("id_func")
        
        st.title("🛡️ AlertaSafe - Validação de Treinamentos")
        st.write("---")

        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT nome, cargo, status FROM funcionarios WHERE id = ?", (id_func,))
        func = cursor.fetchone()
        
        if not func or func[2] == 'pendente':
            st.error("❌ Colaborador não localizado ou aguardando aprovação interna do RH.")
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

    elif "p" in query_params and query_params["p"] == "cadastrar_func":
        st.title("📋 Portal de Cadastro do Colaborador")
        st.write("Insira suas informações abaixo para que o RH da empresa realize a validação.")
        
        with st.form("form_auto_cadastro"):
            nome_auto = st.text_input("Seu Nome Completo")
            cpf_auto = st.text_input("Seu CPF (Apenas números)")
            cargo_auto = st.text_input("Sua Função / Cargo Atual")
            whatsapp_auto = st.text_input("Seu WhatsApp com DDD (Ex: 5522999999999)")
            
            if st.form_submit_button("Enviar Cadastro para Análise"):
                if nome_auto and cpf_auto:
                    cpf_limpo = cpf_auto.strip().replace(".", "").replace("-", "")
                    try:
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO funcionarios (nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, 'pendente')",
                            (nome_auto.strip(), cpf_limpo, cargo_auto.strip(), whatsapp_auto.strip())
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
# PARTE 2: TELA DE LOGIN E AUTO-CADASTRO DE CLIENTES
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
                cursor.execute("SELECT u.senha, u.status, e.nome_empresa FROM usuarios u LEFT JOIN empresas e ON u.empresa_id = e.id WHERE u.usuario = ?", (input_user,))
                resultado = cursor.fetchone()
                conn.close()
                
                if resultado and verificar_senha(input_pass, resultado[0]):
                    senha_hash_db, status_atual, nome_empresa = resultado
                    if status_atual == 'bloqueado':
                        st.error("🔒 Sua conta está **AGUARDANDO LIBERAÇÃO** do administrador.")
                    else:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = input_user
                        st.session_state['empresa_atual'] = nome_empresa or "Matriz"
                        registrar_log(input_user, "LOGIN", "Login efetuado com sucesso")
                        st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
                    
        with aba_cadastro:
            st.subheader("Solicitar Acesso ao Sistema")
            nova_empresa = st.text_input("Nome da Empresa / Organização", key="cad_empresa")
            novo_user = st.text_input("Escolha um Nome de Usuário", key="cad_user")
            nova_pass = st.text_input("Crie uma Senha", type="password", key="cad_pass")
            confirma_pass = st.text_input("Confirme a Senha", type="password", key="cad_pass_conf")
            
            if st.button("Finalizar Meu Cadastro"):
                if novo_user and nova_pass and nova_empresa:
                    if nova_pass != confirma_pass:
                        st.error("❌ As senhas não coincidem!")
                    else:
                        try:
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            # Insere empresa se não existir
                            cursor.execute("INSERT OR IGNORE INTO empresas (nome_empresa, data_criacao) VALUES (?, ?)", (nova_empresa, datetime.now().strftime("%Y-%m-%d")))
                            cursor.execute("SELECT id FROM empresas WHERE nome_empresa = ?", (nova_empresa,))
                            emp_id = cursor.fetchone()[0]
                            
                            senha_criptografada = gerar_hash_senha(nova_pass)
                            cursor.execute("INSERT INTO usuarios (usuario, senha, empresa_id, status) VALUES (?, ?, ?, 'bloqueado')", (novo_user, senha_criptografada, emp_id))
                            conn.commit()
                            conn.close()
                            st.success(f"🎉 Conta da empresa **{nova_empresa}** criada! Status: **BLOQUEADO**. Aguarde o Dev liberar.")
                        except sqlite3.IntegrityError:
                            st.error("❌ Este nome de usuário já está sendo utilizado.")
                else:
                    st.warning("Preencha todos os campos obrigatórios.")
                    
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
# PARTE 4: PAINEL ADMINISTRATIVO INTERNO (RH)
# ===================================================================
try:
    st.sidebar.title(f"👤 {st.session_state['usuario_atual']}")
    st.sidebar.caption(f"🏢 {st.session_state.get('empresa_atual', 'Geral')}")
    if st.sidebar.button("🚪 Sair do Sistema"):
        registrar_log(st.session_state['usuario_atual'], "LOGOUT", "Usuário saiu do sistema")
        st.session_state['logado'] = False
        st.rerun()

    st.sidebar.write("---")
    st.sidebar.title("Navegação")
    opcao = st.sidebar.radio("Selecione uma Tela", [
        "Painel Geral", 
        "Cadastrar Funcionário", 
        "📥 Aprovações de Funcionários", 
        "Leitura de Certificados (IA)", 
        "Gerenciar Crachás / QR Codes", 
        "⚙️ Painel do Dev (Aprovações)"
    ])

    if opcao == "Painel Geral":
        st.subheader("📊 Status de Conformidade Operacional")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM funcionarios WHERE status = 'aprovado'")
        total_func = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM certificados")
        total_cert = cursor.fetchone()[0]
        conn.close()
        
        st.metric("Total de Colaboradores Ativos", total_func)
        st.metric("Total de Certificados Ativos", total_cert)

    elif opcao == "Cadastrar Funcionário":
        st.subheader("👤 Cadastro de Colaboradores")
        link_auto_cadastro = f"{LINK_DA_SUA_VPS}/?p=cadastrar_func"
        st.info(f"🔗 **Link de Auto-Cadastro:**\nEnvie para os funcionários se registrarem:\n\n`{link_auto_cadastro}`")
        
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
                            cursor.execute("INSERT INTO funcionarios (nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, 'aprovado')", (nome, cpf, cargo, whatsapp))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ {nome} cadastrado com sucesso!")
                        except sqlite3.IntegrityError:
                            st.error("❌ Este CPF já está cadastrado.")
                    else:
                        st.warning("Preencha Nome e CPF.")
                        
        with aba_massa:
            st.markdown("### 🗂️ Importação de Funcionários em Massa")
            modelo_dados = {
                "Nome Completo": ["Fulano de Tal"],
                "CPF": ["12345678901"],
                "Cargo": ["Técnico de Segurança"],
                "WhatsApp (com DDD)": ["5522999999999"]
            }
            df_modelo = pd.DataFrame(modelo_dados)
            csv_modelo = df_modelo.to_csv(index=False, encoding='utf-8')
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
                            cp = str(linha.get("CPF", "")).strip().replace(".", "").replace("-", "")
                            cg = str(linha.get("Cargo", "")).strip()
                            wh = str(linha.get("WhatsApp (com DDD)", "")).strip()
                            if nm and cp and nm != "nan":
                                try:
                                    cursor.execute("INSERT INTO funcionarios (nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, 'aprovado')", (nm, cp, cg, wh))
                                    sucessos += 1
                                except sqlite3.IntegrityError:
                                    pass
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 {sucessos} funcionários importados com sucesso!")
                except Exception:
                    st.error("❌ Erro ao processar planilha.")

    elif opcao == "📥 Aprovações de Funcionários":
        st.subheader("📥 Solicitações de Auto-Cadastro")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cpf, cargo, whatsapp FROM funcionarios WHERE status = 'pendente'")
        pendentes = cursor.fetchall()
        conn.close()
        
        if not pendentes:
            st.info("🟢 Nenhuma solicitação pendente.")
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
                        st.rerun()
                    if st.button("❌ Recusar", key=f"rec_{f_id}"):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM funcionarios WHERE id = ?", (f_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                st.markdown("---")

    elif opcao == "Leitura de Certificados (IA)":
        st.subheader("🤖 Cadastro com Inteligência Artificial")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM funcionarios WHERE status = 'aprovado'")
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
                            st.success("Salvo com sucesso!")
                            del st.session_state['ia_resultado']

    elif opcao == "Gerenciar Crachás / QR Codes":
        st.subheader("🪪 Emissão de Crachás Digitais")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cargo FROM funcionarios WHERE status = 'aprovado'")
        funcs = cursor.fetchall()
        conn.close()
        
        for f_id, f_nome, f_cargo in funcs:
            with st.expander(f"👤 {f_nome}"):
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

    elif opcao == "⚙️ Painel do Dev (Aprovações)":
        st.subheader("⚙️ Painel do Desenvolvedor")
        senha_dev = st.text_input("Senha Mestre:", type="password")
        
        if senha_dev == SENHA_MESTRE_DEV:
            st.success("🔓 Acesso Autorizado!")
            conn = sqlite3.connect('alerta_safe.db')
            cursor = conn.cursor()
            cursor.execute("SELECT u.id, u.usuario, e.nome_empresa, u.status FROM usuarios u LEFT JOIN empresas e ON u.empresa_id = e.id")
            usuarios = cursor.fetchall()
            conn.close()
            
            for u_id, u_nome, u_emp, u_status in usuarios:
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.markdown(f"👤 **{u_nome}** | 🏢 `{u_emp}`")
                with col2:
                    st.markdown("🟢 Ativo" if u_status == 'aprovado' else "🔒 Bloqueado")
                with col3:
                    if u_status == 'bloqueado':
                        if st.button("Ativar", key=f"atv_{u_id}"):
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE usuarios SET status = 'aprovado' WHERE id = ?", (u_id,))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    else:
                        if st.button("Bloquear", key=f"blq_{u_id}"):
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE usuarios SET status = 'bloqueado' WHERE id = ?", (u_id,))
                            conn.commit()
                            conn.close()
                            st.rerun()
                st.markdown("---")
        elif senha_dev != "":
            st.error("❌ Senha incorreta.")
except Exception:
    exibir_erro_amigavel()
    st.stop()
    
