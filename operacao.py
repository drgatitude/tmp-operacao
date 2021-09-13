# coding: utf-8
# /home/tecnologia/Operacao1.0/API_Atitude/api_trello_class.py
import requests
from inspect import currentframe, getframeinfo
import time as tm
from pathlib import Path
import pandas as pd
import json
from pprint import pprint
import html5lib
from bs4 import BeautifulSoup
from card import Card
from API_Atitude.api_trello_class import Trello_Board
from API_Atitude.api_portal import Portal
from API_Atitude.firebaseAtitude import FirebaseAtitude
from API_Atitude.dbAtitude import DBAtitude
from API_Atitude.x9 import x9, avisos_bots, send_erro_to_x9
from API_Atitude.diversos import send_status_token, hora_execucao
from regras import fgts, fgts_ressarcido, prioridade_comercial, valida_retorno, retorno_em_4horas, temp_retorno_em_d_mais_3
import sys
from datetime import time, datetime, timedelta, date
import platform
import numpy as np
import constantesviewsql as cvs
import sentry_sdk
import qualidade as qua

BREAK = 300

sentry_sdk.init(
    "https://60d3c8bfee3d4a38b6779f585b85a2fe@o505665.ingest.sentry.io/5594429",
    traces_sample_rate=0.0
)

NOMEDOQUADROTRELLO = "Operação"

IMOBS_EXCLUSAO = ['Aprova Rápido']
STATUS_EXCLUSAO = ['1.27 - Em Reavaliação - Aguardando Aut. para Reavaliar QV',
                   '1.26 - Em Reavaliação - Aguar. Aprovação Via Agência', 
                   '1.24 - Em Reavaliação - Analisar e Rodar', '1.22 - Aguardando para Reavaliar',
                   '1.21 - Em Reavaliação', '3.03 - Montado - Aguardando Baixa de FGTS', 
                   '2.08 - Formulários Enviados - Falta DAMP', '3.01 - Montagem e Conferência de Dossiê',
                   '2.01 - Geração de Formulários']

# SA-127 inclusao convenio_debito_fgts
LISTAS_ADD_INFO_FGTS = ['Montagem de Dossiês', 'Outros Repasse', 'Crítica']

credentialsOpen = open('credentials.json')
credentials = json.load(credentialsOpen)
credentialsOpen.close()

try:
    projectAttadmin = FirebaseAtitude(
        credentials['CertAttadmin'], credentials['DataBaseUrlAttadmin'], "[DEFAULT]", credentials['BucketNameAttadmin'])
except:
    projectAttadmin = FirebaseAtitude(
        credentials['CertAttadmin'], credentials['DataBaseUrlAttadmin'], "attadmin", credentials['BucketNameAttadmin'])

firebaseIdLabels = projectAttadmin.get_info_db_realtime(
    "idsTrelloOperacao/idLabels")

config = {'apikey': credentials['ApiKey'], 'token': credentials['Token']}
Trello = Trello_Board(NOMEDOQUADROTRELLO, config)

credsDb = {'server': cvs.server, 'database': cvs.database, 'username': cvs.username, 'password': cvs.password}
DATABASE = DBAtitude(credsDb)

credentials_portal = projectAttadmin.get_info_db_realtime("Credentials/Portal")
config_portal = {'login':credentials_portal['login'],'password':credentials_portal['senha']}
Portal_atitude = Portal(config_portal)

Card = Card()

inicioHoraComercial = "09:00:00"
fimHoraComercial = "20:00:00"
horaInicioExecucao = "06:00:00"
horaFimExecucao = "23:59:59"

def main():
    print('=== main ===')
    controleOperacao = projectAttadmin.get_info_db_realtime("ControleOperacao/")
    
    for item in controleOperacao:
        if item != None and item['ativo'] == "sim":
            busca_status(item)

    data = {'atualizacao': datetime.now(), 'status': 'online', 'info': Card.nome}		
    projectAttadmin.update_collection_fc('botsStatus', 'Operacao', data)
			

