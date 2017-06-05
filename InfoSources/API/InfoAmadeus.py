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
    def getFlights(self, origen, destino, ida, vuelta):
        flights = Flights(AMADEUS_KEY)
        resp = flights.extensive_search(
            origin=origen,
            destination=destino,
            departure_date='2017-06-05--2017-06-28')
        return resp

class Hotel():
    def getHotel(self):
        hotels = Hotels(AMADEUS_KEY)

        resp = hotels.search_circle(
            latitude='41.3818',
            longitude='2.1685',
            radius='10',
            check_in='2017-06-28',
            check_out='2017-07-20'
        )
        return resp;
"""
print()
print("HOTEL:")
hotel = json.loads(json.dumps(resp, ensure_ascii=False))
hotel_address = json.loads(json.dumps(hotel["results"][0]["address"]))
print ("Nombre Hotel: " + hotel ["results"][0]["property_name"])
print ("Direccion: " + hotel_address["line1"])
print ("Ciudad: " + hotel_address["city"])
"""
