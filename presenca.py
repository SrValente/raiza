import pandas as pd
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import urllib3
import logging
import time

# Configurações
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)

USERNAME = "p_heflo"
PASSWORD = "Q0)G$sW]rj"
BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"

# =============================================================================
# Lista de filiais
# =============================================================================
filiais = [
    {"NOMEFANTASIA": "COLÉGIO QI TIJUCA",      "CODCOLIGADA": 2,  "CODFILIAL": 2},
    {"NOMEFANTASIA": "COLÉGIO QI BOTAFOGO",    "CODCOLIGADA": 2,  "CODFILIAL": 3},
    {"NOMEFANTASIA": "COLÉGIO QI FREGUESIA",   "CODCOLIGADA": 2,  "CODFILIAL": 6},
    {"NOMEFANTASIA": "COLÉGIO QI RIO 2",       "CODCOLIGADA": 2,  "CODFILIAL": 7},
    {"NOMEFANTASIA": "COLEGIO QI METROPOLITANO","CODCOLIGADA": 6,  "CODFILIAL": 1},
    {"NOMEFANTASIA": "COLEGIO QI RECREIO",     "CODCOLIGADA": 10, "CODFILIAL": 1},
]

# =============================================================================
# FUNÇÕES DE CONSULTA
# =============================================================================
def obter_turmas(codcoligada, codfilial, turma_nome="%"):
    """
    Consulta RAIZA.0005 enviando CODCOLIGADA, CODFILIAL e TURMA_NOME (busca parcial).
    É preciso que o SQL no TOTVS aceite algo como:
      (CODTURMA + ' - ' + DESCRICAO) LIKE :TURMA_NOME
      e retorne também 'TURMA_NOME' no SELECT.
    """
    url = f"{BASE_URL}/RAIZA.0005/0/S"
    params = {
        "parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};TURMA_NOME={turma_nome}"
    }
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Erro ao obter turmas: {response.status_code} - {response.text}")
        return []

def obter_alunos_turma(codcoligada, codfilial, codturma, aluno_nome="%"):
    """
    Consulta RAIZA.0009 enviando CODCOLIGADA, CODFILIAL, CODTURMA e ALUNO_NOME (busca parcial).
    O SQL deve aceitar algo como: (RA + ' - ' + NOME) LIKE :ALUNO_NOME 
    e retornar também 'ALUNO_NOME' no SELECT.
    """
    url = f"{BASE_URL}/RAIZA.0009/0/S"
    params = {
        "parameters": f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODTURMA={codturma};ALUNO_NOME={aluno_nome}"
    }
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Erro ao obter alunos da turma: {response.status_code} - {response.text}")
        return []

def obter_faltas_por_aluno(codcoligada, codfilial, codturma, alunos, dia_semana, data):
    """
    Consulta RAIZA.0010 para cada aluno da lista,
    coletando os horários nos quais a frequência deve ser lançada como falta.
    """
    url = f"{BASE_URL}/RAIZA.0010/0/S"
    faltas = []
    for aluno in alunos:
        params = {
            "parameters": (
                f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODTURMA={codturma};"
                f"RA={aluno['RA']};DIASEMANA={dia_semana};DATA={data.strftime('%Y-%m-%d')}"
            )
        }
        response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params=params, verify=False)
        if response.status_code == 200:
            faltas.append({
                "RA": aluno["RA"],
                "NOME": aluno["NOME"],
                "HORARIOS": response.json()
            })
        else:
            logging.error(f"Erro ao obter faltas: {response.status_code} - {response.text}")
    return faltas

# =============================================================================
# GERADOR DE XML
# =============================================================================
def organizar_dados_para_xml(faltas, data, codcoligada, codfilial, codturma, dia_semana):
    """
    Converte a lista de 'faltas' em um DataFrame adequado para gerar o XML.
    """
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
                "IDTURMADISC":   horario.get("IDTURMADISC")
            })
    return pd.DataFrame(dados)

def gerar_xml(row):
    """
    Gera o XML (SOAP Envelope) para lançamento de falta em um horário específico.
    """
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

# =============================================================================
# REGISTRO DE FALTAS
# =============================================================================
def registrar_faltas(tabela_dados):
    logging.debug("Iniciando a função registrar_faltas")
    erros = []
    xmls_enviados = []
    
    for idx, row in tabela_dados.iterrows():
        logging.debug(f"Iniciando o processamento para RA {row['RA']}")
        try:
            envelope = gerar_xml(row)
            logging.debug(f"Envelope gerado para RA {row['RA']}: {envelope[:100]}...")
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
