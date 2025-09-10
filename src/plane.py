from dataclasses import dataclass
from typing import Literal, Optional, Tuple
import utilidades as u
import const as c

Status = Literal["en_fila", "desacelerando", "reinsercion", "desviado", "aterrizado"]

@dataclass
class Plane:
    id: int                   # Id identificador
    t_spawn: int              # Minuto en el que aparecio
    x: float = 100.0          # Distancia al AEP en mn
    v: float = 0.0            # Velocidad del avion en nudos
    status: Status = "en_fila"              # Estado del avion
    tiempo_estimado: Optional[int] = None     # Estimacion simple de arribo en min

    # Max_speed en el rango que esta
    def max_speed(self):
        max_speed = u.velocidad_permitida(self.x)[1]
        return max_speed
    
    # Mix_speed en el rango que esta
    def min_speed(self):
        mix_speed = u.velocidad_permitida(self.x)[0]
        return mix_speed

    def get_status(self):
        return self.status
    
    def get_id(self):
        return self.id

    # Pongo una velocidad al avion respetando los limites del rango
    def set_speed(self):
        self.v = u.random_uniform(self.min_speed(),self.max_speed())
        return 
    
    # Pone la maxima velocidad permitida en el rango
    def set_max_speed(self):
        self.v = self.max_speed()
        return
    
    # Devuleve el rango actual del avion
    def rango_actual(self):
        for dmin, dmax, _ in c.rangos:
            if dmin <= self.x < dmax:
                return dmax
        return c.rangos[-1][1]

    # Actualizacion de la estimacion de llegada (muy basica)  Falta: Actualizar con la funcion rango_actual()
    def time_to_arrive(self):
        lista_rangos = c.LISTA_RANGOS
        rango_anterior = 0
        tiempo_estimado = 0.0
        for rango_actual in lista_rangos:
            if self.x <= rango_actual:
                tiempo_estimado += u.tiempo_min_para_mn(self.v,rango_actual-rango_anterior)
                break
            # Calculo el tiempo que tardo en completar un rango entero, como es no inclucibe el maximo de los rangos uso el rango anterior para calcular la velocidad max
            velocidad_de_ese_rango = u.velocidad_permitida(rango_anterior)[1]
            tiempo_estimado += u.tiempo_min_para_mn(velocidad_de_ese_rango,rango_actual)
            rango_anterior = rango_actual
        self.tiempo_estimado = tiempo_estimado

    # Devuelve True si esta a menos de 4 mins del other avion
    def distancia_menor_4(self,other):
        if self.v/60 * 4  > self.x - other.x:
            return True
        return False

    # Devuelve True si esta a menos de 4 mins del other avion
    def distancia_mayor_5(self,other):
        if self.v/60 * 5  < self.x - other.x:
            return True
        return False

    # Hace avanzar al avion, calcula nuevo rango y se fija si hay que desacelerar 
    def avanzar(self,other,third):
        # Si ya aterizo no hago nada
        if self.status == "aterrizado":
            return
        # Si con este step llega al aeropuerto termina
        if self.x < self.v/60 * c.DT and self.status != "desviado":
            self.status = "aterrizado"
            self.tiempo_estimado = 0
            return
        
        # Si esta desviado retrocede en vez de avanzar y se fija si hay un gap de 10 min
        if self.status == "desviado":
            self.retroceder(other,third)
            return
        if self.status == "reinsercion":
            self.status = "en_fila"
        rango_antes = self.rango_actual()
        # Calculo la nueva pocicion
        self.x -= self.v/60 * c.DT
        # Me fijo si entra en un nuevo rango
        if rango_antes != self.rango_actual():
            self.set_speed()
        if self.distancia_menor_4(other) and other.status != "desviado":
            self.set_desacelerando(other)
            return
        elif self.distancia_mayor_5(other) and self.status == "desacelerando":
            self.set_max_speed()
        self.time_to_arrive()
            
    # Hace retroceder al avion 
    def retroceder(self,other,third):
        self.x += self.v/60 * c.DT
        # Si hay 10 min de distancia entre el de adelante y el de atras # hay por lo menos un DT de distancia entre los aviones entonces reingresa el avion
        if self.v/60 * 10 > third.x - other.x and self.v/60 * c.DT > self.x - other.x and self.v/60 * c.DT > third.x - self.x:
            self.status = "en_fila"
            self.set_speed()

    # Setea el desacelerado
    def set_desacelerando(self,other):
        self.v = other.v - 20
        if self.v < self.min_speed():
            self.set_desviado()
        else:
            self.status = "desacelerando"
            self.time_to_arrive()

    #  Funcion para desviar al avion, no avanzo porque en la primera que gira no puede avanzar
    def set_desviado(self):
        self.status = "desviado"
        self.v = 200
        self.tiempo_estimado = -1 # Pongo en -1 porque no se pouede calcular cuanto va a tardar

    # Calculo la distancia que se movio el avion
    def step(self,other,third):
        self.avanzar(other,third)