def busca_status(dictBusca):
    codPastaExterno = dictBusca['nome_status']
    nomeLista = dictBusca['nome_lista']
    etiquetas = dictBusca['etiqueta']
    regras = dictBusca['regras']
    listaContratosPortal = []
    print("===================== " + codPastaExterno + " =================")
    search = 'is:open and -list:"Finalizados"'
    cartoesTrello = Trello.search_board_cards(search)
    if cartoesTrello[0]['id'] == "na":
        for quantidade_tentativas in range(0,3):
            tm.sleep(3)
            cartoesTrello = Trello.search_board_cards(search)
            if quantidade_tentativas >= 2:
                erro = "Excedeu o máximo de tentativas para se conectar com o Trello"
                print(erro)
                frameinfo = getframeinfo(currentframe())
                send_erro_to_x9(frameinfo, erro)
                return

    contratosList = DATABASE.get_clientes_by_status(codPastaExterno)
    if contratosList == None:
        for quantidade_tentativas in range(0,3):
            tm.sleep(3)
            contratosList = DATABASE.get_clientes_by_status(codPastaExterno)
            if quantidade_tentativas >= 2:
                erro = "retorno nulo na conexão com o banco de dados"
                print(erro)
                frameinfo = getframeinfo(currentframe())
                send_erro_to_x9(frameinfo, erro)
                return

    for contratoUnico in contratosList:
        if contratosList == 'na':
            break
        Card.numContrato = str(contratoUnico['contrato'])
        Card.empreendimento = contratoUnico['empreend_nome']
        nomeCpf = contratoUnico['cpf'] + " - " + contratoUnico['cliente']

        # exclusao por regra de negocio
        if contratoUnico['imobiliaria'] in IMOBS_EXCLUSAO and contratoUnico['evoluido_para'] in STATUS_EXCLUSAO:
            print('nao incluir')
        else:
            # se nao for exclusao, incluir na lista para incluir no quadro
            listaContratosPortal.append(Card.numContrato)

            print(nomeCpf)
            thereIs = verifica_trello(cartoesTrello)

            if thereIs == False: #False - vai incluir | True - não vai incluir
                set_infos_class_card(contratoUnico, nomeCpf, nomeLista)
                direciona_para_trello(etiquetas, regras)

    return 1

def direciona_para_trello(etiquetas, regras):
    nomeLabels = etiquetas
    date = 2
    if nomeLabels != "na":
        idLabels = Trello.deParaNomeIdLabels(nomeLabels)
    else:
        idLabels = "na"
    for idLabel in idLabels:
        if idLabel == "":
            erro = "idLabel não encontrada"
            frameinfo = getframeinfo(currentframe())
            send_erro_to_x9(frameinfo, erro)
            return

    incluir, idLabels, pos = aplica_regras(regras, idLabels)
    
    if "na" in idLabels:
        idLabels = remove_na_from_labels(idLabels)

    if incluir == True:
        for contagem_tentativas in range(0,3):
            
            # SA-127
            if Card.nomeLista in LISTAS_ADD_INFO_FGTS:
                print('in LISTAS_ADD_INFO_FGTS - Contrato: {}'.format(Card.numContrato))
                convenio_debito_fgts = Portal_atitude.get_convenio_debito_fgts(Card.numContrato)
                data = {'atualizacao': datetime.now(), 
                        'status': 'fgts', 
                        'info': str(convenio_debito_fgts),
                        'card_name':Card.nome}
                projectAttadmin.update_collection_fc('botsStatus', 'operacao_convenio_fgts', data)
                if convenio_debito_fgts is not None:
                    descr = Card.desc + " convenio débito FGTS: " + str(convenio_debito_fgts)
                else:
                    descr = Card.desc
            else:
                descr = Card.desc
            
            # caso o retorno seja muito grande, isso evita erro 431 (header too big)
            descr = descr[:500]
            cardId, statusCode = Trello.add_card_list_name(Card.nome, descr, Card.nomeLista, date, pos, idLabels)
            
            if cardId != "na" and statusCode == 200:
                break
            elif contagem_tentativas >= 2:
                print(cardId)
                tm.sleep(3)
                # criar cartao sem labels
                cardId, statusCode = Trello.add_card_list_name(Card.nome, descr, Card.nomeLista)
                print(cardId)
                if cardId != "na" and statusCode == 200:
                    break

                erro = "Excesso de tentativas para incluir um card no trello no bot de operacao, conferir as labels | " + str(idLabels)
                frameinfo = getframeinfo(currentframe())
                send_erro_to_x9(frameinfo, erro)
                return 'erro'

