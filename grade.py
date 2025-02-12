import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from fpdf import FPDF

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

def gerar_pdf(df, codturma):
    filename = f"Grade Horária - {codturma}.pdf"
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(280, 10, "Grade Horária", ln=True, align="C")
    pdf.ln(10)
    
    # Configurações de fonte e layout
    pdf.set_font("Arial", size=8)
    col_widths = [25] + [45] * (len(df.columns) - 1)  # Ajuste de largura
    line_height = 6  # Altura base por linha
    
    # Cabeçalho
    for i, col in enumerate(df.columns):
        pdf.multi_cell(col_widths[i], line_height, col, border=1, align='C', ln=3)
    pdf.ln(line_height)
    
    # Dados com quebra automática
    df = df.fillna("")
    for _, row in df.iterrows():
        start_y = pdf.get_y()
        max_height = 0
        
        # Primeira passada para calcular altura máxima
        for i, col in enumerate(df.columns):
            text = str(row[col])
            text_height = len(pdf.multi_cell(col_widths[i], line_height, text, split_only=True)) * line_height
            if text_height > max_height:
                max_height = text_height
                
        # Verificar quebra de página
        if pdf.get_y() + max_height > pdf.page_break_trigger:
            pdf.add_page()
            start_y = pdf.get_y()
        
        # Segunda passada para desenhar células
        x = pdf.get_x()
        for i, col in enumerate(df.columns):
            text = str(row[col])
            pdf.set_xy(x, start_y)
            pdf.multi_cell(col_widths[i], line_height, text, border=1, align='C')
            x += col_widths[i]
        
        pdf.set_xy(pdf.l_margin, start_y + max_height)
    
    pdf.output(filename)
    return filename

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
                df = pd.DataFrame(grade).fillna("")  # Remover None da visualização
                st.markdown("### 📅 Grade Horária")
                st.dataframe(df)
                pdf_filename = gerar_pdf(df, codturma)
                with open(pdf_filename, "rb") as f:
                    st.download_button("📥 Baixar PDF", f, file_name=pdf_filename, mime="application/pdf")
            elif "error" in grade:
                st.error(f"⚠️ {grade['error']}")
            else:
                st.warning(f"⚠️ Nenhuma grade horária encontrada para a turma {codturma} na filial {filial_escolhida}.")
    else:
        st.warning("⚠️ Nenhuma turma encontrada para esta filial.")
else:
    st.warning("⚠️ Selecione uma filial válida.")
