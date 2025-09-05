from dataclasses import dataclass
from typing import Literal, Optional
import random


MINUTOS_OPEN = 6 * 60        # 06:00
MINUTOS_CLOSE = 24 * 60      # 00:00
DT = 1                       # paso temporal en minutos

SPEED_RULES = [             # velocidades (max y min) según tramo (en nudos)
    (1000, 100, 500, 300),  # 1000 mn < avion < 100 mn, v_max=500, v_min=300
    (100, 50, 300, 250),    # 100 mn < avion < 50 mn, v_max=300, v_min=250
    (50, 15, 250, 200),     # 50 mn < avion < 15 mn, v_max=250, v_min=200
    (15, 5, 200, 150),      # 15 mn < avion < 5 mn, v_max=200, v_min=150
    (5, 0, 150, 120),       # 5 mn < avion < 0 mn, v_max=150, v_min=120
]

# funcion para pasar de nudos a millas náuticas/min
def knots_to_mn_per_min(knots: float) -> float:
    return knots / 60.0

@dataclass
class Plane:
    id: int
    t_spawn: int               # minuto en que apareció
    x: float = 100.0           # distancia inicial (millas nauticas)
    v_current: float = 0.0     # velocidad actual (kt)
    status: Literal["en_fila", "desacelerando", "reinsercion",
                    "desviado", "aterrizado"] = "en_fila"
    eta_estimada: Optional[int] = None


class Simulator:
    def __init__(self, lam: float, seed: int = 42):
        """
        lam = lambda = proba de arribo x minuto
        """
        self.lam = lam
        self.clock = MINUTOS_OPEN
        self.planes: list[Plane] = []
        self.next_id = 0
        random.seed(seed)

    def spawn_plane(self):
        if random.random() < self.lam:
            p = Plane(id=self.next_id, t_spawn=self.clock)
            self.next_id += 1
            # velocidad inicial máxima del primer tramo
            p.v_current = 500
            self.planes.append(p)

    def step(self):
        # 1) posible arribo
        self.spawn_plane()

        # 2) actualizar posición de cada avión
        for p in self.planes:
            if p.status not in ["en_fila", "desacelerando"]:
                continue
            # convertir velocidad actual a mn/min y mover
            dx = knots_to_mn_per_min(p.v_current)
            p.x = max(0, p.x - dx)

            # chequeo aterrizaje
            if p.x <= 0:
                p.status = "aterrizado"
                p.eta_estimada = self.clock

        # (acá después vas a meter separación mínima, congestión, reinserción, etc.)

    def run(self):
        while self.clock < MINUTES_CLOSE:
            self.step()
            self.clock += DT


# -------------------
# MAIN TEST
# -------------------
if __name__ == "__main__":
    sim = Simulator(lam=0.1)
    sim.run()
    print("Aviones simulados:", len(sim.planes))
    print("Aterrizados:", sum(p.status == "aterrizado" for p in sim.planes))
