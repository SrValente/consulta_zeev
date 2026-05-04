import streamlit as st
import requests
from datetime import datetime, date, timedelta
import json
import base64

# --- Configurações Iniciais ---
st.set_page_config(page_title="Novo Pedido - Zeev", layout="wide")
st.title("💸 Solicitação de Pagamento - Zeev")

# Credenciais e Endpoints
ZEEV_TOKEN = "Ewn%2BSOscTs56K5M%2FaIImkoImbCMGqRNslcSy172rSvNQnFZ7J1I1uEnGpbgvJBsoVi48Cw2q6bEOKT84Ve7R9mAIPYeT2FSXaPCoeMouJ2N9KHsTX5%2BXvRrBc6SmYorp"
ZEEV_BASE_URL = "https://raizeducacao.zeev.it/api/2/instances/"

TOTVS_BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"
TOTVS_AUTH = "Basic bHVjYXMudmFsZW50ZTpMdWNhczIyMDgwMg==" # lucas.valente:Lucas220802 em Base64

# --- Funções Auxiliares (Integração TOTVS e Regras) ---
@st.cache_data(ttl=300) # Cache para não fazer múltiplas requisições do mesmo CNPJ rápido
def buscar_dados_totvs(consulta_sql, cnpj):
    url = f"{TOTVS_BASE_URL}/{consulta_sql}/0/S?parameters=CNPJ={cnpj}"
    headers = {"Authorization": TOTVS_AUTH}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json() # Retorna a lista de resultados
        else:
            return []
    except Exception as e:
        st.error(f"Erro ao buscar no TOTVS ({consulta_sql}): {e}")
        return []

def definir_tipo_pedido(data_venc):
    """Verifica as regras de antecedência (dias úteis) para classificar o pedido."""
    hoje = date.today()
    dias_diff = (data_venc - hoje).days
    
    # Validação dos dias da semana (0=Segunda, 2=Quarta, 4=Sexta)
    if data_venc.weekday() not in [0, 2, 4]:
        return "Inválido", "O vencimento deve cair obrigatoriamente em uma Segunda, Quarta ou Sexta-feira."
    
    # Simplificação de dias úteis (poderia usar numpy.busday_count se precisasse de precisão com feriados)
    # Aqui faremos uma estimativa simples pelos dias corridos que atendem à regra mínima:
    if dias_diff >= 7: # Aproximadamente 5 dias úteis (conta fim de semana)
        return "Pagamentos Regulares", ""
    elif dias_diff >= 3: # Emergencial (menos de 5, mas pelo menos 3)
        return "Pagamentos Emergenciais", "Atenção: Necessita justificativa formal e documentação completa."
    else:
        return "Inválido", "Prazo mínimo de 3 dias não atendido para pagamentos."

