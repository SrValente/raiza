import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO

# Configurações
USERNAME = "p_heflo"
PASSWORD = "Q0)G$sW]rj"
BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"

# Lista de filiais
filiais = [
    {"NOMEFANTASIA": "COLÉGIO QI TIJUCA", "CODCOLIGADA": 2, "CODFILIAL": 2},
    {"NOMEFANTASIA": "COLÉGIO QI BOTAFOGO", "CODCOLIGADA": 2, "CODFILIAL": 3},
    {"NOMEFANTASIA": "COLÉGIO QI FREGUESIA", "CODCOLIGADA": 2, "CODFILIAL": 6},
    {"NOMEFANTASIA": "COLÉGIO QI RIO 2", "CODCOLIGADA": 2, "CODFILIAL": 7},
    {"NOMEFANTASIA": "COLEGIO QI METROPOLITANO", "CODCOLIGADA": 6, "CODFILIAL": 1},
    {"NOMEFANTASIA": "COLEGIO QI RECREIO", "CODCOLIGADA": 10, "CODFILIAL": 1},
]

def obter_turmas(codcoligada, codfilial):
    """Busca todas as turmas de uma filial."""
    url = f"{BASE_URL}/RAIZA.0005/0/S"
    params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial}"}
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Erro ao buscar turmas: {str(e)}")
        return []

def obter_alunos_turma(codcoligada, codfilial, codturma):
    """Busca alunos de uma turma específica usando a nova consulta SQL."""
    url = f"{BASE_URL}/RAIZA.0009/0/S"
    params = {
        "parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODTURMA={codturma}"
    }
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Erro ao buscar alunos: {str(e)}")
        return []

def gerar_pdf(turmas_alunos, data):
    """Gera um PDF com uma lista de presença por turma."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    estilo_cabecalho = ParagraphStyle(
        'Cabecalho',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=1,
        spaceAfter=20
    )
    estilo_data = ParagraphStyle(
        'Data',
        parent=styles['Normal'],
        fontSize=10,
        alignment=2
    )
    estilo_tabela = TableStyle([ 
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FFA500')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey)
    ])
    
    # Gerar seção para cada turma
    for turma, alunos in turmas_alunos.items():
        elements.append(Paragraph(f"Lista de Presença - Turma {turma}", estilo_cabecalho))
        elements.append(Paragraph(f"Data: {data.strftime('%d/%m/%Y')}", estilo_data))
        elements.append(Spacer(1, 20))
        
        if not alunos:
            elements.append(Paragraph("⚠️ Nenhum aluno encontrado nesta turma.", styles['Normal']))
            elements.append(PageBreak())
            continue
        
        # Dividir alunos em páginas de 25
        alunos_por_pagina = 25
        paginas = [alunos[i:i+alunos_por_pagina] for i in range(0, len(alunos), alunos_por_pagina)]
        
        for idx, pagina in enumerate(paginas):
            dados_tabela = [["RA", "Nome do Aluno", "Assinatura"]]
            for aluno in pagina:
                dados_tabela.append([aluno['RA'], aluno['NOME'], ""])
            
            tabela = Table(dados_tabela, colWidths=[80, 300, 150])
            tabela.setStyle(estilo_tabela)
            elements.append(tabela)
            
            if idx < len(paginas) - 1:
                elements.append(PageBreak())
        
        elements.append(PageBreak())  # Nova turma em nova página
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Interface
st.title("📋 Gerador de Listas de Presença")

# Seleção da Filial
st.markdown("### 🏫 Selecione a Filial")
filial_selecionada = st.selectbox(
    "Filial:",
    options=[f"{f['NOMEFANTASIA']} (Filial {f['CODFILIAL']})" for f in filiais],
)

# Obter CODCOLIGADA e CODFILIAL
filial_info = next((f for f in filiais if f"Filial {f['CODFILIAL']}" in filial_selecionada), None)
if filial_info:
    codcoligada = filial_info['CODCOLIGADA']
    codfilial = filial_info['CODFILIAL']
    
    # Buscar turmas
    turmas = obter_turmas(codcoligada, codfilial)
    
    if turmas:
        data_selecionada = st.date_input("Selecione a data:", datetime.today())
        
        if st.button("🖨️ Gerar Listas para Todas as Turmas"):
            turmas_alunos = {}
            progresso = st.progress(0)
            
            for i, turma in enumerate(turmas):
                codturma = turma['CODTURMA']
                alunos = obter_alunos_turma(codcoligada, codfilial, codturma)
                turmas_alunos[codturma] = alunos
                progresso.progress((i + 1) / len(turmas))
            
            if any(turmas_alunos.values()):
                pdf = gerar_pdf(turmas_alunos, data_selecionada)
                st.success("✅ PDF gerado com sucesso!")
                
                st.download_button(
                    label="📥 Baixar Listas de Presença",
                    data=pdf,
                    file_name=f"listas_presenca_{filial_info['NOMEFANTASIA']}_{data_selecionada.strftime('%d%m%Y')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("⚠️ Nenhum aluno encontrado nas turmas.")
    else:
        st.warning("⚠️ Nenhuma turma encontrada nesta filial.")
else:
    st.warning("⚠️ Selecione uma filial válida.")
