import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Consulta de Ocorrências - TOTVS", layout="wide")

USERNAME = "p_heflo"
PASSWORD = "Q0)G$sW]rj"
SOAP_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/wsDataServer/IwsDataServer"
BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"

st.title("🔍 Consulta de Ocorrências - TOTVS")

# ------------------------------------------------------------------------------------
# Listagem de filiais
# ------------------------------------------------------------------------------------
filiais = [
    {"NOMEFANTASIA": "COLÉGIO QI TIJUCA",      "CODCOLIGADA": 2,  "CODFILIAL": 2},
    {"NOMEFANTASIA": "COLÉGIO QI BOTAFOGO",    "CODCOLIGADA": 2,  "CODFILIAL": 3},
    {"NOMEFANTASIA": "COLÉGIO QI FREGUESIA",   "CODCOLIGADA": 2,  "CODFILIAL": 6},
    {"NOMEFANTASIA": "COLÉGIO QI RIO 2",       "CODCOLIGADA": 2,  "CODFILIAL": 7},
    {"NOMEFANTASIA": "COLEGIO QI METROPOLITANO","CODCOLIGADA": 6,  "CODFILIAL": 1},
    {"NOMEFANTASIA": "COLEGIO QI RECREIO",     "CODCOLIGADA": 10, "CODFILIAL": 1},
]

filiais_opcoes = {f"{f['NOMEFANTASIA']} ({f['CODFILIAL']})": (f['CODCOLIGADA'], f['CODFILIAL']) for f in filiais}
filial_escolhida = st.selectbox("Selecione a Filial:", list(filiais_opcoes.keys()))
codcoligada, codfilial = filiais_opcoes.get(filial_escolhida, (None, None))

# ------------------------------------------------------------------------------------
# Função de chamada à API TOTVS com lógica condicional para cada RAIZA
# ------------------------------------------------------------------------------------
def consultar_api(codigo, codcoligada=None, codfilial=None, ra=None, codperlet=None, ra_nome=None):
    """
    Monta os parâmetros na ordem exata que cada 'codigo' (RAIZA.000x) precisa.
    """
    if codigo == "RAIZA.0008":
        # SELECT ... WHERE CODCOLIGADA=@CODCOLIGADA, CODFILIAL=@CODFILIAL, CODPERLET=@CODPERLET
        parametros = f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODPERLET={codperlet}"

    elif codigo == "RAIZA.0001":
        # SELECT ... WHERE CODCOLIGADA=@CODCOLIGADA, CODFILIAL=@CODFILIAL, RA=@RA
        parametros = f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};RA={ra}"

    elif codigo == "RAIZA.0002":
        # Agora RAIZA.0002 exige TRES parâmetros: CODCOLIGADA, CODFILIAL e RA_NOME
        if not ra_nome:  # Se não vier nada, usar "%" por padrão
            ra_nome = "%"
        parametros = f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};RA_NOME={ra_nome}"

    else:
        parametros = ""

    url = f"{BASE_URL}/{codigo}/0/S"
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            params={"parameters": parametros},
            verify=False
        )
    except Exception as e:
        st.error(f"❌ Erro na requisição: {e}")
        return None

    if response.status_code == 200:
        try:
            return response.json()
        except Exception as e:
            st.error("❌ Erro ao converter a resposta para JSON.")
            st.error(f"❌ Erro: {e}")
            st.error(f"❌ Response Text: {response.text}")
            st.error(f"❌ URL: {response.url}")
            return None
    else:
        st.error(f"❌ Erro HTTP na consulta: {response.status_code}")
        st.error(f"❌ Response Text: {response.text}")
        st.error(f"❌ URL: {response.url}")
        return None

# ------------------------------------------------------------------------------------
# Buscar IDPERLET via RAIZA.0008 (exige CODCOLIGADA, CODFILIAL, CODPERLET=2025)
# ------------------------------------------------------------------------------------
id_perlet = None
if codcoligada and codfilial:
    perlet_info = consultar_api(
        "RAIZA.0008",
        codcoligada=codcoligada,
        codfilial=codfilial,
        codperlet=2025
    )
    if isinstance(perlet_info, list) and len(perlet_info) > 0:
        id_perlet = perlet_info[0].get("IDPERLET")

# ------------------------------------------------------------------------------------
# Selecionar Aluno via RAIZA.0002 (exige CODCOLIGADA, CODFILIAL, RA_NOME)
# Sempre passamos RA_NOME="%" (ou seja, listar todos)
# ------------------------------------------------------------------------------------
if codcoligada and codfilial:
    alunos = consultar_api(
        "RAIZA.0002",
        codcoligada=codcoligada,
        codfilial=codfilial,
        ra_nome="%"  # <-- Oculto para o usuário, mas passamos "%" fixo
    )

    if alunos is not None and len(alunos) > 0:
        # Montamos {RA_NOME: RA} para exibir no selectbox
        alunos_opcoes = {
            a["RA_NOME"]: a["RA"]
            for a in alunos
            if "RA" in a and "RA_NOME" in a
        }
        if len(alunos_opcoes) > 0:
            aluno_selecionado = st.selectbox("Selecione o Aluno (RA - Nome):", list(alunos_opcoes.keys()))
            ra_aluno = alunos_opcoes[aluno_selecionado]
        else:
            st.warning("⚠ Nenhum aluno encontrado na filial.")
            ra_aluno = None
    else:
        st.warning("⚠ Nenhum aluno encontrado para essa filial.")
        ra_aluno = None
