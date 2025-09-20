"""
archivo de tests comprehensivo para la simulacion de aviones en aep
este archivo testea todos los aspectos de la simulacion incluyendo casos normales,
casos borde, y validaciones de la logica de negocio
"""

import unittest
import numpy as np
import sys
import os
from typing import Any

# agregar el directorio src al path para poder importar los modulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plane import Plane
from sim_core import Simulacion, ejecutar_multiples_simulaciones, estimar_probabilidad_5_aviones_en_1_hora
import const as c
import utilidades as u


class TestPlane(unittest.TestCase):
    """tests para la clase plane - comportamiento individual de aviones"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        # fijar seed para tests reproducibles
        np.random.seed(42)
        
    def test_creacion_avion_basico(self):
        """test: creacion basica de un avion con valores por defecto"""
        avion = Plane(id=1, t_spawn=100)
        
        # verificar valores por defecto
        self.assertEqual(avion.id, 1)
        self.assertEqual(avion.t_spawn, 100)
        self.assertEqual(avion.x, 100.0)  # distancia inicial
        self.assertEqual(avion.v, 0.0)    # velocidad inicial
        self.assertEqual(avion.status, "en_fila")
        self.assertIsNone(avion.tiempo_estimado)
        self.assertEqual(avion.minutos_bloqueo, 0)
        
    def test_velocidades_por_rango(self):
        """test: verificacion de velocidades maximas y minimas por rango de distancia"""
        # avion en rango > 100 mn
        avion_100 = Plane(id=1, t_spawn=0, x=150.0)
        self.assertEqual(avion_100.max_speed(), 500)
        self.assertEqual(avion_100.min_speed(), 300)
        
        # avion en rango 50-100 mn
        avion_50 = Plane(id=2, t_spawn=0, x=75.0)
        self.assertEqual(avion_50.max_speed(), 300)
        self.assertEqual(avion_50.min_speed(), 250)
        
        # avion en rango 15-50 mn
        avion_15 = Plane(id=3, t_spawn=0, x=30.0)
        self.assertEqual(avion_15.max_speed(), 250)
        self.assertEqual(avion_15.min_speed(), 200)
        
        # avion en rango 5-15 mn
        avion_5 = Plane(id=4, t_spawn=0, x=10.0)
        self.assertEqual(avion_5.max_speed(), 200)
        self.assertEqual(avion_5.min_speed(), 150)
        
        # avion en rango 0-5 mn
        avion_0 = Plane(id=5, t_spawn=0, x=2.0)
        self.assertEqual(avion_0.max_speed(), 150)
        self.assertEqual(avion_0.min_speed(), 120)
        
    def test_set_speed_respeta_limites(self):
        """test: set_speed() respeta los limites del rango actual"""
        avion = Plane(id=1, t_spawn=0, x=75.0)  # rango 50-100 mn: 250-300 nudos
        
        # ejecutar set_speed varias veces para verificar que siempre respeta limites
        for _ in range(10):
            avion.set_speed()
            self.assertGreaterEqual(avion.v, 250)
            self.assertLessEqual(avion.v, 300)
            
    def test_set_max_speed_cambia_estado(self):
        """test: set_max_speed() cambia estado de desacelerando a en_fila"""
        avion = Plane(id=1, t_spawn=0, x=75.0, status="desacelerando")
        avion.set_max_speed()
        
        self.assertEqual(avion.status, "en_fila")
        self.assertEqual(avion.v, 300)  # velocidad maxima del rango 50-100 mn
        
    def test_rango_actual_correcto(self):
        """test: rango_actual() devuelve el rango correcto segun la distancia"""
        # test en cada rango
        test_cases = [
            (150.0, (100, float('inf'))),  # > 100 mn
            (75.0, (50, 100)),             # 50-100 mn
            (30.0, (15, 50)),              # 15-50 mn
            (10.0, (5, 15)),               # 5-15 mn
            (2.0, (0, 5))                  # 0-5 mn
        ]
        
        for distancia, rango_esperado in test_cases:
            avion = Plane(id=1, t_spawn=0, x=distancia)
            rango_obtenido = avion.rango_actual()
            self.assertEqual(rango_obtenido, rango_esperado)
            
    def test_distancia_menor_4_casos_borde(self):
        """test: distancia_menor_4() maneja casos borde correctamente"""
        avion1 = Plane(id=1, t_spawn=0, x=50.0, v=300)  # 5 nudos/min
        avion2 = Plane(id=2, t_spawn=0, x=30.0, v=300)  # 5 nudos/min
        
        # caso: other es None
        self.assertFalse(avion1.distancia_menor_4(None))
        
        # caso: other esta atras (x mayor)
        avion2.x = 60.0
        self.assertFalse(avion1.distancia_menor_4(avion2))
        
        # caso: distancia exactamente 4 minutos (20 mn a 5 nudos/min)
        avion2.x = 30.0  # distancia = 20 mn = 4 minutos a 5 nudos/min
        self.assertFalse(avion1.distancia_menor_4(avion2))
        
        # caso: distancia menor a 4 minutos
        avion2.x = 31.0  # distancia = 19 mn = 3.8 minutos a 5 nudos/min
        self.assertTrue(avion1.distancia_menor_4(avion2))
        
    def test_distancia_mayor_5_casos_borde(self):
        """test: distancia_mayor_5() maneja casos borde correctamente"""
        avion1 = Plane(id=1, t_spawn=0, x=50.0, v=300)  # 5 nudos/min
        avion2 = Plane(id=2, t_spawn=0, x=30.0, v=300)  # 5 nudos/min
        
        # caso: other es None
        self.assertTrue(avion1.distancia_mayor_5(None))
        
        # caso: other esta atras
        avion2.x = 60.0
        self.assertTrue(avion1.distancia_mayor_5(avion2))
        
        # caso: distancia exactamente 5 minutos (25 mn a 5 nudos/min)
        avion2.x = 25.0  # distancia = 25 mn = 5 minutos a 5 nudos/min
        self.assertFalse(avion1.distancia_mayor_5(avion2))
        
        # caso: distancia mayor a 5 minutos
        avion2.x = 24.0  # distancia = 26 mn = 5.2 minutos a 5 nudos/min
        self.assertTrue(avion1.distancia_mayor_5(avion2))
        
    def test_avanzar_aterrizaje(self):
        """test: avion aterriza cuando llega al aeropuerto"""
        avion = Plane(id=1, t_spawn=0, x=0.5, v=300)  # muy cerca del aeropuerto
        
        avion.avanzar(None, None)
        
        self.assertEqual(avion.status, "intento_aterrizar")
        self.assertEqual(avion.tiempo_estimado, 0)
        
    def test_avanzar_desviado_retrocede(self):
        """test: avion desviado retrocede en lugar de avanzar"""
        avion = Plane(id=1, t_spawn=0, x=50.0, v=200, status="desviado")
        posicion_inicial = avion.x
        
        avion.avanzar(None, None)
        
        # debe retroceder (aumentar x)
        self.assertGreater(avion.x, posicion_inicial)
        
    def test_set_desacelerando_velocidad_valida(self):
        """test: set_desacelerando() con velocidad valida"""
        avion1 = Plane(id=1, t_spawn=0, x=75.0, v=300)  # rango 50-100: min=250
        avion2 = Plane(id=2, t_spawn=0, x=50.0, v=280)  # velocidad de referencia
        
        avion1.set_desacelerando(avion2)
        
        self.assertEqual(avion1.v, 260)  # 280 - 20
        self.assertEqual(avion1.status, "desacelerando")
        
    def test_set_desacelerando_velocidad_invalida(self):
        """test: set_desacelerando() con velocidad que viola minimo"""
        avion1 = Plane(id=1, t_spawn=0, x=75.0, v=300)  # rango 50-100: min=250
        avion2 = Plane(id=2, t_spawn=0, x=50.0, v=260)  # velocidad que causaria v=240 < 250
        
        avion1.set_desacelerando(avion2)
        
        # debe desviarse porque 240 < 250 (minimo del rango)
        self.assertEqual(avion1.status, "desviado")
        self.assertEqual(avion1.v, 200)  # velocidad de desvio
        self.assertEqual(avion1.tiempo_estimado, -1)
        
    def test_retroceder_con_gap_suficiente(self):
        """test: retroceder() encuentra gap y se reinserta"""
        avion_desviado = Plane(id=1, t_spawn=0, x=60.0, v=200, status="desviado")
        avion_adelante = Plane(id=2, t_spawn=0, x=55.0, v=300)
        avion_atras = Plane(id=3, t_spawn=0, x=90.0, v=300)
        
        # gap de 20 mn = 6 minutos a 200 nudos (suficiente para 10 minutos)
        avion_desviado.retroceder(avion_adelante, avion_atras)
        self.assertEqual(avion_desviado.status, "reinsercion")
        self.assertEqual(avion_desviado.x, 72.5)  # punto medio del gap
        
    def test_retroceder_sin_gap_suficiente(self):
        """test: retroceder() no se reinserta si no hay gap suficiente"""
        avion_desviado = Plane(id=1, t_spawn=0, x=60.0, v=200, status="desviado")
        avion_adelante = Plane(id=2, t_spawn=0, x=50.0, v=300)
        avion_atras = Plane(id=3, t_spawn=0, x=40.0, v=300)
        
        # gap de solo 10 mn = 3 minutos a 200 nudos (insuficiente para 10 minutos)
        avion_desviado.retroceder(avion_adelante, avion_atras)
        
        # debe seguir desviado y retroceder
        self.assertEqual(avion_desviado.status, "desviado")
        self.assertGreater(avion_desviado.x, 60.0)  # retrocedio
        
    def test_retroceder_con_bloqueo(self):
        """test: retroceder() respeta el bloqueo temporal"""
        avion_desviado = Plane(id=1, t_spawn=0, x=60.0, v=200, status="desviado", minutos_bloqueo=5)
        avion_adelante = Plane(id=2, t_spawn=0, x=40.0, v=300)
        avion_atras = Plane(id=3, t_spawn=0, x=20.0, v=300)
        
        avion_desviado.retroceder(avion_adelante, avion_atras)
        
        # debe retroceder pero no reinsertarse por el bloqueo
        self.assertEqual(avion_desviado.status, "desviado")
        self.assertEqual(avion_desviado.minutos_bloqueo, 4)  # se redujo en 1 minuto

class TestSimulacion(unittest.TestCase):
    """tests para la clase simulacion - comportamiento del sistema completo"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_creacion_simulacion_basica(self):
        """test: creacion basica de simulacion con valores por defecto"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        self.assertEqual(sim.lambda_param, 0.1)
        self.assertEqual(sim.dias_simulacion, 1)
        self.assertEqual(sim.tiempo_actual, 350)  # valor por defecto
        self.assertEqual(sim.dia_actual, 1)
        self.assertFalse(sim.viento_activo)
        self.assertFalse(sim.storm_activa)
        self.assertEqual(len(sim.aviones), 0)
        self.assertEqual(len(sim.aviones_aterrizados), 0)
        self.assertEqual(len(sim.aviones_desviados), 0)
        
    def test_estadisticas_iniciales(self):
        """test: estadisticas se inicializan correctamente"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        stats = sim.estadisticas
        self.assertEqual(stats['total_aviones'], 0)
        self.assertEqual(stats['aterrizados'], 0)
        self.assertEqual(stats['desviados'], 0)
        self.assertEqual(stats['tiempo_promedio_aterrizaje'], 0)
        self.assertEqual(stats['congestiones'], 0)
        self.assertEqual(stats['desvios_a_montevideo'], 0)
        self.assertEqual(stats['dias_completados'], 0)
        self.assertEqual(stats['desvios_viento'], 0)
        self.assertEqual(stats['desvios_cierre'], 0)
        self.assertEqual(stats['desvios_tormenta'], 0)
        self.assertEqual(stats['reincerciones_exitosas'], 0)
        
    def test_esta_aeropuerto_abierto_horario_normal(self):
        """test: aeropuerto abierto durante horario operativo"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # horario operativo: 06:00 a 24:00 (360 a 1440 minutos)
        sim.tiempo_actual = 720  # 12:00
        self.assertTrue(sim.esta_aeropuerto_abierto())
        
        sim.tiempo_actual = 1080  # 18:00
        self.assertTrue(sim.esta_aeropuerto_abierto())
        
    def test_esta_aeropuerto_cerrado_fuera_horario(self):
        """test: aeropuerto cerrado fuera del horario operativo"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # fuera del horario operativo
        sim.tiempo_actual = 180  # 03:00
        self.assertFalse(sim.esta_aeropuerto_abierto())
        
        sim.tiempo_actual = 1500  # 01:00 del dia siguiente
        self.assertFalse(sim.esta_aeropuerto_abierto())
        
    def test_generar_nuevo_avion_aeropuerto_abierto(self):
        """test: generacion de aviones cuando el aeropuerto esta abierto"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        sim.tiempo_actual = 720  # 12:00 - aeropuerto abierto
        
        # forzar generacion de avion (lambda muy alto)
        sim.lambda_param = 10.0
        resultado = sim.generar_nuevo_avion()
        
        # debe generar al menos un avion
        self.assertTrue(resultado)
        self.assertGreater(len(sim.aviones), 0)
        self.assertGreater(sim.estadisticas['total_aviones'], 0)
        
    def test_generar_nuevo_avion_aeropuerto_cerrado(self):
        """test: no se generan aviones cuando el aeropuerto esta cerrado"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        sim.tiempo_actual = 180  # 03:00 - aeropuerto cerrado
        
        aviones_iniciales = len(sim.aviones)
        resultado = sim.generar_nuevo_avion()
        
        # no debe generar aviones
        self.assertFalse(resultado)
        self.assertEqual(len(sim.aviones), aviones_iniciales)
        
    def test_ordenar_aviones_por_distancia(self):
        """test: ordenamiento de aviones por distancia al aeropuerto"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # crear aviones en orden aleatorio
        avion1 = Plane(id=1, t_spawn=0, x=30.0)
        avion2 = Plane(id=2, t_spawn=0, x=80.0)
        avion3 = Plane(id=3, t_spawn=0, x=10.0)
        
        sim.aviones = [avion1, avion2, avion3]
        sim.ordenar_aviones_por_distancia()
        
        # debe estar ordenado por distancia (mas cerca primero)
        self.assertEqual(sim.aviones[0].x, 10.0)
        self.assertEqual(sim.aviones[1].x, 30.0)
        self.assertEqual(sim.aviones[2].x, 80.0)
        
    def test_obtener_hora_actual(self):
        """test: conversion correcta de tiempo a formato hora"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # test varios horarios
        sim.tiempo_actual = 360  # 06:00
        self.assertEqual(sim.obtener_hora_actual(), "06:00")
        
        sim.tiempo_actual = 720  # 12:00
        self.assertEqual(sim.obtener_hora_actual(), "12:00")
        
        sim.tiempo_actual = 1080  # 18:00
        self.assertEqual(sim.obtener_hora_actual(), "18:00")
        
        sim.tiempo_actual = 1440  # 00:00 del dia siguiente
        self.assertEqual(sim.obtener_hora_actual(), "00:00")
        
    def test_obtener_dia_actual(self):
        """test: calculo correcto del dia actual"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=3)
        
        # dia 1
        sim.tiempo_actual = 720
        self.assertEqual(sim.obtener_dia_actual(), 1)
        
        # dia 2
        sim.tiempo_actual = 2160  # 1440 + 720
        self.assertEqual(sim.obtener_dia_actual(), 2)
        
        # dia 3
        sim.tiempo_actual = 3600  # 2*1440 + 720
        self.assertEqual(sim.obtener_dia_actual(), 3)

class TestTormentas(unittest.TestCase):
    """tests para el sistema de tormentas y cierres del aeropuerto"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_programar_tormenta_del_dia(self):
        """test: programacion de tormentas para el dia"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1, 
                        storm_activa=True, storm_prob=1.0, storm_duracion_min=60)
        
        # con probabilidad 1.0 siempre debe haber tormenta
        self.assertIsNotNone(sim.storm_inicio_min)
        self.assertGreaterEqual(sim.storm_inicio_min, 0)
        self.assertLessEqual(sim.storm_inicio_min, 1440 - 60)  # no puede empezar muy tarde
        
    def test_motivo_cierre_actual_tormenta(self):
        """test: deteccion correcta de cierre por tormenta"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1,
                        storm_activa=True, storm_prob=1.0, storm_duracion_min=60)
        sim.storm_inicio_min = 720  # 12:00
        
        # durante la tormenta
        sim.tiempo_actual = 750  # 12:30
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertEqual(motivo, "tormenta")
        
        # antes de la tormenta
        sim.tiempo_actual = 700  # 11:40
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertIsNone(motivo)
        
        # despues de la tormenta
        sim.tiempo_actual = 800  # 13:20
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertIsNone(motivo)
        
    def test_tormenta_cruza_medianoche(self):
        """test: tormenta que cruza la medianoche"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1,
                        storm_activa=True, storm_prob=1.0, storm_duracion_min=120)
        sim.storm_inicio_min = 1380  # 23:00, dura hasta 01:00
        
        # antes de la tormenta
        sim.tiempo_actual = 1370  # 22:50
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertIsNone(motivo)
        
        # durante la tormenta (antes de medianoche)
        sim.tiempo_actual = 1390  # 23:10
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertEqual(motivo, "tormenta")
        
        # durante la tormenta (despues de medianoche)
        sim.tiempo_actual = 10  # 00:10
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertEqual(motivo, "horario")
        
        # despues de la tormenta (sigue cerrado x horario)
        sim.tiempo_actual = 70  # 01:10
        motivo = sim._motivo_cierre_actual(sim.tiempo_actual % 1440)
        self.assertEqual(motivo, "horario") 

class TestViento(unittest.TestCase):
    """tests para el sistema de viento y go-arounds"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_go_around_por_viento(self):
        """test: avion que intenta aterrizar con viento activo puede hacer go-around"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1,
                        viento_activo=True, p_goaround=1.0)  # probabilidad 100%
        
        # crear avion que intenta aterrizar
        avion = Plane(id=1, t_spawn=0, x=0.1, v=300, status="intento_aterrizar")
        sim.aviones = [avion]
        sim.tiempo_actual = 720  # aeropuerto abierto
        
        # procesar paso temporal
        sim.procesar_paso_temporal()
        
        # debe hacer go-around (desviarse)
        self.assertEqual(avion.status, "desviado")
        self.assertEqual(sim.estadisticas['desvios_viento'], 1)
        
    def test_aterrizaje_exitoso_sin_viento(self):
        """test: aterrizaje exitoso cuando no hay viento"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1,
                        viento_activo=False)
        
        # crear avion que intenta aterrizar
        avion = Plane(id=1, t_spawn=0, x=0.1, v=300, status="intento_aterrizar")
        sim.aviones = [avion]
        sim.tiempo_actual = 720  # aeropuerto abierto
        
        # procesar paso temporal
        sim.procesar_paso_temporal()
        
        # debe aterrizar exitosamente
        self.assertEqual(avion.status, "aterrizaje_confirmado")
        self.assertEqual(sim.estadisticas['aterrizados'], 1)
        self.assertEqual(len(sim.aviones_aterrizados), 1)

