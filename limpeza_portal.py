# coding: utf-8
# https://docs.google.com/spreadsheets/d/1eH-hPCpJj7mgdLu3KSYcHEDZZZx-NO03QhAUW5jwCl0/edit#gid=0
from API_Atitude.api_trello_class import Trello_Board
#from API_Atitude.firebaseAtitude import FirebaseAtitude
from API_Atitude.dbAtitude import DBAtitude
from API_Atitude.gsheetsAtitude import Gsheets
import constantesviewsql as cvs
import api_firebase as afb
import re
import sys

import json
from datetime import datetime, timedelta, date
import time

NOMEDOQUADROTRELLO = 'Operação'
credentialsOpen = open('credentials.json')
credentials = json.load(credentialsOpen)
credentialsOpen.close()

'''
ERRO NA UTILIZACAO DA CLASSE, TROQUEI PELO ARQUIVO COM FUNCOES
try:
    projectAttadmin = FirebaseAtitude(
        credentials['CertAttadmin'], credentials['DataBaseUrlAttadmin'], "[DEFAULT]", credentials['BucketNameAttadmin'])
except:
    projectAttadmin = FirebaseAtitude(
        credentials['CertAttadmin'], credentials['DataBaseUrlAttadmin'], "attadmin", credentials['BucketNameAttadmin'])
'''

config = {'apikey': credentials['ApiKey'], 'token': credentials['Token']}
Trello = Trello_Board(NOMEDOQUADROTRELLO, config)

credsDb = {'server': cvs.server, 'database': cvs.database, 'username': cvs.username, 'password': cvs.password}
viewPortal = DBAtitude(credsDb)

def main():
    print('inicio')
    if sys.platform == 'linux':
        TOKEN = '/home/tecnologia/gsheetstoken.pickle'
    else:
        TOKEN = r'D:\gsheetstoken.pickle'
    
    LIMP_PORTAL_GSHEET_ID = cvs.gshhets_limpeza_portal
    gsheet1 = Gsheets(TOKEN, LIMP_PORTAL_GSHEET_ID)
    rangeName = 'Carteira!A2:G100'
    # pega linahs de status para limpeza do portal
    linhas_de_status = gsheet1.get_data(rangeName)

    #status = "1.39 - SICAQ Aprovado - Corrigir"
    # verifica o que fazer com cada linha da planilha
    # colunas: status, prazo horas, lista, horario, criar cartao (s/n), labels
    print(linhas_de_status)
    for item in linhas_de_status:
        print(item)
        criar_cartao = item[4]
        executar = False
        if str(criar_cartao).lower() in ['nao','não']:
            print('não criar cartão | status: {}'.format(item[0]))
        else:
            # verifica a hora e compara com a hora de execução
            if datetime.now().hour == int(item[3]):
                executar = True
            else:
                print('Não é horário de executar esse status')
                print(item[3])
                executar = True

        if executar:
            status = item[0]
            prazo_horas = int(item[1])
            duedate = datetime.now() + timedelta(hours=prazo_horas)
            lista_nome = item[2]

            data = {'atualizacao': datetime.now(), 'status': 'online', 'info': str(status)}
            msg = afb.update_collection('botsStatus', 'limpezaPortal', data)
            print(msg)

            labels = ''
            label = item[5]
            if label != '':
                labels = Trello.get_label_id_by_name(label)

            contratos = viewPortal.get_clientes_by_status_groupby(status)
            contrato_anterior = ''
            for contrato in contratos:
                print(contrato)
                nome_cliente = contrato['cliente']
                contrato_nro = contrato['contrato_nro']
                empreend_nome = contrato['empreend_nome']
                dt_evolucao = contrato['dt_evolucao']
                cpf = contrato['cpf']
                nome_cartao = nome_cliente + " | "+cpf+" | "+empreend_nome+" | "+contrato_nro+" | RotinaPortal"

                # cria a variavel como True e depois ste False se cartao existir
                criar_cartao = True

                # verifica se contrato atual eh o mesmo do contrato anterior do loop for (query do banco pode trazer
                # varias linhas para o mesmo contrato
                if contrato_nro == contrato_anterior:
                    criar_cartao = False
                    print('*** contrato = contrato anterior ***')

                date_evolucao = date(year=dt_evolucao.year, month=dt_evolucao.month, day=dt_evolucao.day)
                if date_evolucao >= date.today() - timedelta(days=1):
                    criar_cartao = False
                    print('*** contrato evoluido ontem ou hoje***')

                # para o status 1.39, so cria cartao se for o 5, 10 ou 15 dia apos a evolucao
                if status.startswith('1.39'):
                    if date.today() - date_evolucao in [timedelta(days=5), timedelta(days=10), timedelta(days=15)]:
                        criar_cartao = True
                    elif date.today() - date_evolucao >= timedelta(days=20):
                        criar_cartao = False
                        # TODO mover cartao para distrato
                    else:
                        criar_cartao = False

                # verifica se cartao ja existe no quadro somente se contrato 1= contrato anterior
                if criar_cartao:
                    resp_search = Trello.search_board_cards(nome_cartao + " is:open -list:Finalizados")
                    # maior que zero para ver se há itens na lista, depois compara com o nome do primeiro item da lista
                    print(resp_search)
                    if len(resp_search) > 0 and nome_cartao == resp_search[0].get('name'):
                        #resp_search[0].get('id') != 'na':
                        print('existe cartao no quadro:' + str(nome_cartao))
                        criar_cartao = False

                if criar_cartao:
                    dt_retorno = contrato['dt_retorno']
                    print('===--------------------------------------------------===')
                    print("dt_retorno: {}, lista: {}".format(dt_retorno, lista_nome))

                    if dt_retorno is not None and len(re.findall(r'(\d+/\d+/\d+)',dt_retorno))>0:
                        # valida formato nn/nn/nnnn apenas, nao se a data eh valida
                        #dt_retorno_date = dt_retorno.strptime("%d/%m/%Y").date()
                        dt_retorno_date = datetime.strptime(dt_retorno, "%d/%m/%Y").date()
                        today = datetime.today().date()
                        if today >= dt_retorno_date:
                            descr = contrato_nro+" | "+status+" | "+str(dt_retorno)
                            resp = Trello.add_card_list_name(nome_cartao,descr,lista_nome,duedate=duedate,labels=labels)
                        else:
                            print('nao eh dia de criar cartao')
                            resp = 'nao criar cartao'
                    else:
                        # dt_retorno is none -> criar cartao
                        descr = contrato_nro + " | " + status
                        resp = Trello.add_card_list_name(nome_cartao, descr, lista_nome, duedate=duedate, labels=labels)

                    print(resp)
                    print(nome_cartao)
                    # TODO tratar erro
                    contrato_anterior = contrato_nro


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
        data = {'atualizacao': datetime.now(), 'status': 'except', 'info': str(e)}
        afb.update_collection('botsStatus', 'limpezaPortal', data)
