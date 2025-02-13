import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

st.set_page_config(page_title="Consulta de Ocorrências - TOTVS", layout="wide")

USERNAME = "p_heflo"
PASSWORD = "Q0)G$sW]rj"
SOAP_URL = "https://raizeducacao160289.rm.cloudtotvs.com.br:8051/wsDataServer/IwsDataServer"
BASE_URL = "https://raizeducacao160286.rm.cloudtotvs.com.br:8051/api/framework/v1/consultaSQLServer/RealizaConsulta"

st.title("🔍 Consulta de Ocorrências - TOTVS")

# Seleção da Filial
filiais = [
    {"NOMEFANTASIA": "COLÉGIO QI TIJUCA", "CODCOLIGADA": 2, "CODFILIAL": 2},
    {"NOMEFANTASIA": "COLÉGIO QI BOTAFOGO", "CODCOLIGADA": 2, "CODFILIAL": 3},
    {"NOMEFANTASIA": "COLÉGIO QI FREGUESIA", "CODCOLIGADA": 2, "CODFILIAL": 6},
    {"NOMEFANTASIA": "COLÉGIO QI RIO 2", "CODCOLIGADA": 2, "CODFILIAL": 7},
    {"NOMEFANTASIA": "COLEGIO QI METROPOLITANO", "CODCOLIGADA": 6, "CODFILIAL": 1},
    {"NOMEFANTASIA": "COLEGIO QI RECREIO", "CODCOLIGADA": 10, "CODFILIAL": 1},
]

filiais_opcoes = {f"{f['NOMEFANTASIA']} ({f['CODFILIAL']})": (f['CODCOLIGADA'], f['CODFILIAL']) for f in filiais}
filial_escolhida = st.selectbox("Selecione a Filial:", list(filiais_opcoes.keys()))
codcoligada, codfilial = filiais_opcoes.get(filial_escolhida, (None, None))

# 🔍 Função para consultar a API TOTVS
def consultar_api(codigo, parametros):
    url = f"{BASE_URL}/{codigo}/0/S"
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), params={"parameters": parametros}, verify=False)
    return response.json() if response.status_code == 200 else None

# 🔍 Buscar IDPERLET correto via RAIZA.0008
id_perlet = None
if codcoligada and codfilial:
    perlet_info = consultar_api("RAIZA.0008", f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial};CODPERLET=2025")
    if isinstance(perlet_info, list) and len(perlet_info) > 0:
        id_perlet = perlet_info[0]["IDPERLET"]

# Seleção do Aluno
if codcoligada and codfilial:
    alunos = consultar_api("RAIZA.0002", f"CODCOLIGADA={codcoligada};CODFILIAL={codfilial}")
    alunos_opcoes = {f"{a['NOME']} ({a['RA']})": a["RA"] for a in alunos if "RA" in a and "NOME" in a}
    aluno_selecionado = st.selectbox("Selecione o Aluno:", list(alunos_opcoes.keys()))
    
    ra_aluno = alunos_opcoes[aluno_selecionado]  # Pegando apenas o RA, sem o nome

    if st.button("🔎 Consultar Ocorrências"):
        ocorrencias = consultar_api("RAIZA.0001", f"RA={ra_aluno};CODCOLIGADA={codcoligada};CODFILIAL={codfilial}")
        if isinstance(ocorrencias, list) and ocorrencias:
            df = pd.DataFrame(ocorrencias)
            st.dataframe(df)
        else:
            st.warning("⚠️ Nenhuma ocorrência encontrada.")

    # Botão para exibir o formulário de nova ocorrência
    if st.button("➕ Nova Ocorrência"):
        st.session_state["nova_ocorrencia"] = True

    if "nova_ocorrencia" in st.session_state and st.session_state["nova_ocorrencia"]:
        st.markdown("### 📝 Registrar Nova Ocorrência")

        descricao_tipo = st.selectbox("Selecione o Tipo de Ocorrência:", ["Advertência", "Suspensão", "Outros"])
        cod_ocorrencia_tipo = 30  # Exemplo fixo

        observacoes = st.text_area("Observações")
        observacoes_internas = st.text_area("Observações Internas")

        grupo_ocorrencia = 4
        descricao_grupo = "Grupo Comportamental"

        data_atual = datetime.today().strftime("%Y-%m-%dT%H:%M:%S")

        if id_perlet:
            if st.button("✅ Concluir Inclusão da Ocorrência"):
                xml_data = f"""<EduOcorrenciaAluno>
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
</EduOcorrenciaAluno>"""

                headers = {"Content-Type": "text/xml"}
                response = requests.post(SOAP_URL, data=xml_data, headers=headers, auth=HTTPBasicAuth(USERNAME, PASSWORD))

                if response.status_code == 200:
                    st.success("✅ Ocorrência registrada com sucesso!")
                    del st.session_state["nova_ocorrencia"]
                elif response.status_code == 202:
                    st.warning("⚠️ A API aceitou (`202`), mas o processamento pode estar pendente no TOTVS. Verificando...")
                    
                    # 🔍 Verificar se a ocorrência foi realmente criada
                    st.write("🔍 Consultando se a ocorrência foi registrada...")

                    ocorrencias = consultar_api("RAIZA.0001", f"RA={ra_aluno};CODCOLIGADA={codcoligada};CODFILIAL={codfilial}")

                    if isinstance(ocorrencias, list) and len(ocorrencias) > 0:
                        st.success("✅ A ocorrência foi registrada com sucesso e já aparece na listagem!")
                        df = pd.DataFrame(ocorrencias)
                        st.dataframe(df)
                    else:
                        st.warning("⚠️ A ocorrência ainda não aparece na consulta. Aguarde ou verifique no TOTVS.")

                else:
                    st.error(f"❌ Erro ao registrar ocorrência: {response.status_code}")
