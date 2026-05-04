import streamlit as st
import requests
from datetime import datetime, date, timedelta
import pandas as pd
import os

# --- Configurações Iniciais ---
st.set_page_config(page_title="Novo Pedido - Zeev", layout="wide")
st.title("💸 Solicitação de Pagamento - Zeev")

# Credenciais e Endpoints
ZEEV_TOKEN = "Ewn%2BSOscTs56K5M%2FaIImkoImbCMGqRNslcSy172rSvNQnFZ7J1I1uEnGpbgvJBsoVi48Cw2q6bEOKT84Ve7R9mAIPYeT2FSXaPCoeMouJ2N9KHsTX5%2BXvRrBc6SmYorp"
ZEEV_BASE_URL = "https://raizeducacao.zeev.it/api/2/instances/"

TOTVS_BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"
TOTVS_AUTH = "Basic bHVjYXMudmFsZW50ZTpMdWNhczIyMDgwMg==" # lucas.valente:Lucas220802 em Base64

# --- Funções Auxiliares ---

@st.cache_data(ttl=300)
def buscar_dados_totvs(consulta_sql, cnpj):
    url = f"{TOTVS_BASE_URL}/{consulta_sql}/0/S?parameters=CNPJ={cnpj}"
    headers = {"Authorization": TOTVS_AUTH}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        st.error(f"Erro ao buscar no TOTVS ({consulta_sql}): {e}")
        return []

def definir_tipo_pedido(data_venc):
    hoje = date.today()
    dias_diff = (data_venc - hoje).days
    
    if data_venc.weekday() not in [0, 2, 4]:
        return "Inválido", "O vencimento deve cair obrigatoriamente numa Segunda, Quarta ou Sexta-feira."
    
    if dias_diff >= 7:
        return "Pagamentos Regulares", ""
    elif dias_diff >= 3:
        return "Pagamentos Emergenciais", "Atenção: Necessita justificativa formal e documentação completa."
    else:
        return "Inválido", "Prazo mínimo de 3 dias não atendido para pagamentos."