def aplica_regras(regras, idLabels):
    incluir = True
    pos = "bottom"
    try:
        regrasList = regras.split(",")
    except:
        regrasList = []

    if type(regras) == str:
        regrasList.append(regras)

    for regra in regrasList:
        if regra == "valida_retorno":
            incluir = valida_retorno(Card) #entrada
        if regra == "fgts":
            idLabels = fgts(idLabels, Card) #tag
        if regra == "fgts_ressarcido":
            incluir, idLabels = fgts_ressarcido(idLabels, Card) #entrada e tag
        if regra == "retorno_em_4horas":
            incluir = retorno_em_4horas(Card, inicioHoraComercial, fimHoraComercial)
        if regra == "temp_retorno_em_d_mais_3":
            incluir = temp_retorno_em_d_mais_3(Card)
        if regra == "prioridade_comercial":
            pos, idLabels = prioridade_comercial(idLabels, Card) #posicao e tag
        if regra == "ever_top":
            pos = "top"
        if regra == "ever_bot":
            pos = "bottom"

    return incluir, idLabels, pos

def verifica_trello(cartoesTrello):
    resposta = False
    for i in cartoesTrello:
        if Card.numContrato in i['desc']:
            print("Já tem um cartão com esse nome")
            resposta = True
            break

    print("Resposta do Trello: " + str(resposta))
    return resposta

def set_infos_class_card(dictCliente, nomeCpf, nomeLista):
    Card.nomeLista = nomeLista
    Card.dataRetorno = dictCliente.get('dt_retorno', "na")
    Card.dtEtapaAtual = dictCliente.get('dt_etapa_atual', "na")
    Card.renda = dictCliente.get('vlr_renda_total', "na")
    Card.modalidade = dictCliente.get('modalidade_nome', "na")
    Card.construtora = dictCliente.get('construtora', "na")
    Card.regional = dictCliente.get('regional_nome', "na")
    Card.imobiliaria = dictCliente.get('imobiliaria', "na")
    Card.nome = str(Card.empreendimento) + " | " + str(Card.modalidade) + " | " + str(nomeCpf)
    Card.set_url()
    Card.set_desc()

def remove_na_from_labels(idLabels):
    listLabels = list(idLabels)
    print(listLabels)
    if "na" in listLabels:
        listLabels.remove("na")
    else:
        listLabels.remove("n")
        listLabels.remove("a")
    idLabels = tuple(listLabels)
    return idLabels

if __name__ == "__main__":
    while True:
        checkExecucao, agora = hora_execucao(horaInicioExecucao, horaFimExecucao)
        send_status_token("operacao", projectAttadmin)
        if checkExecucao == True:
            with requests.Session() as session:
                try:
                    main()
                except Exception as e:
                    print(e)
                    data = {'atualizacao': datetime.now(), 'status': 'except', 'info': str(e)}
                    projectAttadmin.update_collection_fc('botsStatus', 'Operacao', data)
			
        else:
            print("Fora do horario de execucao")
        print("Aguardando os {} segundos".format(BREAK))
        tm.sleep(BREAK)

        # chama funcao main do quadro qualidade
        try:
            r = qua.main()
            data = {'atualizacao': datetime.now(), 'status': 'online','info': str(r)}
            projectAttadmin.update_collection_fc('botsStatus', 'Qualidade', data)
        except Exception as e:
            data = {'atualizacao': datetime.now(), 'status': 'except','info': str(e)}
            projectAttadmin.update_collection_fc('botsStatus', 'Qualidade', data)
