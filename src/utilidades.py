import const as c
import numpy as np
from typing import Optional, Tuple

# funcion para pasar de nudos a millas náuticas/min
def knots_to_mn_per_min(knots: float) -> float:
    return knots / 60.0

# devuelve rango de velocidades permitidas con forma de tupla (vmin, vmax)
def velocidad_permitida(distancia) -> Optional[Tuple[int, int]]:
    for dmin, dmax, rango in c.rangos:
        if dmin <= distancia < dmax:
            return rango
    return None

# dar un valor de uniforme en el rango x,y
def random_uniform(x,y) -> float:
    numero_random = np.random.uniform(x, y)
    return numero_random

def tiempo_min_para_mn(nudos,mn) -> float:
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


def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def tiempo_min_vmax_a_punto(x_from: float, x_to: float) -> float:
    """
    Tiempo mínimo (min) para ir de x_from -> x_to (x_to <= x_from),
    usando v_max de cada rango de const.rangos.
    """
    if x_from <= x_to:
        return 0.0
    t = 0.0
    a = x_to
    b = x_from
    for dmin, dmax, (vmin, vmax) in c.rangos:
        hi = dmax if dmax != float('inf') else b
        seg_lo = max(dmin, a)
        seg_hi = min(hi, b)
        if seg_hi > seg_lo:
            dist = seg_hi - seg_lo  # mn
            t += tiempo_min_para_mn(vmax, dist)
    return t

def eta_const_speed_to_point(x_actual: float, v_actual: float, x_point: float, now_min: int) -> float:
    """
    ETA/EAT simple al punto x_point: asume mantener la velocidad actual.
    Retorna minuto absoluto de cruce.
    """
    if x_actual <= x_point:
        return now_min
    if v_actual <= 0:
        v_actual = velocidad_permitida(x_actual)[1]
    dist = max(0.0, x_actual - x_point)   # mn
    t_rest = 60.0 * dist / v_actual       # min
    return now_min + t_rest

