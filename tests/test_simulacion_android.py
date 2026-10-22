"""Simulaciones offline donde los bots corren el motor real y el humano pasa fases."""
import random
import unittest
from controller import ControlMovil


class SimulacionUnHumano(unittest.TestCase):
    def test_distintos_tamanos_de_partida_hasta_tercera_ronda(self):
        for n in (2,3,4,5,6):
            with self.subTest(jugadores=n):
                random.seed(1000+n)
                c=ControlMovil(n,orden_inicial=list(range(n)),objetivos_eliminacion=False)
                j=c.juego
                for paso in range(7000):
                    d=c.dialogo
                    if d:
                        k=d['kind']
                        if k=='situacion':c.procesar_opcion('situacion_ok')
                        elif k=='propuesta_bot':c.procesar_opcion('responder_bot:no')
                        elif k=='reagrupe_aliado':c.procesar_opcion('aliado_no')
                        elif k=='zona_pendiente':
                            z=next(z for z in j.zonas_internacionales if z['activa'] and z.get('decision_pendiente')==0)
                            c.procesar_opcion(f'zona_decidir:{z["id"]}:cancelar')
                        elif k=='info':c.procesar_opcion('cerrar')
                        elif k=='victoria':break
                        else:self.fail(f'Diálogo inesperado: {k}')
                    elif j.fase=='VICTORIA':break
                    elif j.jugador_actual().es_bot:
                        c.tick()
                    elif j.fase=='INCORPORAR':
                        pools=j.desglose_incorporacion()
                        obligados=list(pools['continentes'])
                        propios=j.paises_de(0)
                        permitidos=[p for p in propios if j.etapa=='preparacion' or not j._pais_bloqueado(p)]
                        if obligados:
                            permitidos=[p for p in permitidos if j.tablero[p]['continente'] in obligados]
                        pais=permitidos[0]
                        c.seleccionar_origen(pais)
                        ref=c.accion('incorporar','max')
                        self.assertTrue(ref, c.aviso)
                    else:
                        self.assertTrue(c.accion('pasar'))
                    self.assertTrue(all(d['ejercitos']>=0 for d in j.tablero.values()))
                    self.assertTrue(all(d['misiles']>=0 for d in j.tablero.values()))
                    if j.ronda>=3:break
                else:self.fail(f'Partida {n} sin progreso tras 7000 pasos')
                self.assertTrue(j.ronda>=3 or j.fase=='VICTORIA',f'{n} jugadores, ronda {j.ronda}')
