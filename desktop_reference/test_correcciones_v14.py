"""Regresión v14: colores previos al ataque y transición visual de conquistas."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from logic import JuegoTEG, FASE_ATACAR


class TransicionDeConquistaV14(unittest.TestCase):
    @staticmethod
    def cargar_renderer():
        fake=types.ModuleType('pygame')
        fake.time=types.SimpleNamespace(get_ticks=lambda:1000)
        spec=importlib.util.spec_from_file_location('renderer_pruebas_v14',Path(__file__).with_name('renderer.py'))
        modulo=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'pygame':fake}):
            spec.loader.exec_module(modulo)
        return modulo,fake

    @staticmethod
    def preparar_ataque():
        juego=JuegoTEG(n_jugadores=2,orden_inicial=[0,1])
        juego.turno_idx=0
        juego.fase=FASE_ATACAR
        juego.etapa='hostilidades'
        juego.situacion='Clásico'
        juego.tablero['Nigeria']['propietario']=0
        juego.tablero['Nigeria']['ejercitos']=8
        juego.tablero['Angola']['propietario']=1
        juego.tablero['Angola']['ejercitos']=1
        return juego

    def test_motor_preserva_dueno_y_tropas_del_defensor_previo(self):
        juego=self.preparar_ataque()
        with patch('random.randint',side_effect=[6,5,4,1]):
            resultado=juego.atacar('Nigeria','Angola')
        self.assertTrue(resultado['conquisto'])
        self.assertEqual(resultado['atacante_idx'],0)
        self.assertEqual(resultado['defensor_anterior_idx'],1)
        self.assertEqual(resultado['ejercitos_defensor_antes'],1)
        self.assertEqual(juego.tablero['Angola']['propietario'],0)
        self.assertEqual(juego.tablero['Angola']['ejercitos'],0)

    def test_color_defensor_se_mantiene_antes_de_revelar_al_ganador(self):
        modulo,_=self.cargar_renderer()
        juego=self.preparar_ataque()
        with patch('random.randint',side_effect=[6,5,4,1]):
            resultado=juego.atacar('Nigeria','Angola')
        r=modulo.Renderer.__new__(modulo.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        r.animaciones_activas=True
        r.transiciones_conquista={}
        self.assertTrue(r.registrar_combate('Nigeria','Angola',resultado,juego))
        self.assertEqual(r.combate_visual['atacante_color_nombre'],juego.jugadores[0].color_nombre)
        self.assertEqual(r.combate_visual['defensor_color_nombre'],juego.jugadores[1].color_nombre)
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1000),(1,1))
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1949),(1,1))
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1950),(0,0))
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=2450),(0,0))
        self.assertNotIn('Angola',r.transiciones_conquista)

    def test_sin_animaciones_la_conquista_se_ve_inmediata(self):
        modulo,_=self.cargar_renderer()
        juego=self.preparar_ataque()
        with patch('random.randint',side_effect=[6,5,4,1]):
            resultado=juego.atacar('Nigeria','Angola')
        r=modulo.Renderer.__new__(modulo.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        r.animaciones_activas=False
        r.transiciones_conquista={}
        r.registrar_combate('Nigeria','Angola',resultado,juego)
        self.assertFalse(r.transiciones_conquista)
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1000),(0,0))

    def test_ataque_sin_conquista_no_reemplaza_color(self):
        modulo,_=self.cargar_renderer()
        juego=self.preparar_ataque()
        # Defensor con cinco ejércitos; una tirada no puede conquistarlo.
        juego.tablero['Angola']['ejercitos']=5
        with patch('random.randint',side_effect=[6,5,4,1,1,1]):
            resultado=juego.atacar('Nigeria','Angola')
        self.assertFalse(resultado['conquisto'])
        r=modulo.Renderer.__new__(modulo.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        r.animaciones_activas=True
        r.transiciones_conquista={}
        r.registrar_combate('Nigeria','Angola',resultado,juego)
        self.assertFalse(r.transiciones_conquista)
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1100)[0],1)

    def test_nuevo_ataque_desde_pais_conquistado_revela_su_color(self):
        modulo,_=self.cargar_renderer()
        juego=self.preparar_ataque()
        with patch('random.randint',side_effect=[6,5,4,1]):
            resultado=juego.atacar('Nigeria','Angola')
        r=modulo.Renderer.__new__(modulo.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        r.animaciones_activas=True
        r.transiciones_conquista={}
        r.registrar_combate('Nigeria','Angola',resultado,juego)
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1100)[0],1)
        r.combate_visual={'desde':'Angola','inicio':1120}
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1200)[0],0)

    def test_ataque_de_bot_conserva_defensor_anterior(self):
        modulo,_=self.cargar_renderer()
        juego=self.preparar_ataque()
        juego.turno_idx=1
        juego.tablero['Nigeria']['propietario']=1
        juego.tablero['Angola']['propietario']=0
        with patch('random.randint',side_effect=[6,5,4,1]):
            resultado=juego.atacar('Nigeria','Angola')
        self.assertTrue(resultado['ok'])
        self.assertEqual(resultado['defensor_anterior_idx'],0)
        r=modulo.Renderer.__new__(modulo.Renderer)
        r.combate_visual=None
        r.ultima_conquista_visual=None
        r.animaciones_activas=True
        r.transiciones_conquista={}
        r.registrar_combate('Nigeria','Angola',resultado,juego,jugador_idx=1)
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=1400)[0],0)
        self.assertEqual(r._estado_visual_token('Angola',juego,ahora=2060)[0],1)


if __name__=='__main__':
    unittest.main()
