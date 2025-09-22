# simulador de tráfico aéreo - aep

este proyecto simula el tráfico de aviones en el aeropuerto de ezeiza (aep) usando monte carlo. los aviones llegan con distribución de poisson, se mueven por rangos de velocidad según su distancia al aeropuerto, y pueden desviarse por congestión, viento o tormentas.

## qué hace

- simula aviones que aparecen cada minuto según una distribución de poisson
- cada avión tiene velocidad variable según su rango de distancia (100+ mn hasta aterrizaje)
- maneja desaceleración cuando hay otro avión muy cerca (menos de 4 min)
- desvía aviones cuando no pueden mantener velocidad mínima o por condiciones climáticas
- permite reinserción de aviones desviados cuando hay espacio suficiente
- simula efectos del viento (go-around) y tormentas que cierran el aeropuerto
- incluye protocolo de metering para control de velocidad y separación

## cómo correrlo

### crear y activar entorno virtual (macOS)
```bash
python3 -m venv venv
source venv/bin/activate
```

### opción 1: visualización
```bash
python src/viz.py
```
elegí opción 1 y configurá:
- **lambda**: tasa de llegadas por minuto (ej: 0.0167 = 1 avión/hora)
- **días**: cuántos días simular
- **viento**: si está activo y probabilidad de go-around (0-1)
- **tormenta**: si puede haber tormentas, probabilidad diaria y duración
- **metering**: usar protocolo nuevo de control de velocidad

la visualización incluye:
- movimiento suave de aviones con interpolación
- colores por estado: verde (en fila), naranja (desacelerando), azul (reinserción), rojo (desviado)
- controles de velocidad (0.1x a 20x), pausa y reset
- indicador visual de tormenta
- estadísticas en tiempo real

### opción 2: simulación personalizada
```bash
python src/viz.py
```
elegí opción 2 para:
- configurar todos los parámetros manualmente
- ejecutar múltiples simulaciones con estadísticas detalladas
- obtener promedios y errores estándar

## parámetros del sistema

- **horario operativo**: 06:00 a 24:00
- **separación mínima**: 4 minutos entre aviones
- **separación para reinserción**: 10 minutos
- **velocidad de desviación**: 200 nudos
- **desaceleración**: 20 nudos menos que el avión de adelante
- **metering**: control de velocidad en punto de 15 mn con separación de 5 min (ejercicio 7)

## archivos importantes

- `sim_core.py`: motor principal de la simulación con monte carlo
- `plane.py`: lógica de cada avión individual (movimiento, estados, metering)
- `viz.py`: visualización interactiva tipo videojuego con controles
- `const.py`: parámetros del sistema (rangos de velocidad, metering, etc.)
- `utilidades.py`: funciones auxiliares para cálculos y validaciones
- `tests.py`: testing intensivo de todas las clases y funciones
- 
