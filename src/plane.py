from dataclasses import dataclass
from typing import Literal, Optional, Tuple
import utilidades as u
import const as c

Status = Literal["en_fila", "desacelerando", "reinsercion", "desviado", "aterrizaje_confirmado", "intento_aterrizar"]
@dataclass
class Plane:
    id: int                                 # Id identificador
    t_spawn: int                            # Minuto en el que aparecio
    x: float = 100.0                        # Distancia al AEP en mn
    v: float = 0.0                          # Velocidad del avion en nudos
    status: Status = "en_fila"              # Estado del avion
    tiempo_estimado: Optional[int] = None   # Estimacion simple de arribo en min
    minutos_bloqueo:int = 0
    t_landing: Optional[int] = None         # Minuto en el que aterrizo (si aterrizo)
    sta_meter: Optional[float] = None
    metering: bool = False

    # velocidad maxima dada el rango en el que esta
    def max_speed(self) -> float:
        max_speed = u.velocidad_permitida(self.x)[1]
        return max_speed
    
    # velocidad minima dada el rango en el que esta
    def min_speed(self) -> float:
        mix_speed = u.velocidad_permitida(self.x)[0]
        return mix_speed

    # devuelve el estado del avion
    def get_status(self) -> Status:
        return self.status

    # devuelve el id del avion
    def get_id(self) -> int:
        return self.id
    
    # calcula el tiempo total de vuelo desde que aparecio hasta que aterrizo
    def tiempo_total_vuelo(self) -> Optional[int]:
        """calcula el tiempo total de vuelo desde que aparecio hasta que aterrizo.
        retorna None si el avion no aterrizo aun."""
        if self.t_landing is None:
            return None
        return self.t_landing - self.t_spawn

    # setea velocidad aleatoria al avion respetando los limites del rango
    def set_speed(self) -> None:
        self.v = u.random_uniform(self.min_speed(),self.max_speed())
        return 
    
    # setea la maxima velocidad permitida en el rango al avion
    def set_max_speed(self) -> None:
        self.v = self.max_speed()
        if self.status == "desacelerando": # si estaba desacelerando, vuelve al estado normal
            self.status = "en_fila"
        return

    # devuleve el rango actual del avion en forma tupla (DistMin, DistMax)
    def rango_actual(self) -> Tuple[float, float]:
        for dmin, dmax, _ in c.rangos:
            if dmin <= self.x < dmax:
                return (dmin, dmax)
        return (c.rangos[-1][0], c.rangos[-1][1]) # fallback para cuando esta en rango (0, 5) 

    # verifica si el avion self esta a menos de 4 minutos de other
    def distancia_menor_4(self, other) -> bool:
        if other is None:
            return False
        if other.x >= self.x: # verificar que other esté realmente adelante
            return False
        
        distancia_actual = self.x - other.x  # calcular distancia física actual en millas náuticas
        
        tiempo_para_alcanzar = distancia_actual / (self.v / 60)  # convertir a tiempo basado en la velocidad actual de self 
        
        return tiempo_para_alcanzar < 4

    # verifica si el avion self esta a mas de 5 minutos de other
    def distancia_mayor_5(self, other) -> bool:
        if other is None:
            return True
        
        if other.x >= self.x:
            return True
        
        distancia_actual = self.x - other.x
        tiempo_para_alcanzar = distancia_actual / (self.v / 60)
        
        return tiempo_para_alcanzar > 5

    # actualizacion de la estimacion de llegada
    def time_to_arrive(self) -> None:
        lista_rangos = c.LISTA_RANGOS
        rango_anterior = 0
        tiempo_estimado = 0.0
        for rango_actual in lista_rangos:
            if self.x <= rango_actual:
                tiempo_estimado += u.tiempo_min_para_mn(self.v,rango_actual-rango_anterior)
                break
            # calculo el tiempo que tardo en completar un rango entero, como es no inclucibe el maximo de los rangos uso el rango anterior para calcular la velocidad max
            velocidad_de_ese_rango = u.velocidad_permitida(rango_anterior)[1]
            tiempo_estimado += u.tiempo_min_para_mn(velocidad_de_ese_rango,rango_actual)
            rango_anterior = rango_actual
        self.tiempo_estimado = tiempo_estimado

    # hace avanzar al avion, calcula nuevo rango y se fija si hay que desacelerar 
    def avanzar(self,other,third) -> None:
        
        if self.status == "aterrizaje_confirmado": # si ya aterizo no hago nada
            return

        if self.x <= self.v/60 * c.DT and self.status != "desviado": # si con este step llega al aeropuerto termina
            self.status = "intento_aterrizar"
            self.tiempo_estimado = 0
            return
        
        
        if self.status == "desviado": # si esta desviado retrocede en vez de avanzar y se fija si hay un gap de 10 min
            self.retroceder(other,third)
            return

        if self.status == "reinsercion": # si estaba reinsertando, vuelve a la fila
            self.status = "en_fila"
        
        rango_antes = self.rango_actual() # rango antes de avanzar
        self.x -= self.v/60 * c.DT # nueva posicion
        
        
        if rango_antes != self.rango_actual():# me fijo si entra en un nuevo rango
            if self.metering: # protocolo nuevo (ejercicio 7)
                self.v = u.clamp(self.v, self.min_speed(), self.max_speed())
            else:
                self.set_speed()
            
        if (other is not None and 
            other.status != "desviado" and 
            other.x < self.x and 
            self.distancia_menor_4(other)): # si esta a menos de 4 minutos de other, desacelera
            self.set_desacelerando(other)
            return

        elif (self.status == "desacelerando" and 
            (other is None or 
            other.x >= self.x or 
            other.status == "desviado" or 
            self.distancia_mayor_5(other))):   # verificasi puede dejar de desacelerar y volver a velocidad máxima
            self.set_speed()

        self.time_to_arrive()       
    
    # hace retroceder al avion desviado y evalua reinsercion
    def retroceder(self, other, third) -> None:

        self.x += (self.v / 60.0) * c.DT # nueva posición (se suma distancia porque se esta alejando del aeropuerto)

        if self.minutos_bloqueo > 0: # si hay bloqueo, se reduce el tiempo de bloqueo
            self.minutos_bloqueo = max(0, self.minutos_bloqueo - c.DT)
            return

        if other is not None and third is not None: # si hay avion de adelante y atras, se verifica si hay gap de 10 minutos
            distancia_gap = third.x - other.x  
            if distancia_gap >= (self.v / 60.0) * 10.0:
                punto_medio = other.x + distancia_gap / 2.0
                if other.x < self.x <= punto_medio and punto_medio > 5.0: # reinsertar si estoy antes del punto medio en el espacio entre los otros dos aviones
                    self.x = punto_medio
                    self.status = "reinsercion"
                    self.set_speed()
            return

        if other is not None and third is None: # si el gap es entre el ultimo avion y las 100 mn
            distancia_gap = 100.0 - other.x
            if distancia_gap >= (self.v / 60.0) * 10.0:
                punto_medio = other.x + distancia_gap / 2.0
                if other.x < self.x <= punto_medio and punto_medio > 5.0:
                    self.x = punto_medio
                    self.status = "reinsercion"
                    self.set_speed()
    
    # setea el avion como desacelerando
    def set_desacelerando(self,other) -> None:
        if other is None: # si no hay avion de adelante, no se puede ni se debe desacelerar
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
    
    #  funcion para desviar al avion
    def set_desviado(self) -> None:
        self.status = "desviado"
        self.v = 200
        self.tiempo_estimado = -1 # -1 porque no se puede calcular cuanto va a tardar
    
    # aplica micro-ajuste de velocidad vs STA si el protocolo nuevo (ejercicio 7) está activo.
    def apply_metering(self, now_min: int):
        if not self.metering or self.sta_meter is None:
            return
        if self.status in {"desviado", "aterrizado"}:
            return
        if self.x <= c.METER_POINT_MN:
            return

        eat = u.eta_const_speed_to_point(self.x, self.v, c.METER_POINT_MN, now_min)
        error_min = self.sta_meter - eat                     # >0: tarde, <0: temprano
        deadband_min = c.METER_DEADBAND_SEC / 60.0

        if error_min < -deadband_min:                        # va temprano -> bajar v
            new_v = self.v - c.METER_SPEED_STEP
            self.v = u.clamp(new_v, self.min_speed(), self.max_speed())
            if self.v < new_v + 1e-9:                        # bajó realmente
                self.status = "desacelerando"
        elif error_min > deadband_min:                       # va tarde -> subir v
            new_v = self.v + c.METER_SPEED_STEP
            self.v = u.clamp(new_v, self.min_speed(), self.max_speed())



