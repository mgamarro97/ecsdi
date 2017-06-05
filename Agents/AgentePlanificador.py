# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 15:58:13 2013

Esqueleto de agente usando los servicios web de Flask

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""
from random import random

__author__ = 'jjm'

from multiprocessing import Queue, Process
import sys
from AgentUtil.ACLMessages import get_agent_info, send_message, build_message, get_message_properties, register_agent
from AgentUtil.OntologyNamespaces import ECSDI, ACL
import argparse
import socket
from multiprocessing import Process
from flask import Flask, render_template, request, json
from rdflib import Graph, Namespace, RDF, URIRef, Literal, XSD, parser
from AgentUtil.Agent import Agent
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Logging import config_logger


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
    port = 9085
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
    # Agent Namespace
    agn = Namespace("http://www.agentes.org#")

    # Message Count
    mss_cnt = 0

    # Data Agent
    # Datos del Agente
    AgentePlanificador = Agent('AgentePlanificador',
                        agn.AgentePlanificador,
                        'http://%s:%d/comm' % (hostname, port),
                        'http://%s:%d/Stop' % (hostname, port))

    # Directory agent address
    DirectoryAgent = Agent('DirectoryAgent',
                           agn.Directory,
                           'http://%s:%d/Register' % (dhostname, dport),
                           'http://%s:%d/Stop' % (dhostname, dport))

    # Global triplestore graph
    dsGraph = Graph()

    # Queue
    queue = Queue()

    # Flask app
    app = Flask(__name__)


def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt


# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

def register_message():
    """
    Envia un mensaje de registro al servicio de registro
    usando una performativa Request y una accion Register del
    servicio de directorio

    :param gmess:
    :return:
    """

    logger.info('Nos registramos')
    logger.info(AgentePlanificador.address)

    gr = register_agent(AgentePlanificador, DirectoryAgent, AgentePlanificador.uri, get_count())
    return gr

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """
    logger.info('Peticion de plan recibida')
    global dsGraph

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message)

    msgdic = get_message_properties(gm)

    gr = None
    respfinal = Graph()
    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgentePlanificador.uri, msgcnt=get_count())
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(),
                               ACL['not-understood'],
                               sender=DirectoryAgent.uri,
                               msgcnt=get_count())
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Accion de busqueda
            if accion == ECSDI.Peticion_Transporte:
                transporte = get_agent_info(agn.AgenteTransporte, DirectoryAgent, AgentePlanificador, get_count())
                contentmsg = ECSDI['Peticion_Transporte_' + str(get_count())]
                gr = Graph()
                gr.add((contentmsg, RDF.type, ECSDI.Peticion_Transporte))
                grmsg = send_message(build_message(gr,  perf=ACL.request, sender=AgentePlanificador.uri, receiver=transporte.uri,
                              msgcnt=get_count(),
                              content=contentmsg), transporte.address)

                for(s, p, o) in grmsg:
                    if s == ECSDI['vuelo_'+str(random(0,9))]:
                        respfinal.add((s, p, o))

                alojamiento = get_agent_info(agn.AgenteAlojamiento, DirectoryAgent, AgentePlanificador, get_count())
                contentmsg2 = ECSDI['Peticion_Alojamiento_' + str(get_count())]
                gr2 = Graph()
                gr2.add((contentmsg2, RDF.type, ECSDI.Peticion_Alojamiento))
                grmsg2 = send_message(build_message(gr2, perf=ACL.request, sender=AgentePlanificador.uri, receiver=alojamiento.uri,
                              msgcnt=get_count(),
                              content=contentmsg2), alojamiento.address)
                for (s, p, o) in grmsg2:
                    if s == ECSDI['Alojamiento_'+str(random(0,9))]:
                        respfinal.add((s, p, o))

                actividades = get_agent_info(agn.AgenteActividades, DirectoryAgent, AgentePlanificador, get_count())
                contentmsg3 = ECSDI['Peticion_Actividades_' + str(get_count())]
                gr3 = Graph()
                gr3.add((contentmsg3, RDF.type, ECSDI.Peticion_Actividades))
                grmsg3 = send_message(
                    build_message(gr3, perf=ACL.request, sender=AgentePlanificador.uri, receiver=actividades.uri,
                                  msgcnt=get_count(),
                                  content=contentmsg3), actividades.address)
                for (s, p, o) in grmsg3:
                    if s == ECSDI['Museos_'+str(random(0,9))]:
                        respfinal.add((s, p, o))
                for (s, p, o) in grmsg3:
                    if s == ECSDI['Restaurantes_'+str(random(0,9))]:
                        respfinal.add((s, p, o))


    return respfinal.serialize(format='xml'), 200


        


@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"


def tidyup():
    """
    Acciones previas a parar el agente

    """
    pass


def register(cola):
    """
    Un comportamiento del agente

    :return:
    """

    gr = register_message()
    pass


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=register, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')


