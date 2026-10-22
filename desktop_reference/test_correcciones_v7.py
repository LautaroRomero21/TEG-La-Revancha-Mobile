"""Regresiones v7: asientos, propuestas de bots y mapa consultable."""
import importlib.util
import random
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import logic
from logic import JuegoTEG
from respuestas_pactos import respuesta_propuesta_bot


class ObjetivosAsientos(unittest.TestCase):
    def setUp(self):
        random.seed(1908)
        self.j = JuegoTEG(4, orden_inicial=[2, 0, 3, 1], color_humano=0)

    def test_derecha_es_anterior_en_orden_fijo_no_en_orden_visual(self):
        j = self.j
        self.assertEqual(j.vecino_en_mesa(0,'derecha'),2)
        self.assertEqual(j.vecino_en_mesa(0,'izquierda'),3)
        self.assertEqual(j.vecino_en_mesa(2,'derecha'),1)  # vuelta circular
        self.assertEqual(j.vecino_en_mesa(1,'izquierda'),2)
        j.orden_ronda = [3,1,2,0]  # la rotación NO reordena los asientos
        self.assertEqual(j.vecino_en_mesa(0,'derecha'),2)
        self.assertEqual(j.vecino_en_mesa(0,'izquierda'),3)

    def test_objetivo_color_ausente_recurre_a_derecha(self):
        j = self.j
        # Los cuatro jugadores usan Blanco, Negro, Rojo, Azul. Verde no juega.
        verde={'tipo':'eliminacion','color':'Verde','descripcion':'Destruir ejército Verde','tarjeta_id':17}
        with patch.object(logic,'_objetivos_oficiales',return_value=[dict(verde) for _ in j.jugadores]):
            j._asignar_objetivos()
        for jugador in j.jugadores:
            objetivo=jugador.objetivo
            self.assertTrue(objetivo['objetivo_alternativo'])
            self.assertEqual(objetivo['objetivo_idx'],j.vecino_en_mesa(jugador.idx,'derecha'))
            self.assertIn('derecha',objetivo['descripcion'])

    def test_color_propio_es_alternativa_pero_color_rival_es_objetivo(self):
        j=self.j
        blanco={'tipo':'eliminacion','color':'Blanco','descripcion':'Destruir ejército Blanco','tarjeta_id':12}
        with patch.object(logic,'_objetivos_oficiales',return_value=[dict(blanco) for _ in j.jugadores]):
            j._asignar_objetivos()
        self.assertEqual(j.jugadores[0].objetivo['objetivo_idx'],2)
        self.assertTrue(j.jugadores[0].objetivo['objetivo_alternativo'])
        for jugador in j.jugadores[1:]:
            self.assertEqual(jugador.objetivo['objetivo_idx'],0)
            self.assertFalse(jugador.objetivo.get('objetivo_alternativo',False))

    def test_objetivo_izquierda_apunta_siguiente_en_mesa(self):
        j=self.j
        izquierda={'tipo':'eliminacion','lado':'izquierda','descripcion':'Destruir al jugador de la izquierda','tarjeta_id':18}
        with patch.object(logic,'_objetivos_oficiales',return_value=[dict(izquierda) for _ in j.jugadores]):
            j._asignar_objetivos()
        for jugador in j.jugadores:
            self.assertEqual(jugador.objetivo['objetivo_idx'],j.vecino_en_mesa(jugador.idx,'izquierda'))


