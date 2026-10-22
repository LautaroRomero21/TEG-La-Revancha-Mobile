"""Casos de diplomacia vinculante y menú contextual, reglamento pp. 27-34."""
import unittest
import random
from unittest.mock import patch
from data import PAISES_DATA
from logic import JuegoTEG,FASE_ATACAR,FASE_REAGRUPAR,FASE_TARJETA

class Pactos(unittest.TestCase):
    def setUp(self):
        random.seed(1414)
        self.j=JuegoTEG(n_jugadores=4,orden_inicial=[0,1,2,3])
        j=self.j
        j.etapa='hostilidades';j.etapa_ronda='ATAQUE';j.ronda=3
        j.fase=FASE_ATACAR;j.turno_idx=0;j.situacion='Clásico'
        for p in j.tablero:
            j.tablero[p]['propietario']=3
            j.tablero[p]['ejercitos']=1
            j.tablero[p]['misiles']=0
        for p,owner,tropas in [('Alaska',0,12),('Canada',1,8),('Oregon',2,8),('California',0,13),('Nueva York',1,8),('Brasil',2,10),('Chicago',0,12)]:
            j.tablero[p]['propietario']=owner;j.tablero[p]['ejercitos']=tropas

    def test_pacto_pais_impide_dados(self):
        j=self.j
        self.assertTrue(j.son_adyacentes('Alaska','Canada'))
        pacto=j.proponer_no_agresion(0,1,'pais',paises=('Alaska','Canada'))
        self.assertIsNotNone(pacto)
        self.assertFalse(j.atacar('Alaska','Canada')['ok'])
        j.turno_idx=1
        self.assertFalse(j.atacar('Canada','Alaska')['ok'])

    def test_pacto_diferido_hasta_turno_otro(self):
        j=self.j
        pacto=j.proponer_no_agresion(0,1,'pais',paises=('Alaska','Canada'))
        self.assertTrue(j.romper_pacto(pacto['id'],0))
        self.assertTrue(pacto['activo'])
        j._cierre_turno_diplomatico(0)
        self.assertTrue(pacto['activo'])
        j._cierre_turno_diplomatico(1)
        self.assertFalse(pacto['activo'])

    def test_pacto_termina_si_tercero_ocupa(self):
        j=self.j
        pacto=j.proponer_no_agresion(0,1,'pais',paises=('Alaska','Canada'))
        j.tablero['Canada']['propietario']=2
        j._cambio_control_diplomatico('Canada',1,2)
        self.assertFalse(pacto['activo'])

    def test_pactos_continente_mundial_frontera(self):
        j=self.j
        j.tablero['Mexico']['propietario']=1
        j.tablero['Nueva York']['propietario']=1
        j.tablero['Gran Bretana']['propietario']=0
        j.tablero['Egipto']['propietario']=1
        c=j.proponer_no_agresion(0,1,'continente',continente='America del Norte')
        self.assertIsNotNone(c)
        self.assertTrue(j._prohibido_por_pacto(0,1,'Alaska','Canada'))
        m=j.proponer_no_agresion(0,1,'mundial')
        self.assertIsNotNone(m)
        self.assertTrue(j._prohibido_por_pacto(0,1,'California','Nueva York'))
        # Con frontera intercontinental real: Polonia / Egipto.
        j.tablero['Polonia']['propietario']=0
        f=j.proponer_no_agresion(0,1,'frontera',continentes=('Europa','Africa'))
        self.assertIsNotNone(f)

    def test_proteccion_misiles_por_pacto(self):
        j=self.j
        j.tablero['Alaska']['misiles']=1
        j.tablero['Canada']['ejercitos']=10
        p=j.proponer_no_agresion(0,1,'pais',paises=('Alaska','Canada'))
        self.assertIsNotNone(p)
        self.assertFalse(j.lanzar_misil('Canada',desde='Alaska'))
        self.assertEqual(j.tablero['Alaska']['misiles'],1)

    def test_agresion_conquista_condominio_y_reagrupe(self):
        j=self.j
        # Alianzas Chicago (0), Oregon (1) hacia Las Vegas (2).
        objetivos=set(j.tablero['Chicago']['fronteras'])&set(j.tablero['Oregon']['fronteras'])
        self.assertTrue(objetivos)
        objetivo='Las Vegas'
        j.tablero['Oregon']['propietario']=1
        j.tablero[objetivo]['propietario']=2
        j.tablero[objetivo]['ejercitos']=1
        ag=j.proponer_agresion_conjunta(0,1,'Chicago','Oregon',objetivo)
        self.assertIsNotNone(ag)
        with patch('random.randint', side_effect=[6,6,6,1]):
            resultado=j.ejecutar_agresion_conjunta(ag['id'])
        self.assertEqual(resultado['estado'],'conquistada')
        self.assertIn(objetivo,j.condominios)
        self.assertEqual(set(j.condominios[objetivo]),{0,1})
        self.assertEqual(j.tablero[objetivo]['propietario'],None)
        self.assertEqual(j.tablero[objetivo]['ejercitos'],sum(j.condominios[objetivo].values()))
        self.assertTrue(any(p['tipo']=='condominio' for p in j.pactos_vigentes()))
        j.fase=FASE_REAGRUPAR
        self.assertTrue(j.reagrupar_en_condominio('Chicago',objetivo,1,actor_idx=0))

    def test_condominio_ataque_interno_requiere_ruptura(self):
        j=self.j
        j.condominios['Canada']={0:9,1:2}
        j._sincronizar_condominio('Canada')
        p=j._nuevo_pacto('condominio',0,1,pais='Canada')
        self.assertFalse(j.atacar_condominio('Canada','Canada',defensor_idx=1)['ok'])
        self.assertTrue(j.romper_pacto(p['id'],0))
        self.assertFalse(j.atacar_condominio('Canada','Canada',defensor_idx=1)['ok'])
        j._cierre_turno_diplomatico(1)
        self.assertTrue(j.atacar_condominio('Canada','Canada',defensor_idx=1)['ok'])

    def test_tercero_irrumpe_en_condominio(self):
        j=self.j
        j.condominios['Canada']={0:3,1:1};j._sincronizar_condominio('Canada')
        j.tablero['Alaska']['propietario']=2;j.tablero['Alaska']['ejercitos']=50
        j.turno_idx=2
        with patch('random.randint', side_effect=[6,6,6,1]):
            # Sólo una tirada; el defensor tira un dado y muere.
            res=j.atacar_condominio('Alaska','Canada',defensor_idx=1)
        self.assertTrue(res['ok'])
        self.assertTrue(res['conquisto'])
        self.assertEqual(set(j.condominios['Canada']),{0,2})

    def test_zona_y_penalizacion(self):
        j=self.j
        j.jugadores[0].canjes_realizados=3
        j.jugadores[1].canjes_realizados=3
        j.tablero['Canada']['ejercitos']=1
        j.tablero['Alaska']['propietario']=0
        vecino=next(q for q in j.tablero['Canada']['fronteras'] if q!='Alaska')
        j.tablero[vecino]['propietario']=1
        z=j.proponer_zona_internacional(0,1,'Canada')
        self.assertIsNotNone(z)
        self.assertEqual(z['pendiente'],0)
        j.jugadores[0].tarjetas=['Peru']
        j._cierre_turno_diplomatico(0)
        self.assertEqual(j.jugadores[0].tarjetas,[])
        self.assertEqual(j.descarte_cartas[-1],'Peru')
        self.assertFalse(j._premios_tarjetas(j.jugadores[1]))


    def test_pacto_paises_no_supera_tres_fronteras(self):
        j=self.j
        origen='Alaska'
        destino=next((p for p in j.tablero if j.distancia(origen,p) is None and
                      j.tablero[p]['propietario']==3 and p!=origen),None)
        self.assertIsNotNone(destino)
        self.assertIsNone(j.proponer_no_agresion(0,3,'pais',paises=(origen,destino)))

    def test_agresion_programada_en_turno_del_aliado(self):
        j=self.j
        j.tablero['Oregon']['propietario']=1
        j.tablero['Oregon']['ejercitos']=11
        j.tablero['Las Vegas']['propietario']=2
        j.tablero['Las Vegas']['ejercitos']=1
        ag=j.proponer_agresion_conjunta(0,1,'Chicago','Oregon','Las Vegas',lider=1)
        self.assertIsNotNone(ag)
        self.assertEqual(ag['estado'],'pendiente')
        self.assertIsNone(j.ejecutar_agresion_conjunta(ag['id']))
        j.turno_idx=1
        with patch('random.randint',side_effect=[6,6,6,1]):
            resultado=j.ejecutar_agresion_conjunta(ag['id'])
        self.assertEqual(resultado['estado'],'conquistada')
        self.assertEqual(set(j.condominios['Las Vegas']),{0,1})

    def test_asalto_voluntario_desde_condominio_puede_pausarse(self):
        j=self.j
        j.condominios['Chicago']={0:11,1:10}
        j._sincronizar_condominio('Chicago')
        j.tablero['Las Vegas']['propietario']=2
        j.tablero['Las Vegas']['ejercitos']=250
        ag=j.proponer_agresion_conjunta(0,1,'Chicago','Chicago','Las Vegas',lider=0)
        self.assertIsNotNone(ag)
        self.assertFalse(ag['forzoso'])
        with patch('random.randint',return_value=1):
            resultado=j.ejecutar_agresion_conjunta(ag['id'])
        self.assertEqual(resultado['estado'],'pausada')
        self.assertTrue(j.cancelar_agresion_voluntaria(ag['id'],0))
        self.assertEqual(ag['estado'],'cancelada')

    def test_reagrupe_fuera_turno_del_aliado_humano(self):
        j=self.j
        j.tablero['Oregon']['propietario']=1
        j.tablero['Oregon']['ejercitos']=11
        j.tablero['Las Vegas']['propietario']=2
        j.tablero['Las Vegas']['ejercitos']=1
        ag=j.proponer_agresion_conjunta(0,1,'Chicago','Oregon','Las Vegas',lider=1)
        j.turno_idx=1
        with patch('random.randint',side_effect=[6,6,6,1]):
            j.ejecutar_agresion_conjunta(ag['id'])
        j.fase=FASE_REAGRUPAR
        self.assertFalse(j.preparar_reagrupe_aliado())
        self.assertEqual(j.reagrupe_aliado_pendiente,ag['id'])
        antes=j.ejercitos_de('Las Vegas',0)
        self.assertTrue(j.resolver_reagrupe_aliado('Chicago',1))
        self.assertEqual(j.ejercitos_de('Las Vegas',0),antes+1)
        self.assertTrue(ag['reagrupe_resuelto'])
        self.assertIsNone(j.reagrupe_aliado_pendiente)

    def test_rival_en_condominio_no_se_puede_atacar_desde_afuera(self):
        j=self.j
        j.condominios['Canada']={0:6,1:8}
        j._sincronizar_condominio('Canada')
        pacto=j._nuevo_pacto('condominio',0,1,pais='Canada')
        j.tablero['Alaska']['propietario']=0
        j.tablero['Alaska']['ejercitos']=30
        self.assertFalse(j.atacar_condominio('Alaska','Canada',defensor_idx=1)['ok'])
        j.romper_pacto(pacto['id'],0)
        j._cierre_turno_diplomatico(1)
        self.assertFalse(j.atacar_condominio('Alaska','Canada',defensor_idx=1)['ok'])
        self.assertTrue(j.atacar_condominio('Canada','Canada',defensor_idx=1)['ok'])

if __name__=='__main__':unittest.main()
