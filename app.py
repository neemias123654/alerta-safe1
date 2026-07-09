import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import io
import json
import qrcode
from google import genai
from google.genai import types

# Configuração da página para ficar mais profissional
st.set_page_config(page_title="AlertaSafe Enterprise", page_icon="🛡️", layout="centered")

# ===================================================================
# --- CONFIGURAÇÕES MASTER DO DESENVOLVEDOR ---
# ===================================================================
GEMINI_API_KEY = "SUA_API_KEY_DO_GEMINI_AQUI"  # Insira a sua chave do Google AI Studio
LINK_DA_SUA_VPS = "http://163.245.200.238:8501" # IP público com a porta padrão do Streamlit
SENHA_MESTRE_DEV = "DEV_MASTER_2026"           # Senha para liberar o "Painel do Dev"
EMAIL_MASTER_DEV = "neemias123654@gmail.com"   # E-mail mestre para acesso direto

# ===================================================================
# --- INICIALIZAÇÃO DO BANCO DE DADOS (SQLITE) ---
# ===================================================================
def init_db():
    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT UNIQUE,
            cargo TEXT,
            whatsapp TEXT
        )
    ''')
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            status TEXT DEFAULT 'bloqueado'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ===================================================================
# PARTE 1: ROTEADOR DE URL (TELA PÚBLICA AO ESCANEAR O QR CODE)
# ===================================================================
query_params = st.query_params

if "p" in query_params and query_params["p"] == "consultar":
    id_func = query_params.get("id_func")
    
    st.title("🛡️ AlertaSafe - Validação de Treinamentos")
    st.write("---")

    conn = sqlite3.connect('alerta_safe.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nome, cargo FROM funcionarios WHERE id = ?", (id_func,))
    func = cursor.fetchone()
    
    if not func:
        st.error("❌ Colaborador não localizado na nossa base de dados.")
        conn.close()
        st.stop()

    nome_colaborador, cargo_colaborador = func[0], func[1]
    st.subheader(f"Colaborador: **{nome_colaborador}**")
    st.caption(f"Função/Cargo: {cargo_colaborador}")

    cursor.execute("SELECT nome_curso, data_validade FROM certificados WHERE id_funcionario = ?", (id_func,))
    cursos = cursor.fetchall()
    conn.close()

    if not cursos:
        st.warning("⚠️ Este colaborador não possui nenhum curso registado no sistema.")
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
        st.warning("### 🟨 ATENÇÃO EXIGIDA\nExiste treinamento próximo do vencimento (menos de 30 dias). Agende a reciclagem.")
    else:
        st.error("### 🟥 IMPEDIDO / ACESSO BLOQUEADO\nO colaborador possui treinamentos de segurança obrigatórios vencidos.")

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

# ===================================================================
# PARTE 2: SISTEMA DE LOGIN E ANTE-TELA (MENU RETRÁTIL)
# ===================================================================
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = ""

if not st.session_state['logado']:
    st.sidebar.title("📌 Menu de Navegação")
    menu_inicial = st.sidebar.radio(
        "Ir para:",
        ["🏠 Início / Sobre a Empresa", "📞 Contato", "🔐 Acessar o Sistema", "✨ Criar Nova Conta"]
    )
    
    if menu_inicial == "🏠 Início / Sobre a Empresa":
        st.markdown("<h1 style='text-align: center;'>🛡️ AlertaSafe Enterprise</h1>", unsafe_allow_html=True)
        st.write("---")
        st.markdown("""
        ### O que é o AlertaSafe?
        O **AlertaSafe** é uma plataforma inteligente e automatizada de gestão de conformidade em segurança do trabalho. 
        
        ### Como funciona?
        1. **Cadastro Inteligente:** Faça o upload dos certificados dos funcionários.
        2. **Leitura por IA:** Nossa IA (Gemini) analisa o documento e extrai os dados automaticamente.
        3. **Crachá com QR Code:** O sistema gera um QR Code exclusivo para cada colaborador.
        4. **Validação Instantânea:** Qualquer supervisor pode escanear o crachá em campo para checar a regularidade em tempo real.
        
        👈 *Para acessar o painel ou criar sua conta, clique na setinha ou no quadradinho no canto superior esquerdo e selecione a opção desejada.*
        """)
        
    elif menu_inicial == "📞 Contato":
        st.title("📞 Entre em Contato Conosco")
        st.write("---")
        st.markdown(f"""
        Se você tiver dúvidas, problemas técnicos ou desejar planos customizados, fale diretamente com o suporte oficial:
        
        * ✉️ **E-mail:** {EMAIL_MASTER_DEV}
        * 🕒 **Atendimento:** Segunda a Sexta, das 08h às 18h.
        """)
        
    elif menu_inicial == "🔐 Acessar o Sistema":
        st.title("🔐 Login de Clientes / Gestores")
        st.write("---")
        
        with st.form("form_login"):
            input_user = st.text_input("Usuário / E-mail")
            input_pass = st.text_input("Senha", type="password")
            botao_entrar = st.form_submit_button("Entrar no Painel", use_container_width=True)
            
        if botao_entrar:
            if input_user == EMAIL_MASTER_DEV and input_pass == SENHA_MESTRE_DEV:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = "Dev Mestre 🛠️"
                st.rerun()
            else:
                conn = sqlite3.connect('alerta_safe.db')
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM usuarios WHERE usuario = ? AND senha = ?", (input_user, input_pass))
                resultado_user = cursor.fetchone()
                conn.close()
                
                if resultado_user:
                    status_atual = resultado_user[0]
                    if status_atual == 'bloqueado' or status_atual == 'faturamento_bloqueado':
                        st.error("🔒 Seu acesso ao painel está temporariamente suspenso ou aguardando liberação. Entre em contato com o suporte técnico.")
                    else:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = input_user
                        st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
                
    elif menu_inicial == "✨ Criar Nova Conta":
        st.title("✨ Solicitar Acesso ao Sistema")
        st.write("---")
        
        with st.form("form_cadastro"):
            novo_user = st.text_input("Escolha um Nome de Usuário (Ex: nome da empresa ou e-mail)")
            nova_pass = st.text_input("Crie uma Senha Segura", type="password")
            confirma_pass = st.text_input("Confirme a sua Senha", type="password")
            botao_cadastrar = st.form_submit_button("Finalizar Meu Cadastro", use_container_width=True)
        
        if botao_cadastrar:
            if novo_user and nova_pass:
                if nova_pass != confirma_pass:
                    st.error("❌ As senhas não coincidem!")
                else:
                    try:
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (usuario, senha, status) VALUES (?, ?, 'bloqueado')", (novo_user, nova_pass))
                        conn.commit()
                        conn.close()
                        st.success("🎉 Cadastro enviado! Sua conta foi criada com o status **BLOQUEADO**. O administrador analisará seu acesso para liberação.")
                    except sqlite3.IntegrityError:
                        st.error("❌ Este nome de usuário já está sendo utilizado. Escolha outro.")
            else:
                st.warning("Por favor, preencha todos os campos do formulário.")
                
    st.stop()

# ===================================================================
# PARTE 3: FUNÇÃO DA INTELIGÊNCIA ARTIFICIAL (GEMINI)
# ===================================================================
def analisar_certificado_com_ia(arquivo_bytes, mime_type):
    if GEMINI_API_KEY == "SUA_API_KEY_DO_GEMINI_AQUI":
        return {"erro": "Configuração da API Key do Gemini está em falta. Adicione-a no topo do código."}
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        part_arquivo = types.Part.from_bytes(data=arquivo_bytes, mime_type=mime_type)
        prompt = (
            "Analise o documento anexado (certificado de curso técnico ou SMS). "
            "Extraia o nome completo do funcionario, nome exato do curso (ex: NR-35, NR-10), "
            "data de emissao e data de validade no formato AAAA-MM-DD. "
            "Retorne estritamente um objecto JSON puro com as seguintes chaves: "
            "nome_funcionario, nome_curso, data_emissao, data_validade."
        )
        response = client.models.generate_content(model='gemini-2.5-flash', contents=[part_arquivo, prompt])
        return json.loads(response.text.strip())
    except Exception as e:
        return {"erro": f"Falha na análise da IA: {str(e)}"}

# ===================================================================
# PARTE 4: PAINÉIS DE NAVEGAÇÃO INTERNOS (CLIENTE vs DEV MESTRE)
# ===================================================================
st.sidebar.title(f"👤 {st.session_state['usuario_atual']}")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    st.session_state['logado'] = False
    st.session_state['usuario_atual'] = ""
    st.rerun()

st.sidebar.write("---")

# --- SEPARAÇÃO COMPLETA: SE FOR O DEV MESTRE ---
if st.session_state['usuario_atual'] == "Dev Mestre 🛠️":
    st.sidebar.title("🛠️ Painel do Desenvolvedor")
    opcao_dev = st.sidebar.radio("Selecione uma Função:", ["Controle de Clientes"])
    
    if opcao_dev == "Controle de Clientes":
        st.title("⚙️ Controle de Acesso e Clientes")
        st.write("---")
        
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total_clientes = cursor.fetchone()[0]
        cursor.execute("SELECT id, usuario, status FROM usuarios")
        lista_usuarios = cursor.fetchall()
        conn.close()
        
        st.metric(label="Total de Clientes Cadastrados", value=total_clientes)
        st.write("---")
        
        col_user, col_status, col_acao = st.columns([3, 2, 3])
        with col_user: st.markdown("**Usuário / Cliente**")
        with col_status: st.markdown("**Status Atual**")
        with col_acao: st.markdown("**Gerenciar Acesso**")
            
        st.write("") 

        for u_id, u_nome, u_status in lista_usuarios:
            c1, c2, c3 = st.columns([3, 2, 3])
            
            with c1:
                st.write(u_nome)
                
            with c2:
                if u_status == 'bloqueado':
                    st.markdown("<span style='color:#ff4b4b; font-weight:bold;'>🔴 Pendente / Bloqueado</span>", unsafe_allow_html=True)
                elif u_status == 'faturamento_bloqueado':
                    st.markdown("<span style='color:#ffaa00; font-weight:bold;'>⚠️ Bloqueio Financeiro</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#00cc66; font-weight:bold;'>🟢 Ativo / Permitido</span>", unsafe_allow_html=True)
                    
            with c3:
                # Se o cliente estiver bloqueado por qualquer motivo, exibe o botão de permitir/confirmar cadastro
                if u_status != 'aprovado':
                    if st.button("Aprovar Cadastro ✅", key=f"perm_{u_id}", use_container_width=True):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET status = 'aprovado' WHERE id = ?", (u_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                
                # Se o cliente estiver ativo ou apenas pendente, dá a opção de bloquear por falta de pagamento
                if u_status != 'faturamento_bloqueado':
                    if st.button("Bloquear Pagamento 💳", key=f"pay_{u_id}", use_container_width=True):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET status = 'faturamento_bloqueado' WHERE id = ?", (u_id,))
                        conn.commit()
                        conn.close()
                        st.rerun()

# --- SE FOR UM CLIENTE OPERACIONAL COMUM ---
else:
    st.sidebar.title("Navegação")
    opcao = st.sidebar.radio("Selecione uma Tela", ["Painel Geral", "Cadastrar Funcionário", "Leitura de Certificados (IA)", "Gerenciar Crachás / QR Codes"])

    if opcao == "Painel Geral":
        st.subheader("📊 Status de Conformidade Operacional")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM funcionarios")
        total_func = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM certificados")
        total_cert = cursor.fetchone()[0]
        conn.close()
        
        st.metric("Total de Colaboradores Cadastrados", total_func)
        st.metric("Total de Certificados Ativos no Sistema", total_cert)

    elif opcao == "Cadastrar Funcionário":
        st.subheader("👤 Cadastro de Colaboradores")
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
                        cursor.execute("INSERT INTO funcionarios (nome, cpf, cargo, whatsapp) VALUES (?, ?, ?, ?)", (nome, cpf, cargo, whatsapp))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {nome} cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("❌ Este CPF já está cadastrado no sistema.")
                else:
                    st.warning("Preencha os campos obrigatórios (Nome e CPF).")

    elif opcao == "Leitura de Certificados (IA)":
        st.subheader("🤖 Cadastro Inteligente com Inteligência Artificial")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome FROM funcionarios")
        lista_funcionarios = cursor.fetchall()
        conn.close()
        
        if not lista_funcionarios:
            st.warning("⚠️ Cadastre pelo menos um funcionário antes de processar certificados com a IA.")
        else:
            arquivo_enviado = st.file_uploader("Carregue a foto ou o PDF do Certificado", type=["png", "jpg", "jpeg", "pdf"])
            if arquivo_enviado is not None:
                if arquivo_enviado.type in ["image/jpeg", "image/png"]:
                    st.image(arquivo_enviado, caption="Visualização do documento", width=250)
                if st.button("✨ Analisar com Gemini IA"):
                    with st.spinner("A IA está a extrair as informações... Por favor, aguarde."):
                        bytes_dados = arquivo_enviado.read()
                        resultado = analisar_certificado_com_ia(bytes_dados, arquivo_enviado.type)
                        if "erro" in resultado:
                            st.error(resultado["erro"])
                        else:
                            st.session_state['ia_resultado'] = resultado
                            st.success("Análise concluída com sucesso!")
                
                if 'ia_resultado' in st.session_state:
                    res = st.session_state['ia_resultado']
                    st.info(f"💡 Funcionário identificado no documento pela IA: **{res.get('nome_funcionario')}**")
                    with st.form("confirmar_ia"):
                        dict_func = {f"{f[1]} (ID: {f[0]})": f[0] for f in lista_funcionarios}
                        id_selecionado_txt = st.selectbox("Vincular ao Funcionário do Sistema:", list(dict_func.keys()))
                        id_final = dict_func[id_selecionado_txt]
                        nome_final_sistema = id_selecionado_txt.split(" (ID:")[0]
                        curso_final = st.text_input("Curso / Norma Regulamentadora", value=res.get("nome_curso", ""))
                        emissao_final = st.text_input("Data de Emissão (AAAA-MM-DD)", value=res.get("data_emissao", ""))
                        validade_final = st.text_input("Data de Validade (AAAA-MM-DD)", value=res.get("data_validade", ""))
                        if st.form_submit_button("💾 Confirmar e Salvar no Banco"):
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO certificados (id_funcionario, funcionario, nome_curso, data_emissao, data_validade) VALUES (?, ?, ?, ?, ?)", (id_final, nome_final_sistema, curso_final, emissao_final, validade_final))
                            conn.commit()
                            conn.close()
                            st.balloons()
                            st.success(f"Curso {curso_final} guardado para {nome_final_sistema}!")
                            del st.session_state['ia_resultado']

    elif opcao == "Gerenciar Crachás / QR Codes":
        st.subheader("🪪 Emissão de Crachás Digitais Inteligentes")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cargo FROM funcionarios")
        funcs = cursor.fetchall()
        conn.close()
        
        if not funcs:
            st.warning("Nenhum funcionário cadastrado no sistema.")
        else:
            for f_id, f_nome, f_cargo in funcs:
                with st.expander(f"👤 {f_nome} - {f_cargo or 'Sem cargo'}"):
                    url_consulta = f"{LINK_DA_SUA_VPS}/?p=consultar&id_func={f_id}"
                    qr = qrcode.QRCode(version=1, box_size=8, border=4)
                    qr.add_data(url_consulta)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    byte_im = buf.getvalue()
                    st.image(byte_im, caption="QR Code pronto para crachá", width=150)
                    st.download_button(label=f"📥 Baixar imagem do QR Code", data=byte_im, file_name=f"qrcode_funcionario_{f_id}.png", mime="image/png")