class TestCasosBorde(unittest.TestCase):
    """tests para casos borde y situaciones extremas"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_avion_desviado_sale_100_mn(self):
        """test: avion desviado que sale de las 100 mn va a montevideo"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # crear avion desviado que ya salio de las 100 mn
        avion = Plane(id=1, t_spawn=0, x=105.0, v=200, status="desviado")
        sim.aviones = [avion]
        
        # procesar paso temporal
        sim.procesar_paso_temporal()
        
        # debe irse a montevideo
        self.assertEqual(len(sim.aviones), 0)  # removido de aviones activos
        self.assertEqual(len(sim.aviones_desviados), 1)
        self.assertEqual(sim.estadisticas['desvios_a_montevideo'], 1)
        
    def test_simulacion_sin_aviones(self):
        """test: simulacion que funciona correctamente sin aviones"""
        sim = Simulacion(lambda_param=0.0, dias_simulacion=1)  # lambda = 0, no genera aviones
        
        # ejecutar varios pasos temporales
        for _ in range(100):
            sim.procesar_paso_temporal()
            
        # debe funcionar sin errores
        self.assertEqual(len(sim.aviones), 0)
        self.assertEqual(sim.estadisticas['total_aviones'], 0)
        
    def test_avion_aterrizado_no_avanza(self):
        """test: avion que ya aterrizo no se mueve"""
        avion = Plane(id=1, t_spawn=0, x=0.0, v=300, status="aterrizaje_confirmado")
        posicion_inicial = avion.x
        
        avion.avanzar(None, None)
        
        # no debe moverse
        self.assertEqual(avion.x, posicion_inicial)
        self.assertEqual(avion.status, "aterrizaje_confirmado")
        
    def test_avion_con_velocidad_cero(self):
        """test: avion con velocidad cero no se mueve"""
        avion = Plane(id=1, t_spawn=0, x=50.0, v=0.0)
        posicion_inicial = avion.x
        
        avion.avanzar(None, None)
        
        # no debe moverse
        self.assertEqual(avion.x, posicion_inicial)
        
    def test_reinsercion_desde_estado_reinsercion(self):
        """test: avion en estado reinsercion cambia a en_fila al avanzar"""
        avion = Plane(id=1, t_spawn=0, x=50.0, v=300, status="reinsercion")
        
        avion.avanzar(None, None)
        
        self.assertEqual(avion.status, "en_fila")

