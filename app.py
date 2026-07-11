import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import io
import json
import qrcode
import pandas as pd
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

# Garante que o Streamlit esconderá os tracebacks técnicos de erro do cliente
st.config.set_option("client.showErrorDetails", False)

def exibir_erro_amigavel():
    st.error("⚠️ **Ocorreu um erro inesperado no sistema.**\n\nNossa equipe de desenvolvedores já foi notificada automaticamente e está ciente para corrigir o problema o mais rápido possível. Por favor, tente novamente mais tarde.")

# ===================================================================
# --- CONFIGURAÇÕES MASTER DO DESENVOLVEDOR ---
# ===================================================================
GEMINI_API_KEY = "SUA_API_KEY_DO_GEMINI_AQUI"  # Insira a sua chave do Google AI Studio
LINK_DA_SUA_VPS = "http://MEU_IP_DA_VPS_AQUI"   # Substitua pelo IP público da sua VPS DokeHost
SENHA_MESTRE_DEV = "admin123"                  # Senha para você liberar o "Painel do Dev"

# ===================================================================
# --- INICIALIZAÇÃO DO BANCO DE DADOS (SQLITE) ---
# ===================================================================
def init_db():
    try:
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        
        # Tabela de funcionários (adicionada coluna status)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE,
                cargo TEXT,
                whatsapp TEXT,
                status TEXT DEFAULT 'aprovado'
            )
        ''')
        
        # Tabela de certificados vinculados por id_funcionario
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
        
        # Tabela de Usuários com a nova coluna 'empresa'
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                empresa TEXT,
                status TEXT DEFAULT 'bloqueado'
            )
        ''')
        
        # Migração automática de bases antigas para adicionar coluna 'status' em funcionarios
        cursor.execute("PRAGMA table_info(funcionarios)")
        colunas_func = [col[1] for col in cursor.fetchall()]
        if 'status' not in colunas_func:
            cursor.execute("ALTER TABLE funcionarios ADD COLUMN status TEXT DEFAULT 'aprovado'")
        
        # Migração automática de bases antigas para adicionar coluna 'empresa' em usuarios
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_user = [col[1] for col in cursor.fetchall()]
        if 'empresa' not in colunas_user:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN empresa TEXT")
            
        conn.commit()
        conn.close()
    except Exception:
        exibir_erro_amigavel()
        st.stop()

init_db()

# ===================================================================
# PARTE 1: ROTEADORES DE URL PÚBLICOS (QR CODE E AUTO-CADASTRO)
# ===================================================================
try:
    query_params = st.query_params

    # ROTA A: Roteador de consulta pública via escaneamento do QR Code
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

    # 🆕 ROTA B: Link que o funcionário acessa de forma independente para se cadastrar sozinho
    elif "p" in query_params and query_params["p"] == "cadastrar_func":
        st.title("📋 Portal de Cadastro do Colaborador")
        st.write("Insira suas informações abaixo para que o RH da empresa realize a validação do seu perfil.")
        
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
                        # Cadastra com o status inicial fixo em 'pendente'
                        cursor.execute(
                            "INSERT INTO funcionarios (nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, 'pendente')",
                            (nome_auto.strip(), cpf_limpo, cargo_auto.strip(), whatsapp_auto.strip())
                        )
                        conn.commit()
                        conn.close()
                        st.success("🎉 Seus dados foram transmitidos com sucesso! O RH da sua empresa analisará e confirmará o seu cadastro no painel interno.")
                    except sqlite3.IntegrityError:
                        st.error("❌ Este CPF já se encontra cadastrado no sistema.")
                else:
                    st.warning("Os campos Nome Completo e CPF são de preenchimento obrigatório.")
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
                cursor.execute("SELECT status FROM usuarios WHERE usuario = ? AND senha = ?", (input_user, input_pass))
                resultado_user = cursor.fetchone()
                conn.close()
                
                if resultado_user:
                    status_atual = resultado_user[0]
                    if status_atual == 'bloqueado':
                        st.error("🔒 Sua conta está **AGUARDANDO LIBERAÇÃO** do administrador do sistema.")
                    else:
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = input_user
                        st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos.")
                    
        with aba_cadastro:
            st.subheader("Solicitar Acesso ao Sistema")
            st.write("Preencha os dados operacionais. Seu usuário ficará bloqueado até que o desenvolvedor aprove.")
            
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
                            cursor.execute("INSERT INTO usuarios (usuario, senha, empresa, status) VALUES (?, ?, ?, 'bloqueado')", (novo_user, nova_pass, nova_empresa))
                            conn.commit()
                            conn.close()
                            st.success(f"🎉 Conta da empresa **{nova_empresa}** criada com sucesso! Status: **BLOQUEADO**. Aguarde a liberação do Dev.")
                        except sqlite3.IntegrityError:
                            st.error("❌ Este nome de usuário já está sendo utilizado.")
                else:
                    st.warning("Por favor, preencha todos os campos obrigatórios.")
                    
        st.stop()