else:
    ra_aluno = None

# ------------------------------------------------------------------------------------
# Consulta de Ocorrências (RAIZA.0001) e inclusão de nova ocorrência
# ------------------------------------------------------------------------------------
if ra_aluno and codcoligada and codfilial:

    # Botão para consultar ocorrências
    if st.button("🔎 Consultar Ocorrências"):
        ocorrencias = consultar_api(
            "RAIZA.0001",
            codcoligada=codcoligada,
            codfilial=codfilial,
            ra=ra_aluno
        )
        if isinstance(ocorrencias, list) and len(ocorrencias) > 0:
            st.success("✅ Consulta realizada com sucesso!")
            df = pd.DataFrame(ocorrencias)
            st.dataframe(df)
        else:
            st.warning("⚠ Nenhuma ocorrência encontrada.")
            st.error(f"Detalhes da consulta: CODCOLIGADA={codcoligada};CODFILIAL={codfilial};RA={ra_aluno}")

    # Botão para exibir o formulário de nova ocorrência
    if st.button("➕ Nova Ocorrência"):
        st.session_state["nova_ocorrencia"] = True

    # Formulário de inclusão de ocorrência
    if "nova_ocorrencia" in st.session_state and st.session_state["nova_ocorrencia"]:
        st.markdown("### 📝 Registrar Nova Ocorrência")

        descricao_tipo = st.selectbox("Selecione o Tipo de Ocorrência:", ["Advertência", "Suspensão", "Outros"])
        cod_ocorrencia_tipo = 30  # Exemplo fixo

        # Captura e escapa os caracteres especiais nas observações
        observacoes_input = st.text_area("Observações")
        observacoes_internas_input = st.text_area("Observações Internas")
        observacoes = escape(observacoes_input)
        observacoes_internas = escape(observacoes_internas_input)

        grupo_ocorrencia = 4
        descricao_grupo = "Grupo Comportamental"

        # Data/hora atual
        data_atual = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

        if id_perlet:
            if st.button("✅ Concluir Inclusão da Ocorrência"):
                xml_data = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tot="http://www.totvs.com/">
   <soapenv:Header/>
   <soapenv:Body>
      <tot:SaveRecord>
         <tot:DataServerName>EduOcorrenciaAlunoData</tot:DataServerName>
         <tot:XML><![CDATA[<EduOcorrenciaAluno>
   <SOcorrenciaAluno>
         <CODCOLIGADA>{codcoligada}</CODCOLIGADA>
         <IDOCORALUNO>-1</IDOCORALUNO>
         <RA>{ra_aluno}</RA>
         <CODOCORRENCIAGRUPO>{grupo_ocorrencia}</CODOCORRENCIAGRUPO>
         <CODOCORRENCIATIPO>{cod_ocorrencia_tipo}</CODOCORRENCIATIPO>
         <IDPERLET>{id_perlet}</IDPERLET>
         <CODPERLET>2025</CODPERLET>
         <DATAOCORRENCIA>{data_atual}</DATAOCORRENCIA>
         <DESCGRUPOOCOR>{descricao_grupo}</DESCGRUPOOCOR>
         <DESCTIPOOCOR>{descricao_tipo}</DESCTIPOOCOR>
         <CODTIPOCURSO>1</CODTIPOCURSO>
         <DISPONIVELWEB>0</DISPONIVELWEB>
         <RESPONSAVELCIENTE>0</RESPONSAVELCIENTE>
         <OBSERVACOES>{observacoes}</OBSERVACOES>
         <OBSERVACOESINTERNAS>{observacoes_internas}</OBSERVACOESINTERNAS>
         <POSSUIARQUIVO>N</POSSUIARQUIVO>
   </SOcorrenciaAluno>
</EduOcorrenciaAluno>]]></tot:XML>
         <tot:Contexto>CODCOLIGADA={codcoligada}</tot:Contexto>
      </tot:SaveRecord>
   </soapenv:Body>
</soapenv:Envelope>"""

                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://www.totvs.com/IwsDataServer/SaveRecord"
                }

                response = requests.post(
                    SOAP_URL,
                    data=xml_data.encode('utf-8'),
                    headers=headers,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD),
                    verify=False
                )

                if response.status_code == 200:
                    try:
                        root = ET.fromstring(response.content)
                        fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
                        if fault is not None:
                            faultstring = fault.find('faultstring').text
                            st.error(f"❌ Erro no TOTVS (SOAP Fault): {faultstring}")
                            st.error(f"❌ Status Code: {response.status_code}")
                            st.error(f"❌ Response Text: {response.text}")
                            st.error(f"❌ Headers: {response.headers}")
                            st.error(f"❌ XML Enviado: {xml_data}")
                        else:
                            st.success("✅ Ocorrência registrada com sucesso!")
                            del st.session_state["nova_ocorrencia"]
                    except ET.ParseError as e:
                        st.error("❌ Resposta inválida do servidor TOTVS.")
                        st.error(f"❌ Status Code: {response.status_code}")
                        st.error(f"❌ Response Text: {response.text}")
                        st.error(f"❌ Erro de Parse: {e}")
                        st.error(f"❌ XML Enviado: {xml_data}")
                else:
                    st.error(f"❌ Erro HTTP ao enviar a requisição: {response.status_code}")
                    st.error(f"❌ Response Text: {response.text}")
                    st.error(f"❌ Headers: {response.headers}")
                    st.error(f"❌ XML Enviado: {xml_data}")
        else:
            st.error("❌ IDPERLET não encontrado.")
