# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 15:58:13 2013

Demo de consulta del servicio del tiempo de openweathermap.org

Se pueden hacer consultas sin estar registrado.
Para hacer consultas mas complejas es posible que
haya que registrarse y obtener una clave de desarrollador en su web

@author: javier
"""

__author__ = 'javier'

import requests
from AgentUtil.APIKeys import WEATHERAPPID
# Endpoint que da previsiones del tiempo a 5 dias
WEATHER_END_POINT = 'api.openweathermap.org/data/2.5/forecast?q={city name},{country code}'

# Hacemos el GET al servicio REST
# Prevision del tiempo en Barcelona para los proximos 5 dias en sistema metrico
r = requests.get(WEATHER_END_POINT,
                 params={'q': 'Barcelona,es', 'APPID': WEATHERAPPID})

# Transformamos la respuesta de JSON a un diccionario python
dic = r.json()
print (dic)
# Imprimimos los elementos de la respuesta
for d in dic['list']:
    print (d)