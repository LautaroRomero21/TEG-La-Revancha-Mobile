"""Pruebas funcionales de la capa móvil, sin dependencia de Kivy."""
import random
import unittest
from unittest.mock import patch

from controller import ControlMovil
from data import PAISES_DATA, CONTINENTES


class TestPortatil(unittest.TestCase):
    def setUp(self):
        random.seed(12345)
        self.c = ControlMovil(n_jugadores=2, orden_inicial=[0,1])
        self.j = self.c.juego

    def test_cantidad_paises_y_datos_exactos(self):
        self.assertEqual(len(self.j.tablero),72)
        self.assertEqual(len(CONTINENTES),7)
        self.assertEqual(set(self.j.tablero),set(PAISES_DATA))
        self.assertEqual(len(self.j.mazo_situacion),50)
        self.assertEqual(self.j.situacion,'Clásico')

    def test_configuracion_y_orden(self):
        self.assertEqual(self.c.juego.jugadores[0].color_nombre,'Blanco')
        with self.assertRaises(ValueError): ControlMovil(n_jugadores=1)
        self.assertTrue(ControlMovil(6,color_humano=5,objetivos_eliminacion=False).juego.objetivos_eliminacion is False)

    def test_incorporacion_tactil_y_autoavance(self):
        pais=self.j.paises_de(0)[0]
        ini=self.j.tablero[pais]['ejercitos']
        self.assertTrue(self.c.tocar_pais(pais))
        self.assertEqual(self.c.origen,pais)
        self.assertTrue(self.c.accion('incorporar',18))
        self.assertEqual(self.j.tablero[pais]['ejercitos'],ini+18)
        self.assertEqual(self.j.turno_idx,1)
        self.assertEqual(self.j.fase,'INCORPORAR')

    def test_refuerzos_todos_en_pais(self):
        p=self.j.paises_de(0)[0]
        self.c.tocar_pais(p)
        self.assertTrue(self.c.accion('incorporar','max'))
        self.assertEqual(self.j.turno_idx,1)

    def test_movimiento_y_seleccion_tactil(self):
        self.j.fase='ATACAR';self.j.etapa='hostilidades'
        propios=self.j.paises_de(0)
        a=propios[0]
        b=next(q for q in self.j.tablero if self.j.tablero[q]['propietario']!=0)
        self.c.tocar_pais(a);self.c.tocar_pais(b)
        self.assertEqual((self.c.origen,self.c.destino),(a,b))
        self.c.tocar_pais(a)
        self.assertEqual((self.c.origen,self.c.destino),(None,None))

    def test_combate_real_con_ocupacion(self):
        j=self.j
        a,b=next((p,q) for p in j.tablero for q in j.tablero[p]['fronteras']
                 if j.tablero[p]['propietario']==0 and j.tablero[q]['propietario']==1)
        j.fase='ATACAR';j.etapa='hostilidades';j.etapa_ronda='ATAQUE'
        j.tablero[a]['ejercitos']=50
        j.tablero[b]['ejercitos']=1
        self.c.tocar_pais(a);self.c.tocar_pais(b)
        dados_atacante,_=j._dados_para_ataque(50,1)
        with patch('random.randint',side_effect=[6]*dados_atacante+[1]):
            # Atacante gana con 6, defensor con 1.
            self.assertTrue(self.c.accion('atacar'))
        self.assertIsNotNone(j.conquista_pendiente)
        self.assertEqual(self.c.dialogo['kind'],'conquista')
        self.assertTrue(self.c.dialogo['obligatorio'])
        self.assertFalse(self.c.procesar_opcion('cerrar'))
        self.assertTrue(self.c.procesar_opcion('ocupar:1'))
        self.assertEqual(j.tablero[b]['propietario'],0)
        self.assertGreaterEqual(j.tablero[b]['ejercitos'],1)

    def test_no_puede_pasar_con_refuerzos(self):
        self.assertFalse(self.c.accion('pasar'))
        self.assertEqual(self.c.dialogo['kind'],'info')

    def test_solicitud_tarjeta_limite_cinco(self):
        j=self.j
        j.etapa='hostilidades';j.fase='TARJETA';j.conquistas_turno=3
        carta=self.c.accion('solicitar_tarjeta')
        self.assertTrue(carta)
        self.assertEqual(self.c.dialogo['kind'],'tarjetas')
        jugador=j.jugador_actual();jugador.tarjetas=list(j.tablero)[:5]
        self.c.dialogo=None
        self.assertFalse(self.c.accion('solicitar_tarjeta'))

    def test_bot_paso_no_bloqueante(self):
        # Acaba incorporación humana; el bot debe continuar en pasos discretos.
        p=self.j.paises_de(0)[0]
        self.c.tocar_pais(p);self.c.accion('incorporar',18)
        self.assertTrue(self.j.jugador_actual().es_bot)
        info=self.c.tick()
        self.assertIsInstance(info,dict)
        self.assertIn('texto',info)

    def test_bot_velocidad_pausa(self):
        self.c.velocidad=0
        p=self.j.paises_de(0)[0]
        self.c.tocar_pais(p);self.c.accion('incorporar',18)
        self.assertIsNone(self.c.tick())
        self.assertEqual(self.j.ejercitos_a_colocar,18)

    def test_pacto_no_agresion_mundial(self):
        self.j.fase='ATACAR';self.j.etapa='hostilidades'
        with patch.object(self.j,'bot_acepta_pacto',return_value=True):
            self.c._proponer('mundial',socio=1)
        self.assertTrue(any(p['tipo']=='mundial' for p in self.j.pactos))
        self.assertEqual(self.c.dialogo['kind'],'pactos')

    def test_aceptacion_propuesta_bot(self):
        j=self.j
        a,b=next((p,q) for p in j.tablero for q in j.tablero[p]['fronteras']
                 if j.tablero[p]['propietario']==1 and j.tablero[q]['propietario']==0)
        j.propuesta_pendiente={'tipo':'pais','a':1,'b':0,'paises':(a,b)}
        self.assertIsNone(self.c.tick())
        self.assertTrue(self.c.dialogo['obligatorio'])
        self.assertEqual(self.c.dialogo['kind'],'propuesta_bot')
        self.assertFalse(self.c.procesar_opcion('cerrar'))
        self.assertTrue(self.c.procesar_opcion('responder_bot:si'))
        self.assertIsNone(j.propuesta_pendiente)
        self.assertEqual(len(j.pactos_vigentes()),1)

    def test_no_hay_tarjeta_de_situacion_primera_ronda(self):
        j=self.j;j.etapa='hostilidades';j.ronda=1
        self.c.tick()
        self.assertIsNone(self.c.dialogo)
        j.ronda=2
        self.c.tick()
        self.assertEqual(self.c.dialogo['kind'],'situacion')
        self.assertTrue(self.c.dialogo['obligatorio'])
        self.assertTrue(self.c.procesar_opcion('situacion_ok'))

    def test_canjes_solo_del_motor(self):
        self.j.etapa='hostilidades';self.j.fase='INCORPORAR'
        self.assertFalse(self.c.canjear(automatico=False))
        self.assertEqual(self.c.dialogo['kind'],'info')

    def test_inspeccionar_paises_sin_mover_pactos_pendientes(self):
        self.c._dialogo('propuesta_bot','Pacto','Esperando',[('Aceptar','responder_bot:si')],True)
        propio=self.j.paises_de(0)[0]
        self.c.tocar_pais(propio)
        self.assertIsNone(self.c.origen)
        self.assertEqual(self.c.inspeccion,propio)


if __name__=='__main__': unittest.main()