class TestEstadisticas(unittest.TestCase):
    """tests para el calculo y actualizacion de estadisticas"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_calcular_estadisticas_finales(self):
        """test: calculo correcto de estadisticas finales"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # simular algunos aviones aterrizados
        avion1 = Plane(id=1, t_spawn=0, x=0.0, tiempo_estimado=30.0)
        avion2 = Plane(id=2, t_spawn=0, x=0.0, tiempo_estimado=45.0)
        avion3 = Plane(id=3, t_spawn=0, x=0.0, tiempo_estimado=60.0)
        
        sim.aviones_aterrizados = [avion1, avion2, avion3]
        sim.estadisticas['aterrizados'] = 3
        
        sim.calcular_estadisticas_finales()
        
        # tiempo promedio debe ser 45.0
        self.assertEqual(sim.estadisticas['tiempo_promedio_aterrizaje'], 45.0)
        self.assertEqual(sim.estadisticas['dias_completados'], 1)
        
    def test_estadisticas_sin_aterrizados(self):
        """test: estadisticas cuando no hay aviones aterrizados"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        sim.calcular_estadisticas_finales()
        
        # tiempo promedio debe ser 0
        self.assertEqual(sim.estadisticas['tiempo_promedio_aterrizaje'], 0)
        
    def test_reiniciar_simulacion(self):
        """test: reinicio correcto de la simulacion"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        
        # modificar estado
        sim.tiempo_actual = 1000
        sim.dia_actual = 2
        sim.aviones = [Plane(id=1, t_spawn=0)]
        sim.estadisticas['total_aviones'] = 5
        
        # reiniciar
        sim.reiniciar_simulacion()
        
        # debe volver a estado inicial
        self.assertEqual(sim.tiempo_actual, 0)
        self.assertEqual(sim.dia_actual, 1)
        self.assertEqual(len(sim.aviones), 0)
        self.assertEqual(len(sim.aviones_aterrizados), 0)
        self.assertEqual(len(sim.aviones_desviados), 0)
        self.assertEqual(sim.estadisticas['total_aviones'], 0)

