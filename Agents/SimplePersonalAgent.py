# -*- coding: utf-8 -*-
"""
filename: UserPersonalAgent

Agent que implementa la interacció amb l'usuari


@author: casassg
"""
import random

import sys

import requests
from rdflib.namespace import FOAF

from AgentUtil.ACLMessages import get_agent_info, send_message, build_message, get_message_properties
from AgentUtil.OntologyNamespaces import ECSDI, ACL, DSO
import argparse
import socket
from multiprocessing import Process
from flask import Flask, render_template, request
from rdflib import Graph, Namespace, RDF, URIRef, Literal, XSD
from AgentUtil.Agent import Agent
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger

__author__ = 'amazadonde'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--open', help="Define si el servidor est abierto al exterior o no", action='store_true',
                    default=False)
parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
parser.add_argument('--dhost', default=socket.gethostname(), help="Host del agente de directorio")
parser.add_argument('--dport', type=int, help="Puerto de comunicacion del agente de directorio")

# Logging
logger = config_logger(level=1)

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

# Configuration stuff
if args.port is None:
    port = 9081
else:
    port = args.port

if args.open is None:
    hostname = '0.0.0.0'
else:
    hostname = socket.gethostname()

if args.dport is None:
    dport = 9001
else:
    dport = args.dport

if args.dhost is None:
    dhostname = socket.gethostname()
else:
    dhostname = args.dhost

# Flask stuff
app = Flask(__name__)

# Configuration constants and variables
agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
AgentePersonal = Agent('UserPersonalAgent',
                          agn.UserPersonalAgent,
                          'http://%s:%d/comm' % (hostname, port),
                          'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:%d/Register' % (dhostname, dport),
                       'http://%s:%d/Stop' % (dhostname, dport))

# Global dsgraph triplestore
dsgraph = Graph()

# planes de viaje del usuario encontrados
planes_usuario = []

# planes de viaje similares enconctrados
planes_similares = []

def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt

def infoagent_search_message(addr, ragn_uri):
    """
    Envia una accion a un agente de informacion
    """
    global mss_cnt
    logger.info('Hacemos una peticion al servicio de informacion')

    gmess = Graph()

    # Supuesta ontologia de acciones de agentes de informacion
    IAA = Namespace('IAActions')

    gmess.bind('foaf', FOAF)
    gmess.bind('iaa', IAA)
    reg_obj = agn[AgentePersonal.name + '-info-search']
    gmess.add((reg_obj, RDF.type, IAA.Search))

    msg = build_message(gmess, perf=ACL.request,
                        sender=AgentePersonal.uri,
                        receiver=ragn_uri,
                        msgcnt=mss_cnt)
    gr = send_message(msg, addr)
    mss_cnt += 1
    logger.info('Recibimos respuesta a la peticion al servicio de informacion')

    return gr

@app.route("/", methods=['GET', 'POST'])
def browser_cerca():
    """
    Permite la comunicacion con el agente via un navegador
    via un formulario
    """

    if request.method == 'GET':
        return render_template('busqueda.html', plan=None)
    elif request.method == 'POST':
        # Peticio de cerca
        if request.form['submit'] == 'Generar Plan de Viaje':
            logger.info("Enviando peticion de busqueda")

            # Content of the message
            contentResult = ECSDI['Peticion_Traansporte' + str(get_count())]

            # Graph creation
            gr = Graph()
            gr.add((contentResult, RDF.type, ECSDI.Peticion_Transporte))

            ciudad_origen = request.form['ciudad_origen']
            ciudad_destino = request.form['ciudad_destino']
            fecha_ida = request.form['fecha_ida']
            fecha_vuelta = request.form['fecha_vuelta']
            presupuesto = request.form['presupuesto']

            subject = ECSDI["Restricciones"]
            gr.add((subject+"_origen", ECSDI.aeropuerto_ini, Literal(ciudad_origen,datatype=XSD.string)))
            gr.add((subject+"_destino", ECSDI.aeropuerto_fi, Literal(ciudad_destino,datatype=XSD.string)))
            gr.add((subject+"_ida", ECSDI.Fecha_Partida, Literal(fecha_ida,datatype=XSD.string)))
            gr.add((subject+"_vuelta", ECSDI.Fecha_Llegada, Literal(fecha_vuelta,datatype=XSD.string)))
            gr.add((subject+"_precio", ECSDI.Precio, Literal(presupuesto,datatype=XSD.string)))
            gr.add((contentResult, ECSDI.Restinge, URIRef(subject)))

            planificador = get_agent_info(agn.AgentePlanificador, DirectoryAgent, AgentePersonal, get_count())

            gr2 = send_message(
                build_message(gr, perf=ACL.request, sender=AgentePersonal.uri, receiver=planificador.uri,
                              msgcnt=get_count(),
                              content=contentResult), planificador.address)

            index = 0
            subject_pos = {}
            flights_list = []
            for s, p, o in gr2:
                if s not in subject_pos:
                    subject_pos[s] = index
                    flights_list.append({})
                    index += 1
                if s in subject_pos:
                    subject_dict = flights_list[subject_pos[s]]
                    if p == RDF.type:
                        subject_dict['url'] = s
                    elif p == ECSDI.aeropuerto_ini:
                        subject_dict['ciudad_origen'] = o
                    elif p == ECSDI.aeropuerto_fi:
                        subject_dict['ciudad_destino'] = o
                    elif p == ECSDI.Fecha_Partida:
                        subject_dict['fecha_ida'] = o
                    elif p == ECSDI.Precio:
                        subject_dict['presupuesto'] = o
                    elif p == ECSDI.Fecha_Llegada:
                        subject_dict['fecha_vuelta'] = o
                    elif p == ECSDI.nombre:
                        subject_dict['nombre_hotel'] = o
                    elif p == ECSDI.direccion:
                        subject_dict['direccion_hotel'] = o
                    elif p == ECSDI.telefono:
                        subject_dict['telefono_hotel'] = o
                    flights_list[subject_pos[s]] = subject_dict
            return render_template('busqueda.html', plan=flights_list)


@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion del agente
    """
    return "Hola"


def tidyup():
    """
    Acciones previas a parar el agente

    """
    pass


def agentbehavior1():
    """
    Un comportamiento del agente

    :return:
    """
    print (DirectoryAgent.address)
    pass


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1)
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port, debug=True)

    # Esperamos a que acaben los behaviors
    ab1.join()
    logger.info('The End')
