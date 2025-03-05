import pandas as pd
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import urllib3
import logging  # Novo import

# Configurações
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Remove avisos SSL

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)  # Configuração básica

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

# ================== FUNÇÕES DE CONSULTA ==================
def obter_turmas(codcoligada, codfilial):
    url = f"{BASE_URL}/RAIZA.0005/0/S"
    params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial}"}
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
    return response.json() if response.status_code == 200 else []

def obter_alunos_turma(codcoligada, codfilial, codturma):
    url = f"{BASE_URL}/RAIZA.0009/0/S"
    params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODTURMA={codturma}"}
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
    return response.json() if response.status_code == 200 else []

def obter_faltas_por_aluno(codcoligada, codfilial, codturma, alunos, dia_semana, data):
    url = f"{BASE_URL}/RAIZA.0010/0/S"
    faltas = []
    for aluno in alunos:
        params = {"parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODTURMA={codturma};RA={aluno['RA']};DIASEMANA={dia_semana};DATA={data.strftime('%Y-%m-%d')}"}
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
        if response.status_code == 200:
            faltas.append({"RA": aluno["RA"], "NOME": aluno["NOME"], "HORARIOS": response.json()})
    return faltas

# ================== GERADOR DE XML VALIDADO ==================
def organizar_dados_para_xml(faltas, data, codcoligada, codfilial, codturma, dia_semana):
    dados = []
    for falta in faltas:
        for horario in falta["HORARIOS"]:
            dados.append({
                "CODCOLIGADA": codcoligada,
                "CODFILIAL": codfilial,
                "DATA": data.strftime('%Y-%m-%dT%H:%M:%S'),
                "CODTURMA": codturma,
                "DIADASEMANA": dia_semana,
                "RA": falta["RA"],
                "IDHORARIOTURMA": horario.get("IDHORARIOTURMA"),
                "IDTURMADISC": horario.get("IDTURMADISC")
            })
    return pd.DataFrame(dados)

def gerar_xml(row):
    return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tot="http://www.totvs.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <tot:SaveRecord>
            <tot:DataServerName>EduFrequenciaDiariaWSData</tot:DataServerName>
            <tot:XML><![CDATA[
                <EduFrequenciaDiaria>
                    <SFREQUENCIA>
                        <CODCOLIGADA>{row['CODCOLIGADA']}</CODCOLIGADA>
                        <IDHORARIOTURMA>{row['IDHORARIOTURMA']}</IDHORARIOTURMA>
                        <IDTURMADISC>{row['IDTURMADISC']}</IDTURMADISC>
                        <RA>{row['RA']}</RA>
                        <DATA>{row['DATA']}</DATA>
                        <PRESENCA>A</PRESENCA>
                    </SFREQUENCIA>
                    <PARAMS>
                        <CODCOLIGADA>{row['CODCOLIGADA']}</CODCOLIGADA>
                        <IDTURMADISC>{row['IDTURMADISC']}</IDTURMADISC>
                        <CODETAPA>1</CODETAPA>
                    </PARAMS>
                </EduFrequenciaDiaria>
            ]]></tot:XML>
            <tot:Contexto>CODCOLIGADA={row['CODCOLIGADA']}</tot:Contexto>
        </tot:SaveRecord>
    </soapenv:Body>
</soapenv:Envelope>"""

import time  # Import necessário para o delay

# ================== REGISTRO DE FALTAS ==================
def registrar_faltas(tabela_dados):
    logging.debug("Iniciando a função registrar_faltas")  # Log de início
    erros = []
    xmls_enviados = []
    
    for idx, row in tabela_dados.iterrows():
        logging.debug(f"Iniciando o processamento para RA {row['RA']}")
        try:
            envelope = gerar_xml(row)
            logging.debug(f"Envelope gerado para RA {row['RA']}: {envelope[:100]}...")  # Log parcial do envelope
            response = requests.post(
                "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/wsDataServer/IwsDataServer",
                data=envelope.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.totvs.com/IwsDataServer/SaveRecord"
                },
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                verify=False
            )
            logging.debug(f"Resposta para RA {row['RA']}: Status {response.status_code}")
            
            if response.status_code not in (200, 202):
                error_msg = f"Erro RA {row['RA']}: {response.status_code} - {response.text}"
                logging.error(error_msg)
                erros.append(error_msg)
            else:
                xmls_enviados.append(envelope)
                logging.debug(f"XML enviado com sucesso para RA {row['RA']}")
                
        except Exception as e:
            error_msg = f"Falha crítica RA {row['RA']}: {str(e)}"
            logging.exception(error_msg)
            erros.append(error_msg)
        
        time.sleep(0.5)  # Delay de 1/2 segundo entre as requisições
    
    logging.debug("Finalização da função registrar_faltas")
    return erros, xmls_enviados

# ================== INTERFACE STREAMLIT ==================
st.title("📋 Lançamento de Faltas")

# Seleção de Filial
filial_selecionada = st.selectbox("🏫 Filial:", [f"{f['NOMEFANTASIA']} (Filial {f['CODFILIAL']})" for f in filiais])
filial_info = next((f for f in filiais if f"Filial {f['CODFILIAL']}" in filial_selecionada), None)

if filial_info:
    codcoligada = filial_info['CODCOLIGADA']
    codfilial = filial_info['CODFILIAL']
    turmas = obter_turmas(codcoligada, codfilial)
    
    if turmas:
        data_selecionada = st.date_input("📅 Data:", datetime.today())
        dia_semana = data_selecionada.weekday() + 2
        turmas_selecionadas = st.multiselect("🎯 Turmas:", [t['CODTURMA'] for t in turmas])
        
        # Exibir alunos apenas se turmas forem selecionadas
        if turmas_selecionadas:
            alunos_por_turma = {}
            for codturma in turmas_selecionadas:
                alunos = obter_alunos_turma(codcoligada, codfilial, codturma)
                if alunos:
                    alunos_por_turma[codturma] = alunos
            
            # Lista de Alunos por Turma (Agora visível antes do botão!)
            st.markdown("### 👩🎓 Alunos por Turma")
            alunos_faltosos = []
            for codturma, alunos in alunos_por_turma.items():
                st.subheader(f"Turma {codturma}")
                for aluno in alunos:
                    if st.checkbox(f"{aluno['NOME']} - {aluno['RA']}", key=f"{codturma}_{aluno['RA']}"):
                        alunos_faltosos.append(aluno)
            
            # Botão de envio
            if st.button("🚀 Lançar Faltas"):
                if alunos_faltosos:
                    faltas = obter_faltas_por_aluno(codcoligada, codfilial, codturma, alunos_faltosos, dia_semana, data_selecionada)
                    tabela_dados = organizar_dados_para_xml(faltas, data_selecionada, codcoligada, codfilial, codturma, dia_semana)
                    erros, xmls = registrar_faltas(tabela_dados)
                    
                    if erros:
                        st.error("❌ Erros encontrados:\n" + "\n".join(erros))
                    else:
                        st.success(f"✅ {len(xmls)} faltas registradas com sucesso!")
                        st.download_button("📥 Baixar XMLs", "\n\n".join(xmls), file_name="xmls_enviados.txt")
                else:
                    st.warning("⚠️ Nenhum aluno selecionado!")
    else:
        st.warning("⚠️ Nenhuma turma encontrada nesta filial.")
