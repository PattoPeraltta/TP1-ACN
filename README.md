# simulador de tráfico aéreo - aep

este proyecto simula el tráfico de aviones en el aeropuerto de ezeiza (aep) usando monte carlo. los aviones llegan con distribución de poisson, se mueven por rangos de velocidad según su distancia al aeropuerto, y pueden desviarse por congestión, viento o tormentas.

## qué hace

- simula aviones que aparecen cada minuto según una distribución de poisson
- cada avión tiene velocidad variable según su rango de distancia (100+ mn hasta aterrizaje)
- maneja desaceleración cuando hay otro avión muy cerca (menos de 4 min)
- desvía aviones cuando no pueden mantener velocidad mínima o por condiciones climáticas
- permite reinserción de aviones desviados cuando hay espacio suficiente
- simula efectos del viento (go-around) y tormentas que cierran el aeropuerto

## cómo correrlo

### visualización tipo videojuego (recomendado)
```bash
cd src
python viz.py
```

después elegí la opción 1 y configurá los parámetros que te pida.

### parámetros principales
- **lambda**: tasa de llegadas por minuto (ej: 0.0167 = 1 avión/hora)
- **días**: cuántos días simular
- **viento**: si está activo y probabilidad de go-around
- **tormenta**: si puede haber tormentas y su duración

## archivos importantes

- `sim_core.py`: motor principal de la simulación
- `plane.py`: lógica de cada avión individual  
- `viz.py`: visualización interactiva tipo videojuego
- `const.py`: parámetros del sistema (rangos de velocidad, etc.)
- `utilidades.py`: funciones auxiliares
