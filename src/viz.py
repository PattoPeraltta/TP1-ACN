import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
import numpy as np
import time
from sim_core import Simulacion
from plane import Plane
from utilidades import ask_bool, ask_pos_int, ask_prob_01
import const as c

class visualizador_videojuego:
    """visualizador tipo videojuego para la simulacion de aviones"""
    
    def __init__(self, lambda_param: float, dias_simulacion: int = 3, viento: bool = False, p_go: float = 0.10,
                 tormenta: bool = False, p_tormenta: float = 0.0,  t_dur: int = 30):
        self.sim = Simulacion(lambda_param=lambda_param, dias_simulacion=dias_simulacion, viento_activo=viento,
                              p_goaround=p_go,
                              storm_activa=tormenta,
                              storm_prob=p_tormenta,
                              storm_duracion_min=t_dur)
        self.fig, self.ax = plt.subplots(figsize=(14, 8))
        self.setup_plot()
        
        # sistema de interpolacion para movimiento suave
        self.aviones_anterior = []  # posiciones anteriores para interpolacion
        
        # colores para diferentes estados
        self.colores_estado = {
            'en_fila': '#00ff00',      # verde
            'desacelerando': '#ffaa00', # naranja
            'reinsercion': '#00aaff',   # azul
            'desviado': '#ff0000',      # rojo
            'aterrizado': '#888888'     # gris
        }

        # controles de velocidad y play/pausa
        self.velocidad_multiplier = 1.0
        self.paused = False
        self.slider_velocidad = None
        self.pause_button = None
        
        # control de tiempo para velocidad de simulacion
        self.ultimo_tiempo_simulacion = time.time()
        self.intervalo_simulacion_base = 0.5  # 100ms entre pasos de simulacion (10 pasos/segundo)
        self.tiempo_acumulado = 0.0

        self.setup_controls()
        
    def setup_plot(self):
        """configura el grafico principal"""
        self.fig.subplots_adjust(bottom=0.15)
        self.ax.set_xlim(-10, 110)  # espacio extra para aviones desviados
        self.ax.set_ylim(-2, 2)
        self.ax.set_xlabel('distancia al aeropuerto (millas nauticas)', fontsize=12)
        self.ax.set_ylabel('', fontsize=12)
        self.ax.set_title('simulacion de aproximacion de aviones - aep', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        
        self.ax.grid(True, alpha=0.3)

        # dibujar pista de aterrizaje
        self.ax.axvline(x=0, color='black', linewidth=3, label='pista de aterrizaje')
        
        # dibujar rangos de velocidad con colores
        colores_rangos = ['#ffffff', '#ffcccc', '#ffe6cc', '#fafaaf', '#ccffcc']
        for i, (dmin, dmax, _) in enumerate(c.rangos):
            if dmax == float('inf'):
                dmax = 100
            self.ax.axvspan(dmin, dmax, alpha=0.8, color=colores_rangos[i])
            
            # etiquetas de rangos
            if dmax != 100:
                self.ax.text((dmin + dmax) / 2, 1.5, f'{dmin}-{dmax}mn', 
                           ha='center', va='center', fontsize=10, 
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            else:
                self.ax.text((dmin + dmax) / 2, 1.5, f'{dmin}+mn', 
                           ha='center', va='center', fontsize=10,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # texto de informacion
        self.texto_info = self.ax.text(0.02, 0.98, '', transform=self.ax.transAxes,
                                      verticalalignment='top', fontsize=10,
                                      bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
        
        # texto de estadisticas
        self.texto_stats = self.ax.text(0.98, 0.98, '', transform=self.ax.transAxes,
                                       verticalalignment='top', horizontalalignment='right', fontsize=10,
                                       bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.8))
        
    def obtener_aviones_interpolados(self):
        """retorna posiciones interpoladas de los aviones para movimiento suave"""
        if not self.aviones_anterior or not self.sim.aviones:
            return self.sim.aviones
        
        # calcular factor de interpolacion basado en tiempo acumulado
        intervalo_requerido = self.intervalo_simulacion_base / self.velocidad_multiplier
        factor = min(1.0, self.tiempo_acumulado / intervalo_requerido)
        
        aviones_interpolados = []
        for avion_actual in self.sim.aviones:
            # buscar avion correspondiente en la posicion anterior
            avion_anterior = None
            for avion_ant in self.aviones_anterior:
                if avion_ant.id == avion_actual.id:
                    avion_anterior = avion_ant
                    break
            
            if avion_anterior:
                # detectar si hubo un salto de posicion (reinsercion)
                distancia_salto = abs(avion_actual.x - avion_anterior.x)
                es_reinsercion = (distancia_salto > 5.0 or  # salto grande de posicion
                                avion_anterior.status == "desviado" and avion_actual.status == "reinsercion")
                
                if es_reinsercion:
                    # para reinsercion, usar directamente la posicion actual sin interpolacion
                    avion_interp = Plane(
                        id=avion_actual.id,
                        t_spawn=avion_actual.t_spawn,
                        x=avion_actual.x,
                        v=avion_actual.v,
                        status=avion_actual.status,
                        tiempo_estimado=avion_actual.tiempo_estimado
                    )
                else:
                    # interpolacion normal para movimiento continuo
                    avion_interp = Plane(
                        id=avion_actual.id,
                        t_spawn=avion_actual.t_spawn,
                        x=avion_anterior.x + (avion_actual.x - avion_anterior.x) * factor,
                        v=avion_actual.v,  # velocidad actual
                        status=avion_actual.status,
                        tiempo_estimado=avion_actual.tiempo_estimado
                    )
                aviones_interpolados.append(avion_interp)
            else:
                # si no hay posicion anterior, usar posicion actual
                aviones_interpolados.append(avion_actual)
        
        return aviones_interpolados
        
    def limpiar_aviones_y_etiquetas(self):
        """limpia todos los aviones y etiquetas del grafico"""
        # limpiar aviones anteriores
        for artista in self.ax.collections[:]:
            if hasattr(artista, '_es_avion'):
                artista.remove()
        
        # limpiar etiquetas de texto anteriores
        for artista in self.ax.texts[:]:
            if hasattr(artista, '_es_etiqueta_avion'):
                artista.remove()
        
    def dibujar_aviones(self):
        """dibuja todos los aviones en el grafico"""
        # limpiar aviones y etiquetas anteriores
        self.limpiar_aviones_y_etiquetas()
        
        # obtener aviones interpolados para movimiento suave
        aviones_a_dibujar = self.obtener_aviones_interpolados()
        
        if not aviones_a_dibujar:
            return
            
        # dibujar cada avion
        for i, avion in enumerate(aviones_a_dibujar):
            color = self.colores_estado.get(avion.status, '#000000')
            
            # posicion y: todos en la misma fila excepto los desviados que van arriba
            if avion.status == "desviado":
                y_pos = 0.8  # fila superior para aviones desviados
            else:
                y_pos = 0.0  # fila principal para todos los demas aviones
            
            # dibujar avion como circulo
            avion_artista = self.ax.scatter(avion.x, y_pos, 
                                          color=color, s=150, alpha=0.8, 
                                          edgecolors='black', linewidth=1)
            avion_artista._es_avion = True
            
            # etiqueta simplificada con solo id, status y velocidad
            status_abreviado = {
                'en_fila': 'FILA',
                'desacelerando': 'DESAC',
                'reinsercion': 'REINS',
                'desviado': 'DESV',
                'aterrizado': 'ATER'
            }.get(avion.status, avion.status.upper())
            
            info_text = f'ID: {avion.id}\n{status_abreviado}\n{avion.v:.0f}kt'
                
            etiqueta = self.ax.annotate(info_text, (avion.x, y_pos),
                           xytext=(0, 25 if y_pos > 0 else -25), 
                           textcoords='offset points',
                           fontsize=8, ha='center', va='bottom' if y_pos > 0 else 'top',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='black'))
            etiqueta._es_etiqueta_avion = True
    
    def actualizar_informacion(self):
        """actualiza la informacion de tiempo y estado"""
        hora_actual = self.sim.obtener_hora_actual()
        dia_actual = self.sim.obtener_dia_actual()
        aeropuerto_abierto = self.sim.esta_aeropuerto_abierto()
        
        estado_aeropuerto = "abierto" if aeropuerto_abierto else "cerrado"
        
        info_text = (
            f"dia: {dia_actual}\n"
            f"hora: {hora_actual}\n"
            f"aeropuerto: {estado_aeropuerto}\n"
            f"lambda: {self.sim.lambda_param:.4f}\n"
            f"viento: {'on' if self.sim.viento_activo else 'off'} "
            f"(p de desvio = {self.sim.p_goaround:.2f})\n"
            f"tormenta: {'on' if self.sim.storm_activa else 'off'} "
            f"({(self.sim.storm_inicio_min or 0)//60:02d}:{(self.sim.storm_inicio_min or 0)%60:02d}"
            f"-{((self.sim.storm_inicio_min or 0)+self.sim.storm_duracion_min)%1440//60:02d}:"
            f"{((self.sim.storm_inicio_min or 0)+self.sim.storm_duracion_min)%60:02d})"
        )
        
        self.texto_info.set_text(info_text)
        
        # estadisticas
        stats = self.sim.obtener_estadisticas()
        stats_text = f"aviones activos: {len(self.sim.aviones)}\n"
        stats_text += f"total generados: {stats['total_aviones']}\n"
        stats_text += f"aterrizados: {stats['aterrizados']}\n"
        stats_text += f"desviados por congestion: {stats['desviados']}\n"
        stats_text += f"desvios por viento: {stats['desvios_viento']}\n"
        stats_text += f"desvios por tormenta: {stats['desvios_tormenta']}\n"
        stats_text += f"desvios por cierre: {stats['desvios_cierre']}\n"
        stats_text += f"desvios a montevideo: {stats['desvios_a_montevideo']}"
        
        self.texto_stats.set_text(stats_text)
    
    
    def animar(self, frame):
        """funcion de animacion principal con interpolacion suave"""
        if self.paused:
            return

        tiempo_actual = time.time()
        delta_tiempo = tiempo_actual - self.ultimo_tiempo_simulacion
        self.ultimo_tiempo_simulacion = tiempo_actual
        
        # acumular tiempo y procesar pasos de simulacion segun la velocidad
        self.tiempo_acumulado += delta_tiempo
        intervalo_requerido = self.intervalo_simulacion_base / self.velocidad_multiplier
        
        # procesar pasos de simulacion si ha pasado suficiente tiempo
        while self.tiempo_acumulado >= intervalo_requerido:
            self.tiempo_acumulado -= intervalo_requerido
            
            # guardar posiciones anteriores para interpolacion
            self.aviones_anterior = []
            for avion in self.sim.aviones:
                avion_copia = Plane(
                    id=avion.id,
                    t_spawn=avion.t_spawn,
                    x=avion.x,
                    v=avion.v,
                    status=avion.status,
                    tiempo_estimado=avion.tiempo_estimado
                )
                self.aviones_anterior.append(avion_copia)
            
            # procesar paso de simulacion
            if self.sim.tiempo_actual < self.sim.dias_simulacion * 1440:
                self.sim.procesar_paso_temporal()
            else:
                # simulacion terminada
                self.mostrar_estadisticas_finales()
                return
        
        # actualizar visualizacion con interpolacion (siempre, para movimiento suave)
        self.dibujar_aviones()
        self.actualizar_informacion()
    
    def mostrar_estadisticas_finales(self):
        """muestra las estadisticas finales cuando termina la simulacion"""
        self.sim.calcular_estadisticas_finales()
        stats = self.sim.obtener_estadisticas()
        
        print("\n" + "="*50)
        print("estadisticas finales de la simulacion")
        print("="*50)
        print(f"dias simulados: {stats['dias_completados']}")
        print(f"lambda utilizado: {self.sim.lambda_param}")
        print(f"total de aviones generados: {stats['total_aviones']}")
        print(f"aviones aterrizados: {stats['aterrizados']}")
        print(f"aviones desviados: {stats['desviados']}")
        print(f"desviados por congestion: {stats['desviados']}")
        print(f"desvios por viento: {stats['desvios_viento']}")
        print(f"desvios por tormenta: {stats['desvios_tormenta']}")
        print(f"desvios por cierre: {stats['desvios_cierre']}")
        print(f"desvios a montevideo: {stats['desvios_a_montevideo']}")
        print(f"tiempo promedio de aterrizaje: {stats['tiempo_promedio_aterrizaje']:.2f} minutos")
        
        if stats['total_aviones'] > 0:
            tasa_aterrizaje = stats['aterrizados'] / stats['total_aviones'] * 100
            tasa_desvio = stats['desviados'] / stats['total_aviones'] * 100
            print(f"tasa de aterrizaje exitoso: {tasa_aterrizaje:.1f}%")
            print(f"tasa de desvio: {tasa_desvio:.1f}%")
        print("="*50)
    
    def ejecutar_visualizacion(self):
        """ejecuta la visualizacion tipo videojuego"""
        print("iniciando visualizacion tipo videojuego...")
        
        try:
            # crear animacion con interpolacion suave
            # usar intervalo fijo y controlar velocidad con el multiplicador
            anim = animation.FuncAnimation(self.fig, self.animar, 
                                         interval=33,  # ~30 FPS para movimiento suave
                                         blit=False, repeat=False, cache_frame_data=False)
            
            # plt.tight_layout()
            plt.show()
            
        except KeyboardInterrupt:
            print("\nvisualizacion detenida por el usuario")
            self.mostrar_estadisticas_finales()

    def setup_controls(self):
        """agrega controles interactivos de velocidad, play/pausa y reset"""
        # slider horizontal de velocidad
        ax_speed = plt.axes([0.15, 0.02, 0.3, 0.03])
        self.slider_velocidad = Slider(ax_speed, 'Velocidad', 0.1, 20.0, valinit=1.0)
        self.slider_velocidad.on_changed(self.cambiar_velocidad)

        # botón de play/pausa
        ax_pause = plt.axes([0.50, 0.02, 0.08, 0.03])
        self.pause_button = Button(ax_pause, 'Pausa')
        self.pause_button.on_clicked(self.toggle_pause)

        # boton de reset
        ax_reset = plt.axes([0.60, 0.02, 0.08, 0.03])
        self.reset_button = Button(ax_reset, 'Reset')
        self.reset_button.on_clicked(self.reset_velocidad)

    def cambiar_velocidad(self, val):
        """se llama cuando se modifica el slider de velocidad"""
        self.velocidad_multiplier = val
    
    def toggle_pause(self, event):
        """toggle de play/pausa"""
        self.paused = not self.paused
        self.pause_button.label.set_text('Reanudar' if self.paused else 'Pausa')

    def reset_velocidad(self, event):
        """resetea la velocidad a 1.0 y reanuda"""
        self.velocidad_multiplier = 1.0
        self.paused = False
        self.slider_velocidad.reset()
        self.pause_button.label.set_text('Pausa')

def ejecutar_analisis_completo():
    """ejecuta el analisis completo segun la consigna"""
    print("=== analisis completo del sistema de aproximacion de aviones ===\n")
    
    # 2) calcular lambda para 1 avion por hora
    lambda_1_por_hora = 1.0 / 60.0
    print(f"2) lambda para 1 avion por hora: {lambda_1_por_hora:.6f}")
    
    # 3) estimar probabilidad de 5 aviones en 1 hora
    print("\n3) estimando probabilidad de 5 aviones en 1 hora...")
    from sim_core import estimar_probabilidad_5_aviones_en_1_hora
    prob_5 = estimar_probabilidad_5_aviones_en_1_hora(lambda_1_por_hora, 1000)
    print(f"probabilidad simulada: {prob_5['probabilidad_simulada']:.4f}")
    print(f"probabilidad teorica: {prob_5['probabilidad_teorica']:.4f}")
    print(f"error relativo: {prob_5['error_relativo']:.4f}")
    
    # 4) simular con diferentes valores de lambda
    print("\n4) simulando con diferentes valores de lambda...")
    lambdas = [0.02, 0.1, 0.2, 0.5, 1.0]
    dias_simulacion = 5  # 5 dias para estadisticas robustas
    
    resultados = {}
    for lam in lambdas:
        print(f"\nsimulando con lambda = {lam}...")
        from sim_core import ejecutar_multiples_simulaciones
        stats = ejecutar_multiples_simulaciones(lam, dias_simulacion, 3)
        resultados[lam] = stats
        
        print(f"promedio de aviones generados: {stats['total_aviones']['promedio']:.1f} ± {stats['total_aviones']['error_estandar']:.1f}")
        print(f"promedio de aterrizados: {stats['aterrizados']['promedio']:.1f} ± {stats['aterrizados']['error_estandar']:.1f}")
        print(f"promedio de desviados: {stats['desviados']['promedio']:.1f} ± {stats['desviados']['error_estandar']:.1f}")
        if stats['total_aviones']['promedio'] > 0:
            tasa_desvio = stats['desviados']['promedio']/stats['total_aviones']['promedio']*100
            print(f"tasa de desvio: {tasa_desvio:.1f}%")
    
    return resultados

# funcion principal para ejecutar la visualizacion
def main():
    """funcion principal para ejecutar la simulacion con visualizacion"""
    print("simulador de aproximacion de aviones - aep")
    print("selecciona una opcion:")
    print("1. visualizacion tipo videojuego")
    print("2. analisis completo")
    print("3. simulacion con parametros personalizados")
    
    opcion = input("ingresa tu opcion (1-3): ")
    
    if opcion == "1":
        lambda_param = float(input("ingresa lambda (ej: 0.0167 para 1 avion/hora): "))
        dias_simulacion = int(input("ingresa cantidad de dias a simular (ej: 3): "))
        dia_ventoso = ask_bool("ingresa 'True' si los dias son ventosos (si no 'False'): ")
        p_go = ask_prob_01("ingresa probabilidad de go-around por viento (0-1): ") if dia_ventoso else 0.0

        tormenta = ask_bool("ingresa 'True' si puede haber tormenta (si no 'False'): ")
        p_tormenta = ask_prob_01("ingresa probabilidad diaria de tormenta (0-1): ") if tormenta else 0.0
        tiempo = ask_pos_int("ingresa duración (en minutos) de cada tormenta: ") if tormenta else 0
        
        viz = visualizador_videojuego(lambda_param, dias_simulacion, viento=dia_ventoso, p_go=p_go,
                                  tormenta=tormenta, p_tormenta=p_tormenta, t_dur=tiempo)
        viz.ejecutar_visualizacion()
        
    elif opcion == "2":
        ejecutar_analisis_completo()
        
    elif opcion == "3":
        lambda_param = float(input("ingresa lambda: "))
        dias_simulacion = int(input("ingresa cantidad de dias: "))
        num_sims = int(input("ingresa numero de simulaciones: "))
        dia_ventoso = ask_bool("ingresa 'True' si los dias son ventosos (si no 'False'): ")
        p_go = ask_prob_01("ingresa probabilidad de go-around por viento (0-1): ") if dia_ventoso else 0.0

        tormenta = ask_bool("ingresa 'True' si puede haber tormenta (si no 'False'): ")
        p_tormenta = ask_prob_01("ingresa probabilidad diaria de tormenta (0-1): ") if tormenta else 0.0
        tiempo = ask_pos_int("ingresa duración (en minutos) de cada tormenta: ") if tormenta else 0
        
        from sim_core import ejecutar_multiples_simulaciones
        stats = ejecutar_multiples_simulaciones(lambda_param, dias_simulacion, num_sims,viento_activo=dia_ventoso, p_goaround=p_go,
                                                storm_activa=tormenta, storm_prob=p_tormenta, storm_duracion_min=tiempo)
        print("\nestadisticas finales:")
        for key, value in stats.items():
            print(f"{key}: {value['promedio']:.2f} ± {value['error_estandar']:.2f}")
    
    else:
        print("opcion invalida")

if __name__ == "__main__":
    main()