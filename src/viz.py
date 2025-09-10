import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from sim_core import simulacion
import const as c

class visualizador_videojuego:
    """visualizador tipo videojuego para la simulacion de aviones"""
    
    def __init__(self, lambda_param: float, dias_simulacion: int = 3):
        self.sim = simulacion(lambda_param=lambda_param, dias_simulacion=dias_simulacion)
        self.fig, self.ax = plt.subplots(figsize=(14, 8))
        self.setup_plot()
        
        # configuracion de animacion
        self.velocidad_animacion_cerrado = 50  # frames por segundo cuando cerrado (mucho mas rapido)
        self.velocidad_animacion_abierto = 3   # frames por segundo cuando abierto (1 min = 3 seg)
        self.pasos_por_frame_cerrado = 10  # mas pasos por frame cuando cerrado para ir mas rapido
        self.pasos_por_frame_abierto = 1   # menos pasos por frame cuando abierto para ir mas lento
        
        # colores para diferentes estados
        self.colores_estado = {
            'en_fila': '#00ff00',      # verde
            'desacelerando': '#ffaa00', # naranja
            'reinsercion': '#00aaff',   # azul
            'desviado': '#ff0000',      # rojo
            'aterrizado': '#888888'     # gris
        }
        
    def setup_plot(self):
        """configura el grafico principal"""
        self.ax.set_xlim(-10, 110)  # espacio extra para aviones desviados
        self.ax.set_ylim(-2, 2)
        self.ax.set_xlabel('distancia al aeropuerto (millas nauticas)', fontsize=12)
        self.ax.set_ylabel('', fontsize=12)
        self.ax.set_title('simulacion de aproximacion de aviones - aep', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        
        # dibujar pista de aterrizaje
        self.ax.axvline(x=0, color='black', linewidth=3, label='pista de aterrizaje')
        
        # dibujar rangos de velocidad con colores
        colores_rangos = ['#ffcccc', '#ffe6cc', '#ffffcc', '#e6ffcc', '#ccffcc']
        for i, (dmin, dmax, _) in enumerate(c.rangos):
            if dmax == float('inf'):
                dmax = 100
            self.ax.axvspan(dmin, dmax, alpha=0.2, color=colores_rangos[i])
            
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
        
        if not self.sim.aviones:
            return
            
        # dibujar cada avion
        for i, avion in enumerate(self.sim.aviones):
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
        
        info_text = f"dia: {dia_actual}\n"
        info_text += f"hora: {hora_actual}\n"
        info_text += f"aeropuerto: {estado_aeropuerto}\n"
        info_text += f"lambda: {self.sim.lambda_param:.4f}"
        
        self.texto_info.set_text(info_text)
        
        # estadisticas
        stats = self.sim.obtener_estadisticas()
        stats_text = f"aviones activos: {len(self.sim.aviones)}\n"
        stats_text += f"total generados: {stats['total_aviones']}\n"
        stats_text += f"aterrizados: {stats['aterrizados']}\n"
        stats_text += f"desviados: {stats['desviados']}\n"
        stats_text += f"desvios a montevideo: {stats['desvios_a_montevideo']}"
        
        self.texto_stats.set_text(stats_text)
    
    def obtener_intervalo_animacion(self):
        """retorna el intervalo de animacion en milisegundos segun el estado del aeropuerto"""
        if self.sim.esta_aeropuerto_abierto():
            return 1000 // self.velocidad_animacion_abierto  # mas lento cuando abierto
        else:
            return 1000 // self.velocidad_animacion_cerrado  # mas rapido cuando cerrado
    
    def obtener_pasos_por_frame(self):
        """retorna cuantos pasos de simulacion procesar por frame segun el estado del aeropuerto"""
        if self.sim.esta_aeropuerto_abierto():
            return self.pasos_por_frame_abierto
        else:
            return self.pasos_por_frame_cerrado
    
    def animar(self, frame):
        """funcion de animacion principal"""
        # determinar cuantos pasos procesar segun el estado del aeropuerto
        pasos_a_procesar = self.obtener_pasos_por_frame()
        
        # procesar pasos de simulacion
        for _ in range(pasos_a_procesar):
            if self.sim.tiempo_actual < self.sim.dias_simulacion * 1440:
                self.sim.procesar_paso_temporal()
            else:
                # simulacion terminada
                self.mostrar_estadisticas_finales()
                return
        
        # actualizar visualizacion
        self.dibujar_aviones()
        self.actualizar_informacion()
        
        # mostrar progreso cada 1000 pasos
        if self.sim.tiempo_actual % 1000 == 0:
            print(f"progreso: dia {self.sim.dia_actual}, hora {self.sim.obtener_hora_actual()}, aviones: {len(self.sim.aviones)}")
    
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
        print("presiona ctrl+c para detener")
        print("la simulacion corre automaticamente dia tras dia")
        print("velocidad: 1 minuto = 3 segundos cuando el aeropuerto esta abierto")
        print("velocidad: 10x mas rapido cuando el aeropuerto esta cerrado")
        
        try:
            # crear animacion con velocidad fija pero pasos variables
            anim = animation.FuncAnimation(self.fig, self.animar, 
                                         interval=1000//self.velocidad_animacion_abierto, 
                                         blit=False, repeat=False, cache_frame_data=False)
            
            plt.tight_layout()
            plt.show()
            
        except KeyboardInterrupt:
            print("\nvisualizacion detenida por el usuario")
            self.mostrar_estadisticas_finales()

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
        
        viz = visualizador_videojuego(lambda_param, dias_simulacion)
        viz.ejecutar_visualizacion()
        
    elif opcion == "2":
        ejecutar_analisis_completo()
        
    elif opcion == "3":
        lambda_param = float(input("ingresa lambda: "))
        dias_simulacion = int(input("ingresa cantidad de dias: "))
        num_sims = int(input("ingresa numero de simulaciones: "))
        
        from sim_core import ejecutar_multiples_simulaciones
        stats = ejecutar_multiples_simulaciones(lambda_param, dias_simulacion, num_sims)
        print("\nestadisticas finales:")
        for key, value in stats.items():
            print(f"{key}: {value['promedio']:.2f} ± {value['error_estandar']:.2f}")
    
    else:
        print("opcion invalida")

if __name__ == "__main__":
    main()
#caca