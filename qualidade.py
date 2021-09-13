# coding: utf-8
import json
import sys, os
import time
from API_Atitude.dbAtitude import DBAtitude
from API_Atitude.api_trello_class import Trello_Board

credentialsOpen = open('credentials.json')
credentials = json.load(credentialsOpen)
credentialsOpen.close()

QUADROTRELLO = "Qualidade"

credsDb = {'server': credentials['server'], 'database': credentials['database'],
           'username': credentials['username'], 'password': credentials['password']}
DATABASE = DBAtitude(credsDb)

config = {'apikey': credentials['ApiKey'], 'token': credentials['Token']}
Trello_Qualidade = Trello_Board(QUADROTRELLO,config)


def main():
    items_pesquisa = [{
                'evoluido_de': '*',
                'evoluido_para': '1.12 - SICAQ aprovado',
                'construtora': 'Tenda',
                'lista': 'SICAQ - Tenda',
                'etiqueta': '6061f5405e5fb83323428fcf',
            },{
                'evoluido_de': '*',
                'evoluido_para': '2.08 - Formulários Enviados - Falta DAMP',
                'construtora': 'Tenda',
                'lista':'Conferência DAMP - Tenda',
                'etiqueta': '6061f5405e5fb83323428fcf',
            },{
                'evoluido_de': '2.01 - Geração de Formulários',
                'evoluido_para': '2.03 - Formulários Enviados',
                'construtora': 'Tenda',
                'lista': 'Conferência DAMP - Tenda',
                'etiqueta': '6061f5405e5fb83323428fcf',
            },{
                'evoluido_de':'*',
                'evoluido_para': "2.04 - Formulários Env. sem Quali. e sem DAMP",
                'construtora': 'Tenda',
                'lista': 'Demandas status 2.04',
                'etiqueta': '6061f5405e5fb83323428fcf',
            }]
    r = 'Nenhum cartao criado'
    print('======================= MAIN QUALIDADE =======================')
    for item in items_pesquisa:
        print(item)
        contratos = DATABASE.get_contratos_by_construtora_evoluido_de_para(item['construtora'], item['evoluido_de'], item['evoluido_para'])
        # DAMP: 2.01 para 2.03 ou saiu de 2.08 - lista conferir Damp

        print(contratos)
        print('----')
        if not contratos:
            print("##### Não existem contratos para as condições de pesquisa: {}; de: {}; para: {} #####".format(item['construtora'], item['evoluido_de'], item['evoluido_para']))
        else:
            for contrato in contratos:
                print(contrato)
                # intervalo api trello
                time.sleep(0.2)
                r = cria_contrato_trello(contrato, item['lista'], item['etiqueta'])
    return r


def cria_contrato_trello(contrato, nome_lista,etiqueta):
    r = ''
    titulo = '{}'.format(contrato['contrato_nro']) + '- {}'.format(contrato['cliente']) + '- {}'.format(contrato['cpf'])
    search_string = titulo + " is:open -list:Finalized"
    card = Trello_Qualidade.search_board_cards(search_string)
    print(card)
    
    if len(card) == 0:
        cria_cartao = True
    elif card[0]['id'] == 'na':
        cria_cartao = True
    else:
        cria_cartao = False

    if cria_cartao:
        cardid, rstatuscode = Trello_Qualidade.add_card_list_name(
            titulo, '', nome_lista, pos='bottom', labels=etiqueta)
        if rstatuscode == 200:
            r = 'ok, criado: {}'.format(titulo)
        else:
            # aguarda 3s para erro de muitas tentativas na api do trello
            time.sleep(3)
            # verificar se erro de lista ou label (cardid trara a mensagem de erro do trello):
            # lista inexistente contera texto listid, label inexistente, labelid
            if 'list' in cardid.lower():
                r = 'erro, lista inexistente: {}'.format(nome_lista)
                print(r)
            elif 'label' in cardid.lower():
                cardid, rstatuscode = Trello_Qualidade.add_card_list_name(
                    titulo, '', nome_lista)
                if rstatuscode == 200:
                    r = 'ok, criado: {}'.format(titulo)
                else:
                    r = 'erro na criacao do cartao'
            else:
                r = 'erro na criacao do cartao'
    else:
        r = 'ok, cartão já existe no quadro'
    return r
            

def mover_status_lista():
    contratos = DATABASE.get_clientes_by_status("2.04 - Formulários Env. sem Quali. e sem DAMP")
    if not contratos:
        print("##### Não existe contratos no status 2.04 #####")
    else:
        for cliente in contratos:
            print(cliente)
            titulo = '{}'.format(cliente['contrato_nro']) + '- {}'.format(cliente['cliente']) + '- {}'.format(cliente['cpf'])
            card = Trello_Qualidade.search_board_cards(titulo)
            print(card[0]['id'])
            if card[0]['id'] == 'na':
                Trello_Qualidade.add_card_list_name(
                    titulo, '', 'Demandas status 2.04')
            else: 
                print('##### Card já existente #####')
            
    

if __name__ == '__main__':
    while True:
        mover_status_lista()
        print('##### Aguardando (30 min) #####')
        time.sleep(1800)
