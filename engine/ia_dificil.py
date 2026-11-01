"""IA avanzada para la dificultad Difícil. No depende de Pygame.

No accede a los objetivos secretos de los rivales. Estima los suyos a partir
de los continentes que controlan y de sus movimientos públicos. Todas las
acciones se ejecutan usando el motor de reglas, incluidos sus pactos.
"""
from collections import Counter, deque
from functools import lru_cache
from itertools import combinations_with_replacement
from math import factorial
import random


def _tiradas(n):
    """Cada combinación ordenada de n dados, ponderada por permutaciones."""
    for nums in combinations_with_replacement(range(1,7),n):
        multiplicidad=factorial(n)
        for veces in Counter(nums).values():
            multiplicidad//=factorial(veces)
        yield tuple(sorted(nums,reverse=True)),multiplicidad


@lru_cache(maxsize=16)
def transiciones_dados(atk,defensa):
    """Distribución exacta de bajas de una tirada; empates al defensor."""
    resultados=Counter()
    for a,wa in _tiradas(atk):
        for d,wd in _tiradas(defensa):
            ba=sum(x<=y for x,y in zip(a,d))
            bd=sum(x>y for x,y in zip(a,d))
            resultados[(ba,bd)]+=wa*wd
    total=6**(atk+defensa)
    return tuple((ba,bd,n/total) for (ba,bd),n in resultados.items())


@lru_cache(maxsize=16000)
def probabilidad_conquista(atk,defensa,situacion='Clásico'):
    """(Probabilidad de conquista, bajas esperadas del atacante).

    Programa dinámico sobre los ejércitos restantes. Refleja exactamente
    los dados del motor, incluyendo cuarto dado por doble fuerza, Viento
    a favor, Nieve y límites de bajas. Para pilas mayores a 36 tropas se
    aproxima acotando la dimensión a 36 por rendimiento.
    """
    if defensa<=0:return 1.0,0.0
    if atk<=1:return 0.0,0.0
    atk=min(36,atk)
    defensa=min(36,defensa)
    dados_a=min(3,atk-1)
    if defensa>=3 and atk>=2*defensa:dados_a=4
    if situacion=='Viento a favor':dados_a=min(4,dados_a+1)
    dados_d=min(3,defensa)
    if situacion=='Nieve':dados_d=min(4,dados_d+1)
    victoria=perdidas=0.0
    for ba,bd,prob in transiciones_dados(dados_a,dados_d):
        bajas_a=min(atk-1,ba)
        bajas_d=min(defensa,bd)
        siguiente_a=atk-bajas_a
        siguiente_d=defensa-bajas_d
        if siguiente_d==0:
            win,danio=1.0,0.0
        elif siguiente_a<=1:
            win,danio=0.0,0.0
        else:
            win,danio=probabilidad_conquista(siguiente_a,siguiente_d,situacion)
        victoria+=prob*win
        perdidas+=prob*(bajas_a+danio)
    return victoria,perdidas