class PactoDeBot(unittest.TestCase):
    def setUp(self):
        self.j=JuegoTEG(4,orden_inicial=[0,1,2,3])
        self.j.tablero['Polonia']['propietario']=1
        self.j.tablero['Albania']['propietario']=0
        self.assertTrue(self.j.son_adyacentes('Polonia','Albania'))
        self.j.propuesta_pendiente={'tipo':'pais','a':1,'b':0,'paises':('Polonia','Albania')}

    def test_aceptar_pacto_de_paises_sin_estado_ni_tiradas(self):
        resultado=self.j.aceptar_propuesta_bot(True)
        self.assertEqual(resultado['tipo'],'pais')
        self.assertNotIn('estado',resultado)
        self.assertNotIn('tiradas',resultado)
        titulo,detalle=respuesta_propuesta_bot(resultado,True)
        self.assertEqual(titulo,'PACTO FIRMADO')
        self.assertIn('Polonia',detalle)
        self.assertIn('Albania',detalle)
        self.assertTrue(self.j._prohibido_por_pacto(1,0,'Polonia','Albania'))

    def test_rechazar_pacto_no_lo_registra(self):
        self.assertFalse(self.j.aceptar_propuesta_bot(False))
        titulo,_=respuesta_propuesta_bot(False,False)
        self.assertEqual(titulo,'PACTO RECHAZADO')
        self.assertEqual(len(self.j.pactos_vigentes()),0)

    def test_resultado_ataque_conjunto_y_fallo_sin_excepcion(self):
        titulo,detalle=respuesta_propuesta_bot(
            {'estado':'conquistada','tiradas':4,'destino':'Canada','resultado':'Condominio establecido'},True)
        self.assertEqual(titulo,'ATAQUE CONJUNTO')
        self.assertIn('4',detalle)
        self.assertEqual(respuesta_propuesta_bot(None,True)[0],'PACTO NO FIRMADO')

    @staticmethod
    def _importar_interfaz(solo_renderer=False):
        # Permite probar el armado del popup sin una instalación de pygame.
        falso=types.ModuleType('pygame')
        module_file=Path(__file__).with_name('renderer.py' if solo_renderer else 'main.py')
        modulo=types.ModuleType('_v7_renderer' if solo_renderer else '_v7_main')
        spec=importlib.util.spec_from_file_location(modulo.__name__,module_file)
        modulo.__spec__=spec
        with patch.dict(sys.modules,{'pygame':falso}):
            spec.loader.exec_module(modulo)
        return modulo

    def test_panel_pacto_contiene_focos_visibles_y_mapas_consultables(self):
        renderer_mod=self._importar_interfaz(solo_renderer=True)
        renderer=renderer_mod.Renderer.__new__(renderer_mod.Renderer)
        renderer.popup=None
        renderer.menu_contextual='antiguo menu'
        self.assertTrue(renderer.mostrar_propuesta_pacto(self.j,self.j.propuesta_pendiente))
        p=renderer.popup
        self.assertEqual(p['tipo'],'pacto_propuesta')
        self.assertTrue(p['obligatorio'])
        self.assertEqual([f['pais'] for f in p['focos']],['Polonia','Albania'])
        self.assertEqual([f['jugador'] for f in p['focos']],[1,0])
        posicion=renderer._escalar_coords(self.j.tablero['Albania']['coords'])
        self.assertEqual(renderer.inspeccionar_pais_pacto(posicion,self.j),'Albania')
        self.assertEqual(p['inspeccion'],'Albania')
        self.assertIsNotNone(self.j.propuesta_pendiente)
        self.assertIsNone(renderer.menu_contextual)

    def test_panel_ataque_conjunto_marca_los_tres_territorios(self):
        renderer_mod=self._importar_interfaz(solo_renderer=True)
        renderer=renderer_mod.Renderer.__new__(renderer_mod.Renderer)
        renderer.menu_contextual=None
        pp={'tipo':'agresion','a':1,'b':0,
            'origen_a':'Polonia','origen_b':'Albania','destino':'Turquia'}
        self.assertTrue(renderer.mostrar_propuesta_pacto(self.j,pp))
        self.assertEqual(len(renderer.popup['focos']),3)
        self.assertEqual(renderer.popup['focos'][2]['pais'],'Turquia')

    def test_manejador_real_de_respuesta_pacto_no_crashea(self):
        # Verifica específicamente el trayecto de main.py del traceback de Windows.
        modulo_renderer=self._importar_interfaz(solo_renderer=True)
        anterior=sys.modules.get('renderer')
        sys.modules['renderer']=modulo_renderer
        try:
            modulo_main=self._importar_interfaz(solo_renderer=False)
        finally:
            if anterior is None:sys.modules.pop('renderer',None)
            else:sys.modules['renderer']=anterior
        class StubRenderer:
            pais_seleccionado=None
            pais_objetivo=None
            def __init__(self):self.ventanas=[]
            def mostrar_popup(self,titulo,mensaje):self.ventanas.append((titulo,mensaje))
        r=StubRenderer()
        modulo_main.manejar_pactos('pacto_aceptar_bot',self.j,r)
        self.assertEqual(r.ventanas[0][0],'PACTO FIRMADO')
        self.assertIn('Albania',r.ventanas[0][1])


if __name__=='__main__':
    unittest.main()