except Exception:
    exibir_erro_amigavel()
    st.stop()

# ===================================================================
# PARTE 3: FUNÇÃO DA INTELIGÊNCIA ARTIFICIAL (GEMINI)
# ===================================================================
def analisar_certificado_com_ia(arquivo_bytes, mime_type):
    if GEMINI_API_KEY == "SUA_API_KEY_DO_GEMINI_AQUI" or GEMINI_API_KEY == "":
        return {"erro": "Configuração da API Key do Gemini está em falta. Adicione-a no topo do código."}
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        part_arquivo = types.Part.from_bytes(data=arquivo_bytes, mime_type=mime_type)
        prompt = (
            "Analise o documento anexado. Extraia o nome completo do funcionario, nome exato do curso (ex: NR-35, NR-10), "
            "data de emissao e data de validade no formato AAAA-MM-DD. Se a validade não estiver clara no documento, "
            "calcule-a utilizando a regra padrão brasileira da NR (ex: NR-35 são 2 anos; NR-33 são 1 ano) baseado na data de emissão. "
            "Retorne estritamente um objecto JSON puro com as chaves: nome_funcionario, nome_curso, data_emissao, data_validade. "
            "Não adicione blocos markdown nem texto adicional."
        )
        response = client.models.generate_content(model='gemini-2.5-flash', contents=[part_arquivo, prompt])
        return json.loads(response.text.strip())
    except Exception as e:
        return {"erro": "Falha de comunicação com o servidor de Inteligência Artificial. Os desenvolvedores já estão cientes."}

