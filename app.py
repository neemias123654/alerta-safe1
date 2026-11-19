<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlertaSafe Enterprise — Demonstração Interativa</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        body { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
        .tab-active { background-color: #0f172a; color: #ffffff; border-left: 4px solid #3b82f6; }
        .tab-inactive { color: #cbd5e1; }
        .tab-inactive:hover { background-color: #1e293b; color: #ffffff; }
    </style>
</head>
<body class="text-slate-800 antialiased">

    <!-- BARRA SUPERIOR DE DEMONSTRAÇÃO COMERCIAL -->
    <div class="bg-amber-600 text-white px-4 py-2.5 shadow-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2 text-xs sm:text-sm">
            <div class="flex items-center gap-2 font-semibold">
                <span class="bg-white text-amber-700 px-2 py-0.5 rounded font-extrabold uppercase tracking-wider text-[11px]">Modo Demo</span>
                <span>Simulador Comercial AlertaSafe Enterprise</span>
            </div>
            <div class="flex flex-wrap items-center gap-2">
                <span class="hidden md:inline text-amber-100">Alternar Visão:</span>
                <button onclick="switchRole('gerente')" id="btn-role-gerente" class="px-3 py-1 rounded bg-slate-900 text-white font-medium transition shadow-sm">
                    👔 Visão Gestor
                </button>
                <button onclick="switchRole('rh')" id="btn-role-rh" class="px-3 py-1 rounded bg-amber-700 hover:bg-amber-800 text-white font-medium transition">
                    📋 Visão RH
                </button>
                <button onclick="openMobileScanner()" class="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition shadow-sm flex items-center gap-1.5">
                    <i class="fas fa-qrcode"></i> Simular Portaria (Celular)
                </button>
                <button onclick="toggleLoginModal(true)" class="px-3 py-1 rounded bg-white/20 hover:bg-white/30 text-white font-medium transition">
                    🔐 Tela de Login
                </button>
            </div>
        </div>
    </div>

    <!-- LAYOUT PRINCIPAL DO SISTEMA -->
    <div class="flex min-h-[calc(100vh-44px)]">
        
        <!-- SIDEBAR -->
        <aside class="w-64 bg-slate-900 text-white flex-shrink-0 hidden md:flex flex-col justify-between">
            <div>
                <div class="p-6 border-b border-slate-800">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-xl shadow-lg">
                            🛡️
                        </div>
                        <div>
                            <h1 class="font-bold text-lg tracking-tight leading-none">AlertaSafe</h1>
                            <span class="text-[11px] text-blue-400 font-semibold uppercase tracking-widest">Enterprise</span>
                        </div>
                    </div>
                    <div class="mt-4 bg-slate-800/80 rounded-lg p-3 text-xs border border-slate-700/60">
                        <p class="font-semibold text-white truncate" id="sidebar-user">Carlos Eduardo (Gestor)</p>
                        <p class="text-slate-400 truncate mt-0.5">Offshore Tech Serviços Ltda</p>
                        <p class="text-slate-500 font-mono text-[10px] mt-0.5">CNPJ: 12.345.678/0001-99</p>
                    </div>
                </div>

                <nav class="p-3 space-y-1" id="sidebar-nav">
                    <button onclick="showSection('painel')" id="nav-painel" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium tab-active transition">
                        <i class="fas fa-chart-pie w-5 text-center"></i> Painel Geral
                    </button>
                    <button onclick="showSection('cadastrar')" id="nav-cadastrar" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium tab-inactive transition">
                        <i class="fas fa-user-plus w-5 text-center"></i> Cadastrar Funcionário
                    </button>
                    <button onclick="showSection('aprovacoes-func')" id="nav-aprovacoes-func" class="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium tab-inactive transition">
                        <span class="flex items-center gap-3"><i class="fas fa-inbox w-5 text-center"></i> Aprovações Func.</span>
                        <span class="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full" id="badge-func-count">2</span>
                    </button>
                    <button onclick="showSection('ia-certificados')" id="nav-ia-certificados" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium tab-inactive transition">
                        <i class="fas fa-robot w-5 text-center text-purple-400"></i> Leitura Certificados (IA)
                    </button>
                    <button onclick="showSection('crachas')" id="nav-crachas" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium tab-inactive transition">
                        <i class="fas fa-id-badge w-5 text-center text-emerald-400"></i> Crachás / QR Codes
                    </button>

                    <!-- MENU EXCLUSIVO DO GESTOR -->
                    <div id="gestor-only-menu" class="pt-3 mt-3 border-t border-slate-800 space-y-1">
                        <p class="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500">Administração Gestor</p>
                        <button onclick="showSection('gestao-equipe')" id="nav-gestao-equipe" class="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium tab-inactive transition">
                            <span class="flex items-center gap-3"><i class="fas fa-users-cog w-5 text-center text-amber-400"></i> Contas & Equipe</span>
                            <span class="bg-amber-500 text-slate-900 font-bold text-xs px-2 py-0.5 rounded-full" id="badge-rh-count">1</span>
                        </button>
                        <button onclick="showSection('logs')" id="nav-logs" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium tab-inactive transition">
                            <i class="fas fa-history w-5 text-center text-slate-400"></i> Logs de Auditoria
                        </button>
                    </div>
                </nav>
            </div>

            <div class="p-4 border-t border-slate-800 text-xs text-slate-400">
                <div class="flex items-center gap-2 text-emerald-400 font-medium mb-1">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Licença Corporativa Ativa
                </div>
                <p>Ambiente de Demonstração v2.5</p>
            </div>
        </aside>

        <!-- CONTEÚDO PRINCIPAL -->
        <main class="flex-1 p-4 sm:p-8 overflow-y-auto">
            
            <!-- NAVEGAÇÃO MOBILE SIMPLIFICADA -->
            <div class="md:hidden flex overflow-x-auto gap-2 pb-4 mb-4 border-b border-slate-200">
                <button onclick="showSection('painel')" class="px-3 py-1.5 bg-slate-900 text-white rounded text-xs whitespace-nowrap">Painel</button>
                <button onclick="showSection('cadastrar')" class="px-3 py-1.5 bg-white border rounded text-xs whitespace-nowrap">Cadastrar</button>
                <button onclick="showSection('ia-certificados')" class="px-3 py-1.5 bg-white border rounded text-xs whitespace-nowrap">Leitura IA</button>
                <button onclick="showSection('crachas')" class="px-3 py-1.5 bg-white border rounded text-xs whitespace-nowrap">QR Codes</button>
                <button onclick="showSection('gestao-equipe')" id="mob-gestor-btn" class="px-3 py-1.5 bg-amber-100 text-amber-900 border border-amber-300 rounded text-xs whitespace-nowrap">Gestão Contas</button>
            </div>

            <!-- SEÇÃO 1: PAINEL GERAL -->
            <section id="sec-painel" class="space-y-6">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-900">Status de Conformidade Operacional</h2>
                        <p class="text-sm text-slate-500">Monitoramento em tempo real das Normas Regulamentadoras (NRs) da equipe</p>
                    </div>
                    <button onclick="openMobileScanner()" class="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-sm self-start">
                        <i class="fas fa-mobile-alt"></i> Testar Leitura de Crachá
                    </button>
                </div>

                <!-- CARDS DE MÉTRICAS -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                        <div class="flex items-center justify-between text-slate-500 text-sm font-medium">
                            <span>Colaboradores Ativos</span>
                            <i class="fas fa-hard-hat text-blue-600 text-lg"></i>
                        </div>
                        <p class="text-3xl font-extrabold text-slate-900 mt-2" id="metric-funcs">142</p>
                        <p class="text-xs text-emerald-600 font-medium mt-1"><i class="fas fa-arrow-up"></i> 100% documentados</p>
                    </div>

                    <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                        <div class="flex items-center justify-between text-slate-500 text-sm font-medium">
                            <span>Treinamentos em Dia</span>
                            <i class="fas fa-check-circle text-emerald-600 text-lg"></i>
                        </div>
                        <p class="text-3xl font-extrabold text-emerald-600 mt-2">468</p>
                        <p class="text-xs text-slate-500 mt-1">Aptos para embarque / campo</p>
                    </div>

                    <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                        <div class="flex items-center justify-between text-slate-500 text-sm font-medium">
                            <span>Alerta (&lt; 30 dias)</span>
                            <i class="fas fa-exclamation-triangle text-amber-500 text-lg"></i>
                        </div>
                        <p class="text-3xl font-extrabold text-amber-500 mt-2">14</p>
                        <p class="text-xs text-amber-700 mt-1">Agendar reciclagem preventiva</p>
                    </div>

                    <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                        <div class="flex items-center justify-between text-slate-500 text-sm font-medium">
                            <span>Bloqueados (Vencidos)</span>
                            <i class="fas fa-ban text-rose-600 text-lg"></i>
                        </div>
                        <p class="text-3xl font-extrabold text-rose-600 mt-2">4</p>
                        <p class="text-xs text-rose-700 mt-1">Acesso barrado na portaria</p>
                    </div>
                </div>

                <!-- TABELA DE MONITORAMENTO -->
                <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <div class="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <h3 class="font-bold text-slate-900">Quadro de Validade de NRs por Colaborador</h3>
                        <span class="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">Atualizado automaticamente</span>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-200">
                                    <th class="py-3.5 px-5 font-semibold">Colaborador</th>
                                    <th class="py-3.5 px-5 font-semibold">Função</th>
                                    <th class="py-3.5 px-5 font-semibold">Certificado / NR</th>
                                    <th class="py-3.5 px-5 font-semibold">Validade</th>
                                    <th class="py-3.5 px-5 font-semibold">Status Portaria</th>
                                    <th class="py-3.5 px-5 font-semibold text-right">Ação</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 text-sm" id="tabela-colaboradores">
                                <!-- Preenchido via JS -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>

            <!-- SEÇÃO 2: CADASTRAR FUNCIONÁRIO -->
            <section id="sec-cadastrar" class="hidden space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-900">Cadastro de Colaboradores</h2>
                    <p class="text-sm text-slate-500">Cadastre individualmente ou envie o link de auto-cadastro para os trabalhadores</p>
                </div>

                <div class="bg-blue-50 border border-blue-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div class="text-sm text-blue-900">
                        <p class="font-bold"><i class="fas fa-link mr-1"></i> Link de Auto-Cadastro Exclusivo da Empresa</p>
                        <p class="text-blue-700 text-xs mt-0.5">Envie no grupo de WhatsApp para que cada funcionário preencha seus próprios dados:</p>
                        <code class="block mt-2 bg-white px-3 py-1.5 rounded border border-blue-200 text-xs text-slate-700 select-all">https://alertasafe.com.br/?p=cadastrar_func&emp=offshore-tech</code>
                    </div>
                    <button onclick="alert('Link copiado para a área de transferência!')" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-xs font-semibold whitespace-nowrap">
                        Copiar Link
                    </button>
                </div>

                <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm max-w-2xl">
                    <h3 class="font-bold text-slate-800 mb-4">Novo Cadastro Direto (Ativo Imediato)</h3>
                    <form onsubmit="addColaborador(event)" class="space-y-4">
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 mb-1">Nome Completo *</label>
                                <input type="text" id="novo-nome" required placeholder="Ex: João Paulo Souza" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 mb-1">CPF *</label>
                                <input type="text" id="novo-cpf" required placeholder="000.000.000-00" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none">
                            </div>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 mb-1">Cargo / Função *</label>
                                <input type="text" id="novo-cargo" required placeholder="Ex: Soldador TIG / Escalador" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 mb-1">WhatsApp com DDD</label>
                                <input type="text" id="novo-whats" placeholder="(22) 99999-9999" class="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none">
                            </div>
                        </div>
                        <button type="submit" class="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2.5 rounded-lg text-sm font-semibold">
                            <i class="fas fa-save mr-1"></i> Salvar e Gerar Crachá QR
                        </button>
                    </form>
                </div>
            </section>

            <!-- SEÇÃO 3: APROVAÇÕES DE FUNCIONÁRIOS -->
            <section id="sec-aprovacoes-func" class="hidden space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-900">Aprovações de Auto-Cadastro</h2>
                    <p class="text-sm text-slate-500">Colaboradores que preencheram o formulário externo aguardando validação do RH</p>
                </div>

                <div class="space-y-3" id="lista-pendentes-func">
                    <div id="pend-f1" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <span class="text-xs font-bold text-blue-600 uppercase">Solicitação via Link Externo</span>
                            <h4 class="font-bold text-slate-900 text-base">Marcos Vinícius Almeida</h4>
                            <p class="text-xs text-slate-500">Cargo: <strong>Caldeireiro Industrial</strong> | CPF: 145.892.330-11 | WhatsApp: (22) 99812-4410</p>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="aprovarPendente('pend-f1', 'Marcos Vinícius Almeida', 'Caldeireiro Industrial')" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-xs font-semibold">✅ Confirmar</button>
                            <button onclick="document.getElementById('pend-f1').remove(); atualizarContadores()" class="bg-rose-100 hover:bg-rose-200 text-rose-700 px-3 py-2 rounded-lg text-xs font-semibold">❌ Recusar</button>
                        </div>
                    </div>

                    <div id="pend-f2" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <span class="text-xs font-bold text-blue-600 uppercase">Solicitação via Link Externo</span>
                            <h4 class="font-bold text-slate-900 text-base">Rafael Costa Nogueira</h4>
                            <p class="text-xs text-slate-500">Cargo: <strong>Montador de Andaimes</strong> | CPF: 098.441.219-04 | WhatsApp: (22) 99745-1029</p>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="aprovarPendente('pend-f2', 'Rafael Costa Nogueira', 'Montador de Andaimes')" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-xs font-semibold">✅ Confirmar</button>
                            <button onclick="document.getElementById('pend-f2').remove(); atualizarContadores()" class="bg-rose-100 hover:bg-rose-200 text-rose-700 px-3 py-2 rounded-lg text-xs font-semibold">❌ Recusar</button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- SEÇÃO 4: LEITURA DE CERTIFICADOS COM IA -->
            <section id="sec-ia-certificados" class="hidden space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-900">Leitura Inteligente de Certificados (Gemini IA)</h2>
                    <p class="text-sm text-slate-500">Envie a foto ou PDF do certificado e a Inteligência Artificial extrai os dados e calcula a validade automaticamente</p>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                        <div class="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-purple-500 transition cursor-pointer bg-slate-50" onclick="simularLeituraIA()">
                            <div class="w-12 h-12 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mx-auto text-xl mb-3">
                                <i class="fas fa-file-pdf"></i>
                            </div>
                            <p class="font-semibold text-slate-800 text-sm">Clique aqui para simular o envio de um Certificado PDF</p>
                            <p class="text-xs text-slate-500 mt-1">Suporta PDF, JPG ou PNG (Ex: Certificado NR-35 Trabalho em Altura)</p>
                            <button type="button" class="mt-4 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-xs font-semibold shadow-sm">
                                ✨ Simular Extração com IA Agora
                            </button>
                        </div>
                    </div>

                    <div id="resultado-ia-box" class="bg-white p-6 rounded-xl border border-purple-200 shadow-sm hidden space-y-4">
                        <div class="flex items-center gap-2 text-purple-700 font-bold text-sm">
                            <i class="fas fa-sparkles"></i> Dados Extraídos pela Inteligência Artificial:
                        </div>
                        <div class="space-y-3 text-sm">
                            <div>
                                <label class="text-xs text-slate-500 font-semibold">Colaborador Identificado</label>
                                <input type="text" value="Roberto Carlos Mendes" class="w-full mt-1 px-3 py-2 bg-slate-50 border rounded-lg font-medium">
                            </div>
                            <div>
                                <label class="text-xs text-slate-500 font-semibold">Norma / Curso Detectado</label>
                                <input type="text" value="NR-35 - Trabalho em Altura (Reciclagem)" class="w-full mt-1 px-3 py-2 bg-slate-50 border rounded-lg font-medium">
                            </div>
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <label class="text-xs text-slate-500 font-semibold">Data Emissão</label>
                                    <input type="text" value="15/11/2026" class="w-full mt-1 px-3 py-2 bg-slate-50 border rounded-lg">
                                </div>
                                <div>
                                    <label class="text-xs text-slate-500 font-semibold">Validade Calculada (2 anos)</label>
                                    <input type="text" value="15/11/2028" class="w-full mt-1 px-3 py-2 bg-emerald-50 border border-emerald-300 text-emerald-800 font-bold rounded-lg">
                                </div>
                            </div>
                            <button onclick="alert('✅ Certificado salvo e crachá atualizado com sucesso!')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2.5 rounded-lg font-semibold text-sm">
                                💾 Confirmar e Salvar no Sistema
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- SEÇÃO 5: CRACHÁS / QR CODES -->
            <section id="sec-crachas" class="hidden space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-900">Emissão de Crachás Digitais Inteligentes</h2>
                    <p class="text-sm text-slate-500">Cada colaborador possui um QR Code único para leitura instantânea na portaria ou canteiro de obras</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <!-- CRACHÁ 1 -->
                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5 text-center space-y-3">
                        <div class="inline-block px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">🟢 REGULAR</div>
                        <h4 class="font-bold text-slate-900">Roberto Carlos Mendes</h4>
                        <p class="text-xs text-slate-500">Soldador Escalador | NR-35, NR-33</p>
                        <div class="p-3 bg-slate-50 rounded-lg inline-block border">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=130x130&data=AlertaSafe-Roberto-Regular" alt="QR Code" class="mx-auto">
                        </div>
                        <div>
                            <button onclick="openMobileScanner('regular')" class="w-full bg-slate-900 hover:bg-slate-800 text-white py-2 rounded-lg text-xs font-semibold">
                                📱 Simular Leitura na Portaria
                            </button>
                        </div>
                    </div>

                    <!-- CRACHÁ 2 -->
                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5 text-center space-y-3">
                        <div class="inline-block px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">🟡 ALERTA (VENCE EM 12 DIAS)</div>
                        <h4 class="font-bold text-slate-900">Anderson Silva Santos</h4>
                        <p class="text-xs text-slate-500">Eletricista Industrial | NR-10</p>
                        <div class="p-3 bg-slate-50 rounded-lg inline-block border">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=130x130&data=AlertaSafe-Anderson-Alerta" alt="QR Code" class="mx-auto">
                        </div>
                        <div>
                            <button onclick="openMobileScanner('alerta')" class="w-full bg-amber-600 hover:bg-amber-700 text-white py-2 rounded-lg text-xs font-semibold">
                                📱 Simular Leitura na Portaria
                            </button>
                        </div>
                    </div>

                    <!-- CRACHÁ 3 -->
                    <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5 text-center space-y-3">
                        <div class="inline-block px-3 py-1 rounded-full bg-rose-100 text-rose-800 text-xs font-bold">🔴 BLOQUEADO (NR VENCIDA)</div>
                        <h4 class="font-bold text-slate-900">Diego Ferreira Lima</h4>
                        <p class="text-xs text-slate-500">Operador de Espaço Confinado | NR-33</p>
                        <div class="p-3 bg-slate-50 rounded-lg inline-block border">
                            <img src="https://api.qrserver.com/v1/create-qr-code/?size=130x130&data=AlertaSafe-Diego-Bloqueado" alt="QR Code" class="mx-auto">
                        </div>
                        <div>
                            <button onclick="openMobileScanner('bloqueado')" class="w-full bg-rose-600 hover:bg-rose-700 text-white py-2 rounded-lg text-xs font-semibold">
                                📱 Simular Leitura na Portaria
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- SEÇÃO 6: GESTÃO DE CONTAS DA EMPRESA (EXCLUSIVA GESTOR) -->
            <section id="sec-gestao-equipe" class="hidden space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-900">Gestão de Contas & Notificações (CNPJ)</h2>
                    <p class="text-sm text-slate-500">Aprove novos acessos da sua equipe de RH, redefina senhas ou bloqueie usuários vinculados ao CNPJ <strong>12.345.678/0001-99</strong></p>
                </div>

                <!-- NOTIFICAÇÃO DE NOVA CONTA DE RH -->
                <div id="notif-rh-box" class="bg-amber-50 border border-amber-300 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <span class="bg-amber-500 text-slate-900 text-[10px] font-extrabold px-2 py-0.5 rounded uppercase">Nova Solicitação de Acesso</span>
                        <h4 class="font-bold text-slate-900 mt-1">Usuária: juliana.rh (Equipe de RH)</h4>
                        <p class="text-xs text-slate-600">Solicitou vínculo com o CNPJ 12.345.678/0001-99. Deseja permitir o acesso?</p>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="aprovarContaRH()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-xs font-semibold">✅ Permitir Acesso</button>
                        <button onclick="document.getElementById('notif-rh-box').remove(); document.getElementById('badge-rh-count').remove();" class="bg-rose-600 hover:bg-rose-700 text-white px-4 py-2 rounded-lg text-xs font-semibold">❌ Recusar</button>
                    </div>
                </div>

                <!-- LISTA DE CONTAS ATIVAS DA EMPRESA -->
                <div class="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-200" id="lista-contas-empresa">
                    <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <span class="text-xs bg-slate-900 text-white px-2 py-0.5 rounded font-semibold">👔 Gestor Principal</span>
                            <h4 class="font-bold text-slate-900 mt-1">carlos.gestor</h4>
                            <p class="text-xs text-emerald-600 font-medium">🟢 Conta Ativa (Administrador da Empresa)</p>
                        </div>
                        <button onclick="alert('Senha do Gestor alterada com criptografia bcrypt!')" class="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50">
                            🔑 Alterar Minha Senha
                        </button>
                    </div>

                    <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                            <span class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-semibold">📋 Equipe de RH</span>
                            <h4 class="font-bold text-slate-900 mt-1">fernanda.dp</h4>
                            <p class="text-xs text-emerald-600 font-medium" id="status-fernanda">🟢 Conta Ativa</p>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="alert('Nova senha temporária gerada para fernanda.dp!')" class="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50">
                                🔑 Redefinir Senha
                            </button>
                            <button onclick="toggleBloqueioRH()" id="btn-blq-fernanda" class="px-3 py-1.5 bg-rose-100 text-rose-700 rounded-lg text-xs font-semibold hover:bg-rose-200">
                                🚫 Bloquear
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- SEÇÃO 7: LOGS DE AUDITORIA -->
            <section id="sec-logs" class="hidden space-y-6">
                <div>
                    <h2 class="text-2xl font-bold text-slate-900">Logs de Auditoria e Rastreabilidade</h2>
                    <p class="text-sm text-slate-500">Registro jurídico de todas as ações executadas pelos usuários da empresa</p>
                </div>
                <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-50 border-b text-slate-500 uppercase">
                            <tr>
                                <th class="py-3 px-4">Data / Hora</th>
                                <th class="py-3 px-4">Usuário</th>
                                <th class="py-3 px-4">Ação</th>
                                <th class="py-3 px-4">Detalhes</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y">
                            <tr><td class="py-3 px-4 font-mono">19/11/2026 18:10</td><td class="py-3 px-4 font-bold">fernanda.dp</td><td class="py-3 px-4 text-purple-700 font-semibold">CERTIFICADO_IA</td><td class="py-3 px-4">Extraiu NR-35 para Roberto Carlos Mendes</td></tr>
                            <tr><td class="py-3 px-4 font-mono">19/11/2026 17:42</td><td class="py-3 px-4 font-bold">carlos.gestor</td><td class="py-3 px-4 text-emerald-700 font-semibold">APROVACAO_RH</td><td class="py-3 px-4">Liberou acesso para fernanda.dp</td></tr>
                            <tr><td class="py-3 px-4 font-mono">19/11/2026 14:15</td><td class="py-3 px-4 font-bold">fernanda.dp</td><td class="py-3 px-4 text-blue-700 font-semibold">IMPORTACAO_MASSA</td><td class="py-3 px-4">Importou 38 colaboradores via planilha CSV</td></tr>
                        </tbody>
                    </table>
                </div>
            </section>

        </main>
    </div>

    <!-- MODAL 1: SIMULADOR DE CELULAR NA PORTARIA (QR CODE) -->
    <div id="modal-scanner" class="fixed inset-0 bg-slate-900/75 backdrop-blur-sm hidden items-center justify-center z-50 p-4">
        <div class="bg-white rounded-3xl max-w-sm w-full overflow-hidden shadow-2xl border-4 border-slate-800">
            <!-- TOPO DO CELULAR -->
            <div class="bg-slate-900 text-white px-5 py-3 flex items-center justify-between text-xs">
                <span class="font-bold">🛡️ Validação Portaria / Fiscal</span>
                <button onclick="closeMobileScanner()" class="text-slate-400 hover:text-white text-base"><i class="fas fa-times"></i></button>
            </div>

            <!-- SELETOR DE CENÁRIO DE TESTE -->
            <div class="bg-slate-100 p-2 flex justify-center gap-1 border-b text-[11px]">
                <button onclick="setScannerState('regular')" class="px-2.5 py-1 rounded bg-emerald-600 text-white font-semibold">🟢 Regular</button>
                <button onclick="setScannerState('alerta')" class="px-2.5 py-1 rounded bg-amber-500 text-white font-semibold">🟡 Alerta</button>
                <button onclick="setScannerState('bloqueado')" class="px-2.5 py-1 rounded bg-rose-600 text-white font-semibold">🔴 Vencido</button>
            </div>

            <!-- CONTEÚDO DA TELA DO CELULAR -->
            <div class="p-5 space-y-4" id="scanner-body">
                <!-- Preenchido via JS -->
            </div>
        </div>
    </div>

    <!-- MODAL 2: TELA DE LOGIN / CADASTRO MULTI-TENANT -->
    <div id="modal-login" class="fixed inset-0 bg-slate-900/80 backdrop-blur-sm hidden items-center justify-center z-50 p-4">
        <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 relative">
            <button onclick="toggleLoginModal(false)" class="absolute top-4 right-4 text-slate-400 hover:text-slate-700"><i class="fas fa-times text-lg"></i></button>
            
            <div class="text-center">
                <div class="w-12 h-12 bg-blue-600 text-white rounded-xl flex items-center justify-center text-2xl mx-auto shadow">🛡️</div>
                <h3 class="text-xl font-bold text-slate-900 mt-2">AlertaSafe Enterprise</h3>
                <p class="text-xs text-slate-500">Acesso Corporativo Multi-Empresa (CNPJ)</p>
            </div>

            <div class="flex border-b text-sm font-semibold">
                <button onclick="switchLoginTab('entrar')" id="tab-entrar" class="flex-1 py-2 border-b-2 border-blue-600 text-blue-600">Acessar Painel</button>
                <button onclick="switchLoginTab('criar')" id="tab-criar" class="flex-1 py-2 text-slate-500">Criar Conta (Empresa)</button>
            </div>

            <!-- FORM ENTRAR -->
            <div id="form-entrar" class="space-y-3">
                <div>
                    <label class="block text-xs font-semibold text-slate-700 mb-1">Usuário</label>
                    <input type="text" value="carlos.gestor" class="w-full px-3 py-2 border rounded-lg text-sm">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-700 mb-1">Senha</label>
                    <input type="password" value="••••••••" class="w-full px-3 py-2 border rounded-lg text-sm">
                </div>
                <button onclick="toggleLoginModal(false)" class="w-full bg-slate-900 hover:bg-slate-800 text-white py-2.5 rounded-lg text-sm font-semibold">
                    Entrar no Sistema
                </button>
            </div>

            <!-- FORM CRIAR CONTA -->
            <div id="form-criar" class="space-y-3 hidden">
                <div>
                    <label class="block text-xs font-semibold text-slate-700 mb-1">Tipo de Conta</label>
                    <select class="w-full px-3 py-2 border rounded-lg text-sm bg-slate-50 font-medium">
                        <option>👔 Gestor / Gerente (Conta Principal - Aprovação Dev)</option>
                        <option>📋 Equipe de RH (Subordinada - Aprovação Gestor)</option>
                    </select>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div>
                        <label class="block text-xs font-semibold text-slate-700 mb-1">Nome da Empresa</label>
                        <input type="text" placeholder="Ex: Metalúrgica Macaé" class="w-full px-3 py-2 border rounded-lg text-sm">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-700 mb-1">CNPJ</label>
                        <input type="text" placeholder="00.000.000/0001-00" class="w-full px-3 py-2 border rounded-lg text-sm">
                    </div>
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-700 mb-1">Usuário Desejado</label>
                    <input type="text" placeholder="nome.sobrenome" class="w-full px-3 py-2 border rounded-lg text-sm">
                </div>
                <button onclick="alert('✅ Solicitação enviada! Se for Gestor, vai para o Painel do Dev Master. Se for RH, notifica o Gestor do CNPJ.'); toggleLoginModal(false);" class="w-full bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg text-sm font-semibold">
                    Solicitar Cadastro
                </button>
            </div>
        </div>
    </div>

    <script>
        // DADOS INICIAIS SIMULADOS
        const colaboradores = [
            { nome: "Roberto Carlos Mendes", cargo: "Soldador Escalador", curso: "NR-35 / NR-33", validade: "15/11/2028", status: "regular" },
            { nome: "Anderson Silva Santos", cargo: "Eletricista Industrial", curso: "NR-10 SEP", validade: "01/12/2026", status: "alerta" },
            { nome: "Diego Ferreira Lima", cargo: "Op. Espaço Confinado", curso: "NR-33", validade: "10/10/2026", status: "bloqueado" },
            { nome: "Lucas Pereira Gomes", cargo: "Caldeireiro", curso: "NR-35 / NR-12", validade: "20/08/2027", status: "regular" },
            { nome: "Thiago Oliveira Rocha", cargo: "Técnico de Segurança", curso: "NR-35 / NR-10", validade: "14/05/2027", status: "regular" }
        ];

        function renderTabela() {
            const tbody = document.getElementById('tabela-colaboradores');
            tbody.innerHTML = '';
            colaboradores.forEach(c => {
                let badge = '';
                if (c.status === 'regular') badge = '<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">🟢 EM DIA</span>';
                else if (c.status === 'alerta') badge = '<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">🟡 ALERTA</span>';
                else badge = '<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">🔴 VENCIDO</span>';

                tbody.innerHTML += `
                    <tr class="hover:bg-slate-50 transition">
                        <td class="py-3.5 px-5 font-semibold text-slate-900">${c.nome}</td>
                        <td class="py-3.5 px-5 text-slate-600">${c.cargo}</td>
                        <td class="py-3.5 px-5 font-medium text-slate-800">${c.curso}</td>
                        <td class="py-3.5 px-5 text-slate-600 font-mono text-xs">${c.validade}</td>
                        <td class="py-3.5 px-5">${badge}</td>
                        <td class="py-3.5 px-5 text-right">
                            <button onclick="openMobileScanner('${c.status}')" class="text-blue-600 hover:text-blue-800 font-semibold text-xs">Ver Crachá QR</button>
                        </td>
                    </tr>
                `;
            });
        }

        function showSection(secName) {
            const sections = ['painel', 'cadastrar', 'aprovacoes-func', 'ia-certificados', 'crachas', 'gestao-equipe', 'logs'];
            sections.forEach(s => {
                const el = document.getElementById('sec-' + s);
                if (el) el.classList.add('hidden');
                const nav = document.getElementById('nav-' + s);
                if (nav) {
                    nav.classList.remove('tab-active');
                    nav.classList.add('tab-inactive');
                }
            });
            document.getElementById('sec-' + secName).classList.remove('hidden');
            const activeNav = document.getElementById('nav-' + secName);
            if (activeNav) {
                activeNav.classList.remove('tab-inactive');
                activeNav.classList.add('tab-active');
            }
        }

        function switchRole(role) {
            const gestorMenu = document.getElementById('gestor-only-menu');
            const mobGestor = document.getElementById('mob-gestor-btn');
            const sidebarUser = document.getElementById('sidebar-user');
            const btnG = document.getElementById('btn-role-gerente');
            const btnR = document.getElementById('btn-role-rh');

            if (role === 'gerente') {
                gestorMenu.classList.remove('hidden');
                mobGestor.classList.remove('hidden');
                sidebarUser.innerText = 'Carlos Eduardo (Gestor)';
                btnG.className = 'px-3 py-1 rounded bg-slate-900 text-white font-medium transition shadow-sm';
                btnR.className = 'px-3 py-1 rounded bg-amber-700 hover:bg-amber-800 text-white font-medium transition';
            } else {
                gestorMenu.classList.add('hidden');
                mobGestor.classList.add('hidden');
                sidebarUser.innerText = 'Fernanda Lima (Equipe RH)';
                btnR.className = 'px-3 py-1 rounded bg-slate-900 text-white font-medium transition shadow-sm';
                btnG.className = 'px-3 py-1 rounded bg-amber-700 hover:bg-amber-800 text-white font-medium transition';
                showSection('painel');
            }
        }

        function addColaborador(e) {
            e.preventDefault();
            const nome = document.getElementById('novo-nome').value;
            const cargo = document.getElementById('novo-cargo').value;
            colaboradores.unshift({ nome, cargo, curso: "NR-35 (Pendente)", validade: "Aguardando", status: "regular" });
            renderTabela();
            const metric = document.getElementById('metric-funcs');
            metric.innerText = parseInt(metric.innerText) + 1;
            e.target.reset();
            alert(`✅ Colaborador ${nome} cadastrado com sucesso!`);
            showSection('painel');
        }

        function aprovarPendente(elemId, nome, cargo) {
            document.getElementById(elemId).remove();
            colaboradores.unshift({ nome, cargo, curso: "NR-35 / NR-10", validade: "19/11/2028", status: "regular" });
            renderTabela();
            atualizarContadores();
            alert(`✅ ${nome} aprovado e ativado no sistema!`);
        }

        function atualizarContadores() {
            const rest = document.getElementById('lista-pendentes-func').children.length;
            const badge = document.getElementById('badge-func-count');
            if (rest === 0 && badge) badge.remove();
            else if (badge) badge.innerText = rest;
        }

        function simularLeituraIA() {
            const box = document.getElementById('resultado-ia-box');
            box.classList.remove('hidden');
        }

        function aprovarContaRH() {
            document.getElementById('notif-rh-box').remove();
            const badge = document.getElementById('badge-rh-count');
            if (badge) badge.remove();
            const lista = document.getElementById('lista-contas-empresa');
            lista.innerHTML += `
                <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-emerald-50/40">
                    <div>
                        <span class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-semibold">📋 Equipe de RH (Recém Aprovada)</span>
                        <h4 class="font-bold text-slate-900 mt-1">juliana.rh</h4>
                        <p class="text-xs text-emerald-600 font-medium">🟢 Conta Ativa</p>
                    </div>
                    <button onclick="alert('Senha redefinida!')" class="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold hover:bg-slate-50">🔑 Redefinir Senha</button>
                </div>
            `;
            alert('✅ Acesso de juliana.rh liberado com sucesso!');
        }

        let fernandaBloqueada = false;
        function toggleBloqueioRH() {
            fernandaBloqueada = !fernandaBloqueada;
            const st = document.getElementById('status-fernanda');
            const btn = document.getElementById('btn-blq-fernanda');
            if (fernandaBloqueada) {
                st.innerHTML = '🚫 Conta Bloqueada pelo Gestor';
                st.className = 'text-xs text-rose-600 font-bold';
                btn.innerText = '🔓 Reativar';
                btn.className = 'px-3 py-1.5 bg-emerald-100 text-emerald-700 rounded-lg text-xs font-semibold';
            } else {
                st.innerHTML = '🟢 Conta Ativa';
                st.className = 'text-xs text-emerald-600 font-medium';
                btn.innerText = '🚫 Bloquear';
                btn.className = 'px-3 py-1.5 bg-rose-100 text-rose-700 rounded-lg text-xs font-semibold';
            }
        }

        // SIMULADOR DE CELULAR (QR CODE)
        function openMobileScanner(state = 'regular') {
            document.getElementById('modal-scanner').classList.remove('hidden');
            document.getElementById('modal-scanner').classList.add('flex');
            setScannerState(state);
        }

        function closeMobileScanner() {
            document.getElementById('modal-scanner').classList.add('hidden');
            document.getElementById('modal-scanner').classList.remove('flex');
        }

        function setScannerState(state) {
            const body = document.getElementById('scanner-body');
            if (state === 'regular') {
                body.innerHTML = `
                    <div class="text-center">
                        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-bold">Offshore Tech Serviços Ltda</span>
                        <h4 class="text-lg font-extrabold text-slate-900">Roberto Carlos Mendes</h4>
                        <p class="text-xs text-slate-500">Função: Soldador Escalador</p>
                    </div>
                    <div class="bg-emerald-50 border-2 border-emerald-500 rounded-xl p-4 text-center">
                        <p class="text-emerald-800 font-extrabold text-base">🟩 TRABALHO LIBERADO</p>
                        <p class="text-xs text-emerald-700 mt-1">Todos os treinamentos obrigatórios (NRs) estão rigorosamente válidos.</p>
                    </div>
                    <div class="space-y-2 text-xs">
                        <div class="p-2.5 bg-slate-50 rounded border-l-4 border-emerald-500 flex justify-between">
                            <span><strong>NR-35</strong> Trabalho em Altura</span>
                            <span class="text-emerald-700 font-bold">15/11/2028</span>
                        </div>
                        <div class="p-2.5 bg-slate-50 rounded border-l-4 border-emerald-500 flex justify-between">
                            <span><strong>NR-33</strong> Espaço Confinado</span>
                            <span class="text-emerald-700 font-bold">10/09/2027</span>
                        </div>
                    </div>
                `;
            } else if (state === 'alerta') {
                body.innerHTML = `
                    <div class="text-center">
                        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-bold">Offshore Tech Serviços Ltda</span>
                        <h4 class="text-lg font-extrabold text-slate-900">Anderson Silva Santos</h4>
                        <p class="text-xs text-slate-500">Função: Eletricista Industrial</p>
                    </div>
                    <div class="bg-amber-50 border-2 border-amber-500 rounded-xl p-4 text-center">
                        <p class="text-amber-800 font-extrabold text-base">🟨 ATENÇÃO EXIGIDA</p>
                        <p class="text-xs text-amber-700 mt-1">Treinamento próximo do vencimento (menos de 30 dias). Agendar reciclagem.</p>
                    </div>
                    <div class="space-y-2 text-xs">
                        <div class="p-2.5 bg-slate-50 rounded border-l-4 border-amber-500 flex justify-between">
                            <span><strong>NR-10</strong> Segurança em Eletricidade</span>
                            <span class="text-amber-700 font-bold">01/12/2026</span>
                        </div>
                    </div>
                `;
            } else {
                body.innerHTML = `
                    <div class="text-center">
                        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-bold">Offshore Tech Serviços Ltda</span>
                        <h4 class="text-lg font-extrabold text-slate-900">Diego Ferreira Lima</h4>
                        <p class="text-xs text-slate-500">Função: Op. Espaço Confinado</p>
                    </div>
                    <div class="bg-rose-50 border-2 border-rose-600 rounded-xl p-4 text-center">
                        <p class="text-rose-800 font-extrabold text-base">🟥 ACESSO BLOQUEADO</p>
                        <p class="text-xs text-rose-700 mt-1">O colaborador possui treinamentos obrigatórios vencidos. Impedido de operar.</p>
                    </div>
                    <div class="space-y-2 text-xs">
                        <div class="p-2.5 bg-slate-50 rounded border-l-4 border-rose-600 flex justify-between">
                            <span><strong>NR-33</strong> Espaço Confinado</span>
                            <span class="text-rose-700 font-bold">VENCIDO (10/10/2026)</span>
                        </div>
                    </div>
                `;
            }
        }

        function toggleLoginModal(show) {
            const m = document.getElementById('modal-login');
            if (show) { m.classList.remove('hidden'); m.classList.add('flex'); }
            else { m.classList.add('hidden'); m.classList.remove('flex'); }
        }

        function switchLoginTab(tab) {
            const fEntrar = document.getElementById('form-entrar');
            const fCriar = document.getElementById('form-criar');
            const tEntrar = document.getElementById('tab-entrar');
            const tCriar = document.getElementById('tab-criar');
            if (tab === 'entrar') {
                fEntrar.classList.remove('hidden'); fCriar.classList.add('hidden');
                tEntrar.className = 'flex-1 py-2 border-b-2 border-blue-600 text-blue-600';
                tCriar.className = 'flex-1 py-2 text-slate-500';
            } else {
                fCriar.classList.remove('hidden'); fEntrar.classList.add('hidden');
                tCriar.className = 'flex-1 py-2 border-b-2 border-blue-600 text-blue-600';
                tEntrar.className = 'flex-1 py-2 text-slate-500';
            }
        }

        // Inicializa tabela
        renderTabela();
    </script>
</body>
</html>
    
