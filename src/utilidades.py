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
    # evitar division por cero
    if nudos == 0:
        return float('inf')
    return 60 * mn /nudos

def ask_bool(prompt: str) -> bool:
    s = input(prompt).strip().lower()
    return s in {"true", "t", "1", "si", "sí", "y", "s"}

def ask_prob_01(prompt: str) -> float:
    while True:
        try:
            p = float(input(prompt).strip())
            if 0.0 <= p <= 1.0:
                return p
        except ValueError:
            pass
        print("⚠️ Ingresá un número entre 0 y 1.")

def ask_pos_int(prompt: str) -> int:
    while True:
        try:
            x = int(input(prompt).strip())
            if x > 0:
                return x
        except ValueError:
            pass
        print("⚠️ Ingresá un entero positivo.")

