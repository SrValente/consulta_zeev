import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Portal de Pagamentos - Raiz Educação",
    page_icon="🏫",
    layout="wide"
)

st.title("🏫 Portal de Gestão Financeira - Raiz Educação")
st.markdown("""
Bem-vindo ao sistema de gestão de solicitações. Utilize o menu lateral para navegar entre as funcionalidades.
""")

st.divider()

# --- DASHBOARD DE RESUMO ---
st.subheader("📊 Resumo de Solicitações (Pedidos Abertos localmente)")

caminho_csv = "data/requests.csv"

if os.path.exists(caminho_csv):
    try:
        df = pd.read_csv(caminho_csv)
        
        # Métricas Rápidas
        total_pedidos = len(df)
        
        # Limpeza simples para cálculo de valor (removendo a vírgula se necessário)
        # Nota: assumindo que o valor foi salvo como string "1.234,56"
        df_valor = df.copy()
        df_valor['Valor_Num'] = df_valor['Valor Total (R$)'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        valor_total = df_valor['Valor_Num'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Solicitações", total_pedidos)
        m2.metric("Volume Financeiro Total", f"R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m3.metric("Última Atualização", df['Data de Submissão'].iloc[-1].split()[0])

        st.divider()

        # Tabela com os últimos pedidos
        st.markdown("### 🕒 Últimas Atividades")
        st.dataframe(
            df.sort_index(ascending=False).head(10), # Mostra os 10 mais recentes
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:
        st.error(f"Erro ao ler os dados locais: {e}")
else:
    st.info("💡 Ainda não existem pedidos registrados no histórico local. Comece criando um 'Novo Pedido'.")

# --- ATALHOS RÁPIDOS ---
st.divider()
st.subheader("🚀 Atalhos Rápidos")
col_a, col_b = st.columns(2)

with col_a:
    st.info("### ➕ Novo Pedido\nCrie uma nova solicitação de pagamento integrada ao Zeev e TOTVS.")
    if st.button("Ir para Novo Pedido"):
        st.switch_page("pages/1_Novo_Pedido.py")

with col_b:
    st.success("### 🔎 Consultar Ticket\nVerifique o status, executor atual e histórico de um ticket já existente.")
    if st.button("Ir para Consulta"):
        st.switch_page("pages/2_Consulta_ZEEV.py")

# Rodapé
st.markdown("---")
st.caption(f"Portal Financeiro | v1.0 | {datetime.now().year}")
