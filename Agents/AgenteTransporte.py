# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 15:58:13 2013

Esqueleto de agente usando los servicios web de Flask

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""
from InfoSources.API.InfoAmadeus import Vuelo

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
    port = 9082
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
    AgenteTransporte = Agent('AgenteTransporte',
                        agn.AgenteTransporte,
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
    logger.info(AgenteTransporte.address)

    gr = register_agent(AgenteTransporte, DirectoryAgent, AgenteTransporte.uri, get_count())
    return gr



@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """
    logger.info('Peticion de informacion recibida')
    global dsGraph

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message)

    msgdic = get_message_properties(gm)

    gr = None

    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteTransporte.uri, msgcnt=get_count())
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
            if accion == ECSDI.Cerca_productes:
                restriccions = gm.objects(content, ECSDI.Restringe)
                restriccions_dict = {}
                for restriccio in restriccions:
                    if gm.value(subject=restriccio, predicate=RDF.type) == ECSDI.Restriccion_Marca:
                        destino = gm.value(subject=restriccio, predicate=ECSDI.Marca)
                        logger.info('Ciudad Destino: ' + destino)
                        restriccions_dict['brand'] = destino
                    elif gm.value(subject=restriccio, predicate=RDF.type) == ECSDI.Restriccion_modelo:
                        origen = gm.value(subject=restriccio, predicate=ECSDI.Modelo)
                        logger.info('Ciudad Origen: ' + origen)
                        restriccions_dict['model'] = origen
                    elif gm.value(subject=restriccio, predicate=RDF.type) == ECSDI.Rango_precio:
                        ida = gm.value(subject=restriccio, predicate=ECSDI.Precio_max)
                        vuelta = gm.value(subject=restriccio, predicate=ECSDI.Precio_min)
                        if ida:
                            logger.info('Fecha Ida: ' + ida)
                            restriccions_dict['min_price'] = ida.toPython()
                        if vuelta:
                            logger.info('Fecha Vuelta: ' + vuelta)
                            restriccions_dict['max_price'] = vuelta.toPython()
                    elif gm.value(subject=restriccio, predicate=RDF.type) == ECSDI.RestriccioNom:
                        presupuesto = gm.value(subject=restriccio, predicate=ECSDI.Nom)
                        logger.info('Presupuesto: ' + presupuesto)
                        restriccions_dict['name'] = presupuesto

                gr = findProducts(**restriccions_dict)

    logger.info('Respondemos a la peticion')

    serialize = gr.serialize(format='xml')
    return serialize, 200

def findProducts(presuppuesto=None, destino=None, ida=0.0, vuelta=sys.float_info.max, origen=None):
    graph = Graph()
    vuelos = Vuelo.getFlights()
    result = Graph()
    result.bind('ECSDI', ECSDI)
    vuelo = json.loads(json.dumps(vuelos, ensure_ascii=False))
    i = 0
    origen = vuelo["origin"]
    while i < 10:
        destination = vuelo["results"][i]["destination"]
        departure = vuelo["results"][i]["departure_date"]
        return_date = vuelo["results"][i]["return_date"]
        price = vuelo["results"][0]["price"]
        aerolinea = vuelo["results"][0]["airline"]
        logger.debug(origen, destination, departure, return_date, price, aerolinea)
        subject = aerolinea + "_" + departure
        result.add((subject, RDF.type, ECSDI.Producte))
        result.add((subject, ECSDI.Marca, Literal(origen, datatype=XSD.string)))
        result.add((subject, ECSDI.Modelo, Literal(destination, datatype=XSD.string)))
        result.add((subject, ECSDI.Precio, Literal(departure, datatype=XSD.date)))
        result.add((subject, ECSDI.Peso, Literal(return_date, datatype=XSD.date)))
        result.add((subject, ECSDI.Nombre, Literal(price, datatype=XSD.float)))
        result.add((subject, ECSDI.Nombre, Literal(aerolinea, datatype=XSD.string)))
    return result

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


def agentbehavior1(queue):
    """
    Un comportamiento del agente

    :return:
    """
    gr = register_message()
    """""
    vuelos = Vuelo().getFlights()
    """""
    """
    print("VUELO:")

    vuelo = json.loads(json.dumps(vuelos, ensure_ascii=False))
    print("Ciudad Origen: " + vuelo["origin"])
    print("Ciudad Destino: " + vuelo["results"][0]["destination"])
    print("Fecha Salida: " + vuelo["results"][0]["departure_date"])
    print("Fecha Llegada: " + vuelo["results"][0]["return_date"])
    print("Precio Total: " + vuelo["results"][0]["price"])
    print("Aerolinea: " + vuelo["results"][0]["airline"])
    """


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(queue,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print ('The End')


