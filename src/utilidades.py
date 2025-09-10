import const as c
import numpy as np

# funcion para pasar de nudos a millas náuticas/min
def knots_to_mn_per_min(knots: float) -> float:
    return knots / 60.0

# devuelve rango de velocidades permitidas con forma de tupla (vmin, vmax)
def velocidad_permitida(distancia):
    for dmin, dmax, rango in c.rangos:
        if dmin <= distancia < dmax:
            return rango
    return None

# dar un valor de uniforme en el rango x,y
def random_uniform(x,y):
    numero_random = np.random.uniform(x, y)
    return numero_random

def tiempo_min_para_mn(nudos,mn):
    return 60 * mn /nudos

