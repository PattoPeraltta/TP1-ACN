from dataclasses import dataclass
from typing import Literal, Optional, List
import numpy as np
import random
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
                'go_arounds_viento': 0,
                'desviados_tormenta': 0,
                'reincerciones_exitosas': 0              
            }

        # sistema de interpolacion para movimiento suave
        self.aviones_anterior = []  # posiciones anteriores para interpolacion
        self.frame_interpolacion = 0  # frame actual de interpolacion
        self.frames_por_paso = 8  # cuantos frames visuales por paso de simulacion

        # Clima
        self.viento_activo: bool = False
        self.p_goaround: float = 0.10
        self.storm_activa: bool = False
        self.storm_inicio_min: int | None = None
        self.storm_duracion_min: int = 30

    def esta_aeropuerto_abierto(self) -> bool:
        m = self.tiempo_actual % 1440  # minuto del día

        # Horario operativo: [06:00, 24:00)
        if not (360 <= m < 1440):
            return False

        # Cierre por tormenta (solo si está activa y se definió inicio)
        if self.storm_activa and self.storm_inicio_min is not None:
            start = self.storm_inicio_min % 1440
            end   = (start + int(self.storm_duracion_min)) % 1440

            if start < end:
                if start <= m < end:
                    return False
            else:  # cruza medianoche
                if (m >= start) or (m < end):
                    return False

        return True

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
        """genera un nuevo avion con probabilidad lambda si el aeropuerto esta abierto"""
        if self.esta_aeropuerto_abierto():
            if random.random() < self.lambda_param:
                nuevo_avion = Plane(
                    id=self.estadisticas['total_aviones'],
                    t_spawn=self.tiempo_actual,
                    x=100.0,  # aparece a 100 mn
                    v=0.0,
                    status="en_fila"
                )
                # setear velocidad inicial aleatoria
                nuevo_avion.set_speed()
                self.aviones.append(nuevo_avion)
                self.estadisticas['total_aviones'] += 1
                return True
        return False
    


    def ordenar_aviones_por_distancia(self):
        """ordena los aviones por distancia al aeropuerto (mas cerca primero)"""
        self.aviones.sort(key=lambda avion: avion.x, reverse=False)

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
            
            status_prev = avion.status
            x_prev = avion.x
            # hacer avanzar el avion
            avion.step(avion_adelante, avion_atras)
            
            # verificar si aterrizo
            if avion.status == "aterrizado":
                if not self.esta_aeropuerto_abierto():
                    avion.set_desviado()
                    avion.motivo_desvio = "tormenta"
                    self.estadisticas["go_arounds_tormenta"] += 1
                elif self.viento_activo and np.random.binomial(1, self.p_goaround) == 1:
                    avion.set_desviado()
                    avion.motivo_desvio = "viento"
                    self.estadisticas["go_arounds_viento"] += 1
                else:
                    aviones_a_remover.append(avion)
                    self.aviones_aterrizados.append(avion)
                    self.estadisticas['aterrizados'] += 1
                    
            # verificar si se desvio a montevideo (sale de las 100mn)
            elif avion.x > 100.0 and avion.status == "desviado":
                aviones_a_remover.append(avion)
                self.aviones_desviados.append(avion)
                self.estadisticas['desviados'] += 1
                self.estadisticas['desvios_a_montevideo'] += 1
        
        # remover aviones que ya no estan en el sistema
        for avion in aviones_a_remover:
            self.aviones.remove(avion)
        
        # incrementar tiempo
        self.tiempo_actual += c.DT
        
        # actualizar dia actual
        self.dia_actual = self.obtener_dia_actual()

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

def ejecutar_multiples_simulaciones(lambda_param: float, dias_simulacion: int, num_simulaciones: int = 10) -> dict:
    """ejecuta multiples simulaciones y retorna estadisticas promedio"""
    print(f"ejecutando {num_simulaciones} simulaciones con lambda={lambda_param}")
    
    estadisticas_totales = {
        'total_aviones': [],
        'aterrizados': [],
        'desviados': [],
        'tiempo_promedio_aterrizaje': [],
        'congestiones': [],
        'desvios_a_montevideo': []
    }
    
    for i in range(num_simulaciones):
        print(f"simulacion {i+1}/{num_simulaciones}")
        sim = simulacion(lambda_param=lambda_param, dias_simulacion=dias_simulacion)
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
    """estima la probabilidad de que lleguen 5 aviones en una hora"""
    print(f"estimando probabilidad de 5 aviones en 1 hora con lambda={lambda_param}")
    
    conteos_por_hora = []
    
    for sim_num in range(num_simulaciones):
        # simular 1 hora (60 minutos)
        aviones_en_hora = 0
        for minuto in range(60):
            if random.random() < lambda_param:
                aviones_en_hora += 1
        
        conteos_por_hora.append(aviones_en_hora)
    
    # calcular probabilidad de exactamente 5 aviones
    aviones_5 = sum(1 for count in conteos_por_hora if count == 5)
    probabilidad_5 = aviones_5 / num_simulaciones
    
    # calcular probabilidad teorica (distribucion de poisson)
    # p(x=5) = (lambda*60)^5 * e^(-lambda*60) / 5!
    lambda_60 = lambda_param * 60
    probabilidad_teorica = (lambda_60**5 * np.exp(-lambda_60)) / np.math.factorial(5)
    
    return {
        'probabilidad_simulada': probabilidad_5,
        'probabilidad_teorica': probabilidad_teorica,
        'error_relativo': abs(probabilidad_5 - probabilidad_teorica) / probabilidad_teorica,
        'conteos_por_hora': conteos_por_hora
    }
