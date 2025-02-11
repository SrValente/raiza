import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

# 🔹 Configuração da página Streamlit (Deve ser a primeira linha após as importações)
st.set_page_config(page_title="Consulta de Ocorrências - TOTVS", layout="wide")

# Código para modificar o estilo com CSS
st.markdown(
    """
    <style>
   

    .streamlit-expanderHeader {
        color: #FFA500;
    }

    .stButton > button {
        color: #FFA500;
    }

    .stSelectbox, .stMultiselect, .stTextInput, .stSelectSlider, .stNumberInput, .stCheckbox {
        color: white;
    }

    .stTextInput input {
        color: white;
    }

    .stSelectbox, .stSelectSlider, .stMultiselect {
        border-color: #444;
    }

    </style>
    """, unsafe_allow_html=True
)

# 🔹 Configuração da API TOTVS RM
USERNAME = "p_heflo"
PASSWORD = "Q0)G$sW]rj"
BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"

# 🔹 Tabela fixa de Filiais
filiais = [
    {"NOMEFANTASIA": "COLÉGIO QI TIJUCA", "CODCOLIGADA": 2, "CODFILIAL": 2},
    {"NOMEFANTASIA": "COLÉGIO QI BOTAFOGO", "CODCOLIGADA": 2, "CODFILIAL": 3},
    {"NOMEFANTASIA": "COLÉGIO QI FREGUESIA", "CODCOLIGADA": 2, "CODFILIAL": 6},
    {"NOMEFANTASIA": "COLÉGIO QI RIO 2", "CODCOLIGADA": 2, "CODFILIAL": 7},
    {"NOMEFANTASIA": "COLEGIO QI METROPOLITANO", "CODCOLIGADA": 6, "CODFILIAL": 1},
    {"NOMEFANTASIA": "COLEGIO QI RECREIO", "CODCOLIGADA": 10, "CODFILIAL": 1},
]

# 🔹 Função para buscar ALUNOS (com SSL desativado)
def obter_alunos(codcoligada, codfilial):
    url = f"{BASE_URL}/RAIZA.0002/0/S"
    params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial}"}
    
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)  # <- SSL Ignorado

        if response.status_code == 200:
            alunos = response.json()
            if alunos:
                max_ano = max(int(a["CODPERLET"]) for a in alunos)
                alunos_filtrados = {a["RA"]: a["NOME"] for a in alunos if int(a["CODPERLET"]) == max_ano and a["RA"] != "**********"}
                return alunos_filtrados
    except requests.exceptions.SSLError:
        return {"error": "Erro de certificado SSL ao acessar a API"}
    
    return {}

# 🔹 Função para buscar OCORRÊNCIAS (com SSL desativado)
def obter_ocorrencias(ra, codcoligada, codfilial):
    url = f"{BASE_URL}/RAIZA.0001/0/S"
    params = {"parameters": f"RA={ra};CODCOLIGADA={codcoligada};CODFILIAL={codfilial}"}
    
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)  # <- SSL Ignorado

        if response.status_code == 200:
            return response.json()
    except requests.exceptions.SSLError:
        return {"error": "Erro de certificado SSL ao acessar a API"}
    
    return {"error": "Erro na consulta de ocorrências"}

# 🎯 **Interface no Streamlit**
st.title("🔍 Consulta de Ocorrências - TOTVS")

# 🔄 **Selecionar Filial**
st.markdown("### 🏫 Selecionar Filial")
filiais_opcoes = {f"{f['NOMEFANTASIA']} ({f['CODFILIAL']})": (f['CODCOLIGADA'], f['CODFILIAL']) for f in filiais}
filial_escolhida = st.selectbox("Selecione a Filial:", list(filiais_opcoes.keys()))
codcoligada, codfilial = filiais_opcoes.get(filial_escolhida, (None, None))

if codcoligada and codfilial:
    st.markdown(f"📌 **Código da Coligada:** `{codcoligada}`")
    st.markdown(f"📌 **Código da Filial:** `{codfilial}`")

    # 🔄 **Buscar ALUNOS da Filial Selecionada**
    st.markdown("### 🆔 Selecionar Aluno")
    alunos = obter_alunos(codcoligada, codfilial)

    if alunos:
        alunos_opcoes = {f"{nome} ({ra})": ra for ra, nome in sorted(alunos.items(), key=lambda x: x[1])}
        ra_aluno = st.selectbox("Selecione o Aluno:", list(alunos_opcoes.keys()))

        # 🔍 **Botão para Consultar Ocorrências**
        if st.button("🔎 Consultar Ocorrências"):
            st.markdown(f"🔍 **Buscando ocorrências para o aluno:** `{ra_aluno}`...")

            ra = alunos_opcoes[ra_aluno]
            ocorrencias = obter_ocorrencias(ra, codcoligada, codfilial)

            # 📋 **Exibir Ocorrências**
            if isinstance(ocorrencias, list) and len(ocorrencias) > 0:
                df = pd.DataFrame(ocorrencias)
                df = df[["PERLETIVO", "GRUPO", "TIPO", "DATAOCORRENCIA", "OBSERVACOES","OBSERVACOESINTERNAS"]]  # Campos importantes
                df.columns = ["Período Letivo", "Grupo", "Tipo", "Data da Ocorrência", "Observações","Obs. Internas"]
                st.markdown("### 📋 Ocorrências Encontradas:")
                st.dataframe(df)
            elif "error" in ocorrencias:
                st.error(f"⚠️ {ocorrencias['error']}: {ocorrencias['message']}")
            else:
                st.warning("⚠️ Nenhuma ocorrência encontrada para este aluno.")
    else:
        st.warning("⚠️ Nenhum aluno encontrado para esta filial.")
else:
    st.warning("⚠️ Selecione uma filial válida.")
