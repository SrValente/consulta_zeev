import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Configurações da Aplicação ---
st.set_page_config(page_title="Consulta Zeev", layout="wide")

st.title("🔎 Consulta de Tickets - Zeev Raiz Educação")

TOKEN = "Ewn%2BSOscTs56K5M%2FaIImkoImbCMGqRNslcSy172rSvNQnFZ7J1I1uEnGpbgvJBsoVi48Cw2q6bEOKT84Ve7R9mAIPYeT2FSXaPCoeMouJ2N9KHsTX5%2BXvRrBc6SmYorp"
BASE_URL = "https://raizeducacao.zeev.it/api/2/instances/"

# --- Funções Auxiliares ---

def formatar_data(data_str):
    """Converte uma data do formato ISO para o formato brasileiro, se não for nula."""
    if not data_str:
        return "N/A"
    try:
        # Tenta converter com e sem os milissegundos
        if '.' in data_str:
            dt_obj = datetime.fromisoformat(data_str.split('.')[0])
        else:
            dt_obj = datetime.fromisoformat(data_str)
        return dt_obj.strftime('%d/%m/%Y %H:%M:%S')
    except (ValueError, TypeError):
        return data_str # Retorna a string original se houver erro

def consultar_ticket(instance_id):
    """Função para fazer a requisição à API do Zeev."""
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    # Parâmetros para garantir que todos os dados sejam retornados, conforme as regras
    params = {
        "showPendingInstanceTasks": "true",
        "showFinishedInstanceTasks": "true",
        "showPendingAssignees": "true",
        "useCache": "false"
    }
    
    try:
        response = requests.get(f"{BASE_URL}{instance_id}", headers=headers, params=params)
        
        # Verifica o status da resposta
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro na API: {response.status_code}")
            try:
                # Tenta mostrar a mensagem de erro da API
                st.json(response.json())
            except Exception:
                st.text(response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão: {e}")
        return None

# --- Interface do Usuário ---

ticket_id = st.text_input("Digite o número do Ticket (Instance ID):", placeholder="Ex: 12345")

if st.button("Consultar Ticket"):
    if ticket_id and ticket_id.isdigit():
        with st.spinner("Buscando informações do ticket..."):
            resultado = consultar_ticket(ticket_id)

            # Aceita resposta tanto com 'data' quanto resposta direta do ticket
            if resultado:
                # Se vier dentro de 'data', usa ela, senão usa o próprio resultado
                data = resultado.get('data', resultado)

                st.success(f"Ticket **#{data.get('id', 'N/A')}** encontrado!")

                # --- Máscara Bonita: Resumo do Ticket ---
                st.markdown("### 🎫 Dados do Ticket")
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", data.get('flowResult', 'N/A'))
                col2.metric("Aberto em", formatar_data(data.get('startDateTime')))
                col3.metric("Finalizado em", formatar_data(data.get('endDateTime')))
                st.markdown(f"**Nome da Solicitação:** {data.get('requestName', 'N/A')}")
                st.markdown(f"**Código de Confirmação:** `{data.get('confirmationCode', 'N/A')}`")
                st.markdown(f"**Fluxo:** {data.get('flow', {}).get('name', 'N/A')} (v{data.get('flow', {}).get('version', 'N/A')})")
                if data.get('reportLink'):
                    st.markdown(f"**🔗 [Acessar Relatório]({data.get('reportLink')})**")
                st.divider()

                # --- Solicitante ---
                requester = data.get('requester', {})
                st.markdown("### 👤 Solicitante")
                st.markdown(f"**Nome:** {requester.get('name', 'N/A')}")
                st.markdown(f"**E-mail:** {requester.get('email', 'N/A')}")
                st.markdown(f"**Time:** {requester.get('team', {}).get('name', 'N/A')}")
                st.markdown(f"**Cargo:** {requester.get('position', {}).get('name', 'N/A')}")
                st.divider()

                # --- Campos do Formulário ---
                if data.get('formFields'):
                    st.markdown("### 📋 Campos do Formulário")
                    df_fields = pd.DataFrame(data['formFields'])
                    df_fields_display = df_fields[['name', 'value']].rename(
                        columns={'name': 'Campo', 'value': 'Valor Preenchido'}
                    )
                    st.dataframe(df_fields_display, use_container_width=True)
                    st.divider()

                # --- Tarefas/Etapas ---
                if data.get('instanceTasks'):
                    st.markdown("### ⚙️ Etapas do Processo")
                    tasks = []
                    for task in data['instanceTasks']:
                        # Nome do executor ou dos responsáveis
                        executor = task.get('executor')
                        if executor:
                            executor_nome = executor.get('name', 'N/A')
                        elif task.get('assignees'):
                            # Pode ser uma lista de responsáveis
                            executor_nome = ', '.join([a.get('name', 'N/A') for a in task.get('assignees')])
                        else:
                            executor_nome = 'N/A'
                        tasks.append({
                            "Etapa": task.get('task', {}).get('name', 'N/A'),
                            "Status": "Concluída" if task.get('endDateTime') else "Pendente",
                            "Início": formatar_data(task.get('startDateTime')),
                            "Fim": formatar_data(task.get('endDateTime')),
                            "Executor/Responsável": executor_nome
                        })
                    df_tasks = pd.DataFrame(tasks)
                    st.dataframe(df_tasks, use_container_width=True)
            else:
                st.error("Não foi possível encontrar o ticket ou a resposta da API está em formato inesperado.")
                if resultado:
                    st.json(resultado)

    elif not ticket_id:
        st.warning("Por favor, insira o número de um ticket.")
    else:
        st.error("O número do ticket deve conter apenas dígitos.")