class EstrategiaDificil:
    """Estrategia autónoma de decisiones para bots, una acción por llamada."""

    def __init__(self,juego):
        self.j=juego
        self._max_reagrupes=4

    def contexto(self,jugador):
        """Snapshot de propietarios y continentes, sin objetivos secretos ajenos."""
        juego=self.j
        paises={j.idx:0 for j in juego.jugadores}
        continentes={c:Counter() for c in {d['continente'] for d in juego.tablero.values()}}
        totales=Counter()
        for nombre,d in juego.tablero.items():
            c=d['continente']
            totales[c]+=1
            if nombre not in juego.condominios:
                propietario=d['propietario']
                if propietario is not None:
                    paises[propietario]+=1
                    continentes[c][propietario]+=1
        return {'paises':paises,'continentes':continentes,'totales':totales}

    def valor_pais(self,pais,jugador,ctx):
        """Evalúa misión, líder enemigo, países clave y posibles objetivos rivales.

        El reglamento implementado no define capitales especiales; se valoran
        nodos de alta conectividad sin inventar bonificaciones inexistentes.
        """
        juego=self.j
        d=juego.tablero[pais]
        c=d['continente']
        propietario=d['propietario']
        total=ctx['totales'][c]
        propios=ctx['continentes'][c][jugador.idx]
        valor=3.0+min(6,len(d['fronteras']))*.75
        valor+=min(13,juego._preferencia(pais,jugador))*.75
        if propietario!=jugador.idx:
            faltantes=total-propios
            if faltantes==1:valor+=14
            elif faltantes==2:valor+=8
            elif faltantes<=4:valor+=3
            if propietario is not None:
                rival=ctx['paises'][propietario]
                if rival>=35:valor+=min(30,(rival-34)*2.2)
                su_cont=ctx['continentes'][c][propietario]
                if su_cont>=total-1:valor+=13
                elif su_cont>=total-3:valor+=5
                # Inferencia pública sobre posibles intereses de ese rival.
                if su_cont/total>=.55:valor+=6*(su_cont/total)
                if rival<=2 and len(juego.jugadores[propietario].tarjetas)>0:
                    valor+=6+min(8,2*len(juego.jugadores[propietario].tarjetas))
            propios_total=ctx['paises'][jugador.idx]
            if propios_total>=38:valor+=min(28,(propios_total-37)*3)
        return valor

    def vecinos_amenazantes(self,pais,jugador):
        juego=self.j
        return [q for q in juego.tablero[pais]['fronteras']
                if not juego.es_propietario(q,jugador.idx)
                and juego.tablero[q]['propietario'] is not None
                and juego._ataque_permitido(q,pais,actor_idx=juego.tablero[q]['propietario'])]

    def _frentes(self,pais,jugador):
        juego=self.j
        return [q for q in juego.tablero[pais]['fronteras']
                if not juego.es_propietario(q,jugador.idx)
                and juego.tablero[q]['propietario'] is not None
                and juego._ataque_permitido(pais,q,actor_idx=jugador.idx)]

    def evaluacion_ataque(self,origen,destino,jugador,ctx):
        juego=self.j
        tropas=juego.ejercitos_de(origen,jugador.idx)
        enemigo=juego.tablero[destino]['propietario']
        defensa=juego.ejercitos_de(destino,enemigo)
        if tropas<2 or defensa<1:return None
        if origen in juego.condominios and enemigo in juego.condominios[origen]:
            return None
        p,bajas=probabilidad_conquista(tropas,defensa,juego.situacion)
        urgencia=ctx['paises'][enemigo]>=43
        if p<(.60 if urgencia else .72):return None
        valor=self.valor_pais(destino,jugador,ctx)
        despues=max(1,tropas-bajas-3)
        vecinos=[v for v in juego.tablero[destino]['fronteras']
                 if v!=origen and not juego.es_propietario(v,jugador.idx)
                 and juego.tablero[v]['propietario'] is not None]
        mayor=max((juego.tablero[v]['ejercitos'] for v in vecinos),default=0)
        contragolpe=max(0,mayor-despues)*.65
        otros=[v for v in self.vecinos_amenazantes(origen,jugador) if v!=destino]
        mayor_origen=max((juego.tablero[v]['ejercitos'] for v in otros),default=0)
        riesgo_origen=max(0,mayor_origen-(tropas-bajas-3))*.8
        puntaje=p*valor-bajas*1.7-(1-p)*min(25,defensa)*.6
        puntaje-=contragolpe+riesgo_origen
        if juego.conquistas_turno==0 and len(jugador.tarjetas)<5:puntaje+=4
        if urgencia:puntaje+=8
        return puntaje,p

    def candidato_ataque(self,jugador):
        juego=self.j
        ctx=self.contexto(jugador)
        candidatos=[]
        for origen in juego.paises_de(jugador.idx):
            if juego.ejercitos_de(origen,jugador.idx)<2:continue
            # Tras romper la tregua, los copropietarios originales atacan
            # solamente DENTRO del condominio, nunca desde otro territorio.
            if origen in juego.condominios:
                rivales=[i for i in juego.condominios[origen] if i!=jugador.idx]
                for otro in rivales:
                    activo=any(p['activo'] and p['tipo']=='condominio'
                               and p['pais']==origen and
                               set(p['jugadores'])=={jugador.idx,otro}
                               for p in juego.pactos)
                    if activo or juego._prohibido_por_pacto(jugador.idx,otro,origen,origen):continue
                    defensa=juego.ejercitos_de(origen,otro)
                    prob,bajas=probabilidad_conquista(juego.ejercitos_de(origen,jugador.idx),
                                                       defensa,juego.situacion)
                    if prob>=.76:
                        score=prob*(9+self.valor_pais(origen,jugador,ctx))-bajas*1.7
                        if score>0:candidatos.append((score,prob,origen,origen))
            for destino in self._frentes(origen,jugador):
                eval_=self.evaluacion_ataque(origen,destino,jugador,ctx)
                if eval_:
                    puntaje,p=eval_
                    if puntaje>0:candidatos.append((puntaje,p,origen,destino))
        return max(candidatos) if candidatos else None

    def refuerzo(self,jugador):
        juego=self.j
        # Un canje puede guardarse, pero no conviene perder una oportunidad por
        # límite de cartas ni ignorar un rival que está por ganar.
        if juego.etapa=='hostilidades' and jugador.canje_ultima_ronda!=juego.ronda:
            if juego.opcion_canje(jugador) is not None:
                ctx=self.contexto(jugador)
                urgente=any(ctx['paises'][i]>=38 for i in ctx['paises'] if i!=jugador.idx)
                if (len(jugador.tarjetas)>=4 or urgente
                    or len(juego.paises_exclusivos(jugador.idx))<10
                    or (not juego.bot_refuerzos_por_pais and juego.ejercitos_a_colocar<=6)):
                    valor=juego.canjear_tarjetas()
                    if valor:
                        return {'texto':f'{jugador.nombre}: canje táctico +{valor}',
                                'accion':'canje','valor':valor}
        paises=[p for p in juego.paises_de(jugador.idx)
                if juego.etapa=='preparacion' or not juego._pais_bloqueado(p)]
        continentes=[c for c,n in juego.refuerzos_continente.items() if n>0]
        if continentes:paises=[p for p in paises if juego.tablero[p]['continente'] in continentes]
        if not paises:raise RuntimeError('IA Difícil: no hay país válido para incorporar')
        ctx=self.contexto(jugador)
        evaluados=[]
        for pais in paises:
            propias=juego.ejercitos_de(pais,jugador.idx)
            destinos=self._frentes(pais,jugador)
            amenaza=max((juego.tablero[q]['ejercitos']
                        for q in self.vecinos_amenazantes(pais,jugador)),default=0)
            oportunidades=[]
            for q in destinos:
                defensor=juego.tablero[q]['ejercitos']
                faltan=max(1,int(1.6*defensor+3-propias))
                valor=self.valor_pais(q,jugador,ctx)
                oportunidades.append((valor/max(2,faltan),faltan,q))
            mejor=max(oportunidades,default=(0,2,None))
            riesgo=max(0,amenaza+2-propias)
            repetidos=juego.bot_refuerzos_por_pais.get(pais,0)
            puntuacion=mejor[0]*6+min(12,riesgo)*1.15+min(3,len(destinos))*1.4
            puntuacion-=max(0,propias-amenaza-7)*.8+repetidos*.45
            if not destinos and amenaza==0:puntuacion-=15
            evaluados.append((puntuacion,pais,mejor,riesgo))
        _,pais,mejor,riesgo=max(evaluados)
        pool=juego.refuerzos_continente.get(juego.tablero[pais]['continente'],0)
        libres=juego.ejercitos_a_colocar-sum(juego.refuerzos_continente.values())
        maximo=min(juego.ejercitos_a_colocar,pool if pool else libres)
        cantidad=max(1,max(mejor[1],riesgo))
        if not self._frentes(pais,jugador) and riesgo==0:cantidad=1
        cantidad=min(maximo,cantidad,10)
        if not juego.incorporar(pais,cantidad):
            raise RuntimeError('IA Difícil: incorporación inválida')
        juego.bot_refuerzos_por_pais[pais]=juego.bot_refuerzos_por_pais.get(pais,0)+cantidad
        return {'texto':f'{jugador.nombre} (Difícil): +{cantidad} en {pais}',
                'accion':'incorporar','pais':pais,'cantidad':cantidad}

    def proponer_ataque_conjunto(self,jugador,contexto):
        """Ataques coordinados cuando las fuerzas individuales son insuficientes.

        Valida Fronteras abiertas/cerradas antes de proponer el acuerdo.
        """
        juego=self.j
        candidatos=[]
        for propio in juego.paises_exclusivos(jugador.idx):
            tropas_a=juego.ejercitos_de(propio,jugador.idx)
            if tropas_a<3:continue
            for destino in self._frentes(propio,jugador):
                if destino in juego.condominios:continue
                defensa=juego.tablero[destino]['ejercitos']
                if defensa<3:continue
                individual=probabilidad_conquista(tropas_a,defensa,juego.situacion)[0]
                if individual>=.80:continue
                for p in juego.tablero[destino]['fronteras']:
                    socio=juego.tablero[p]['propietario']
                    if socio is None or socio in (jugador.idx,juego.tablero[destino]['propietario']):continue
                    if contexto['paises'][socio]>=39:continue
                    tropas_b=juego.ejercitos_de(p,socio)
                    if tropas_b<3:continue
                    if not juego.puede_proponer_agresion_conjunta(jugador.idx,socio,propio,p,destino):continue
                    p_combinada=probabilidad_conquista(tropas_a+tropas_b-1,defensa,juego.situacion)[0]
                    if p_combinada<.83:continue
                    valor=self.valor_pais(destino,jugador,contexto)
                    candidatos.append((p_combinada*valor,propio,p,destino,socio))
        if not candidatos:return None
        _,propio,otro,destino,socio=max(candidatos)
        if socio==0:
            juego.propuesta_pendiente={'tipo':'agresion','a':jugador.idx,'b':0,
                'origen_a':propio,'origen_b':otro,'destino':destino}
            return {'texto':f'{jugador.nombre} propone ofensiva coordinada a {destino}'}
        if juego.bot_acepta_pacto(socio,'agresion',jugador.idx,destino):
            ag=juego.proponer_agresion_conjunta(jugador.idx,socio,propio,otro,destino)
            if ag:
                resultado=juego.ejecutar_agresion_conjunta(ag['id'])
                return {'texto':f'{jugador.nombre}: ataque conjunto a {destino}',
                        'pais':propio,'destino':destino,'agresion':resultado}
        return None

    def diplomacia(self,jugador):
        juego=self.j
        clave=(juego.ronda,jugador.idx,juego.turnos_terminados[jugador.idx])
        if clave in juego._bot_diplomacia_intentada:return None
        juego._bot_diplomacia_intentada.add(clave)
        ctx=self.contexto(jugador)
        # Romper un pacto peligroso NO libera de inmediato el ataque.
        for pacto in juego.pactos_vigentes():
            if jugador.idx not in pacto['jugadores'] or pacto['ruptura_por'] is not None:continue
            otro=next(i for i in pacto['jugadores'] if i!=jugador.idx)
            if (ctx['paises'][otro]>=39 or any(o['tipo']=='eliminacion'
                 and o.get('objetivo_idx')==otro and not o.get('imposible')
                 for o in jugador.objetivos)):
                if juego.romper_pacto(pacto['id'],jugador.idx):
                    return {'texto':f'{jugador.nombre} anuncia ruptura estratégica #{pacto["id"]}'}
        if random.random()<.22:
            ofensiva=self.proponer_ataque_conjunto(jugador,ctx)
            if ofensiva:return ofensiva
        if random.random()>.16:return None
        opciones=[]
        for p in juego.paises_exclusivos(jugador.idx):
            for q in juego.tablero[p]['fronteras']:
                rival=juego.tablero[q]['propietario']
                if rival is None or rival==jugador.idx or ctx['paises'][rival]>=38:continue
                if any(o['tipo']=='eliminacion' and o.get('objetivo_idx')==rival
                       for o in jugador.objetivos):continue
                if juego.tablero[q]['ejercitos']<=juego.tablero[p]['ejercitos']+2:continue
                opciones.append((juego.tablero[q]['ejercitos']-juego.tablero[p]['ejercitos'],p,q,rival))
        if not opciones:return None
        _,p,q,rival=max(opciones)
        if rival==0:
            juego.propuesta_pendiente={'tipo':'pais','a':jugador.idx,'b':0,'paises':(p,q)}
            return {'texto':f'{jugador.nombre} propone tregua defensiva {p}/{q}'}
        if juego.bot_acepta_pacto(rival,'pais',jugador.idx):
            pacto=juego.proponer_no_agresion(jugador.idx,rival,'pais',paises=(p,q))
            if pacto:return {'texto':f'{jugador.nombre} acuerda tregua #{pacto["id"]}'}
        return None

    def atacar(self,jugador):
        juego=self.j
        acuerdo=self.diplomacia(jugador)
        if acuerdo:return acuerdo
        if juego.situacion!=f'Descanso {jugador.color_nombre}':
            if juego.bot_ataques_turno<50:
                candidato=self.candidato_ataque(jugador)
                if candidato:
                    _,_,origen,destino=candidato
                    resultado=juego.atacar(origen,destino)
                    juego.bot_ataques_turno+=1
                    if resultado['ok']:
                        return {'texto':f'{jugador.nombre} calcula y ataca {origen}->{destino}',
                                'accion':'atacar','pais':origen,'destino':destino,'dados':resultado}
            # Bombardear un objetivo que tenga un valor estratégico real.
            ctx=self.contexto(jugador)
            opciones=[]
            for origen in juego.paises_exclusivos(jugador.idx):
                if juego.tablero[origen]['misiles']<1:continue
                for destino,d in juego.tablero.items():
                    if juego.es_propietario(destino,jugador.idx) or destino in juego.condominios:continue
                    distancia=juego.distancia(origen,destino)
                    if distancia is None or not 1<=distancia<=3 or d['ejercitos']<5:continue
                    valor=self.valor_pais(destino,jugador,ctx)
                    if valor>12:opciones.append((valor+d['ejercitos']*.3,origen,destino))
            for _,origen,destino in sorted(opciones,reverse=True)[:8]:
                if juego.lanzar_misil(destino,desde=origen):
                    return {'texto':f'{jugador.nombre}: misil táctico {origen}->{destino}',
                            'accion':'misil','pais':origen,'destino':destino}
        juego.avanzar_fase()
        return {'texto':f'{jugador.nombre}: reorganiza ejércitos'}

    def reagrupar(self,jugador):
        juego=self.j
        if (juego.bot_reagrupes_turno>=self._max_reagrupes
                or juego.situacion==f'Descanso {jugador.color_nombre}'):
            juego.avanzar_fase()
            return {'texto':f'{jugador.nombre}: revisa tarjetas'}
        juego.bot_reagrupes_turno+=1
        propios=set(juego.paises_exclusivos(jugador.idx))
        ctx=self.contexto(jugador)
        frentes=[p for p in propios if self._frentes(p,jugador)]
        dist={p:0 for p in frentes}
        cola=deque(frentes)
        while cola:
            p=cola.popleft()
            for q in juego.tablero[p]['fronteras']:
                if q in propios and q not in dist:
                    dist[q]=dist[p]+1
                    cola.append(q)
        opciones=[]
        for origen in propios:
            if origen not in dist:continue
            tropas=juego.ejercitos_de(origen,jugador.idx)
            rivales=self.vecinos_amenazantes(origen,jugador)
            mayor=max((juego.tablero[v]['ejercitos'] for v in rivales),default=0)
            recibidos=juego.reagrupados_recibidos.get(origen,0)
            reserva=max(1,int(mayor*.9)+2) if rivales else 1
            disponibles=tropas-reserva-recibidos
            if disponibles<1:continue
            for destino in juego.tablero[origen]['fronteras']:
                if destino not in propios or destino not in dist:continue
                if dist[destino]>dist[origen]:continue
                valor=self.valor_pais(destino,jugador,ctx)
                def_rivales=self.vecinos_amenazantes(destino,jugador)
                necesidad=max((juego.tablero[v]['ejercitos'] for v in def_rivales),default=0)
                necesidad=max(0,necesidad+3-juego.ejercitos_de(destino,jugador.idx))
                if dist[destino]==dist[origen] and necesidad<=0:continue
                if dist[destino]==dist[origen] and reserva>=tropas-1:continue
                score=10*(dist[origen]-dist[destino])+valor*.3+necesidad*2
                cantidad=min(disponibles,max(1,necesidad+3) if necesidad else disponibles)
                opciones.append((score,origen,destino,cantidad))
        for _,origen,destino,cantidad in sorted(opciones,reverse=True):
            if juego.reagrupar(origen,destino,cantidad):
                return {'texto':f'{jugador.nombre}: reagrupe {origen}->{destino} +{cantidad}',
                        'accion':'reagrupar','pais':origen,'destino':destino,'cantidad':cantidad}
        juego.avanzar_fase()
        return {'texto':f'{jugador.nombre}: revisa tarjetas'}

    def paso(self,jugador):
        juego=self.j
        if juego.fase=='INCORPORAR':return self.refuerzo(jugador)
        if juego.fase=='ATACAR':return self.atacar(jugador)
        if juego.fase=='REAGRUPAR':return self.reagrupar(jugador)
        if juego.fase=='TARJETA':
            if juego.puede_solicitar_tarjeta():
                carta=juego.solicitar_tarjeta()
                return {'texto':f'{jugador.nombre}: pide tarjeta ({carta})',
                        'accion':'tarjeta','carta':carta}
            juego.avanzar_fase()
            return {'texto':f'{jugador.nombre}: termina turno'}
        return None