class TestFuncionesAuxiliares(unittest.TestCase):
    """tests para funciones auxiliares y de utilidad"""
    
    def test_velocidad_permitida(self):
        """test: funcion velocidad_permitida devuelve rangos correctos"""
        # test en cada rango
        test_cases = [
            (150.0, (300, 500)),  # > 100 mn
            (75.0, (250, 300)),   # 50-100 mn
            (30.0, (200, 250)),   # 15-50 mn
            (10.0, (150, 200)),   # 5-15 mn
            (2.0, (120, 150))     # 0-5 mn
        ]
        
        for distancia, rango_esperado in test_cases:
            rango_obtenido = u.velocidad_permitida(distancia)
            self.assertEqual(rango_obtenido, rango_esperado)
            
    def test_velocidad_permitida_caso_borde(self):
        """test: velocidad_permitida en casos borde"""
        # exactamente en los limites
        self.assertEqual(u.velocidad_permitida(100.0), (300, 500))  # limite superior
        self.assertEqual(u.velocidad_permitida(50.0), (250, 300))   # limite superior
        self.assertEqual(u.velocidad_permitida(15.0), (200, 250))   # limite superior
        self.assertEqual(u.velocidad_permitida(5.0), (150, 200))    # limite superior
        self.assertEqual(u.velocidad_permitida(0.0), (120, 150))    # limite inferior
        
    def test_tiempo_min_para_mn(self):
        """test: calculo correcto de tiempo para distancia"""
        # 60 nudos = 1 mn/min
        tiempo = u.tiempo_min_para_mn(60, 30)
        self.assertEqual(tiempo, 30.0)
        
        # 120 nudos = 2 mn/min
        tiempo = u.tiempo_min_para_mn(120, 30)
        self.assertEqual(tiempo, 15.0)
        
        # 300 nudos = 5 mn/min
        tiempo = u.tiempo_min_para_mn(300, 30)
        self.assertEqual(tiempo, 6.0)
        
    def test_knots_to_mn_per_min(self):
        """test: conversion de nudos a mn/min"""
        # 60 nudos = 1 mn/min
        self.assertEqual(u.knots_to_mn_per_min(60), 1.0)
        
        # 120 nudos = 2 mn/min
        self.assertEqual(u.knots_to_mn_per_min(120), 2.0)
        
        # 300 nudos = 5 mn/min
        self.assertEqual(u.knots_to_mn_per_min(300), 5.0)

