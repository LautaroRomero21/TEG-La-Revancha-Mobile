"""Motor de TEG La Revancha basado en el reglamento aportado (edición Yetem).
El núcleo de juego no importa pygame; es comprobable con unittest.
Los pactos públicos y condominios tienen lógica vinculante (pactos.py).
"""
import random
from pactos import DiplomaciaMixin
from collections import deque
from itertools import combinations, product
from data import (
    PAISES_DATA, CONTINENTES, PLAYER_COLORS, PLAYER_NAMES_DEFAULT,
    FIGURAS_TARJETA, FIGURAS_POR_PAIS, SIMBOLOS_CONTINENTES, COLORES_OFICIALES, ISLAS, construir_tablero,
    ejercitos_por_paises, MISIL_COSTO_EJERCITOS,
)

FASE_INCORPORAR = 'INCORPORAR'
FASE_MISILES = 'MISILES'  # Alias histórico; los misiles se disparan durante ATACAR.
FASE_ATACAR = 'ATACAR'
FASE_REAGRUPAR = 'REAGRUPAR'
FASE_TARJETA = 'TARJETA'
FASE_FIN = 'FIN'
FASES_ORDEN = [FASE_INCORPORAR, FASE_ATACAR, FASE_REAGRUPAR, FASE_TARJETA]


def _objetivos_oficiales():
    """19 fichas que aparecen efectivamente en el anexo (pp. 37 y 38).
    El texto de la página 6 habla de 20; la vigésima NO está en el anexo aportado.
    """
    def ocupar(descripcion, completos=(), parciales=None, islas=None, cantidad=0):
        return {'tipo': 'ocupacion', 'descripcion': descripcion,
                'completos': list(completos), 'parciales': dict(parciales or {}),
                'islas': islas or {}, 'cantidad': cantidad}
    A='America del Norte'; B='America Central'; C='America del Sur'
    E='Europa'; S='Asia'; F='Africa'; O='Oceania'
    objetivos = [
        ocupar('4 N.Am., 4 Eur., 4 Asia, 3 S.Am., 3 C.Am., 3 Afr. y 3 Oceanía',
               parciales={A:4,E:4,S:4,C:3,B:3,F:3,O:3}),
        ocupar('Europa y América del Sur', completos=(E,C)),
        ocupar('América del Norte, Oceanía y 5 países de África', completos=(A,O), parciales={F:5}),
        ocupar('Asia y América Central', completos=(S,B)),
        ocupar('América del Norte, 8 de Asia y 4 de Europa', completos=(A,), parciales={S:8,E:4}),
        ocupar('Oceanía, 6 de Asia, 6 de África y 6 de América del Norte', completos=(O,), parciales={S:6,F:6,A:6}),
        ocupar('América Central, 6 de América del Sur, 6 de Europa y 6 de Asia', completos=(B,), parciales={C:6,E:6,S:6}),
        ocupar('América del Sur, África y 8 países de Asia', completos=(C,F), parciales={S:8}),
        ocupar('Oceanía, África, 4 de América Central y 4 de Asia', completos=(O,F), parciales={B:4,S:4}),
        ocupar('Europa, 4 países de Asia y 4 de América del Sur', completos=(E,), parciales={S:4,C:4}),
        ocupar('África, 4 de Europa, 4 de Asia y 6 islas de al menos 3 continentes',
               completos=(F,), parciales={E:4,S:4}, islas={'cantidad':6,'continentes':3}),
        ocupar('Ocupar 35 países', cantidad=35),
        *[{'tipo':'eliminacion', 'color':color, 'descripcion':f'Destruir ejército {color}'}
          for color in COLORES_OFICIALES],
        {'tipo':'eliminacion', 'lado':'izquierda', 'descripcion':'Destruir al jugador de la izquierda'},
    ]
    for numero, objetivo in enumerate(objetivos):
        objetivo['tarjeta_id'] = numero
    return objetivos


def _tres_figuras_validas(figuras):
    """Soldado sustituye libremente a cualquier símbolo. Tres iguales o tres distintos."""
    opciones = [[f] if f != 'Soldado' else ['Avion','Tanque','Granada','Barco'] for f in figuras]
    return any(len(set(x)) in (1,3) for x in product(*opciones))


class Jugador:
    def __init__(self, idx, nombre, es_bot=False, color_idx=None):
        self.idx, self.nombre, self.es_bot = idx, nombre, es_bot
        self.color_idx = idx if color_idx is None else color_idx
        self.color = PLAYER_COLORS[self.color_idx]
        self.color_nombre = COLORES_OFICIALES[self.color_idx]
        self.tarjetas = []
        self.tarjetas_premiadas = set()
        self.cartas_continente = set()
        self.continentes_usados = set()
        self.misiles = 0  # Los misiles están en los países, no en esta reserva.
        self.eliminado = False
        self.objetivo = None
        self.objetivos = []  # 2 en partidas de 2 jugadores.
        self.canjes_realizados = 0
        self.canje_ultima_ronda = -1
        self.estilo_bot = None  # Perfil estratégico persistente por partida.


