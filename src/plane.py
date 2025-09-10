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
    tiempo_estimado: Optional[int] = None   # Estimacion simple de arribo en min

    # velocidad maxima dada el rango en el que esta
    def max_speed(self):
        max_speed = u.velocidad_permitida(self.x)[1]
        return max_speed
    
    # velocidad minima dada el rango en el que esta
    def min_speed(self):
        mix_speed = u.velocidad_permitida(self.x)[0]
        return mix_speed

    def get_status(self):
        return self.status
    
    def get_id(self):
        return self.id

    # setea velocidad aleatoria al avion respetando los limites del rango
    def set_speed(self):
        self.v = u.random_uniform(self.min_speed(),self.max_speed())
        return 
    
    # setea la maxima velocidad permitida en el rango al avion
    def set_max_speed(self):
        self.v = self.max_speed()
        # si estaba desacelerando, volver a estado normal
        if self.status == "desacelerando":
            self.status = "en_fila"
        return
    
    # Devuleve el rango actual del avion en forma tupla (DistMin, DistMax)
    def rango_actual(self):
        for dmin, dmax, _ in c.rangos:
            if dmin <= self.x < dmax:
                return (dmin, dmax)
        return (c.rangos[-1][0], c.rangos[-1][1]) # fallback para cuando esta en rango (0, 5)

    def distancia_menor_4(self, other):
        if other is None:
            return False
        
        # ✅ Verificar que other esté realmente adelante (más cerca del aeropuerto)
        if other.x >= self.x:
            return False  # other no está adelante
        
        # ✅ Calcular distancia real entre aviones
        distancia_actual = self.x - other.x  # Siempre positiva si other está adelante
        
        # ✅ Calcular tiempo que tardará self en alcanzar la posición actual de other
        # Asumiendo que other mantiene su velocidad
        if self.v <= other.v:
            return False  # self no alcanzará a other
        
        velocidad_relativa = self.v - other.v  # velocidad de acercamiento
        tiempo_alcance = distancia_actual / (velocidad_relativa / 60)  # en minutos
        
        return tiempo_alcance < 4

    def distancia_mayor_5(self, other):
        if other is None:
            return True
        
        if other.x >= self.x:
            return True  # other no está adelante
        
        distancia_actual = self.x - other.x
        
        if self.v <= other.v:
            return True  # self no alcanzará a other
        
        velocidad_relativa = self.v - other.v
        tiempo_alcance = distancia_actual / (velocidad_relativa / 60)
        
        return tiempo_alcance > 5

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

    # hace avanzar al avion, calcula nuevo rango y se fija si hay que desacelerar 
    def avanzar(self,other,third):
        # si ya aterizo no hago nada
        if self.status == "aterrizado":
            return
        # si con este step llega al aeropuerto termina
        if self.x < self.v/60 * c.DT and self.status != "desviado":
            self.status = "aterrizado"
            self.tiempo_estimado = 0
            return
        
        # si esta desviado retrocede en vez de avanzar y se fija si hay un gap de 10 min
        if self.status == "desviado":
            self.retroceder(other,third)
            return  # importante: salir aqui para no ejecutar el resto del codigo

        if self.status == "reinsercion":
            self.status = "en_fila"
        
        rango_antes = self.rango_actual()

        # calcular la nueva posicion (solo para aviones no desviados)
        self.x -= self.v/60 * c.DT
        
        # me fijo si entra en un nuevo rango
        if rango_antes != self.rango_actual():
            self.set_speed()
            
        # verificar si debe desacelerar por estar muy cerca del avion de adelante
        # esto aplica sin importar el estado del avion de adelante (excepto si es desviado)
        if (other is not None and other.status != "desviado" and other.x < self.x and self.status != "desacelerando" and  self.distancia_menor_4(other)):
            self.set_desacelerando(other)
            return
    
    # ✅ Verificar si puede volver a velocidad máxima
        elif (self.status == "desacelerando" and (other is None or other.x >= self.x or other.status == "desviado" or  self.distancia_mayor_5(other))):
            self.set_max_speed()
            self.time_to_arrive()
            
    # hace retroceder al avion desviado y evalua reinsercion
    def retroceder(self,other,third):
        # el avion desviado se mueve en direccion opuesta (alejandose del aeropuerto)
        self.x += self.v/60 * c.DT
        
        # caso 1: hay un gap entre dos aviones en la fila
        if other is not None and third is not None:
            # calcular la distancia entre el avion de adelante y el de atras
            distancia_gap = other.x - third.x
            
            # si hay un gap de al menos 10 minutos entre los aviones en la fila
            if distancia_gap >= self.v/60 * 10:
                # calcular el punto medio del gap
                punto_medio_gap = third.x + distancia_gap / 2
                
                # verificar si este avion desviado puede reinsertarse
                # debe estar en la primera mitad del gap (entre third.x y el punto medio)
                if third.x < self.x <= punto_medio_gap:
                    # posicionar exactamente en el medio del gap
                    self.x = punto_medio_gap
                    self.status = "reinsercion"
                    # samplear velocidad segun el rango de la nueva posicion
                    self.set_speed()
                    return
        
        # caso 2: hay un gap entre el ultimo avion y las 100 millas nauticas
        elif other is not None and third is None:
            # calcular la distancia desde el ultimo avion hasta las 100mn
            distancia_gap = 100.0 - other.x
            
            # si hay un gap de al menos 10 minutos
            if distancia_gap >= self.v/60 * 10:
                # calcular el punto medio del gap
                punto_medio_gap = other.x + distancia_gap / 2
                
                # verificar si este avion desviado puede reinsertarse
                # debe estar en la primera mitad del gap (entre other.x y el punto medio)
                if other.x < self.x <= punto_medio_gap:
                    # posicionar exactamente en el medio del gap
                    self.x = punto_medio_gap
                    self.status = "reinsercion"
                    # samplear velocidad segun el rango de la nueva posicion
                    self.set_speed()
                    return
        
        return

    # setea el avion como desacelerando
    def set_desacelerando(self,other):
        if other is None:
            # si no hay avion de adelante, no se puede desacelerar
            return
        
        # desacelerar a 20 nudos menos que el avion de adelante
        nueva_velocidad = other.v - 20
        
        # verificar que no baje de la velocidad minima permitida
        if nueva_velocidad < self.min_speed():
            self.set_desviado()
        else:
            self.v = nueva_velocidad
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
