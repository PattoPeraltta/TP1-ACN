rangos = [
    (100, float("inf"), (300, 500)),   # más de 100 mn
    (50, 100, (250, 300)),             # 100 a 50 mn
    (15, 50, (200, 250)),              # 50 a 15 mn
    (5, 15, (150, 200)),               # 15 a 5 mn
    (0, 5, (120, 150))                 # 5 a aterrizaje
]
MINUTOS_OPEN = 6 * 60        # 06:00
MINUTOS_CLOSE = 24 * 60      # 00:00
DT = 1                       # paso temporal en minutos
LISTA_RANGOS = (5,15,50,100)

METERING_ENABLE = True                # activar/desactivar
METER_POINT_MN = 15                   # punto de control (5 o 15 mn)
METER_TARGET_SPACING_MIN = 5          # separación deseada entre STAs
METER_DEADBAND_SEC = 30               # +/- 30s sin corregir
METER_SPEED_STEP = 10                 # ajuste de velocidad por minuto (kt)