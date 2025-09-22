from dataclasses import dataclass
from typing import Literal, Optional, List
import numpy as np
import utilidades as u
import const as c
from plane import Plane

@dataclass
# clase principal para manejar la simulacion de monte carlo por dias
class Simulacion:
    lambda_param: float  # probabilidad de arribo por minuto
    dias_simulacion: int    # cantidad de dias a simular

    aviones: List[Plane] = None  # lista de aviones en el sistema
    tiempo_actual: int = 350       # tiempo actual de la simulacion en minutos
    aviones_aterrizados: List[Plane] = None  # aviones que ya aterrizaron
    aviones_desviados: List[Plane] = None    # aviones que se fueron a montevideo
    estadisticas: dict = None    # diccionario con estadisticas de la simulacion
    dia_actual: int = 1          # dia actual de la simulacion

    viento_activo: bool = False
    p_goaround: float = 0.10                       # prob go-around por viento (por intento de aterrizaje)
    storm_activa: bool = False                     # habilita tormentas
    storm_prob: float = 0.0                        # prob diaria de que haya tormenta
    storm_duracion_min: int = 30                   # duración de cada tormenta
    storm_inicio_min: Optional[int] = None         # inicio programado para el día actual (si hay)

    enable_metering: bool = False
    _last_sta_meter: Optional[float] = None
    
    # inicializa las listas vacias al crear la simulacion
    def __post_init__(self) -> None:
        if self.aviones is None:
            self.aviones = []
        if self.aviones_aterrizados is None:
            self.aviones_aterrizados = []
        if self.aviones_desviados is None:
            self.aviones_desviados = []
        if self.estadisticas is None:
            self.estadisticas = {
                'total_aviones': 0,
                'aterrizados': 0,
                'desviados': 0,
                'tiempo_promedio_aterrizaje': 0,
                'desvios_a_montevideo': 0,
                'dias_completados': 0,
                'desvios_viento': 0,
                'desvios_cierre': 0,
                'desvios_tormenta': 0,
                'reincerciones_exitosas': 0     
            }

        self._programar_tormenta_del_dia()

    # devuelve 'horario' si está fuera de [06:00,24:00), 'tormenta' si cae en la ventana activa, o None si abierto
    def _motivo_cierre_actual(self, m: int) -> str | None:
        if not (360 <= m < 1440): # horario operativo: [06:00, 24:00)
            return "horario"

        if self.storm_activa and (self.storm_inicio_min is not None): # ventana de tormenta, si aplica
            start = int(self.storm_inicio_min) % 1440
            end   = (start + int(self.storm_duracion_min)) % 1440
            if (start < end and start <= m < end) or (start >= end and (m >= start or m < end)): # ventana [start, end) con wrap-around
                return "tormenta"

        return None  # abierto

    # decide si hay tormenta hoy y, si sí, elige inicio uniforme en [0, 1440 - dur]
    def _programar_tormenta_del_dia(self) -> None:
        if not self.storm_activa or self.storm_prob <= 0.0:
            self.storm_inicio_min = None
            return
        
        prob = self.storm_prob
        has_storm = np.random.binomial(1, prob)
        if has_storm == 1:
            max_ini = max(0, 1440 - self.storm_duracion_min)
            self.storm_inicio_min = int(np.random.uniform(0, max_ini + 1))
        else:
            self.storm_inicio_min = None

    # retorna True si el aeropuerto está abierto
    def esta_aeropuerto_abierto(self) -> bool:
        m = self.tiempo_actual % 1440
        return self._motivo_cierre_actual(m) is None
    
    # retorna la hora actual en formato hh:mm
    def obtener_hora_actual(self) -> str:
        minutos_en_dia = self.tiempo_actual % 1440
        horas = minutos_en_dia // 60
        minutos = minutos_en_dia % 60
        return f"{horas:02d}:{minutos:02d}"

    # retorna el dia actual de la simulacion
    def obtener_dia_actual(self) -> int:
        return (self.tiempo_actual // 1440) + 1

    # genera k~poisson(lambda) aviones si el aeropuerto está abierto, devuelve true si generó al menos 1
    def generar_nuevo_avion(self) -> bool:
        m = self.tiempo_actual % 1440
        if not self.esta_aeropuerto_abierto() and self._motivo_cierre_actual(m) != "tormenta":
            return False

        k = int(np.random.poisson(self.lambda_param)) # k llegadas en este minuto (poisson)
        for _ in range(k):
            nuevo_avion = Plane(
                id=self.estadisticas['total_aviones'],
                t_spawn=self.tiempo_actual,
                status="en_fila"
            )
            nuevo_avion.set_speed()

            self._asignar_sta_meter(nuevo_avion)

            self.aviones.append(nuevo_avion)
            self.estadisticas['total_aviones'] += 1

        return (k > 0)
    
    # cierra el día actual y prepara el siguiente (tormenta nueva, contadores de día, etc.)
    def _al_cambiar_de_dia(self) -> None:
        self.estadisticas['dias_completados'] = self.estadisticas.get('dias_completados', 0) + 1

        self.dia_actual += 1 # avanzar marcador de día

        self.storm_inicio_min = None # limpiar programación anterior de tormenta y reprogramar para el nuevo día
        self._programar_tormenta_del_dia()

        self._last_sta_meter = None

    # ordena los aviones por distancia al aeropuerto (mas cerca primero)
    def ordenar_aviones_por_distancia(self) -> None:
        self.aviones.sort(key=lambda avion: avion.x, reverse=False)

    # retorna la cantidad de minutos hasta que se reabra el aeropuerto
    def _minutos_hasta_apertura(self) -> int:
        m = self.tiempo_actual % 1440  # minuto del día
        motivo = self._motivo_cierre_actual(m)

        if motivo == "horario": # reabre a las 06:00 (360), si estamos entre 0–359, faltan (360 - m)
            return (360 - m) % 1440

        if motivo == "tormenta":
            start = int(self.storm_inicio_min) % 1440
            end   = (start + int(self.storm_duracion_min)) % 1440
            if start < end:
                return max(0, end - m)
            return (1440 - m) + end if m >= start else max(0, end - m) # la tormenta cruza medianoche

        return 0 

    # procesa un paso temporal de la simulacion
    def procesar_paso_temporal(self) -> None:
        m_actual = self.tiempo_actual % 1440
        motivo_ahora = self._motivo_cierre_actual(m_actual)
        motivo_antes = self._motivo_cierre_actual((m_actual - c.DT) % 1440)
        self.generar_nuevo_avion()
        if motivo_ahora == "tormenta" and motivo_antes != "tormenta": # veo si hay tormenta y hago que todos los aviones vuelvan
            minutos_bloqueo = self._minutos_hasta_apertura()
            for avion in self.aviones:
                if avion.status in ("en_fila", "desacelerando", "reinsercion"):
                    avion.set_desviado()
                    avion.minutos_bloqueo = minutos_bloqueo  # bloquear reinserción hasta que abra
                    self.estadisticas["desvios_tormenta"] += 1
        
        self.ordenar_aviones_por_distancia() # ordenar aviones por distancia
        
        aviones_a_remover = []
        for i, avion in enumerate(self.aviones):
            # determinar aviones adyacentes: como los aviones estan ordenados por distancia (mas cerca primero), 
            # el avion de adelante es el que tiene indice menor (i-1), el avion de atras es el que tiene indice mayor (i+1)
            avion_adelante = self.aviones[i-1] if i > 0 else None
            avion_atras = self.aviones[i+1] if i < len(self.aviones)-1 else None

            if self.enable_metering:
                avion.apply_metering(self.tiempo_actual)
            
            status_antes = avion.status
            avion.avanzar(avion_adelante, avion_atras) # hacer avanzar el avion
            
            if status_antes == "reinsercion" and avion.status == "en_fila": # verificar si hubo una reinsercion exitosa
                self.estadisticas['reincerciones_exitosas'] += 1

            if avion.status == "intento_aterrizar": # verificar si aterrizo
                m = self.tiempo_actual % 1440
                motivo_cierre = self._motivo_cierre_actual(m)
                if motivo_cierre is not None: # no puede aterrizar: forzá escape y contá por motivo
                    avion.set_desviado()
                    avion.minutos_bloqueo = self._minutos_hasta_apertura()

                    if motivo_cierre == "tormenta":
                        self.estadisticas["desvios_tormenta"] += 1
                    else:  # "horario"
                        self.estadisticas["desvios_cierre"] += 1

                elif self.viento_activo and np.random.binomial(1, self.p_goaround) == 1:
                    avion.set_desviado()
                    self.estadisticas["desvios_viento"] += 1
                else:
                    aviones_a_remover.append(avion)
                    self.aviones_aterrizados.append(avion)
                    self.estadisticas['aterrizados'] += 1
                    avion.status = "aterrizaje_confirmado"
                    avion.t_landing = self.tiempo_actual  # registrar el tiempo de aterrizaje
                    
            elif avion.x > 100.0 and avion.status == "desviado": # verificar si se desvio a montevideo (sale de las 100mn)
                aviones_a_remover.append(avion)
                self.aviones_desviados.append(avion)
                self.estadisticas['desviados'] += 1
                self.estadisticas['desvios_a_montevideo'] += 1
        
        for avion in aviones_a_remover: # remover aviones que ya no estan en el sistema
            self.aviones.remove(avion)

        prev_day_idx = int(self.tiempo_actual // 1440)
        
        self.tiempo_actual += c.DT # incrementar tiempo

        new_day_idx = int(self.tiempo_actual // 1440)
        
        days_crossed = max(0, new_day_idx - prev_day_idx)
        for _ in range(days_crossed):
            self._al_cambiar_de_dia()

    # ejecuta la simulacion completa desde el inicio hasta el final
    def ejecutar_simulacion_completa(self) -> None:
        print(f"iniciando simulacion con lambda={self.lambda_param}")
        print(f"dias a simular: {self.dias_simulacion}")
        
        tiempo_total_minutos = self.dias_simulacion * 1440
        
        while self.tiempo_actual < tiempo_total_minutos:
            self.procesar_paso_temporal()
            
            if self.tiempo_actual % 1440 == 0 and self.tiempo_actual > 0: # mostrar progreso cada dia
                dia_completado = self.tiempo_actual // 1440
                print(f"dia {dia_completado} completado, aviones activos: {len(self.aviones)}")
        
        self.calcular_estadisticas_finales() # calcular estadisticas finales

    # calcula las estadisticas finales de la simulacion
    def calcular_estadisticas_finales(self) -> None:
        if self.estadisticas['aterrizados'] > 0:
            tiempos_aterrizaje = []
            for avion in self.aviones_aterrizados:
                tiempo_vuelo = avion.tiempo_total_vuelo() # usar el tiempo real de vuelo (t_landing - t_spawn) en lugar de tiempo_estimado
                if tiempo_vuelo is not None:
                    tiempos_aterrizaje.append(tiempo_vuelo)
            
            if tiempos_aterrizaje:  # verificar que hay tiempos válidos
                self.estadisticas['tiempo_promedio_aterrizaje'] = np.mean(tiempos_aterrizaje)
            else:
                self.estadisticas['tiempo_promedio_aterrizaje'] = 0
        else:
            self.estadisticas['tiempo_promedio_aterrizaje'] = 0 # si no hay aviones aterrizados, el promedio es 0
        
        self.estadisticas['dias_completados'] = self.dias_simulacion

    # retorna un diccionario con las estadisticas de la simulacion
    def obtener_estadisticas(self) -> dict:
        return self.estadisticas.copy()
    
    # retorna una lista con los tiempos totales de vuelo de todos los aviones que aterrizaron
    def obtener_tiempos_aterrizaje(self) -> List[int]:
        tiempos = []
        for avion in self.aviones_aterrizados:
            tiempo_vuelo = avion.tiempo_total_vuelo()
            if tiempo_vuelo is not None:
                tiempos.append(tiempo_vuelo)
        return tiempos
    
    # retorna una lista de diccionarios con detalles de cada aterrizaje
    def obtener_detalles_aterrizajes(self) -> List[dict]:
        detalles = []
        for avion in self.aviones_aterrizados:
            tiempo_vuelo = avion.tiempo_total_vuelo()
            if tiempo_vuelo is not None:
                detalles.append({
                    'id': avion.id,
                    't_spawn': avion.t_spawn,
                    't_landing': avion.t_landing,
                    'tiempo_total_vuelo': tiempo_vuelo
                })
        return detalles

    # reinicia la simulacion a su estado inicial
    def reiniciar_simulacion(self) -> None:
        self.aviones = []
        self.aviones_aterrizados = []
        self.aviones_desviados = []
        self.tiempo_actual = 0
        self.dia_actual = 1
        self.estadisticas = {
            'total_aviones': 0,
            'aterrizados': 0,
            'desviados': 0,
            'tiempo_promedio_aterrizaje': 0,
            'desvios_a_montevideo': 0,
            'dias_completados': 0,
            'desvios_viento': 0,
            'desvios_cierre': 0,
            'desvios_tormenta': 0,
            'reincerciones_exitosas': 0     
        }
    
    # define sta al meter point respetando la separación objetivo
    def _asignar_sta_meter(self, avion: Plane):
        if not self.enable_metering:
            return
        if avion.x <= c.METER_POINT_MN:
            avion.metering = False
            avion.sta_meter = None
            return

        tmin = u.tiempo_min_vmax_a_punto(avion.x, c.METER_POINT_MN)
        sta_cand = self.tiempo_actual + tmin

        if self._last_sta_meter is None:
            sta = sta_cand
        else:
            sta = max(sta_cand, self._last_sta_meter + c.METER_TARGET_SPACING_MIN)

        avion.sta_meter = sta
        avion.metering  = True
        self._last_sta_meter = sta

# ejecuta multiples simulaciones y retorna estadisticas promedio
def ejecutar_multiples_simulaciones(lambda_param: float,
                                    dias_simulacion: int,
                                    num_simulaciones: int = 10,
                                    viento_activo: bool = False,
                                    p_goaround: float = 0.10,
                                    storm_activa: bool = False,
                                    storm_prob: float = 0.0,
                                    storm_duracion_min: int = 30,
                                    enable_metering:bool = False) -> dict:
    print(f"ejecutando {num_simulaciones} simulaciones con lambda={lambda_param}")
    
    estadisticas_totales = {
        'total_aviones': [],
        'aterrizados': [],
        'desviados': [],
        'tiempo_promedio_aterrizaje': [],
        'desvios_a_montevideo': [],
        'desvios_viento': [],
        'desvios_tormenta': [],
        'desvios_cierre': [],
        'reincerciones_exitosas': []
    }
    
    for i in range(num_simulaciones):
        print(f"simulacion {i+1}/{num_simulaciones}")
        sim = Simulacion(
            lambda_param=lambda_param,
            dias_simulacion=dias_simulacion,
            viento_activo=viento_activo,
            p_goaround=p_goaround,
            storm_activa=storm_activa,
            storm_prob=storm_prob,
            storm_duracion_min=storm_duracion_min,
            enable_metering=enable_metering
        )
        sim.ejecutar_simulacion_completa()
        
        stats = sim.obtener_estadisticas()
        for key in estadisticas_totales:
            estadisticas_totales[key].append(stats[key])
    
    estadisticas_promedio = {} # calcular promedios y errores
    for key, valores in estadisticas_totales.items():
        estadisticas_promedio[key] = {
            'promedio': np.mean(valores),
            'error_estandar': np.std(valores) / np.sqrt(len(valores)),
            'valores': valores
        }
    
    return estadisticas_promedio

# estima p{x=5} en 1 hora con x~poisson(lambda_param*60)
def estimar_probabilidad_5_aviones_en_1_hora(lambda_param: float, num_simulaciones: int = 1000) -> dict:
    print(f"estimando probabilidad de 5 aviones en 1 hora con lambda={lambda_param}")

    lambda_60 = lambda_param * 60.0 # tasa por hora

    conteos_por_hora = np.random.poisson(lam=lambda_60, size=num_simulaciones) # simulación vectorizada: num_simulaciones horas

    probabilidad_simulada = float(np.mean(conteos_por_hora == 5)) # prob simulada de exactamente 5

    import math
    probabilidad_teorica = (lambda_60**5 * np.exp(-lambda_60)) / math.factorial(5) # prob teórica poisson

    if probabilidad_teorica > 0: # error relativo (cuida división por cero por si lambda_60=0)
        error_relativo = abs(probabilidad_simulada - probabilidad_teorica) / probabilidad_teorica
    else:
        error_relativo = 0.0 if probabilidad_simulada == 0.0 else float('inf')

    return {
        'probabilidad_simulada': probabilidad_simulada,
        'probabilidad_teorica': probabilidad_teorica,
        'error_relativo': error_relativo,
        'conteos_por_hora': conteos_por_hora.tolist(),
    }