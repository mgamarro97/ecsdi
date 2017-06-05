"""
.. module:: AgentAmadeus

AgentAmadeus
*************

:Description: AgentAmadeus

    Uso de la API de Amadeus, hoteles, vuelos, tren

    http://sandbox.amadeus.com

    Documentacion de la API REST (usando requests)

    https://sandbox.amadeus.com/api-catalog

    Tambien se puede usar el modulo python amadeus

    http://amadeus.readthedocs.io/en/latest/index.html

:Authors: bejar
    

:Version: 

:Created on: 23/01/2017 16:24 

"""
from AgentUtil.APIKeys import AMADEUS_KEY
from amadeus import Flights, Hotels
import json


__author__ = 'bejar'

class Vuelo():
    def getFlights(self):
        flights = Flights(AMADEUS_KEY)
        resp = flights.extensive_search(
            origin='MAD',
            destination='BCN',
            departure_date='2017-06-05--2017-06-28')
        return resp