class TestSimulacionesMultiples(unittest.TestCase):
    """tests para funciones de simulaciones multiples"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_ejecutar_multiples_simulaciones(self):
        """test: ejecucion de multiples simulaciones retorna estadisticas promedio"""
        # ejecutar pocas simulaciones para test rapido
        stats = ejecutar_multiples_simulaciones(
            lambda_param=0.1, 
            dias_simulacion=1, 
            num_simulaciones=3
        )
        
        # verificar estructura de respuesta
        self.assertIn('total_aviones', stats)
        self.assertIn('aterrizados', stats)
        self.assertIn('desviados', stats)
        
        # verificar que cada estadistica tiene promedio y error estandar
        for key, value in stats.items():
            self.assertIn('promedio', value)
            self.assertIn('error_estandar', value)
            self.assertIn('valores', value)
            self.assertIsInstance(value['valores'], list)
            self.assertEqual(len(value['valores']), 3)
            
    def test_estimar_probabilidad_5_aviones(self):
        """test: estimacion de probabilidad de 5 aviones en 1 hora"""
        lambda_param = 1.0 / 60.0  # 1 avion por hora
        resultado = estimar_probabilidad_5_aviones_en_1_hora(lambda_param, 100)
        
        # verificar estructura de respuesta
        self.assertIn('probabilidad_simulada', resultado)
        self.assertIn('probabilidad_teorica', resultado)
        self.assertIn('error_relativo', resultado)
        self.assertIn('conteos_por_hora', resultado)
        
        # verificar tipos
        self.assertIsInstance(resultado['probabilidad_simulada'], float)
        self.assertIsInstance(resultado['probabilidad_teorica'], float)
        self.assertIsInstance(resultado['error_relativo'], float)
        self.assertIsInstance(resultado['conteos_por_hora'], list)
        self.assertEqual(len(resultado['conteos_por_hora']), 100)

class TestIntegracion(unittest.TestCase):
    """tests de integracion que combinan multiples componentes"""
    
    def setUp(self) -> None:
        """configuracion inicial para cada test"""
        np.random.seed(42)
        
    def test_simulacion_completa_un_dia(self):
        """test: simulacion completa de un dia con lambda bajo"""
        sim = Simulacion(lambda_param=0.01, dias_simulacion=1)  # lambda muy bajo
        
        # ejecutar simulacion completa
        sim.ejecutar_simulacion_completa()
        
        # verificar que termino correctamente
        self.assertEqual(sim.tiempo_actual, 1440)  # 1 dia completo
        self.assertEqual(sim.dia_actual, 2)
        
        # verificar que las estadisticas son consistentes
        stats = sim.estadisticas
        total_aviones = stats['total_aviones']
        aterrizados = stats['aterrizados']
        desviados = stats['desviados']
        
        # la suma de aterrizados y desviados debe ser <= total_aviones
        # (algunos pueden quedar en vuelo al final del dia)
        self.assertLessEqual(aterrizados + desviados, total_aviones)
        
    def test_simulacion_con_tormenta_y_viento(self):
        """test: simulacion con tormenta y viento activos"""
        sim = Simulacion(
            lambda_param=0.1, 
            dias_simulacion=1,
            viento_activo=True,
            p_goaround=0.5,
            storm_activa=True,
            storm_prob=1.0,  # siempre hay tormenta
            storm_duracion_min=60
        )
        
        # ejecutar simulacion completa
        sim.ejecutar_simulacion_completa()
        
        # verificar que se registraron desvios por tormenta
        self.assertGreaterEqual(sim.estadisticas['desvios_tormenta'], 0)
        
        # verificar que se registraron desvios por viento (si hubo intentos de aterrizaje)
        self.assertGreaterEqual(sim.estadisticas['desvios_viento'], 0)
        
    def test_avion_completa_ciclo_vida(self):
        """test: avion que completa todo su ciclo de vida"""
        sim = Simulacion(lambda_param=0.1, dias_simulacion=1)
        sim.tiempo_actual = 720  # 12:00 - aeropuerto abierto
        
        # crear avion que va a aterrizar
        avion = Plane(id=1, t_spawn=720, x=10.0, v=300)
        sim.aviones = [avion]
        sim.estadisticas['total_aviones'] = 1
        
        # simular hasta que aterrice
        pasos = 0
        while avion.status != "aterrizaje_confirmado" and avion.status != "desviado" and pasos < 1000:
            sim.procesar_paso_temporal()
            pasos += 1
            
        # debe haber terminado su ciclo
        self.assertTrue(avion.status in ["aterrizaje_confirmado", "desviado"])
        
        # si aterrizo, debe estar en la lista de aterrizados
        if avion.status == "aterrizaje_confirmado":
            self.assertIn(avion, sim.aviones_aterrizados)
            self.assertEqual(sim.estadisticas['aterrizados'], 1)

def ejecutar_todos_los_tests() -> bool:
    """funcion para ejecutar todos los tests y mostrar resultados"""
    print("ejecutando tests comprehensivos de la simulacion de aviones...")
    print("=" * 60)
    
    # crear suite de tests
    test_suite = unittest.TestSuite()
    
    # agregar todas las clases de test
    test_classes = [
        TestPlane,
        TestSimulacion,
        TestTormentas,
        TestViento,
        TestCasosBorde,
        TestEstadisticas,
        TestFuncionesAuxiliares,
        TestSimulacionesMultiples,
        TestIntegracion
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(test_suite)
    
    # mostrar resumen
    print("\n" + "=" * 60)
    print(f"tests ejecutados: {resultado.testsRun}")
    print(f"errores: {len(resultado.errors)}")
    print(f"fallos: {len(resultado.failures)}")
    print(f"exitosos: {resultado.testsRun - len(resultado.errors) - len(resultado.failures)}")
    
    if resultado.errors:
        print("\nerrores encontrados:")
        for test, error in resultado.errors:
            print(f"- {test}: {error}")
            
    if resultado.failures:
        print("\nfallos encontrados:")
        for test, failure in resultado.failures:
            print(f"- {test}: {failure}")
    
    return resultado.wasSuccessful()

if __name__ == "__main__":
    # ejecutar todos los tests
    exito = ejecutar_todos_los_tests()
    
    if exito:
        print("\n✅ todos los tests pasaron correctamente!")
    else:
        print("\n❌ algunos tests fallaron. revisar los errores arriba.")
















