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