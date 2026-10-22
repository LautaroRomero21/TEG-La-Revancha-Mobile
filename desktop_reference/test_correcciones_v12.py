"""Regresiones de la v12: límite de mano, nueva frontera y animaciones de combate.

Ejecución: python -m unittest -v test_correcciones_v12
"""
import importlib.util
import random
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from data import PAISES_DATA
from logic import JuegoTEG, FASE_TARJETA


class ReglasV12(unittest.TestCase):
    def setUp(self):
        random.seed(1200)
        self.j=JuegoTEG(4,orden_inicial=[0,1,2,3])
        self.j.etapa='hostilidades'
        self.j.fase=FASE_TARJETA
        self.j.ronda=4
        self.j.turno_idx=0
        self.j.conquistas_turno=2
        self.j.tarjeta_solicitada=False

    def test_nigeria_angola_bidireccional_sin_duplicados(self):
        self.assertIn('Angola', PAISES_DATA['Nigeria']['fronteras'])
        self.assertIn('Nigeria', PAISES_DATA['Angola']['fronteras'])
        self.assertEqual(PAISES_DATA['Nigeria']['fronteras'].count('Angola'),1)
        self.assertEqual(PAISES_DATA['Angola']['fronteras'].count('Nigeria'),1)
        self.assertTrue(self.j.son_adyacentes('Nigeria','Angola'))
        self.assertTrue(self.j.son_adyacentes('Angola','Nigeria'))
        self.assertEqual(len(self.j.tablero),72)

    def test_cinco_cartas_pais_ninguna_solicitud_posible(self):
        jugador=self.j.jugador_actual()
        jugador.tarjetas=['Alaska','Canada','Italia','Angola','China']
        jugador.cartas_continente={'Africa','Europa'}
        self.assertFalse(self.j.puede_solicitar_tarjeta())
        restante=len(self.j.mazo_cartas_pais)
        self.assertIsNone(self.j.solicitar_tarjeta())
        self.assertFalse(self.j.tarjeta_solicitada)
        self.assertEqual(len(jugador.tarjetas),5)
        self.assertEqual(len(self.j.mazo_cartas_pais),restante)
        self.assertEqual(jugador.cartas_continente,{'Africa','Europa'})

    def test_cuatro_cartas_pais_mas_continentales_si_puede_recibir_quinta(self):
        jugador=self.j.jugador_actual()
        jugador.tarjetas=['Alaska','Canada','Italia','Angola']
        jugador.cartas_continente={'Africa','Europa','Asia'}
        self.assertTrue(self.j.puede_solicitar_tarjeta())
        carta=self.j.solicitar_tarjeta()
        self.assertIsNotNone(carta)
        self.assertEqual(len(jugador.tarjetas),5)
        self.assertEqual(len(jugador.cartas_continente),3)
        self.assertFalse(self.j.puede_solicitar_tarjeta())
        self.assertIsNone(self.j.solicitar_tarjeta())

    def test_cinco_pais_seguir_sin_poder_pedir_tras_otra_conquista(self):
        jugador=self.j.jugador_actual()
        jugador.tarjetas=['Alaska','Canada','Italia','Angola','China']
        self.j.conquistas_turno=8
        self.j.tarjeta_solicitada=False
        self.assertFalse(self.j.puede_solicitar_tarjeta())
        jugador.tarjetas.pop()
        self.assertTrue(self.j.puede_solicitar_tarjeta())

    def test_bot_con_cinco_cartas_no_roba_en_su_fase_de_tarjetas(self):
        bot=self.j.jugadores[1]
        bot.tarjetas=['Alaska','Canada','Italia','Angola','China']
        self.j.turno_idx=1
        n=len(self.j.mazo_cartas_pais)
        estado=self.j.paso_bot()
        self.assertIn('termina turno',estado['texto'])
        self.assertEqual(len(bot.tarjetas),5)
        self.assertEqual(len(self.j.mazo_cartas_pais),n)


class AnimacionV12(unittest.TestCase):
    @staticmethod
    def cargar_renderer():
        fake=types.ModuleType('pygame')
        fake.time=types.SimpleNamespace(get_ticks=lambda:1234)
        nombre='_renderer_v12_pruebas'
        spec=importlib.util.spec_from_file_location(nombre,Path(__file__).with_name('renderer.py'))
        m=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'pygame':fake}):
            spec.loader.exec_module(m)
        return m, fake

    def test_animacion_registra_focos_y_aviso_de_conquista_persistente(self):
        m, fake=self.cargar_renderer()
        j=JuegoTEG(4,orden_inicial=[0,1,2,3])
        r=m.Renderer.__new__(m.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        resultado={'ok':True,'bajas_atk':1,'bajas_def':2,'conquisto':True}
        self.assertTrue(r.registrar_combate('Nigeria','Angola',resultado,j))
        self.assertEqual(r.combate_visual['pos_desde'],r._escalar_coords(j.tablero['Nigeria']['coords']))
        self.assertEqual(r.combate_visual['pos_hacia'],r._escalar_coords(j.tablero['Angola']['coords']))
        self.assertEqual(r.combate_visual['bajas_def'],2)
        self.assertEqual(r.ultima_conquista_visual['pais'],'Angola')
        # Otro ataque sobreescribe la flecha pero NO oculta el aviso de conquista anterior.
        self.assertTrue(r.registrar_combate('Nigeria','Etiopia',{'ok':True,'conquisto':False},j))
        self.assertEqual(r.combate_visual['hacia'],'Etiopia')
        self.assertEqual(r.ultima_conquista_visual['pais'],'Angola')

    def test_misil_y_nombres_invalidos_para_animacion(self):
        m, fake=self.cargar_renderer()
        j=JuegoTEG(2,orden_inicial=[0,1])
        r=m.Renderer.__new__(m.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        self.assertFalse(r.registrar_combate('País inventado','Nigeria',None,j))
        self.assertIsNone(r.combate_visual)
        self.assertTrue(r.registrar_combate('Nigeria','Angola',None,j,tipo='misil'))
        self.assertEqual(r.combate_visual['tipo'],'misil')
        self.assertIsNone(r.ultima_conquista_visual)


if __name__=='__main__':
    unittest.main()