# ===================================================================
# PARTE 4: PAINEL ADMINISTRATIVO INTERNO (SISTEMA DE GESTÃO DO RH)
# ===================================================================
try:
    st.sidebar.title(f"👤 {st.session_state['usuario_atual']}")
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state['logado'] = False
        st.rerun()

    st.sidebar.write("---")
    st.sidebar.title("Navegação")
    opcao = st.sidebar.radio("Selecione uma Tela", [
        "Painel Geral", 
        "Cadastrar Funcionário", 
        "📥 Aprovações de Funcionários", # 🆕 Nova tela inserida na navegação do RH
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
        
        st.metric("Total de Colaboradores Cadastrados (Ativos)", total_func)
        st.metric("Total de Certificados Ativos no Sistema", total_cert)

    elif opcao == "Cadastrar Funcionário":
        st.subheader("👤 Cadastro de Colaboradores")
        
        # Link gerado dinamicamente para o RH copiar e enviar para os funcionários
        link_auto_cadastro = f"{LINK_DA_SUA_VPS}/?p=cadastrar_func"
        st.info(f"🔗 **Link de Auto-Cadastro para Funcionários:**\nCopie o link abaixo e envie para os funcionários se registrarem sozinhos de qualquer lugar:\n\n`{link_auto_cadastro}`")
        
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
                            st.success(f"✅ {nome} cadastrado e ativo com sucesso!")
                        except sqlite3.IntegrityError:
                            st.error("❌ Este CPF já está cadastrado no sistema.")
                    else:
                        st.warning("Preencha os campos obrigatórios (Nome e CPF).")
                        
        with aba_massa:
            st.markdown("### 🗂️ Importação de Funcionários em Massa")
            modelo_dados = {
                "Nome Completo": ["Fulano de Tal", "Ciclano da Silva"],
                "CPF": ["12345678901", "98765432100"],
                "Cargo": ["Técnico de Segurança", "Eletricista"],
                "WhatsApp (com DDD)": ["5522999999999", "5521988888888"]
            }
            df_modelo = pd.DataFrame(modelo_dados)
            csv_modelo = df_modelo.to_csv(index=False, encoding='utf-8')
            
            st.download_button(label="📥 Baixar Modelo de Planilha (.CSV)", data=csv_modelo, file_name="modelo_cadastro_alertasafe.csv", mime="text/csv")
            
            arquivo_planilha = st.file_uploader("Suba a sua planilha preenchida", type=["csv", "xlsx", "xls"])
            if arquivo_planilha is not None:
                try:
                    if arquivo_planilha.name.endswith('.csv'):
                        df_importado = pd.read_csv(arquivo_planilha, dtype=str)
                    else:
                        df_importado = pd.read_excel(arquivo_planilha, dtype=str)
                        
                    st.dataframe(df_importado)
                    
                    if st.button("🚀 Confirmar e Importar Todos"):
                        conn = sqlite3.connect('alerta_safe.db')
                        cursor = conn.cursor()
                        sucessos = 0
                        erros_duplicados = 0
                        
                        for _, linha in df_importado.iterrows():
                            nome_massa = str(linha.get("Nome Completo", "")).strip()
                            cpf_massa = str(linha.get("CPF", "")).strip().replace(".", "").replace("-", "")
                            cargo_massa = str(linha.get("Cargo", "")).strip()
                            whats_massa = str(linha.get("WhatsApp (com DDD)", "")).strip()
                            
                            if nome_massa and cpf_massa and nome_massa != "nan" and cpf_massa != "nan":
                                try:
                                    cursor.execute(
                                        "INSERT INTO funcionarios (nome, cpf, cargo, whatsapp, status) VALUES (?, ?, ?, ?, 'aprovado')",
                                        (nome_massa, cpf_massa, cargo_massa, whats_massa)
                                    )
                                    sucessos += 1
                                except sqlite3.IntegrityError:
                                    erros_duplicados += 1
                                    
                        conn.commit()
                        conn.close()
                        st.success(f"🎉 {sucessos} funcionários importados diretamente como Ativos!")
                except Exception:
                    st.error("❌ Erro ao ler planilha.")

    # 🆕 NOVA TELA DO PAINEL INTERNO: Gerenciamento e aprovação de cadastros feitos via link pelos funcionários
    elif opcao == "📥 Aprovações de Funcionários":
        st.subheader("📥 Solicitações de Cadastro de Funcionários (Auto-Cadastro)")
        st.write("Abaixo estão listados os colaboradores que utilizaram o link externo de cadastro. Revise as informações e clique em Confirmar.")
        
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, cpf, cargo, whatsapp FROM funcionarios WHERE status = 'pendente'")
        funcionarios_pendentes = cursor.fetchall()
        conn.close()
        
        if not funcionarios_pendentes:
            st.info("🟢 Nenhuma solicitação pendente no momento. Todos os cadastros externos estão atualizados!")
        else:
            for f_id, f_nome, f_cpf, f_cargo, f_whats in funcionarios_pendentes:
                with st.container():
                    col_info, col_botoes = st.columns([5, 2])
                    with col_info:
                        st.markdown(f"👤 Nome: **{f_nome}** | Cargo: `{f_cargo or 'Não Informado'}`")
                        st.caption(f"💳 CPF: {f_cpf} | 📱 WhatsApp: {f_whats or 'Não Informado'}")
                    with col_botoes:
                        c_atv, c_rec = st.columns(2)
                        with c_atv:
                            # Botão para aceitar e mudar status para aprovado
                            if st.button("✅ Confirmar", key=f"btn_aprov_func_{f_id}"):
                                conn = sqlite3.connect('alerta_safe.db')
                                cursor = conn.cursor()
                                cursor.execute("UPDATE funcionarios SET status = 'aprovado' WHERE id = ?", (f_id,))
                                conn.commit()
                                conn.close()
                                st.toast(f"Cadastro de {f_nome} aprovado com sucesso!")
                                st.rerun()
                        with c_rec:
                            # Botão para excluir caso o cadastro esteja errado ou inválido
                            if st.button("❌ Recusar", key=f"btn_delet_func_{f_id}"):
                                conn = sqlite3.connect('alerta_safe.db')
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM funcionarios WHERE id = ?", (f_id,))
                                conn.commit()
                                conn.close()
                                st.toast(f"Solicitação de {f_nome} recusada e removida.")
                                st.rerun()
                st.markdown("---")

    elif opcao == "Leitura de Certificados (IA)":
        st.subheader("🤖 Cadastro Inteligente com Inteligência Artificial")
        conn = sqlite3.connect('alerta_safe.db')
        cursor = conn.cursor()
        # Filtro adicionado: Apenas funcionários que já foram confirmados pelo RH aparecem para receber certificados
        cursor.execute("SELECT id, nome FROM funcionarios WHERE status = 'aprovado'")
        lista_funcionarios = cursor.fetchall()
        conn.close()
        
        if not lista_funcionarios:
            st.warning("⚠️ Cadastre ou aprove pelo menos um funcionário ativo antes de processar certificados com a IA.")
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
        # Filtro adicionado: Apenas funcionários ativos e confirmados possuem QR Code ativo para crachá
        cursor.execute("SELECT id, nome, cargo FROM funcionarios WHERE status = 'aprovado'")
        funcs = cursor.fetchall()
        conn.close()
        
        if not funcs:
            st.warning("Nenhum funcionário ativo cadastrado no sistema.")
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

    elif opcao == "⚙️ Painel do Dev (Aprovações)":
        st.subheader("⚙️ Painel do Desenvolvedor - Gerenciamento de Acessos")
        senha_dev = st.text_input("Digite a Senha Mestre do Desenvolvedor para desbloquear:", type="password")
        
        if senha_dev == SENHA_MESTRE_DEV:
            st.success("🔓 Acesso autorizado, Dev!")
            
            conn = sqlite3.connect('alerta_safe.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, usuario, empresa, status FROM usuarios")
            lista_usuarios = cursor.fetchall()
            conn.close()
            
            empresas_cadastradas = sorted(list(set([u[2] for u in lista_usuarios if u[2] is not None])))
            
            st.write("---")
            st.subheader("🔍 Filtrar Contas")
            filtro_empresa = st.selectbox("Selecione para filtrar por Nome da Empresa:", ["Todas as Empresas"] + empresas_cadastradas)
            st.write("---")
            
            st.markdown("### Contas Registradas na Plataforma")
            
            for u_id, u_nome, u_empresa, u_status in lista_usuarios:
                nome_empresa_limpo = u_empresa if u_empresa else "Não Informada"
                
                if filtro_empresa != "Todas as Empresas" and u_empresa != filtro_empresa:
                    continue
                    
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.markdown(f"👤 Usuário: **{u_nome}**\n\n🏢 Empresa: `{nome_empresa_limpo}`")
                with col2:
                    if u_status == 'bloqueado':
                        st.warning("🔒 Bloqueado")
                    else:
                        st.success("🟢 Ativo / Aprovado")
                with col3:
                    if u_status == 'bloqueado':
                        if st.button(f"Ativar Acesso", key=f"btn_ativar_{u_id}"):
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE usuarios SET status = 'aprovado' WHERE id = ?", (u_id,))
                            conn.commit()
                            conn.close()
                            st.toast(f"Conta de {u_nome} ({nome_empresa_limpo}) ativada!")
                            st.rerun()
                    else:
                        if st.button(f"Bloquear Usuário", key=f"btn_bloq_{u_id}"):
                            conn = sqlite3.connect('alerta_safe.db')
                            cursor = conn.cursor()
                            cursor.execute("UPDATE usuarios SET status = 'bloqueado' WHERE id = ?", (u_id,))
                            conn.commit()
                            conn.close()
                            st.toast(f"Conta de {u_nome} ({nome_empresa_limpo}) bloqueada!")
                            st.rerun()
                st.markdown("---")
        elif senha_dev != "":
            st.error("❌ Senha Mestre do Dev incorreta.")
except Exception:
    exibir_erro_amigavel()
    st.stop()
    