def salvar_pedido_csv(ticket_id, variables):
    """Guarda as informações do pedido submetido num ficheiro CSV."""
    # Garante que o diretório 'data' existe
    os.makedirs("data", exist_ok=True)
    caminho_ficheiro = "data/requests.csv"
    
    # Prepara o dicionário com os dados a gravar
    dados = {
        "ID Ticket Zeev": ticket_id,
        "Data de Submissão": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Coligada": variables.get("inp19037", ""),
        "Filial": variables.get("inp19050", ""),
        "Fornecedor": variables.get("inp18978", ""),
        "CNPJ Busca": cnpj_input,
        "Nº Nota Fiscal": variables.get("inp19013", ""),
        "Data Emissão": variables.get("inp19012", ""),
        "Data Vencimento": variables.get("inp19078", ""),
        "Valor Total (R$)": variables.get("inp19049", ""),
        "Centro de Custo": variables.get("inp18977", ""),
        "Tipo de Pedido": variables.get("inp19074", "")
    }
    
    df_novo = pd.DataFrame([dados])
    
    # Se o ficheiro já existir, adiciona a linha sem o cabeçalho. Senão, cria com o cabeçalho.
    if os.path.exists(caminho_ficheiro):
        df_novo.to_csv(caminho_ficheiro, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df_novo.to_csv(caminho_ficheiro, mode='w', header=True, index=False, encoding='utf-8-sig')


# --- Interface do Formulário ---
with st.form("form_novo_pedido"):
    
    st.subheader("🏢 Dados da Organização")
    col1, col2 = st.columns(2)
    with col1:
        coligada = st.selectbox("Coligada *", ["", "08 - COLÉGIO E CURSO MATRIZ EDUCAÇÃO LTDA. - 28.336.302/0001-54"])
        coligada_destino = st.selectbox("Coligada de destino *", ["", "08 - COLÉGIO E CURSO MATRIZ EDUCAÇÃO LTDA. - 28.336.302/0001-54"])
    with col2:
        filial = st.selectbox("Unidade / Filial *", ["", "01 - COLEGIO E CURSO MATRIZ EDUCACAO ROCHA MIRANDA"])
        filial_destino = st.selectbox("Unidade / Filial de destino *", ["", "01 - COLEGIO E CURSO MATRIZ EDUCACAO ROCHA MIRANDA"])

    st.divider()

    st.subheader("📝 Dados da Solicitação")
    col3, col4, col5 = st.columns(3)
    with col3:
        tipo_solicitacao = st.selectbox("Tipo da solicitação *", ["Adiantamento", "Fundo fixo", "Pagamento", "Reembolso"], index=2)
        investimento = st.selectbox("É um investimento (CAPEX)? *", ["Não", "Sim"], index=0)
    with col4:
        tipo_pagamento = st.selectbox("Tipo de pagamento *", ["Contas de consumo", "Nota de Transporte", "Nota fiscal", "Outros gastos"], index=2)
        pagamento_recorrente = st.selectbox("Pagamento recorrente? *", ["Não", "Sim"], index=1)
    with col5:
        tipo_item = st.selectbox("Tipo *", ["Material", "Serviço", "Transporte"], index=1)
        possui_contrato = st.selectbox("Possui contrato? *", ["", "Não", "Sim"])

    st.divider()
    
    st.subheader("🤝 Fornecedor e Conta Bancária")
    cnpj_input = st.text_input("Digite o CNPJ do Fornecedor para busca (Somente números)")
    
    fornecedor_selecionado = ""
    conta_selecionada = ""
    
    if cnpj_input:
        with st.spinner("Buscando no TOTVS..."):
            resultados_fornecedor = buscar_dados_totvs("SMP.0063", cnpj_input)
            if resultados_fornecedor:
                lista_fornecedores = [item.get("Identificacao_Fornecedor", "") for item in resultados_fornecedor]
                fornecedor_selecionado = st.selectbox("Fornecedor (TOTVS)", lista_fornecedores)
            else:
                st.warning("Nenhum fornecedor encontrado com este CNPJ.")

            resultados_contas = buscar_dados_totvs("SMP.0064", cnpj_input)
            if resultados_contas:
                lista_contas = [item.get("Dados_Bancarios", "") for item in resultados_contas]
                conta_selecionada = st.selectbox("Contas Cadastradas", lista_contas)
            else:
                st.warning("Nenhuma conta bancária encontrada para este CNPJ.")

    st.divider()

    st.subheader("📄 Dados da Nota e Prazos")
    col6, col7, col8 = st.columns(3)
    with col6:
        numero_nf = st.text_input("Número da Nota *")
        documento = st.file_uploader("Anexar Documento / NF")
    with col7:
        data_emissao = st.date_input("Data de emissão *")
        amanha = date.today() + timedelta(days=1)
        data_vencimento = st.date_input("Data de vencimento *", min_value=amanha)
        tipo_pedido, msg_pedido = definir_tipo_pedido(data_vencimento)
    with col8:
        st.info(f"**Tipo de Pedido Calculado:**\n{tipo_pedido}")
        if msg_pedido:
            if tipo_pedido == "Inválido":
                st.error(msg_pedido)
            else:
                st.warning(msg_pedido)

    st.divider()

    st.subheader("💰 Valores e Itens")
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

    informacoes = st.text_area("Informações referentes à solicitação *")
    
    submit_btn = st.form_submit_button("Subir Pedido para o Zeev 🚀")


# --- Lógica de Envio ---
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
            
            variables = {
                "inp19037": coligada,
                "inp19050": filial,
                "inp19000": coligada_destino,
                "inp19053": filial_destino,
                "inp18986": tipo_solicitacao[:2].upper(),
                "inp19001": tipo_pagamento,
                "inp19019": tipo_item,
                "inp19012": data_emissao.strftime("%d/%m/%Y"),
                "inp19013": numero_nf,
                "inp18978": fornecedor_selecionado,
                "inp19009": str(outras_despesas).replace('.', ','),
                "inp19070": investimento,
                "inp19051": pagamento_recorrente,
                "inp19052": possui_contrato,
                "inp18977": centro_custo,
                "inp19075": natureza_orcamentaria,
                "inp19036": item_desc,
                "inp18984": str(preco_unitario).replace('.', ','),
                "inp18985": str(qtd_item),
                "inp19048": str(desconto).replace('.', ','),
                "inp19049": str(total_item).replace('.', ','),
                "inp19010": conta_selecionada,
                "inp19078": data_vencimento.strftime("%d/%m/%Y"),
                "inp19074": tipo_pedido,
                "inp19073": informacoes
            }
            
            payload = {
                "processId": "SEU_PROCESS_ID", 
                "variables": variables
            }
            
            try:
                response = requests.post(ZEEV_BASE_URL, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    res_json = response.json()
                    ticket_id = res_json.get('id', 'N/A')
                    
                    st.success(f"✅ Pedido {ticket_id} criado com sucesso!")
                    st.balloons()
                    
                    # Chama a função para guardar os dados no ficheiro CSV
                    salvar_pedido_csv(ticket_id, variables)
                    st.info("💾 As informações do pedido foram guardadas em '/data/requests.csv'.")
                    
                else:
                    st.error(f"❌ Erro do Zeev (Código: {response.status_code})")
                    st.json(response.json())
            except Exception as e:
                st.error(f"Erro de comunicação: {e}")
