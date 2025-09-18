from dataclasses import dataclass
from typing import Literal, Optional, List
import numpy as np
import utilidades as u
import const as c
from plane import Plane

@dataclass
class simulacion:
    """clase principal para manejar la simulacion de monte carlo por dias"""
    lambda_param: float  # probabilidad de arribo por minuto
    dias_simulacion: int    # cantidad de dias a simular

    aviones: List[Plane] = None  # lista de aviones en el sistema
    tiempo_actual: int = 350       # tiempo actual de la simulacion en minutos
    aviones_aterrizados: List[Plane] = None  # aviones que ya aterrizaron
    aviones_desviados: List[Plane] = None    # aviones que se fueron a montevideo
    estadisticas: dict = None    # diccionario con estadisticas de la simulacion
    dia_actual: int = 1          # dia actual de la simulacion

    # Clima
    viento_activo: bool = False
    p_goaround: float = 0.10                       # prob go-around por viento (por intento de aterrizaje)
    storm_activa: bool = False                     # habilita tormentas
    storm_prob: float = 0.0                        # prob diaria de que haya tormenta
    storm_duracion_min: int = 30                   # duración de cada tormenta
    storm_inicio_min: Optional[int] = None         # inicio programado para el día actual (si hay)


    
    
    def __post_init__(self):
        """inicializa las listas vacias al crear la simulacion"""
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
                'congestiones': 0,
                'desvios_a_montevideo': 0,
                'dias_completados': 0,
                'desvios_viento': 0,
                'desvios_cierre': 0,
                'desvios_tormenta': 0,
                'reincerciones_exitosas': 0     
            }

        self._programar_tormenta_del_dia()

        # sistema de interpolacion para movimiento suave
        self.aviones_anterior = []  # posiciones anteriores para interpolacion
        self.frame_interpolacion = 0  # frame actual de interpolacion
        self.frames_por_paso = 8  # cuantos frames visuales por paso de simulacion



    def _motivo_cierre_actual(self, m: int) -> str | None:
        """Devuelve 'horario' si está fuera de [06:00,24:00), 'tormenta' si cae en la ventana activa, o None si abierto."""
        # Horario operativo: [06:00, 24:00)
        if not (360 <= m < 1440):
            return "horario"

        # Ventana de tormenta, si aplica
        if self.storm_activa and (self.storm_inicio_min is not None):
            start = int(self.storm_inicio_min) % 1440
            end   = (start + int(self.storm_duracion_min)) % 1440
            # ventana [start, end) con wrap-around
            if (start < end and start <= m < end) or (start >= end and (m >= start or m < end)):
                return "tormenta"

        return None  # abierto

    def _programar_tormenta_del_dia(self):
        """Decide si hay tormenta hoy y, si sí, elige inicio uniforme en [0, 1440 - dur]."""
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

    def esta_aeropuerto_abierto(self) -> bool:
        m = self.tiempo_actual % 1440
        return self._motivo_cierre_actual(m) is None
    
    

    def obtener_hora_actual(self) -> str:
        """retorna la hora actual en formato hh:mm"""
        minutos_en_dia = self.tiempo_actual % 1440
        horas = minutos_en_dia // 60
        minutos = minutos_en_dia % 60
        return f"{horas:02d}:{minutos:02d}"

    def obtener_dia_actual(self) -> int:
        """retorna el dia actual de la simulacion"""
        return (self.tiempo_actual // 1440) + 1

    def generar_nuevo_avion(self) -> bool:
        """Genera k~Poisson(lambda) aviones si el aeropuerto está abierto. 
        Devuelve True si generó al menos 1."""
        if not self.esta_aeropuerto_abierto():
            return False

        # k llegadas en este minuto (Poisson)
        k = int(np.random.poisson(self.lambda_param))
        for _ in range(k):
            nuevo_avion = Plane(
                id=self.estadisticas['total_aviones'],
                t_spawn=self.tiempo_actual,
                status="en_fila"
            )
            nuevo_avion.set_speed()  # si acá hay aleatoriedad, convendría migrarla también a NumPy
            self.aviones.append(nuevo_avion)
            self.estadisticas['total_aviones'] += 1

        return (k > 0)
    
    def _al_cambiar_de_dia(self) -> None:
        """Cierra el día actual y prepara el siguiente (tormenta nueva, contadores de día, etc.)."""
        # cerrar el día que termina
        self.estadisticas['dias_completados'] = self.estadisticas.get('dias_completados', 0) + 1

        # avanzar marcador de día
        self.dia_actual += 1

        # limpiar programación anterior de tormenta y reprogramar para el nuevo día
        self.storm_inicio_min = None
        self._programar_tormenta_del_dia()

    def ordenar_aviones_por_distancia(self):
        """ordena los aviones por distancia al aeropuerto (mas cerca primero)"""
        self.aviones.sort(key=lambda avion: avion.x, reverse=False)

    def _minutos_hasta_apertura(self) -> int:
        m = self.tiempo_actual % 1440  # minuto del día
        motivo = self._motivo_cierre_actual(m)

        if motivo == "horario":
            # reabre a las 06:00 (360). Si estamos entre 0–359, faltan (360 - m).
            # si cerró por pasar la medianoche, también cae en este caso.
            return (360 - m) % 1440

        if motivo == "tormenta":
            start = int(self.storm_inicio_min) % 1440
            end   = (start + int(self.storm_duracion_min)) % 1440
            if start < end:
                return max(0, end - m)
            # la tormenta cruza medianoche
            return (1440 - m) + end if m >= start else max(0, end - m)

        return 0 

    def procesar_paso_temporal(self):
        """procesa un paso temporal de la simulacion"""
        # generar nuevo avion si corresponde
        self.generar_nuevo_avion()
        
        # ordenar aviones por distancia
        self.ordenar_aviones_por_distancia()
        
        # procesar cada avion
        aviones_a_remover = []
        for i, avion in enumerate(self.aviones):
            # determinar aviones adyacentes
            # como los aviones estan ordenados por distancia (mas cerca primero), 
            # el avion de adelante es el que tiene indice menor (i-1)
            # el avion de atras es el que tiene indice mayor (i+1)
            avion_adelante = self.aviones[i-1] if i > 0 else None
            avion_atras = self.aviones[i+1] if i < len(self.aviones)-1 else None
            
            # hacer avanzar el avion
            avion.avanzar(avion_adelante, avion_atras)


            # verificar si aterrizo
            if avion.status == "Intento Aterrizar":
                m = self.tiempo_actual % 1440
                motivo_cierre = self._motivo_cierre_actual(m)
                if motivo_cierre is not None:
                    # NO puede aterrizar: forzá escape y contá por motivo
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
                    avion.status = "Aterrizage conf"
                    
            # verificar si se desvio a montevideo (sale de las 100mn)
            elif avion.x > 100.0 and avion.status == "desviado":
                aviones_a_remover.append(avion)
                self.aviones_desviados.append(avion)
                self.estadisticas['desviados'] += 1
                self.estadisticas['desvios_a_montevideo'] += 1
        
        # remover aviones que ya no estan en el sistema
        for avion in aviones_a_remover:
            self.aviones.remove(avion)

        prev_day_idx = int(self.tiempo_actual // 1440)
        
        # incrementar tiempo
        self.tiempo_actual += c.DT

        new_day_idx = int(self.tiempo_actual // 1440)
        
        days_crossed = max(0, new_day_idx - prev_day_idx)
        for _ in range(days_crossed):
            self._al_cambiar_de_dia()
        # actualizar dia actual

    def ejecutar_simulacion_completa(self):
        """ejecuta la simulacion completa desde el inicio hasta el final"""
        print(f"iniciando simulacion con lambda={self.lambda_param}")
        print(f"dias a simular: {self.dias_simulacion}")
        
        tiempo_total_minutos = self.dias_simulacion * 1440
        
        while self.tiempo_actual < tiempo_total_minutos:
            self.procesar_paso_temporal()
            
            # mostrar progreso cada dia
            if self.tiempo_actual % 1440 == 0 and self.tiempo_actual > 0:
                dia_completado = self.tiempo_actual // 1440
                print(f"dia {dia_completado} completado, aviones activos: {len(self.aviones)}")
        
        # calcular estadisticas finales
        self.calcular_estadisticas_finales()
        print("simulacion completada!")

    def calcular_estadisticas_finales(self):
        """calcula las estadisticas finales de la simulacion"""
        if self.estadisticas['aterrizados'] > 0:
            tiempos_aterrizaje = []
            for avion in self.aviones_aterrizados:
                tiempo_vuelo = avion.tiempo_estimado if avion.tiempo_estimado is not None else 0
                tiempos_aterrizaje.append(tiempo_vuelo)
            
            self.estadisticas['tiempo_promedio_aterrizaje'] = np.mean(tiempos_aterrizaje)
        
        self.estadisticas['dias_completados'] = self.dias_simulacion

    def obtener_estadisticas(self) -> dict:
        """retorna un diccionario con las estadisticas de la simulacion"""
        return self.estadisticas.copy()

    def reiniciar_simulacion(self):
        """reinicia la simulacion a su estado inicial"""
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
            'congestiones': 0,
            'desvios_a_montevideo': 0,
            'dias_completados': 0
        }

def ejecutar_multiples_simulaciones(lambda_param: float,
                                    dias_simulacion: int,
                                    num_simulaciones: int = 10,
                                    viento_activo: bool = False,
                                    p_goaround: float = 0.10,
                                    storm_activa: bool = False,
                                    storm_prob: float = 0.0,
                                    storm_duracion_min: int = 30) -> dict:
    """ejecuta multiples simulaciones y retorna estadisticas promedio"""
    print(f"ejecutando {num_simulaciones} simulaciones con lambda={lambda_param}")
    
    estadisticas_totales = {
        'total_aviones': [],
        'aterrizados': [],
        'desviados': [],
        'tiempo_promedio_aterrizaje': [],
        'congestiones': [],
        'desvios_a_montevideo': [],
        'desvios_viento': [],
        'desvios_tormenta': [],
        'desvios_cierre': []
    }
    
    for i in range(num_simulaciones):
        print(f"simulacion {i+1}/{num_simulaciones}")
        sim = simulacion(
            lambda_param=lambda_param,
            dias_simulacion=dias_simulacion,
            viento_activo=viento_activo,
            p_goaround=p_goaround,
            storm_activa=storm_activa,
            storm_prob=storm_prob,
            storm_duracion_min=storm_duracion_min
        )
        sim.ejecutar_simulacion_completa()
        
        stats = sim.obtener_estadisticas()
        for key in estadisticas_totales:
            estadisticas_totales[key].append(stats[key])
    
    # calcular promedios y errores
    estadisticas_promedio = {}
    for key, valores in estadisticas_totales.items():
        estadisticas_promedio[key] = {
            'promedio': np.mean(valores),
            'error_estandar': np.std(valores) / np.sqrt(len(valores)),
            'valores': valores
        }
    
    return estadisticas_promedio

def estimar_probabilidad_5_aviones_en_1_hora(lambda_param: float, num_simulaciones: int = 1000) -> dict:
    """Estima P{X=5} en 1 hora con X~Poisson(lambda_param*60)."""
    print(f"estimando probabilidad de 5 aviones en 1 hora con lambda={lambda_param}")

    # tasa por hora:
    lambda_60 = lambda_param * 60.0

    # simulación vectorizada: num_simulaciones horas
    conteos_por_hora = np.random.poisson(lam=lambda_60, size=num_simulaciones)

    # prob simulada de exactamente 5
    probabilidad_simulada = float(np.mean(conteos_por_hora == 5))

    # prob teórica Poisson
    probabilidad_teorica = (lambda_60**5 * np.exp(-lambda_60)) / np.math.factorial(5)

    # error relativo (cuida división por cero por si lambda_60=0)
    if probabilidad_teorica > 0:
        error_relativo = abs(probabilidad_simulada - probabilidad_teorica) / probabilidad_teorica
    else:
        error_relativo = 0.0 if probabilidad_simulada == 0.0 else float('inf')

    return {
        'probabilidad_simulada': probabilidad_simulada,
        'probabilidad_teorica': probabilidad_teorica,
        'error_relativo': error_relativo,
        'conteos_por_hora': conteos_por_hora.tolist(),  # si preferís list en vez de array
    }