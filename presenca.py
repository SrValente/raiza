import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

st.set_page_config(page_title="Consulta de Grade Horária - TOTVS", layout="wide")

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
    .block-container {
        padding-bottom: 50px;
    }
    </style>
    """, unsafe_allow_html=True
)

USERNAME = "p_heflo"
PASSWORD = "Q0)G$sW]rj"
BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"

filiais = [
    {"NOMEFANTASIA": "COLÉGIO QI TIJUCA", "CODCOLIGADA": 2, "CODFILIAL": 2},
    {"NOMEFANTASIA": "COLÉGIO QI BOTAFOGO", "CODCOLIGADA": 2, "CODFILIAL": 3},
    {"NOMEFANTASIA": "COLÉGIO QI FREGUESIA", "CODCOLIGADA": 2, "CODFILIAL": 6},
    {"NOMEFANTASIA": "COLÉGIO QI RIO 2", "CODCOLIGADA": 2, "CODFILIAL": 7},
    {"NOMEFANTASIA": "COLEGIO QI METROPOLITANO", "CODCOLIGADA": 6, "CODFILIAL": 1},
    {"NOMEFANTASIA": "COLEGIO QI RECREIO", "CODCOLIGADA": 10, "CODFILIAL": 1},
]

def obter_turmas(codcoligada, codfilial):
    url = f"{BASE_URL}/RAIZA.0005/0/S"
    params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial}"}
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
        if response.status_code == 200:
            turmas = response.json()
            return [t for t in turmas if t.get("CODCOLIGADA") == codcoligada and t.get("CODFILIAL") == codfilial]
    except requests.exceptions.SSLError:
        return {"error": "Erro de certificado SSL ao acessar a API"}
    return []

def obter_grade_horario(codturma, codcoligada, codfilial):
    url = f"{BASE_URL}/RAIZA.0004/0/S"
    params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODTURMA={codturma}"}
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.SSLError:
        return {"error": "Erro de certificado SSL ao acessar a API"}
    return {"error": "Erro na consulta da grade de horários"}

def gerar_html(df, codturma):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Grade Horária - {codturma}</title>
        <style>
            @page {{
                size: A4 landscape;
                margin: 1cm;
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
            }}
            h1 {{
                color: #FFA500;
                text-align: center;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
                font-size: 12px;
            }}
            th {{
                background-color: #f2f2f2;
            }}
        </style>
    </head>
    <body>
        <h1>Grade Horária - {codturma}</h1>
        {df.to_html(index=False, escape=False)}
        <script>
            // Força o diálogo de impressão ao abrir o arquivo
            window.onload = function() {{
                window.print();
            }};
        </script>
    </body>
    </html>
    """
    return html

st.title("📅 Consulta de Grade Horária - TOTVS")

st.markdown("### 🏫 Selecionar Filial")
filiais_opcoes = {f"{f['NOMEFANTASIA']} ({f['CODFILIAL']})": (f['CODCOLIGADA'], f['CODFILIAL']) for f in filiais}
filial_escolhida = st.selectbox("Selecione a Filial:", list(filiais_opcoes.keys()))
codcoligada, codfilial = filiais_opcoes.get(filial_escolhida, (None, None))

if codcoligada and codfilial:
    st.markdown("### 📋 Selecionar Turma")
    turmas = obter_turmas(codcoligada, codfilial)
    if turmas:
        turmas_opcoes = {t["CODTURMA"]: t["CODTURMA"] for t in turmas}
        codturma = st.selectbox("Selecione a Turma:", list(turmas_opcoes.keys()))
        if st.button("🔎 Consultar Grade Horária"):
            grade = obter_grade_horario(codturma, codcoligada, codfilial)
            if isinstance(grade, list) and len(grade) > 0:
                df = pd.DataFrame(grade).fillna("")
                st.markdown("### 📅 Grade Horária")
                st.dataframe(df)
                
                # Gera e disponibiliza o HTML
                html_content = gerar_html(df, codturma)
                st.download_button(
                    label="📥 Baixar para PDF",
                    data=html_content,
                    file_name=f"Grade Horária - {codturma}.html",
                    mime="text/html",
                    help="O arquivo será aberto automaticamente para impressão. Use 'Salvar como PDF' nas opções de impressão do navegador."
                )
                
            elif "error" in grade:
                st.error(f"⚠️ {grade['error']}")
            else:
                st.warning(f"⚠️ Nenhuma grade horária encontrada para a turma {codturma} na filial {filial_escolhida}.")
    else:
        st.warning("⚠️ Nenhuma turma encontrada para esta filial.")
else:
    st.warning("⚠️ Selecione uma filial válida.")