class JuegoTEG(DiplomaciaMixin):
    MAX_DADOS_ATACANTE = 4
    MAX_DADOS_DEFENSOR = 4

    def __init__(self, n_jugadores=4, nombres=None, color_humano=0, orden_inicial=None, objetivos_eliminacion=True):
        if not 2 <= n_jugadores <= 6:
            raise ValueError('Se requieren entre 2 y 6 jugadores (1 humano, resto bots).')
        if not isinstance(color_humano,int) or not 0 <= color_humano < 6:
            raise ValueError('Color humano fuera del rango (0-5)')
        colores = [color_humano] + [c for c in range(6) if c != color_humano][:n_jugadores-1]
        self.n_jugadores = n_jugadores
        self.objetivos_eliminacion = bool(objetivos_eliminacion)
        self.jugadores = [Jugador(i, nombres[i] if nombres and i < len(nombres)
                                 else ('Humano '+COLORES_OFICIALES[colores[i]] if i==0 else 'Bot '+COLORES_OFICIALES[colores[i]]),
                                 i != 0, color_idx=colores[i])
                          for i in range(n_jugadores)]
        if orden_inicial is None:
            self.orden_base = random.sample(list(range(n_jugadores)), n_jugadores)
        else:
            if sorted(orden_inicial) != list(range(n_jugadores)):
                raise ValueError('Orden de juego no válido')
            self.orden_base = list(orden_inicial)
        self.orden_ronda = list(self.orden_base)
        self.indice_turno_ronda = 0
        self.tablero = construir_tablero()
        self._iniciar_diplomacia()
        self.mazo_cartas_pais = list(PAISES_DATA)
        random.shuffle(self.mazo_cartas_pais)
        self.descarte_cartas = []
        self.figuras_cartas = self._crear_figuras()
        self.mazo_situacion = (['Clásico']*20 + ['Nieve']*4 + ['Viento a favor']*4 +
                               ['Crisis']*4 + ['Refuerzos extras']*4 +
                               ['Fronteras abiertas']*4 + ['Fronteras cerradas']*4 +
                               [f'Descanso {c}' for c in COLORES_OFICIALES])
        random.shuffle(self.mazo_situacion)
        self.descarte_situacion = []
        self.situacion = 'Clásico'
        self.crisis_sin_tarjeta = set()
        self.turno_idx = self.orden_ronda[0]
        self.primero_de_ronda = self.turno_idx
        self.ronda = 0
        self.fase = FASE_INCORPORAR
        self.etapa = 'preparacion'
        self.etapa_ronda = 'PREPARACION'  # INCORPORACION para todos, luego ATAQUE para todos.
        self.incorporaciones_completadas = []
        self.bot_refuerzos_por_pais = {}
        self.bot_reagrupes_turno = 0
        self.vuelta_preparacion = 0  # 0: 8; 1: 4, salvo 2 jugadores = 18 una vez.
        self.preparacion_pendientes = 0
        self.ejercitos_a_colocar = 0
        self.refuerzos_continente = {}
        self.conquista_pendiente = None
        self.conquistas_compartidas_por_jugador={i:0 for i in range(n_jugadores)}
        self.conquisto_pais = False
        self.conquistas_turno = 0
        self.tarjeta_solicitada = False
        self.bot_ataques_turno = 0
        self.bot_reagrupe_turno = False
        self.continentes_inicio_turno = set()
        self.reagrupados_recibidos = {}  # para impedir movimiento indirecto en el mismo turno
        self.historial = []
        self.canje_numero = 0
        self.ganador_idx = None
        self._ultimo_atacante = None
        self.propuesta_pendiente = None
        self.reagrupe_aliado_pendiente = None
        self._bot_diplomacia_intentada = set()
        self._repartir_paises()
        self._asignar_objetivos()
        perfiles = ['Agresivo', 'Defensivo', 'Objetivo', 'Oportunista', 'Equilibrado']
        random.SystemRandom().shuffle(perfiles)
        for i, jugador in enumerate(self.jugadores[1:]):
            jugador.estilo_bot = perfiles[i % len(perfiles)]
        self.ejercitos_a_colocar = 18 if n_jugadores == 2 else 8
        self.log('ORDEN INICIAL: ' + ' > '.join(self.jugadores[i].nombre for i in self.orden_ronda))
        self.log('ESTRATEGIAS BOTS: '+', '.join(f'{j.nombre}: {j.estilo_bot}' for j in self.jugadores if j.es_bot))
        self.log(f'PREPARACIÓN: {self.ejercitos_a_colocar} ejércitos por participante.')

    @staticmethod
    def _crear_figuras():
        """Figuras reales, extraídas de las 72 cartas del PDF aportado."""
        return dict(FIGURAS_POR_PAIS)

    def log(self, texto):
        self.historial.append(texto)
        self.historial = self.historial[-300:]

    def jugador_actual(self):
        return self.jugadores[self.turno_idx]

    def orden_visual_jugadores(self):
        """Orden de la ronda actual; eliminados visibles únicamente al final."""
        vivos=[i for i in self.orden_ronda if not self.jugadores[i].eliminado]
        fuera=[j.idx for j in self.jugadores if j.eliminado and j.idx not in vivos]
        return vivos+fuera

    def paises_de(self, jugador_idx):
        # Un condominio no pertenece en exclusiva a nadie; sí cuenta como país
        # ocupado por ambos para evitar eliminaciones erróneas.
        return [p for p,d in self.tablero.items() if d['propietario']==jugador_idx
                or jugador_idx in self.condominios.get(p,{})]

    def paises_exclusivos(self, jugador_idx):
        return [p for p,d in self.tablero.items() if d['propietario']==jugador_idx]

    def _repartir_paises(self):
        paises = list(PAISES_DATA)
        random.shuffle(paises)
        for i,p in enumerate(paises):
            self.tablero[p]['propietario'] = i % self.n_jugadores
            self.tablero[p]['ejercitos'] = 1

    def vecino_en_mesa(self, jugador_idx, lado):
        """Vecinos de asiento FIJOS: no cambian cuando rota el primer turno.

        En esta versión de la mesa, quien jugó inmediatamente antes está a la
        derecha (-1), y quien juega a continuación está a la izquierda (+1).
        El `orden_ronda` cambia de primer jugador, nunca cambia las sillas.
        """
        if lado not in ('derecha', 'izquierda'):
            raise ValueError('Lado desconocido')
        pos = self.orden_base.index(jugador_idx)
        desplazamiento = -1 if lado == 'derecha' else 1
        return self.orden_base[(pos + desplazamiento) % self.n_jugadores]

    def _asignar_objetivos(self):
        objetivos = _objetivos_oficiales()
        if self.n_jugadores <= 3:
            objetivos = [o for o in objetivos if o['tipo'] != 'eliminacion' and o.get('cantidad') != 35]
        elif not self.objetivos_eliminacion:
            objetivos = [o for o in objetivos if o['tipo'] != 'eliminacion']
        random.shuffle(objetivos)
        por_jugador = 2 if self.n_jugadores == 2 else 1
        for jugador in self.jugadores:
            jugador.objetivos = []
            for _ in range(por_jugador):
                o = dict(objetivos.pop())
                if o['tipo'] == 'eliminacion':
                    if o.get('lado') == 'izquierda':
                        o['objetivo_idx'] = self.vecino_en_mesa(jugador.idx, 'izquierda')
                        o['descripcion'] += f' ({self.jugadores[o["objetivo_idx"]].nombre})'
                    else:
                        objetivo_color = next((j.idx for j in self.jugadores
                                               if j.color_nombre == o['color']
                                               and j.idx != jugador.idx), None)
                        if objetivo_color is None:
                            # Color ausente o el propio: se activa la alternativa
                            # de la tarjeta, jugador sentado a la derecha.
                            o['objetivo_idx'] = self.vecino_en_mesa(jugador.idx, 'derecha')
                            o['objetivo_alternativo'] = True
                            motivo = ('es tu propio color' if jugador.color_nombre == o['color']
                                      else 'no participa')
                            o['descripcion'] = (f'Color {o["color"]}: {motivo}. '
                                                f'Destruir al jugador de tu derecha: '
                                                f'{self.jugadores[o["objetivo_idx"]].nombre}')
                        else:
                            o['objetivo_idx'] = objetivo_color
                            o['descripcion'] += f' ({self.jugadores[objetivo_color].nombre})'
                jugador.objetivos.append(o)
            jugador.objetivo = jugador.objetivos[0]

    def son_adyacentes(self, a, b):
        return a in self.tablero and b in self.tablero and b in self.tablero[a]['fronteras']

    def paises_limites_enemigos(self, pais):
        propio=self.tablero[pais]['propietario']
        return [p for p in self.tablero[pais]['fronteras'] if
                self.tablero[p]['propietario'] != propio]

    def puede_atacar_desde(self, pais):
        return (pais in self.tablero and self.es_propietario(pais,self.turno_idx)
                and self.ejercitos_de(pais,self.turno_idx) > 1 and
                any(self._ataque_permitido(pais,p) for p in self.paises_limites_enemigos(pais)))

    def _pais_bloqueado(self, pais):
        if pais in self.condominios:return False
        vecinos = self.tablero[pais]['fronteras']
        if len(vecinos) < 3 or len(self.paises_de(self.tablero[pais]['propietario'])) == 1:
            return False
        # El bloqueo exige que TODOS los limítrofes sean del mismo color.
        # Un país en condominio no es propiedad exclusiva de un único color.
        if any(v in self.condominios for v in vecinos):
            return False
        dueños = {self.tablero[v]['propietario'] for v in vecinos}
        return (len(dueños)==1 and None not in dueños
                and self.tablero[pais]['propietario'] not in dueños
                and all(self.tablero[v]['ejercitos']>=2 for v in vecinos))

    def _controla_continente(self, j, cont):
        return all(d['propietario']==j for d in self.tablero.values() if d['continente']==cont)

    def _revocar_tarjetas_continente_por_perdida(self, continente=None):
        """Revoca inmediatamente tarjetas cuyo continente dejó de controlarse.

        Se llama al cambiar una propiedad (conquistas normales y condominios).
        Una tarjeta que ya fue canjeada nunca se devuelve.
        """
        continentes=(continente,) if continente is not None else CONTINENTES
        for cont in continentes:
            for jugador in self.jugadores:
                if cont in jugador.cartas_continente and not self._controla_continente(jugador.idx,cont):
                    jugador.cartas_continente.discard(cont)
                    self.log(f'{jugador.nombre} pierde tarjeta de continente: {cont}')

    def _dados_para_ataque(self, tropas_atacantes, tropas_defensoras):
        """Dados automáticos según pág. 12 del reglamento.

        La ventaja de doble fuerza puede dar un cuarto dado aun en Clásico.
        El viento también da un dado adicional, siempre hasta cuatro.
        """
        cantidad=min(3,tropas_atacantes-1)
        ventaja=(tropas_defensoras>=3 and tropas_atacantes>=2*tropas_defensoras)
        if ventaja:
            cantidad=4
        viento=self.situacion=='Viento a favor'
        if viento:
            cantidad=min(4,cantidad+1)
        razon=None
        if cantidad==4:
            if ventaja and viento:razon='DOBLE FUERZA / VIENTO A FAVOR'
            elif ventaja:razon='DOBLE FUERZA (regla oficial)'
            else:razon='VIENTO A FAVOR'
        return cantidad,razon

    def _calcular_incorporacion(self, jugador):
        base = ejercitos_por_paises(len(self.paises_exclusivos(jugador.idx)))
        self.refuerzos_continente = {
            c: info['bonus'] for c,info in CONTINENTES.items() if self._controla_continente(jugador.idx,c)
        }
        extras = len(self.paises_exclusivos(jugador.idx))//2 if self.situacion=='Refuerzos extras' else 0
        total = base + sum(self.refuerzos_continente.values())+extras
        self.log(f'Incorpora {total}: países {base}, continentes {sum(self.refuerzos_continente.values())}, extra {extras}')
        return total

    def _siguiente_situacion(self):
        """Extrae exactamente una de las 50 cartas sin reemplazo.

        Una carta de descanso de un color que no esté en juego se consume,
        pero en esta edición se aplica COMBATE CLÁSICO (no se vuelve a robar).
        """
        if not self.mazo_situacion:
            self.mazo_situacion, self.descarte_situacion = self.descarte_situacion, []
            random.shuffle(self.mazo_situacion)
        carta=self.mazo_situacion.pop()
        self.descarte_situacion.append(carta)
        colores_activos={j.color_nombre for j in self.jugadores if not j.eliminado}
        if carta.startswith('Descanso ') and carta[len('Descanso '):] not in colores_activos:
            self.log(f'{carta}: color fuera de la partida; se aplica Combate clásico')
            carta='Clásico'
        self.situacion=carta
        self.crisis_sin_tarjeta=set()
        if carta=='Crisis':
            activos=[j for j in self.jugadores if not j.eliminado]
            dados={j.idx:random.randint(1,6) for j in activos}
            minimo=min(dados.values())
            self.crisis_sin_tarjeta={i for i,x in dados.items() if x==minimo}
            self.log('Crisis: sin tarjeta '+', '.join(self.jugadores[i].nombre for i in self.crisis_sin_tarjeta))
        self.log(f'TARJETA DE SITUACIÓN: {carta}')

    def _comenzar_hostilidades(self):
        self.etapa = 'hostilidades'
        self.etapa_ronda = 'ATAQUE'  # Ronda 1 sin nuevos refuerzos.
        self.ronda = 1
        self.orden_ronda = list(self.orden_base)
        self.indice_turno_ronda = 0
        self.turno_idx = self.primero_de_ronda = self.orden_ronda[0]
        # La primera ronda de hostilidades es siempre clásica: no se saca
        # ninguna carta del mazo hasta que comienza la segunda ronda.
        self.situacion = 'Clásico'
        self.crisis_sin_tarjeta.clear()
        self.log('RONDA 1: combate clásico, sin extracción de tarjeta de situación.')
        self._empezar_turno(inicial=True)

    def _empezar_turno(self, inicial=False):
        j=self.jugador_actual()
        self.conquisto_pais=False
        self.conquistas_turno=0
        self.conquistas_colectivas=self.conquistas_compartidas_por_jugador.get(self.turno_idx,0)
        self.tarjeta_solicitada=False
        self.bot_ataques_turno=0
        self.bot_reagrupe_turno=False
        self.bot_reagrupes_turno=0
        self.bot_refuerzos_por_pais={}
        self.conquista_pendiente=None
        self.reagrupados_recibidos={}
        self.continentes_inicio_turno={c for c in CONTINENTES if self._controla_continente(j.idx,c)}
        if inicial:
            self.refuerzos_continente={}
            self.ejercitos_a_colocar=0
            self.fase=FASE_ATACAR
        else:
            self.fase=FASE_INCORPORAR
            self.ejercitos_a_colocar=self._calcular_incorporacion(j)
        self.log(f'Ronda {self.ronda}: turno de {j.nombre} ({self.fase})')

    def desglose_incorporacion(self):
        """Saldos pendientes que muestra la interfaz durante la incorporación.

        Los refuerzos libres abarcan la mitad de países (mínimo 4), extras de
        situación y canjes; los de continente sólo pueden ir a ese continente.
        """
        continentes={c:n for c,n in self.refuerzos_continente.items() if n>0}
        libres=max(0,self.ejercitos_a_colocar-sum(continentes.values()))
        return {'libres':libres,'continentes':continentes,'total':self.ejercitos_a_colocar}

    def incorporar(self, pais, cantidad=1):
        if (self.fase!=FASE_INCORPORAR or pais not in self.tablero or
            not self.es_propietario(pais,self.turno_idx) or
            cantidad<1 or cantidad>self.ejercitos_a_colocar or self._pais_bloqueado(pais) and self.etapa!='preparacion'):
            return False
        obligatorios=sum(self.refuerzos_continente.values())
        pool=self.refuerzos_continente.get(self.tablero[pais]['continente'],0)
        disponibles_generales=self.ejercitos_a_colocar-obligatorios
        # No gastar refuerzos de un continente en otro; priorizar su propio fondo.
        a_cont=min(cantidad,pool)
        if cantidad-a_cont>disponibles_generales:
            return False
        if a_cont:
            self.refuerzos_continente[self.tablero[pais]['continente']]-=a_cont
        self._ajustar_guarnicion(pais,self.turno_idx,cantidad)
        self.ejercitos_a_colocar-=cantidad
        self.log(f'{self.jugador_actual().nombre} incorpora {cantidad} en {pais}')
        if self.ejercitos_a_colocar==0:
            self.avanzar_fase()
        return True

    def incorporar_misil(self, pais, reemplazar=False):
        """Añade misil a país. Costo 6 fuerzas nuevas o sustituye 6 ejércitos existentes.
        Debe quedar al menos un ejército de ocupación.
        """
        if (self.fase!=FASE_INCORPORAR or pais not in self.tablero or
            self.tablero[pais]['propietario']!=self.turno_idx or
            self._pais_bloqueado(pais) and self.etapa!='preparacion'):
            return False
        if reemplazar:
            if self.tablero[pais]['ejercitos']<7:
                return False
            self.tablero[pais]['ejercitos']-=MISIL_COSTO_EJERCITOS
        else:
            if self.ejercitos_a_colocar < MISIL_COSTO_EJERCITOS:
                return False
            obligatorios=sum(self.refuerzos_continente.values())
            pool=self.refuerzos_continente.get(self.tablero[pais]['continente'],0)
            a_cont=min(MISIL_COSTO_EJERCITOS,pool)
            if MISIL_COSTO_EJERCITOS-a_cont > self.ejercitos_a_colocar-obligatorios:
                return False
            # Sólo se descuenta el bono continental si ese continente aportó
            # ejércitos al misil. Si no se controla, su clave no existe en el
            # diccionario y la compra debe financiarse con refuerzos libres.
            if a_cont:
                self.refuerzos_continente[self.tablero[pais]['continente']]-=a_cont
            self.ejercitos_a_colocar-=MISIL_COSTO_EJERCITOS
        self.tablero[pais]['misiles']+=1
        self.log(f'Misil añadido a {pais} ({"sustituye 6" if reemplazar else "cuesta 6 refuerzos"})')
        if not reemplazar and self.ejercitos_a_colocar==0:
            self.avanzar_fase()
        return True

    def comprar_misil(self):
        self.log('Seleccioná un país propio e incorporá un misil usando 6 ejércitos (regla oficial).')
        return False

    def distancia(self, origen, destino, limite=3):
        if origen not in self.tablero or destino not in self.tablero:
            return None
        q=deque([(origen,0)]); vistos={origen}
        while q:
            p,dist=q.popleft()
            if p==destino:
                return dist
            if dist>=limite:continue
            for v in self.tablero[p]['fronteras']:
                if v not in vistos:
                    vistos.add(v);q.append((v,dist+1))
        return None

    def _ataque_permitido(self, desde, hacia, actor_idx=None, defensor_idx=None):
        if not self.son_adyacentes(desde,hacia): return False
        actor=self.turno_idx if actor_idx is None else actor_idx
        defensor=self.tablero[hacia]['propietario'] if defensor_idx is None else defensor_idx
        if defensor is not None and self._prohibido_por_pacto(actor,defensor,desde,hacia):return False
        misma=self.tablero[desde]['continente']==self.tablero[hacia]['continente']
        if self.situacion=='Fronteras cerradas' and not misma: return False
        if self.situacion=='Fronteras abiertas' and misma: return False
        return True

    def lanzar_misil(self, pais_objetivo, desde=None):
        if (self.fase!=FASE_ATACAR or self.conquista_pendiente or pais_objetivo not in self.tablero
            or self.situacion==f'Descanso {self.jugador_actual().color_nombre}'):
            return False
        if self.tablero[pais_objetivo]['propietario']==self.turno_idx or pais_objetivo in self.condominios:
            return False
        candidatos=([desde] if desde else self.paises_de(self.turno_idx))
        validos=[]
        for p in candidatos:
            if p not in self.tablero or self.tablero[p]['propietario']!=self.turno_idx or self.tablero[p]['misiles']==0:
                continue
            distancia=self.distancia_misil_legal(p,pais_objetivo,self.turno_idx)
            if distancia is None or not 1<=distancia<=3:continue
            if self._prohibido_por_pacto(self.turno_idx,self.tablero[pais_objetivo]['propietario'],p,pais_objetivo):continue
            daño=4-distancia
            destino=self.tablero[pais_objetivo]
            if destino['ejercitos']<=daño:continue
            if destino['misiles']>=self.tablero[p]['misiles']:continue
            if not self._ataque_permitido_misil(p,pais_objetivo):continue
            validos.append((daño,p))
        if not validos: return False
        daño,origen=max(validos)
        self.tablero[origen]['misiles']-=1
        self.tablero[pais_objetivo]['ejercitos']-=daño
        self.log(f'MISIL {origen} -> {pais_objetivo}: {daño} bajas; no conquista')
        return True

    def _ataque_permitido_misil(self, desde, hacia):
        # Situación de fronteras es para ataques, también se aplica al misil.
        misma=self.tablero[desde]['continente']==self.tablero[hacia]['continente']
        if self.situacion=='Fronteras cerradas' and not misma:return False
        if self.situacion=='Fronteras abiertas' and misma:return False
        return True

    def atacar(self, desde, hacia, n_dados_atk=3, actor_idx=None, conjunto=False, defensor_idx=None):
        actor=self.turno_idx if actor_idx is None else actor_idx
        if hacia in self.condominios:
            return self.atacar_condominio(desde,hacia,defensor_idx=defensor_idx,actor_idx=actor)
        res={'ok':False,'dados_atk':[],'dados_def':[], 'bajas_atk':0,'bajas_def':0,'conquisto':False}
        if actor!=self.turno_idx and not (conjunto and self._ataque_conjunto_en_curso):return res
        if (self.fase!=FASE_ATACAR or self.conquista_pendiente or
            self.situacion==f'Descanso {self.jugadores[actor].color_nombre}' or
            desde not in self.tablero or hacia not in self.tablero or
            not self.es_propietario(desde,actor) or
            self.tablero[hacia]['propietario']==actor or
            self.tablero[hacia]['ejercitos']<1 or
            not self._ataque_permitido(desde,hacia,actor_idx=actor) or
            self.ejercitos_de(desde,actor)<2 or not isinstance(n_dados_atk,int) or n_dados_atk<1):
            return res
        a=self.tablero[desde]; b=self.tablero[hacia]
        # Instantánea previa a la tirada: permite al renderer enseñar el color
        # del defensor aun cuando la conquista ya cambió el dueño en el motor.
        defensor_anterior_idx=b['propietario']
        ejercitos_defensor_antes=b['ejercitos']
        if desde in self.condominios and b['propietario'] in self.condominios[desde]:return res
        tropas_actor=self.ejercitos_de(desde,actor)
        maxatk,razon_4_dados=self._dados_para_ataque(tropas_actor,b['ejercitos'])
        maxdef=min(3,b['ejercitos'])
        if self.situacion=='Nieve': maxdef=min(4,maxdef+1)
        da=sorted((random.randint(1,6) for _ in range(maxatk)),reverse=True)
        dd=sorted((random.randint(1,6) for _ in range(maxdef)),reverse=True)
        ba=min(tropas_actor-1, sum(x<=y for x,y in zip(da,dd)))
        bd=min(b['ejercitos'], sum(x>y for x,y in zip(da,dd)))
        self._ajustar_guarnicion(desde,actor,-ba)
        b['ejercitos']-=bd
        conquisto=b['ejercitos']==0
        if conquisto:
            anterior=b['propietario']
            b['propietario']=actor
            # Una tarjeta de continente pendiente se devuelve en el instante
            # en que deja de controlarse todo el continente, NO en el próximo turno.
            self._revocar_tarjetas_continente_por_perdida(b['continente'])
            zona_al_conquistar=self.zona_para(hacia)
            cumplir_zona=bool(zona_al_conquistar and zona_al_conquistar['pendiente']==actor)
            self._cambio_control_diplomatico(hacia,anterior,actor)
            # Los misiles pertenecen al PAÍS, no al jugador derrotado:
            # se capturan intactos y pueden dispararse desde ese país.
            # Reglamento: Ataques con misiles, pág. 17, apartado 2.
            if b['misiles']:
                self.log(f'MISILES CAPTURADOS: {b["misiles"]} en {hacia} para {self.jugador_actual().nombre}')
            self.conquisto_pais=True
            if conjunto:
                aliado=next(i for i in next(ag for ag in self.agresiones_pendientes if ag['estado']=='en_curso' and ag['destino']==hacia)['jugadores'] if i!=actor)
                self.conquistar_en_condominio(desde,hacia,actor,aliado)
            else:
                self.conquistas_turno+=1
            disponibles=self.ejercitos_de(desde,actor)-1
            max_pasar=min(3,disponibles)
            # Un país conquistado debe ocuparlo al menos un ejército; validación de regla.
            if not conjunto:
                if max_pasar<1:
                    raise AssertionError('Conquista sin ejército de ocupación disponible')
                if cumplir_zona:
                    self._transferir_conquista(desde,hacia,1)
                elif self.jugadores[actor].es_bot or max_pasar==1:
                    self._transferir_conquista(desde,hacia,max_pasar)
                else:
                    self.conquista_pendiente={'desde':desde,'hacia':hacia,
                                              'max_pasar':max_pasar,'disponibles':disponibles}
            self._ultimo_atacante=actor
            self._verificar_eliminacion(anterior, actor)
        self.log(f'ATAQUE {desde}->{hacia}: {da} vs {dd}; pérdidas {ba}/{bd}' + (' CONQUISTA' if conquisto else '')
                 + (f' | 4 DADOS: {razon_4_dados}' if razon_4_dados else ''))
        res.update(ok=True,dados_atk=da,dados_def=dd,bajas_atk=ba,bajas_def=bd,
                   conquisto=conquisto,desde=desde,hacia=hacia,razon_4_dados=razon_4_dados,
                   atacante_idx=actor,defensor_anterior_idx=defensor_anterior_idx,
                   ejercitos_defensor_antes=ejercitos_defensor_antes)
        if not self.conquista_pendiente and not conjunto:
            self._verificar_victoria(self.jugadores[actor])
        return res

    def _transferir_conquista(self, desde, hacia, cantidad):
        self._ajustar_guarnicion(desde,self.turno_idx,-cantidad)
        self.tablero[hacia]['ejercitos']+=cantidad
        self.log(f'OCUPACIÓN {desde}->{hacia}: pasan {cantidad} ejércitos')

    def resolver_conquista(self, cantidad):
        """cantidad: TOTAL a mover (1..3), no un adicional a un movimiento previo."""
        p=self.conquista_pendiente
        if not p or not isinstance(cantidad,int) or not 1<=cantidad<=p['max_pasar']:
            return False
        zona=self.zona_para(p['hacia'])
        if zona and zona['pendiente']==self.turno_idx and cantidad!=1:return False
        self._transferir_conquista(p['desde'],p['hacia'],cantidad)
        self.conquista_pendiente=None
        self._verificar_victoria(self.jugador_actual())
        return True

    def _verificar_eliminacion(self, victima_idx, atacante_idx=None):
        if victima_idx is None or self.paises_de(victima_idx):return
        victima=self.jugadores[victima_idx]
        if victima.eliminado:return
        victima.eliminado=True
        if atacante_idx is not None:
            atacante=self.jugadores[atacante_idx]
            total=len(victima.tarjetas)
            atacante.tarjetas.extend(victima.tarjetas)
            # Las tarjetas heredadas dan derecho al premio si el nuevo titular
            # también posee el país correspondiente. Su uso por el jugador
            # eliminado no cancela el derecho del nuevo propietario.
            # El premio se comprueba al llegar a la fase TARJETA.
            self.log(f'{atacante.nombre} hereda {total} tarjetas de {victima.nombre}')
        victima.tarjetas.clear()
        victima.tarjetas_premiadas.clear()
        for jugador in self.jugadores:
            for obj in jugador.objetivos:
                if obj['tipo']=='eliminacion' and obj['objetivo_idx']==victima_idx:
                    if jugador.idx!=atacante_idx:
                        obj['imposible']=True  # solo le queda el objetivo común de 45.
        self.log(f'ELIMINADO: {victima.nombre}')

    def _cumple_ocupacion(self, jidx, obj):
        mis=set(self.paises_exclusivos(jidx))
        for c in obj.get('completos',[]):
            if not self._controla_continente(jidx,c):return False
        for c,n in obj.get('parciales',{}).items():
            if sum(PAISES_DATA[p]['continente']==c for p in mis)<n:return False
        req=obj.get('islas') or {}
        if req:
            propias=mis & ISLAS
            if len(propias)<req['cantidad']:return False
            if len({PAISES_DATA[p]['continente'] for p in propias})<req['continentes']:return False
        if obj.get('cantidad',0)>len(mis):return False
        if self.n_jugadores==3:
            # Mínimo de 10 países extras: encima de los mínimos del objetivo.
            demanda={c:len([p for p in PAISES_DATA if PAISES_DATA[p]['continente']==c])
                     for c in obj.get('completos',[])}
            for c,n in obj.get('parciales',{}).items():demanda[c]=max(demanda.get(c,0),n)
            minimo=max(obj.get('cantidad',0),sum(demanda.values()))
            if req:
                # Las islas ya requeridas por otros criterios cuentan; las
                # adicionales necesarias se suman al mínimo del objetivo.
                islas_incluidas=sum(min(demanda.get(c,0),sum(PAISES_DATA[p]['continente']==c for p in ISLAS))
                                    for c in demanda)
                minimo+=max(0,req['cantidad']-islas_incluidas)
            if len(mis)<minimo+10:return False
        return True

    def _verificar_victoria(self, jugador):
        if self.fase=='VICTORIA' or self.etapa=='preparacion':return False
        if len(self.paises_exclusivos(jugador.idx))>=45:
            motivo='45 países (objetivo común)'
        else:
            resultados=[]
            for obj in jugador.objetivos:
                if obj['tipo']=='eliminacion':
                    exito=(not obj.get('imposible') and self.jugadores[obj['objetivo_idx']].eliminado
                           and self._ultimo_atacante==jugador.idx)
                else:exito=self._cumple_ocupacion(jugador.idx,obj)
                resultados.append(exito)
            if not resultados or not all(resultados):return False
            motivo='objetivo(s) secreto(s)'
        self.ganador_idx=jugador.idx
        self.fase='VICTORIA'
        self.log(f'VICTORIA de {jugador.nombre}: {motivo}')
        return True

    def reagrupar(self, desde, hacia, cantidad):
        if hacia in self.condominios:
            return self.reagrupar_en_condominio(desde,hacia,cantidad)
        if (self.fase!=FASE_REAGRUPAR or self.situacion==f'Descanso {self.jugador_actual().color_nombre}'
            or desde not in self.tablero or hacia not in self.tablero
            or not self.son_adyacentes(desde,hacia) or cantidad<1
            or self.tablero[desde]['propietario']!=self.turno_idx or self.tablero[hacia]['propietario']!=self.turno_idx
            or self.tablero[desde]['ejercitos']-1-self.reagrupados_recibidos.get(desde,0)<cantidad):
            return False
        if self.zona_para(hacia):return False  # Mantener exactamente una ficha.
        self.tablero[desde]['ejercitos']-=cantidad
        self.tablero[hacia]['ejercitos']+=cantidad
        self.reagrupados_recibidos[hacia]=self.reagrupados_recibidos.get(hacia,0)+cantidad
        self.log(f'REAGRUPE {desde}->{hacia}: {cantidad} ejércitos')
        return True

    def reagrupar_misil(self, desde, hacia):
        if (self.fase!=FASE_REAGRUPAR or self.situacion==f'Descanso {self.jugador_actual().color_nombre}'
            or desde not in self.tablero or hacia not in self.tablero
            or not self.son_adyacentes(desde,hacia) or self.tablero[desde]['propietario']!=self.turno_idx
            or self.tablero[hacia]['propietario']!=self.turno_idx or self.tablero[desde]['misiles']<1):
            return False
        self.tablero[desde]['misiles']-=1
        self.tablero[hacia]['misiles']+=1
        self.log(f'Misil reagrupado {desde}->{hacia}')
        return True

    def valor_canje(self, jugador=None):
        """Valor del próximo canje DE ESE JUGADOR.

        Cada participante inicia su propia secuencia con 6, 10, 15, 20...
        No se ve afectada por los canjes de los bots o de otros jugadores.
        """
        jugador = jugador if jugador is not None else self.jugador_actual()
        anteriores = jugador.canjes_realizados
        if anteriores == 0:return 6
        return 10 + 5 * (anteriores - 1)

    def combinacion_canje(self, jugador=None):
        """Devuelve combinación de 3 cartas de país válida, si existe."""
        jugador=jugador or self.jugador_actual()
        for indices in combinations(range(len(jugador.tarjetas)),3):
            figuras=[self.figuras_cartas[jugador.tarjetas[i]] for i in indices]
            if 'Super' not in figuras and _tres_figuras_validas(figuras):
                return list(indices)
        return None

    @staticmethod
    def _figuras_continente(cont):
        return [s for s in SIMBOLOS_CONTINENTES.get(cont,()) if s!='CANJE']

    def opcion_canje(self, jugador=None):
        """Retorna (índices de cartas de país, continentes), incluida supertarjeta.
        Una tarjeta mayor (Am. Norte, Europa, Asia) constituye un canje sola.
        """
        jugador=jugador or self.jugador_actual()
        for i,carta in enumerate(jugador.tarjetas):
            if self.figuras_cartas[carta]=='Super':return [i],[]
        for c in ('America del Norte','Europa','Asia'):
            if c in jugador.cartas_continente and self._controla_continente(jugador.idx,c):return [],[c]
        # Combinación de tres símbolos, mediante tarjetas de país y continentes.
        continentales=sorted(c for c in jugador.cartas_continente
                             if self._controla_continente(jugador.idx,c))
        for n_cont in range(min(3,len(continentales))+1):
            for conts in combinations(continentales,n_cont):
                simbolos=[]
                for c in conts:simbolos+=self._figuras_continente(c)
                if len(simbolos)>3:continue
                paises_necesarios=3-len(simbolos)
                for indices in combinations(range(len(jugador.tarjetas)),paises_necesarios):
                    figuras=simbolos+[self.figuras_cartas[jugador.tarjetas[i]] for i in indices]
                    if len(figuras)==3 and 'Super' not in figuras and _tres_figuras_validas(figuras):
                        return list(indices),list(conts)
        return None

    def canje_valido(self, indices=(), continentes=(), jugador=None):
        jugador=jugador or self.jugador_actual()
        if (self.fase!=FASE_INCORPORAR or self.etapa!='hostilidades'
            or jugador.canje_ultima_ronda==self.ronda):return False
        indices=list(indices);conts=list(continentes)
        if len(set(indices))!=len(indices) or len(set(conts))!=len(conts):return False
        if any(not isinstance(i,int) or not 0<=i<len(jugador.tarjetas) for i in indices):return False
        if any(c not in jugador.cartas_continente or
               c in jugador.continentes_usados or
               not self._controla_continente(jugador.idx,c) for c in conts):return False
        figs=[self.figuras_cartas[jugador.tarjetas[i]] for i in indices]
        if len(indices)==1 and not conts and figs==['Super']:return True
        if not indices and len(conts)==1 and conts[0] in ('America del Norte','Europa','Asia'):return True
        for c in conts:figs+=self._figuras_continente(c)
        return len(figs)==3 and 'Super' not in figs and _tres_figuras_validas(figs)

    def canjear_tarjetas(self, indices=None, continente=None):
        """Canje automático o explícito de tarjetas, máximo uno por ronda por jugador."""
        jugador=self.jugador_actual()
        if (self.fase!=FASE_INCORPORAR or self.etapa!='hostilidades'
            or jugador.canje_ultima_ronda==self.ronda):return 0
        if indices is None and continente is None:
            opcion=self.opcion_canje(jugador)
            if opcion is None:return 0
            indices,conts=opcion
        else:
            indices=list(indices or [])
            conts=[continente] if isinstance(continente,str) else list(continente or [])
        if not self.canje_valido(indices, conts, jugador):return 0
        for i in sorted(indices,reverse=True):
            carta=jugador.tarjetas.pop(i)
            jugador.tarjetas_premiadas.discard(carta)
            self.descarte_cartas.append(carta)
        for c in conts:
            jugador.cartas_continente.remove(c)
            jugador.continentes_usados.add(c)
        beneficio=self.valor_canje(jugador)
        ordinal=jugador.canjes_realizados+1
        self.canje_numero+=1  # Total de canjes de la partida; no fija su valor.
        jugador.canjes_realizados+=1
        jugador.canje_ultima_ronda=self.ronda
        self.ejercitos_a_colocar+=beneficio
        self.log(f'CANJE {ordinal} de {jugador.nombre}: +{beneficio} ejércitos')
        return beneficio

    def _premios_tarjetas(self, jugador):
        for carta in jugador.tarjetas:
            if (carta not in jugador.tarjetas_premiadas and self.tablero[carta]['propietario']==jugador.idx
                    and not self.zona_para(carta)):
                if not self._pais_bloqueado(carta):
                    self.tablero[carta]['ejercitos']+=3
                    jugador.tarjetas_premiadas.add(carta)
                    self.log(f'Premio tarjeta {carta}: +3 ejércitos')

    def robar_tarjeta(self, jugador):
        if not self.mazo_cartas_pais:
            self.mazo_cartas_pais,self.descarte_cartas=self.descarte_cartas,[]
            random.shuffle(self.mazo_cartas_pais)
        if not self.mazo_cartas_pais:return None
        carta=self.mazo_cartas_pais.pop()
        jugador.tarjetas.append(carta)
        self.log(f'{jugador.nombre} recibe tarjeta {carta} ({self.figuras_cartas[carta]})')
        self._premios_tarjetas(jugador)
        return carta

    def _actualizar_tarjetas_continente(self, jugador):
        for c in CONTINENTES:
            if self._controla_continente(jugador.idx,c):
                if c not in jugador.continentes_usados and c not in jugador.cartas_continente:
                    jugador.cartas_continente.add(c)
                    self.log(f'{jugador.nombre} obtiene tarjeta de continente: {c}')
            else:jugador.cartas_continente.discard(c)

    def puede_solicitar_tarjeta(self, jugador=None):
        jugador = jugador or self.jugador_actual()
        umbral = 1 if jugador.canjes_realizados < 3 else 2
        return (self.etapa=='hostilidades' and self.fase==FASE_TARJETA and
                not self.tarjeta_solicitada and (self.conquistas_turno>=umbral or self.conquistas_colectivas>=2) and
                jugador.idx not in self.crisis_sin_tarjeta and
                len(jugador.tarjetas)<5 and self.sancion_tarjeta[jugador.idx]==0)

    def solicitar_tarjeta(self):
        """Sólo se roba por petición explícita en la fase TARJETA."""
        if not self.puede_solicitar_tarjeta():return None
        self.tarjeta_solicitada=True
        return self.robar_tarjeta(self.jugador_actual())

    def _fin_turno(self):
        # La finalización computa rupturas diferidas y zonas internacionales.
        idx=self.turno_idx
        sanciones_preexistentes=self.sancion_tarjeta[idx]
        self._cierre_turno_diplomatico(idx)
        j=self.jugadores[idx]
        requiere=1 if j.canjes_realizados<3 else 2
        if (sanciones_preexistentes>0 and
            (self.conquistas_turno>=requiere or self.conquistas_colectivas>=2) and
            len(j.tarjetas)<5 and idx not in self.crisis_sin_tarjeta):
            self.sancion_tarjeta[idx]-=1
            self.log(f'{j.nombre}: se aplicó la sanción de tarjeta por Zona Internacional')
        self._siguiente_jugador()

    def _jugadores_activos_ronda(self):
        return [i for i in self.orden_ronda if not self.jugadores[i].eliminado]

    def _finalizar_incorporacion_ronda(self):
        """Barrera de sincronización: todos colocan ANTES de empezar los ataques."""
        activos=self._jugadores_activos_ronda()
        if len(self.incorporaciones_completadas) < len(activos):
            siguiente=next(i for i in activos if i not in self.incorporaciones_completadas)
            self.turno_idx=siguiente
            self.indice_turno_ronda=self.orden_ronda.index(siguiente)
            self._empezar_turno(inicial=False)
            return
        self.etapa_ronda='ATAQUE'
        self.incorporaciones_completadas=[]
        self.turno_idx=activos[0]
        self.indice_turno_ronda=self.orden_ronda.index(self.turno_idx)
        self.log(f'REFUERZOS COMPLETADOS: atacan desde {self.jugador_actual().nombre}')
        self._empezar_turno(inicial=True)

    def _siguiente_jugador(self):
        """Tras ataques/tarjetas, rotar el primer asiento de la siguiente ronda.

        En ronda 2+ la incorporación es una vuelta completa independiente.
        """
        activos=self._jugadores_activos_ronda()
        if not activos:return
        actual=self.turno_idx
        pos=activos.index(actual)
        if pos+1 < len(activos):
            siguiente=activos[pos+1]
            self.turno_idx=siguiente
            self.indice_turno_ronda=self.orden_ronda.index(siguiente)
            self._empezar_turno(inicial=True)  # Los refuerzos ya se distribuyeron.
            return
        # Todos atacaron, reagruparon y resolvieron tarjetas.
        self.ronda+=1
        activos=activos[1:]+activos[:1]
        self.orden_ronda=activos
        self.turno_idx=activos[0]
        self.primero_de_ronda=self.turno_idx
        self.indice_turno_ronda=0
        self.etapa_ronda='INCORPORACION'
        self.incorporaciones_completadas=[]
        self._siguiente_situacion()
        self.log('ORDEN RONDA '+str(self.ronda)+': '+ ' > '.join(self.jugadores[i].nombre for i in activos))
        self._empezar_turno(inicial=False)

    def avanzar_fase(self):
        if self.conquista_pendiente or self.fase=='VICTORIA':return False
        if self.fase==FASE_INCORPORAR:
            if self.ejercitos_a_colocar>0:return False
            if self.etapa=='preparacion':
                self.preparacion_pendientes+=1
                if self.preparacion_pendientes==self.n_jugadores:
                    self.preparacion_pendientes=0
                    if self.n_jugadores!=2 and self.vuelta_preparacion==0:
                        self.vuelta_preparacion=1
                        self.indice_turno_ronda=0
                        self.turno_idx=self.orden_ronda[0]
                        self.ejercitos_a_colocar=4
                        self.log('SEGUNDA INCORPORACIÓN INICIAL: 4 ejércitos por jugador')
                    else:self._comenzar_hostilidades()
                else:
                    self.indice_turno_ronda+=1
                    self.turno_idx=self.orden_ronda[self.indice_turno_ronda]
                    self.ejercitos_a_colocar=18 if self.n_jugadores==2 else (8 if self.vuelta_preparacion==0 else 4)
                return True
            if self.etapa=='hostilidades' and self.etapa_ronda=='INCORPORACION':
                if self.turno_idx not in self.incorporaciones_completadas:
                    self.incorporaciones_completadas.append(self.turno_idx)
                self._finalizar_incorporacion_ronda()
            else:
                self.fase=FASE_ATACAR
        elif self.fase==FASE_ATACAR:
            self.fase=FASE_REAGRUPAR
        elif self.fase==FASE_REAGRUPAR:
            if not self.preparar_reagrupe_aliado():return False
            self._premios_tarjetas(self.jugador_actual())
            self._actualizar_tarjetas_continente(self.jugador_actual())
            self.fase=FASE_TARJETA
            self.log('Etapa de tarjetas: solicitá una si reunís las conquistas requeridas.')
        elif self.fase==FASE_TARJETA:
            self.conquistas_compartidas_por_jugador[self.turno_idx]=0
            self._fin_turno()
        else:return False
        return True

    def pasar_fase(self):
        return self.avanzar_fase()

    def _preferencia(self, pais, jugador):
        """Importancia estratégica del país según las misiones asignadas."""
        cont=self.tablero[pais]['continente']
        peso=0.0
        for obj in jugador.objetivos:
            if obj['tipo']=='ocupacion':
                if cont in obj.get('completos',[]):
                    # El beneficio aumenta cuando estamos cerca de cerrar el continente.
                    total=sum(d['continente']==cont for d in self.tablero.values())
                    propios=sum(d['continente']==cont and d['propietario']==jugador.idx for d in self.tablero.values())
                    peso+=6+4*propios/max(1,total)
                if cont in obj.get('parciales',{}):
                    necesarios=obj['parciales'][cont]
                    propios=sum(d['continente']==cont and d['propietario']==jugador.idx for d in self.tablero.values())
                    if propios < necesarios:peso+=4+2*propios/max(1,necesarios)
                if obj.get('islas') and pais in ISLAS:peso+=4
            elif obj['tipo']=='eliminacion' and self.tablero[pais]['propietario']==obj.get('objetivo_idx'):
                peso+=12
        return peso

    def _frontera_estrategica(self, pais, j):
        """Presión y oportunidades cercanas: concentración útil, no al azar."""
        d=self.tablero[pais]
        fr=[q for q in d['fronteras'] if self.tablero[q]['propietario']!=j.idx]
        if not fr:return -7.0
        amenaza=sum(max(0,self.tablero[q]['ejercitos']-d['ejercitos']) for q in fr)
        accesibles=sum(1 for q in fr if self._ataque_permitido(pais,q))
        objetivos=max((self._preferencia(q,j) for q in fr),default=0)
        return min(len(fr),4)*2.0+min(amenaza,18)*.35+objetivos*.65+accesibles

    def _seleccionar_refuerzo_bot(self, j, paises):
        """Selecciona territorio con estrategia y ruido moderado; no repite siempre el máximo."""
        perfil=j.estilo_bot or 'Equilibrado'
        valores=[]
        for p in paises:
            d=self.tablero[p]
            fr=self.paises_limites_enemigos(p)
            propios_en= self.bot_refuerzos_por_pais.get(p,0)
            presion=self._frontera_estrategica(p,j)
            objetivo=self._preferencia(p,j)
            if perfil=='Agresivo':
                s=presion*1.6+objetivo*.6- d['ejercitos']*.21-propios_en*.65
            elif perfil=='Defensivo':
                amenaza=max((self.tablero[q]['ejercitos'] for q in fr),default=0)
                s=presion*.8+min(amenaza,18)*.8+objetivo*.35-d['ejercitos']*.8-propios_en*2.0
            elif perfil=='Objetivo':
                s=presion*.75+objetivo*1.9-d['ejercitos']*.35-propios_en*1.0
            elif perfil=='Oportunista':
                presa=min((self.tablero[q]['ejercitos'] for q in fr),default=12)
                s=presion*1.2+objetivo*.6-min(presa,10)*.6-d['ejercitos']*.4-propios_en*1.6
            else:
                s=presion+objetivo*.95-d['ejercitos']*.48-propios_en*1.55
            s+=random.uniform(-2.0,2.0)
            valores.append((s,p))
        valores.sort(reverse=True)
        # Entre los mejores, evita una conducta completamente previsible.
        mejores=valores[:min(3,len(valores))]
        pesos=[max(.2,5-(mejores[0][0]-valor)) for valor,_ in mejores]
        return random.choices([p for _,p in mejores],weights=pesos,k=1)[0]

    def _ataques_posibles_bot(self, j):
        perfil=j.estilo_bot or 'Equilibrado'
        umbrales={'Agresivo':1.08,'Defensivo':1.85,'Objetivo':1.30,
                  'Oportunista':1.30,'Equilibrado':1.48}
        lista=[]
        for p in self.paises_de(j.idx):
            a=self.ejercitos_de(p,j.idx)
            if a<=1:continue
            for q in self.paises_limites_enemigos(p):
                if not self._ataque_permitido(p,q) or self.es_propietario(q,j.idx):continue
                b=self.tablero[q]['ejercitos']
                if a-1 < b*umbrales[perfil]:continue
                op=self._preferencia(q,j)
                ventaja=(a-1)/max(1,b)
                presion_desde=len(self.paises_limites_enemigos(p))
                riesgo_restante=max((self.tablero[v]['ejercitos'] for v in self.paises_limites_enemigos(p) if v!=q),default=0)
                puntuacion=op*(1.5 if perfil=='Objetivo' else 1.0) + min(ventaja,7)*3 - b*.55
                puntuacion+=min(presion_desde,4)*.3-min(riesgo_restante,14)*.22
                if perfil=='Oportunista':puntuacion+=6/max(1,b)
                if perfil=='Defensivo':puntuacion-=b*.85
                puntuacion+=random.uniform(-1.5,1.5)
                lista.append((puntuacion,p,q))
        return sorted(lista,reverse=True)

    def _reagrupe_estrategico_bot(self, j):
        # Hasta dos transferencias seguras; no mover desde territorios atacables.
        opciones=[]
        for p in self.paises_exclusivos(j.idx):
            d=self.tablero[p]
            disponibles=d['ejercitos']-1-self.reagrupados_recibidos.get(p,0)
            if disponibles<2:continue
            if self.paises_limites_enemigos(p):continue
            for q in d['fronteras']:
                if self.tablero[q]['propietario']!=j.idx or not self.paises_limites_enemigos(q):continue
                valor=self._frontera_estrategica(q,j)+self._preferencia(q,j)*.5
                opciones.append((valor,p,q,disponibles))
        if not opciones:return None
        opciones.sort(reverse=True)
        _,p,q,cantidad=opciones[0]
        if self.reagrupar(p,q,cantidad):return (p,q,cantidad)
        return None

    def _propuesta_ocasional_bot(self):
        """Bots negocian pacificación y ataques con el humano o entre bots."""
        j=self.jugador_actual()
        clave=(self.ronda,j.idx,self.turnos_terminados[j.idx])
        if clave in self._bot_diplomacia_intentada:return None
        self._bot_diplomacia_intentada.add(clave)
        if self.fase!=FASE_ATACAR or j.idx==0 or random.random()>.23:return None
        # Buscar un objetivo compartido que pueda ser atacado desde dos países.
        aliados=[]
        for pais in self.paises_exclusivos(j.idx):
            if self.tablero[pais]['ejercitos']<3:continue
            for destino in self.tablero[pais]['fronteras']:
                victima=self.tablero[destino]['propietario']
                if victima is None or victima==j.idx:continue
                for vecino in self.tablero[destino]['fronteras']:
                    socio=self.tablero[vecino]['propietario']
                    if socio is None or socio in (victima,j.idx) or self.tablero[vecino]['ejercitos']<3:continue
                    if socio==0:
                        aliados.append((pais,vecino,destino,socio))
        if aliados and random.random()<.55:
            o1,o2,destino,socio=random.choice(aliados)
            if socio==0:
                self.propuesta_pendiente={'tipo':'agresion','a':j.idx,'b':0,
                    'origen_a':o1,'origen_b':o2,'destino':destino}
                return {'texto':f'{j.nombre} propone ataque conjunto a {destino}. Esperando respuesta.'}
            ag=self.proponer_agresion_conjunta(j.idx,socio,o1,o2,destino)
            if ag:
                r=self.ejecutar_agresion_conjunta(ag['id'])
                return {'texto':f'{j.nombre}: ofensiva conjunta a {destino}: {r["estado"]}', 'pais':o1,'destino':destino}
        bordes=[(p,q,self.tablero[q]['propietario']) for p in self.paises_exclusivos(j.idx)
                 for q in self.tablero[p]['fronteras'] if self.tablero[q]['propietario'] != j.idx
                 and self.tablero[q]['propietario'] is not None]
        random.shuffle(bordes)
        for p,q,socio in bordes:
            if socio==0:
                self.propuesta_pendiente={'tipo':'pais','a':j.idx,'b':0,'paises':(p,q)}
                return {'texto':f'{j.nombre} propone NO AGRESIÓN {p}/{q}. Esperando respuesta.'}
            if self.bot_acepta_pacto(socio,'pais',j.idx):
                pacto=self.proponer_no_agresion(j.idx,socio,'pais',paises=(p,q))
                if pacto:return {'texto':f'{j.nombre}: pacto de no agresión con {self.jugadores[socio].nombre}'}
        return None

    def aceptar_propuesta_bot(self, aceptar):
        propuesta=self.propuesta_pendiente
        if not propuesta:return None
        self.propuesta_pendiente=None
        if not aceptar:
            self.log(f'PACTO RECHAZADO por el humano ({self.jugadores[propuesta["a"]].nombre})')
            return False
        if propuesta['tipo']=='pais':
            return self.proponer_no_agresion(propuesta['a'],propuesta['b'],'pais',paises=propuesta['paises'])
        if propuesta['tipo']=='agresion':
            ag=self.proponer_agresion_conjunta(propuesta['a'],0,propuesta['origen_a'],
                propuesta['origen_b'],propuesta['destino'],lider=propuesta['a'])
            return self.ejecutar_agresion_conjunta(ag['id']) if ag else False
        return False

    def bot_acepta_pacto(self,bot_idx,tipo,otro_idx,destino=None):
        """Negociación voluntaria, pero pactos firmados son obligatorios."""
        j=self.jugadores[bot_idx]
        if not j.es_bot or j.eliminado:return False
        perfil=j.estilo_bot or 'Equilibrado'
        chances={'Agresivo':.55,'Defensivo':.92,'Objetivo':.75,
                 'Oportunista':.70,'Equilibrado':.82}
        if tipo=='agresion':
            chances={'Agresivo':.86,'Defensivo':.45,'Objetivo':.72,
                     'Oportunista':.80,'Equilibrado':.67}
            if destino is not None and self._preferencia(destino,j)>4:chances[perfil]=min(1,chances[perfil]+.12)
        return random.random()<chances[perfil]

    def paso_bot(self):
        """Una decisión por llamada, con perfiles distintos, siempre validada por las reglas."""
        j=self.jugador_actual()
        if not j.es_bot or j.eliminado or self.fase=='VICTORIA' or self.propuesta_pendiente or self.reagrupe_aliado_pendiente:return None
        idx=j.idx
        if self.fase==FASE_INCORPORAR:
            if (self.etapa=='hostilidades' and j.canje_ultima_ronda!=self.ronda
                    and self.opcion_canje(j) is not None):
                v=self.canjear_tarjetas()
                if v:return {'texto':f'{j.nombre}: canje +{v} ejércitos','accion':'canje','valor':v}
            mis=[p for p in self.paises_de(idx) if self.etapa=='preparacion' or not self._pais_bloqueado(p)]
            con=[c for c,n in self.refuerzos_continente.items() if n>0]
            if con:mis=[p for p in mis if self.tablero[p]['continente'] in con]
            if not mis:raise RuntimeError(f'Sin países válidos para incorporaciones: {j.nombre}')
            pais=self._seleccionar_refuerzo_bot(j,mis)
            pool=self.refuerzos_continente.get(self.tablero[pais]['continente'],0)
            libres=self.ejercitos_a_colocar-sum(self.refuerzos_continente.values())
            maximo=min(self.ejercitos_a_colocar,pool if pool else libres)
            perfil=j.estilo_bot or 'Equilibrado'
            lote={'Agresivo':4,'Defensivo':2,'Objetivo':3,'Oportunista':2,'Equilibrado':3}[perfil]
            cantidad=max(1,min(maximo,lote))
            if not self.incorporar(pais,cantidad):raise RuntimeError('Bot no pudo incorporar tropas')
            self.bot_refuerzos_por_pais[pais]=self.bot_refuerzos_por_pais.get(pais,0)+cantidad
            return {'texto':f'{j.nombre} ({perfil}): +{cantidad} en {pais}', 'accion':'incorporar', 'pais':pais, 'cantidad':cantidad}
        if self.fase==FASE_ATACAR:
            propuesta=self._propuesta_ocasional_bot()
            if propuesta:return propuesta
            if self.situacion!=f'Descanso {j.color_nombre}':
                for zona in self.zonas_internacionales:
                    if not zona['activa'] or zona['pendiente']!=idx:continue
                    pais=zona['pais']
                    opciones=[p for p in self.tablero[pais]['fronteras'] if
                        self.es_propietario(p,idx) and self.ejercitos_de(p,idx)>1 and
                        self._ataque_permitido(p,pais)]
                    if opciones:
                        origen=max(opciones,key=lambda p:self.ejercitos_de(p,idx))
                        resultado=self.atacar(origen,pais)
                        if resultado['ok']:
                            self.bot_ataques_turno+=1
                            return {'texto':f'{j.nombre}: cumple ZONA INTERNACIONAL {pais}',
                                    'pais':origen,'destino':pais,'dados':resultado}
                # Misiles orientados hacia un rival fuerte o un objetivo propio.
                opciones=[]
                for p in self.paises_de(idx):
                    if p in self.condominios or self.tablero[p]['misiles']<1:continue
                    for q,d in self.tablero.items():
                        if d['propietario']==idx or q in self.condominios or d['ejercitos']<4:continue
                        dist=self.distancia(p,q)
                        if dist is None or not 1<=dist<=3:continue
                        score=d['ejercitos']*.28+self._preferencia(q,j)*2-dist*1.2
                        opciones.append((score,p,q))
                for _,p,q in sorted(opciones,reverse=True)[:8]:
                    if self.lanzar_misil(q,desde=p):
                        return {'texto':f'{j.nombre}: MISIL {p} -> {q}', 'accion':'misil', 'pais':p,'destino':q}
                max_ataques={'Agresivo':48,'Defensivo':14,'Objetivo':38,'Oportunista':28,'Equilibrado':30}
                if self.bot_ataques_turno<max_ataques[j.estilo_bot or 'Equilibrado']:
                    candidatos=self._ataques_posibles_bot(j)
                    if candidatos:
                        _,p,q=candidatos[0]
                        r=self.atacar(p,q)
                        self.bot_ataques_turno+=1
                        if r['ok']:
                            return {'texto':f'{j.nombre}: ataca {p} -> {q}', 'accion':'atacar', 'pais':p,'destino':q,'dados':r}
            self.avanzar_fase()
            return {'texto':f'{j.nombre}: pasa a reagrupar'}
        if self.fase==FASE_REAGRUPAR:
            if self.bot_reagrupes_turno<2 and self.situacion!=f'Descanso {j.color_nombre}':
                self.bot_reagrupes_turno+=1
                movimiento=self._reagrupe_estrategico_bot(j)
                if movimiento:
                    p,q,cant=movimiento
                    return {'texto':f'{j.nombre}: mueve {cant} de {p} a {q}', 'accion':'reagrupar', 'pais':p,'destino':q,'cantidad':cant}
            self.avanzar_fase()
            return {'texto':f'{j.nombre}: revisa tarjetas'}
        if self.fase==FASE_TARJETA:
            if self.puede_solicitar_tarjeta():
                carta=self.solicitar_tarjeta()
                return {'texto':f'{j.nombre}: solicita tarjeta ({carta})','accion':'tarjeta','carta':carta}
            self.avanzar_fase()
            return {'texto':f'{j.nombre}: termina turno'}
        return None

    def turno_bot(self, delay_callback=None):
        """Compatibilidad para simulaciones; la GUI llama a paso_bot por intervalos."""
        j=self.jugador_actual()
        acciones=[]
        for _ in range(500):
            if self.turno_idx!=j.idx or self.fase=='VICTORIA':break
            estado=self.paso_bot()
            if estado:
                acciones.append(estado['texto'])
                if delay_callback:delay_callback(estado)
            else:break
        else:
            raise RuntimeError('Bot excedió 500 acciones en turno')
        return acciones
