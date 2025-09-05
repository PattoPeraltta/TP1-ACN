from dataclasses import dataclass
from typing import Literal, Optional
import random
import numpy as np


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
    v_current: float = 0.0     # velocidad actual (nudos)
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
        if np.random.binomial(1, self.lam) == 1:            # Bernoulli con probabilidad lam de que haya un arribo
            p = Plane(id=self.next_id, t_spawn=self.clock)
            if next_id > 0:
                avion_previo = self.planes[next_id - 1]
            self.next_id += 1
            p.v_current = np.random.uniform(250, 300)       # velocidad inicial en nudos, la máxima                               
            self.planes.append(p)
            return True
        return False
        

    def step(self):
        # 1) posible arribo
        if(len(self.planes) > 0):
            ante_ultimo_avion = self.planes[-1]
            llego_un_avion = self.spawn_plane()
            ultimo_avion = self.planes[-1]
        else:
            llego_un_avion = self.spawn_plane()
        if(llego_un_avion):
            ultimo_avion = self.planes[-1]
        # checkeo velocidades 
        i=0
        while(i < len(self.planes)-1 and len(self.planes) > 1):
            if self.planes[i].status not in ["desacelerando"]:   
                dx = knots_to_mn_per_min(self.planes[i].v_current)
                self.planes[i].x = max(0, self.planes[i].x - dx)
                if self.planes[i].x < 50:
                    self.planes[i].v_current = np.random.uniform(200, 250)
                if self.planes[i].x < 15:
                    self.planes[i].v_current = np.random.uniform(150, 200)
                if self.planes[i].x < 5:
                    self.planes[i].v_current = np.random.uniform(120, 150)
            i += 1

        # caso primer avión
        if(len(self.planes) == 1):
            dx = knots_to_mn_per_min(self.planes[0].v_current)
            self.planes[0].x = max(0, self.planes[i].x - dx)
            if self.planes[i].x < 50:
                    self.planes[i].v_current = np.random.uniform(200, 250)
            if self.planes[i].x < 15:
                self.planes[i].v_current = np.random.uniform(150, 200)
            if self.planes[i].x < 5:
                self.planes[i].v_current = np.random.uniform(120, 150)
            

        dist = ultimo_avion.x - ante_ultimo_avion.x
        
        if (llego_un_avion and ultimo_avion.id > 0):
            if(dist * knots_to_mn_per_min(ultimo_avion.v_current) < 4): # esta a < 4' del siguiente 
                ultimo_avion.status = "desacelerando"

        # actualizar velocidades de aviones desacelerando
        i=0
        while(i < len(self.planes)):
            if(self.planes[i].status=="desacelerando"):
                if((planes[i].x - planes[i-1]) * knots_to_mn_per_min(planes[i].v_current) >= 5):
                    if planes[i].x < 50:
                        self.planes[i].v_current = 250
                    if planes[i].x < 15:
                        self.planes[i].v_current = 200
                    if planes[i].x < 5:
                        self.planes[i].v_current = 150
                    self.planes[i].status = "en_fila"
                else:
                    self.planes[i].v_current = self.planes[i-1].v_current - 20
            i += 1
            # chequeo aterrizaje
            if self.planes[i].x <= 0:
                self.planes[i].status = "aterrizado"
                self.planes[i].eta_estimada = self.clock


    def run(self):
        while self.clock < MINUTOS_CLOSE:
            self.step()
            self.clock += DT

if __name__ == "__main__":
    sim = Simulator(lam=0.1)
    sim.run()
    print("Aviones simulados:", len(sim.planes))
    print("Aterrizados:", sum(p.status == "aterrizado" for p in sim.planes))
