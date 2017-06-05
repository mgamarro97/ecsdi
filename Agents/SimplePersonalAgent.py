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
            contentResult = ECSDI['Cerca_productes_' + str(get_count())]

            # Graph creation
            gr = Graph()
            gr.add((contentResult, RDF.type, ECSDI.Cerca_productes))

            # Add restriccio ciudad origen
            ciudad_origen = request.form['ciudad_origen']
            print(ciudad_origen)
            if ciudad_origen:
                # Subject origen
                subject_origen = ECSDI['Restriccion_modelo' + str(get_count())]
                gr.add((subject_origen, RDF.type, ECSDI.Restriccion_modelo))
                gr.add((subject_origen, ECSDI.Modelo, Literal(subject_origen, datatype=XSD.string)))
                # Add restriccio to content
                gr.add((contentResult, ECSDI.Restringe, URIRef(subject_origen)))

            # Add restriccio ciudad destino
            ciudad_destino = request.form['ciudad_destino']
            if ciudad_destino:
                # Subject destino
                subject_destino = ECSDI['Restriccio_Marca' + str(get_count())]
                gr.add((subject_destino, RDF.type, ECSDI.Restriccion_Marca))
                gr.add((subject_destino, ECSDI.Marca, Literal(subject_destino, datatype=XSD.string)))
                # Add restriccio to content
                gr.add((contentResult, ECSDI.Restringe, URIRef(subject_destino)))

            # Add restriccio rango fechas
            fecha_ida = request.form['fecha_ida']
            fecha_vuelta = request.form['fecha_vuelta']
            if fecha_ida or fecha_vuelta:
                # Subject destino
                subject_fechas = ECSDI['Restriccion_Preus_' + str(get_count())]
                gr.add((subject_fechas, RDF.type, ECSDI.Rango_precio))
                if fecha_ida:
                    gr.add((subject_fechas, ECSDI.Precio_min, Literal(fecha_ida)))
                if fecha_vuelta:
                    gr.add((subject_fechas, ECSDI.Precio_max, Literal(fecha_vuelta)))
                gr.add((contentResult, ECSDI.Restringe, URIRef(subject_fechas)))

            # Add restriccio presupuesto
            presupuesto = request.form['presupuesto']
            if presupuesto:
                # Subject presupuesto
                subject_presupuesto = ECSDI['RestriccioNom' + str(get_count())]
                gr.add((subject_presupuesto, RDF.type, ECSDI.RestriccioNom))
                gr.add((subject_presupuesto, ECSDI.Nom, Literal(presupuesto, datatype=XSD.string)))
                # Add restriccio to content
                gr.add((contentResult, ECSDI.Restringe, URIRef(subject_presupuesto)))

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
                    elif p == ECSDI.Marca:
                        subject_dict['ciudad_origen'] = o
                    elif p == ECSDI.Modelo:
                        subject_dict['ciudad_destino'] = o
                    elif p == ECSDI.Precio:
                        subject_dict['fecha_ida'] = o
                    elif p == ECSDI.Nombre:
                        subject_dict['presupuesto'] = o
                    elif p == ECSDI.Peso:
                        subject_dict['fecha_vuelta'] = o
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