# --- Interface do Formulário ---
with st.form("form_novo_pedido"):
    
    # 1. Dados de Organização
    st.subheader("🏢 Dados da Organização")
    col1, col2 = st.columns(2)
    with col1:
        coligada = st.selectbox("Coligada *", ["", "08 - COLÉGIO E CURSO MATRIZ EDUCAÇÃO LTDA. - 28.336.302/0001-54", "Outras coligadas..."], index=1)
        coligada_destino = st.selectbox("Coligada de destino *", ["", "08 - COLÉGIO E CURSO MATRIZ EDUCAÇÃO LTDA. - 28.336.302/0001-54", "Outras coligadas..."], index=1)
    with col2:
        filial = st.selectbox("Unidade / Filial *", ["", "01 - COLEGIO E CURSO MATRIZ EDUCACAO ROCHA MIRANDA", "Outras filiais..."])
        filial_destino = st.selectbox("Unidade / Filial de destino *", ["", "01 - COLEGIO E CURSO MATRIZ EDUCACAO ROCHA MIRANDA", "Outras filiais..."])

    st.divider()

    # 2. Dados da Solicitação
    st.subheader("📝 Dados da Solicitação")
    col3, col4, col5 = st.columns(3)
    with col3:
        tipo_solicitacao = st.selectbox("Tipo da solicitação *", ["Adiantamento", "Fundo fixo", "Pagamento", "Reembolso"], index=2) # Default Pagamento
        investimento = st.selectbox("É um investimento (CAPEX)? *", ["Não", "Sim"], index=0)
    with col4:
        tipo_pagamento = st.selectbox("Tipo de pagamento *", ["Contas de consumo", "Nota de Transporte", "Nota fiscal", "Outros gastos"], index=2) # Default NF
        pagamento_recorrente = st.selectbox("Pagamento recorrente? *", ["Não", "Sim"], index=1)
    with col5:
        tipo_item = st.selectbox("Tipo *", ["Material", "Serviço", "Transporte"], index=1) # Default Serviço
        possui_contrato = st.selectbox("Possui contrato? *", ["", "Não", "Sim"])

    st.divider()
    
    # 3. Fornecedor e Contas (Integração TOTVS)
    st.subheader("🤝 Fornecedor e Conta Bancária")
    cnpj_input = st.text_input("Digite o CNPJ do Fornecedor para busca", help="Somente números")
    
    # Variáveis para armazenar as seleções do usuário
    fornecedor_selecionado = ""
    conta_selecionada = ""
    
    if cnpj_input:
        with st.spinner("Buscando no TOTVS..."):
            # Busca Fornecedores (SMP.0063)
            resultados_fornecedor = buscar_dados_totvs("SMP.0063", cnpj_input)
            if resultados_fornecedor:
                lista_fornecedores = [item.get("Identificacao_Fornecedor", "") for item in resultados_fornecedor]
                fornecedor_selecionado = st.selectbox("Fornecedor (TOTVS)", lista_fornecedores)
            else:
                st.warning("Nenhum fornecedor encontrado com este CNPJ.")

            # Busca Contas (SMP.0064)
            resultados_contas = buscar_dados_totvs("SMP.0064", cnpj_input)
            if resultados_contas:
                lista_contas = [item.get("Dados_Bancarios", "") for item in resultados_contas]
                conta_selecionada = st.selectbox("Contas Cadastradas", lista_contas)
            else:
                st.warning("Nenhuma conta bancária encontrada para este CNPJ.")

    st.divider()

    # 4. Dados da Nota / Faturamento
    st.subheader("📄 Dados da Nota e Prazos")
    col6, col7, col8 = st.columns(3)
    with col6:
        numero_nf = st.text_input("Número da Nota *")
        documento = st.file_uploader("Anexar Documento / NF", type=["pdf", "png", "jpg"])
    with col7:
        data_emissao = st.date_input("Data de emissão *")
        
        # Lógica de Vencimento
        amanha = date.today() + timedelta(days=1)
        data_vencimento = st.date_input("Data de vencimento *", min_value=amanha)
        tipo_pedido, msg_pedido = definir_tipo_pedido(data_vencimento)
        
    with col8:
        # Exibição visual da Regra de Vencimento
        st.info(f"**Tipo de Pedido Calculado:**\n{tipo_pedido}")
        if msg_pedido:
            if tipo_pedido == "Inválido":
                st.error(msg_pedido)
            else:
                st.warning(msg_pedido)

    st.divider()

    # 5. Valores e Itens
    st.subheader("💰 Valores e Itens (Centro de Custo)")
    centro_custo = st.text_input("Centro de Custo *", value="1.05.004 - PESSOAL PJ")
    natureza_orcamentaria = st.text_input("Natureza Orçamentária *", value="02.01.00034 - Colaboradores por Contrato")
    item_desc = st.text_input("Item *", value="1.09.000174 - COLABORADORES POR CONTRATO")
    
    col9, col10, col11 = st.columns(3)
    with col9:
        preco_unitario = st.number_input("Preço unitário (R$) *", min_value=0.0, format="%.2f")
    with col10:
        qtd_item = st.number_input("Quantidade (UN) *", min_value=1, value=1)
    with col11:
        desconto = st.number_input("Desconto (R$)", min_value=0.0, format="%.2f")
    
    outras_despesas = st.number_input("Outras despesas (R$)", min_value=0.0, value=0.0, format="%.2f")
    total_item = (preco_unitario * qtd_item) - desconto
    st.success(f"**Total do Item Calculado:** R$ {total_item:.2f}")

    informacoes = st.text_area("Informações referentes à solicitação *", help="Inclua justificativas se emergencial")
    
    submit_btn = st.form_submit_button("Subir Pedido para o Zeev 🚀")


