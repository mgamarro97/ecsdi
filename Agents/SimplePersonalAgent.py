# -*- coding: utf-8 -*-
"""
filename: SimplePersonalAgent

Antes de ejecutar hay que añadir la raiz del proyecto a la variable PYTHONPATH

Ejemplo de agente que busca en el directorio y llama al agente obtenido


Created on 09/02/2014

@author: javier
"""

__author__ = 'javier'

from multiprocessing import Process
import socket
import argparse

from flask import Flask, render_template, request
from rdflib import Graph, Namespace
from rdflib.namespace import FOAF, RDF
import requests

from AgentUtil.OntologyNamespaces import ACL, DSO
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import build_message, send_message
from AgentUtil.Agent import Agent
from AgentUtil.Logging import config_logger
import sys
#sys.path.append('/path/to/dir')
PYTHONPATH='C:/Users/Jan/Documents/GitHub/ecsdi/Agents'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--open', help="Define si el servidor est abierto al exterior o no", action='store_true',
                    default=False)
parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
parser.add_argument('--dhost', default='localhost', help="Host del agente de directorio")
parser.add_argument('--dport', type=int, help="Puerto de comunicacion del agente de directorio")

# Logging
logger = config_logger(level=1)

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

# Configuration stuff
if args.port is None:
    port = 9002
else:
    port = args.port

if args.open is None:
    hostname = '0.0.0.0'
else:
    hostname = socket.gethostname()

if args.dport is None:
    dport = 9000
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
AgentePersonal = Agent('AgentePersonal',
                       agn.AgentePersonal,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:%d/Register' % (dhostname, dport),
                       'http://%s:%d/Stop' % (dhostname, dport))

# Global dsgraph triplestore
dsgraph = Graph()

#vuelos
vuelos_list = []

#hoteles
hoteles_list = []

#actividades
actividades_list = []


def directory_search_message(type):
    """
    Busca en el servicio de registro mandando un
    mensaje de request con una accion Search del servicio de directorio

    Podria ser mas adecuado mandar un query-ref y una descripcion de registo
    con variables

    :param type:
    :return:
    """
    global mss_cnt
    logger.info('Buscamos en el servicio de registro')

    gmess = Graph()

    gmess.bind('foaf', FOAF)
    gmess.bind('dso', DSO)
    reg_obj = agn[AgentePersonal.name + '-search']
    gmess.add((reg_obj, RDF.type, DSO.Search))
    gmess.add((reg_obj, DSO.AgentType, type))

    msg = build_message(gmess, perf=ACL.request,
                        sender=AgentePersonal.uri,
                        receiver=DirectoryAgent.uri,
                        content=reg_obj,
                        msgcnt=mss_cnt)
    gr = send_message(msg, DirectoryAgent.address)
    mss_cnt += 1
    logger.info('Recibimos informacion del agente')

    return gr


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
def browser_root():
    if request.method == 'GET':
        return render_template('rootPersonalAgent.html')
    else:
        usuario = request.form['usuario']
        ciudad_origen = request.form['ciudad_origen']
        ciudad_destino = request.form['ciudad_destino']
        fecha_ida = request.form['fecha_ida']
        fecha_vuelta = request.form['fecha_vuelta']
        presupuesto = request.form['presupuesto']

        return render_template('datosPersonalAgent.html', usuario=usuario, ciudad_origen=ciudad_origen,
                               ciudad_destino=ciudad_destino, fecha_ida=fecha_ida, fecha_vuelta=fecha_vuelta,
                               presupuesto=presupuesto)

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

    # Buscamos en el directorio
    # un agente de hoteles
    gr = directory_search_message(DSO.HotelsAgent)

    # Obtenemos la direccion del agente de la respuesta
    # No hacemos ninguna comprobacion sobre si es un mensaje valido
    msg = gr.value(predicate=RDF.type, object=ACL.FipaAclMessage)
    content = gr.value(subject=msg, predicate=ACL.content)
    ragn_addr = gr.value(subject=content, predicate=DSO.Address)
    ragn_uri = gr.value(subject=content, predicate=DSO.Uri)

    # Ahora mandamos un objeto de tipo request mandando una accion de tipo Search
    # que esta en una supuesta ontologia de acciones de agentes
    infoagent_search_message(ragn_addr, ragn_uri)

    # r = requests.get(ra_stop)
    # print r.text

    # Selfdestruct
    requests.get(AgentePersonal.stop)


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1)
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    logger.info('The End')