# --- Lógica de Envio para a API do Zeev ---
if submit_btn:
    if tipo_pedido == "Inválido":
        st.error("Corrija a Data de Vencimento antes de enviar.")
    elif not filial or not numero_nf or not fornecedor_selecionado or not informacoes:
        st.warning("Preencha todos os campos obrigatórios (*).")
    else:
        with st.spinner("Conectando ao Zeev..."):
            
            headers = {
                "Authorization": f"Bearer {ZEEV_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # --- Montagem do Payload ---
            # ATENÇÃO: Os arrays de tabelas no Zeev (como itens da NF) geralmente 
            # necessitam de uma estrutura específica de tabela na API. 
            # Abaixo estamos passando tudo no objeto `variables` padrão.
            payload = {
                "processId": "SEU_PROCESS_ID", # Substituir pelo ID correto do processo no Zeev
                "variables": {
                    "inp19037": coligada,                     # Coligada
                    "inp19050": filial,                       # Filial
                    "inp19000": coligada_destino,             # Coligada Destino
                    "inp19053": filial_destino,               # Filial Destino
                    "inp18986": tipo_solicitacao[:2].upper(), # Envia PG, AD, RE, etc
                    "inp19001": tipo_pagamento,               # Tipo Pgto (Ajustar p/ Sigla se a API exigir: NF, CC...)
                    "inp19019": tipo_item,                    # Tipo (Material, Serviço)
                    "inp19012": data_emissao.strftime("%d/%m/%Y"), # Data emissão
                    "inp19013": numero_nf,                    # Número NF
                    "inp18978": fornecedor_selecionado,       # Fornecedor TOTVS
                    "inp19009": str(outras_despesas).replace('.', ','), # Outras Despesas
                    "inp19070": investimento,                 # CAPEX
                    "inp19051": pagamento_recorrente,         # Recorrente
                    "inp19052": possui_contrato,              # Contrato
                    "inp18977": centro_custo,                 # Centro de Custo
                    "inp19075": natureza_orcamentaria,        # Natureza
                    "inp19036": item_desc,                    # Item
                    "inp18984": str(preco_unitario).replace('.', ','), # Preco
                    "inp18985": str(qtd_item),                # Qtd
                    "inp19048": str(desconto).replace('.', ','), # Desconto
                    "inp19049": str(total_item).replace('.', ','), # Total
                    "inp19010": conta_selecionada,            # Conta TOTVS
                    "inp19078": data_vencimento.strftime("%d/%m/%Y"), # Vencimento
                    "inp19074": tipo_pedido,                  # Tipo Pedido (Regular/Emergencial)
                    "inp19073": informacoes                   # Informações
                }
            }
            
            try:
                # Realizar o POST para a API do Zeev
                response = requests.post(ZEEV_BASE_URL, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    res_json = response.json()
                    st.success(f"✅ Pedido {res_json.get('id', '')} criado com sucesso!")
                    st.balloons()
                else:
                    st.error(f"❌ Erro do Zeev (Código: {response.status_code})")
                    st.json(response.json())
            except Exception as e:
                st.error(f"Erro de comunicação: {e}")
