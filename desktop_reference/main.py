"""
main.py - TEG La Revancha (Python + Pygame)
============================================
Punto de entrada del juego.

COMO INSTALAR:
    pip install pygame

ESTRUCTURA DE ARCHIVOS:
    teg_revancha/
        main.py        <- este archivo
        data.py        <- datos del tablero (paises, fronteras, coords)
        logic.py       <- logica del juego (combate, turnos, bots)
        renderer.py    <- interfaz grafica Pygame
        mapa.jpg       <- imagen del mapa oficial

COMO EJECUTAR:
    python main.py
    (desde la carpeta teg_revancha/)

CONTROLES:
    - Clic izquierdo en el mapa: seleccionar pais origen/destino
    - Clic derecho sobre país: menú de acciones in situ
    - [P]: pactos públicos, agresiones conjuntas y rupturas
    - Botones panel derecho: acciones de turno
    - Scroll del raton: navegar historial
    - ESC: salir del juego
"""
import sys

# Verificar dependencias
try:
    import pygame
except ImportError:
    print("ERROR: Pygame no esta instalado.")
    print("Instala con: pip install pygame")
    sys.exit(1)

from logic import JuegoTEG, FASE_INCORPORAR, FASE_MISILES, FASE_ATACAR, FASE_REAGRUPAR, FASE_TARJETA
from renderer import Renderer
from respuestas_pactos import respuesta_propuesta_bot


def debe_mostrar_situacion(juego, situacion_anunciada, renderer):
    """La ronda 1 no roba ni anuncia situaciones; se empieza desde ronda 2."""
    return (juego.etapa == 'hostilidades' and juego.ronda >= 2
            and juego.ronda > situacion_anunciada
            and not renderer.popup and not renderer.vista_tarjetas)


def manejar_clic_mapa(pos, juego, renderer):
    """
    Maneja el clic sobre el mapa.
    Logica de seleccion de origen/destino y acciones automaticas
    segun la fase del turno.
    """
    jugador = juego.jugador_actual()
    if jugador.es_bot or juego.conquista_pendiente:
        return

    pais_clic = renderer.pais_en_pos(pos, juego.tablero)
    if not pais_clic:
        return

    fase = juego.fase

    # ── INCORPORAR: clic en pais propio agrega 1 ejercito ────────────
    if fase == FASE_INCORPORAR:
        if juego.es_propietario(pais_clic,jugador.idx):
            if juego.incorporar(pais_clic, 1):
                renderer.registrar_incorporacion(pais_clic,1,juego,tipo='ejercitos')
            renderer.construir_botones(juego)
        return

    # ATACAR y REAGRUPAR: primero seleccionar origen, luego destino, finalmente botón.
    if fase in (FASE_ATACAR, FASE_REAGRUPAR, FASE_TARJETA):
        if renderer.pais_seleccionado is None:
            if juego.es_propietario(pais_clic,jugador.idx):
                renderer.pais_seleccionado=pais_clic
                renderer.pais_objetivo=None
        elif renderer.pais_seleccionado==pais_clic:
            renderer.pais_seleccionado=None
            renderer.pais_objetivo=None
        elif juego.es_propietario(pais_clic,jugador.idx) and fase==FASE_ATACAR:
            renderer.pais_seleccionado=pais_clic
            renderer.pais_objetivo=None
        else:
            renderer.pais_objetivo=pais_clic
        renderer.construir_botones(juego)


def manejar_boton(accion, juego, renderer):
    """Ejecuta la accion correspondiente al boton presionado."""
    if accion == 'velocidad_bot':
        renderer.cambiar_velocidad_bot()
        renderer.construir_botones(juego)
        return
    if accion == 'ver_pactos':
        renderer.mostrar_pactos(juego)
        return
    if accion == 'ctx_origen':
        renderer.pais_seleccionado=renderer._contexto_pais
        renderer.pais_objetivo=None
        renderer.construir_botones(juego)
        return
    if accion.startswith('ctx_ref_'):
        pais=renderer._contexto_pais
        n=int(accion.rsplit('_',1)[1])
        # Hasta el máximo realmente disponible del fondo elegido.
        for intento in range(min(n,juego.ejercitos_a_colocar),0,-1):
            if juego.incorporar(pais,intento):
                renderer.registrar_incorporacion(pais,intento,juego,tipo='ejercitos')
                break
        renderer.construir_botones(juego)
        return
    if accion.startswith('ctx_misil_'):
        pais=renderer._contexto_pais
        if not juego.incorporar_misil(pais,reemplazar=accion=='ctx_misil_convertir'):
            renderer.mostrar_popup('MISIL','No se puede incorporar ese misil en el país.')
        else:
            renderer.registrar_incorporacion(pais,1,juego,tipo='misil')
        renderer.construir_botones(juego)
        return
    if accion == 'ctx_cerrar':return
    if accion == 'ver_tarjetas':
        renderer.abrir_tarjetas(juego)
        return
    if accion == 'ver_objetivos':
        renderer.mostrar_objetivos(juego)
        return
    if accion == 'ver_historial':
        renderer.mostrar_historial(juego)
        return
    if juego.conquista_pendiente:
        return
    jugador = juego.jugador_actual()

    if accion == 'solicitar_tarjeta':
        # Mostrar expresamente si la tarjeta recién robada añadió +3 al país.
        premiadas_antes=set(jugador.tarjetas_premiadas)
        carta=juego.solicitar_tarjeta()
        if carta:
            figura=juego.figuras_cartas[carta]
            mensaje=f'Recibiste {carta} ({figura}).\nEstá disponible en VER TARJETAS.'
            if carta in jugador.tarjetas_premiadas and carta not in premiadas_antes:
                mensaje+=f'\nPREMIO: +3 ejércitos incorporados en {carta}.'
            elif juego.tablero[carta]['propietario']==jugador.idx:
                mensaje+='\nPremio +3 pendiente por bloqueo o zona internacional.'
            else:
                mensaje+=f'\nSi conquistás {carta} mientras conservás la tarjeta, recibirás +3 al terminar ese turno.'
            renderer.mostrar_popup('TARJETA OBTENIDA',mensaje)
        else:
            renderer.mostrar_popup('SIN DERECHO A TARJETA','Se requieren 1 o 2 conquistas según canjes.\nVerificá también el límite de cinco cartas y la crisis.')

    elif accion == "pasar":
        juego.pasar_fase()
        renderer.pais_seleccionado = None
        renderer.pais_objetivo     = None

    elif accion == "cancelar":
        renderer.pais_seleccionado = None
        renderer.pais_objetivo     = None
        juego.log("Seleccion cancelada.")

    elif accion == "canjear":
        renderer.abrir_tarjetas(juego)

    elif accion in ('misil_nuevo','misil_convertir'):
        pais=renderer.pais_seleccionado
        if not pais or not juego.incorporar_misil(pais, reemplazar=accion=='misil_convertir'):
            renderer.mostrar_popup('MISIL','Elegí un país propio con clic derecho.\nSe requieren 6 refuerzos o 7 ejércitos en ese país.')
        else:
            renderer.registrar_incorporacion(pais,1,juego,tipo='misil')
            renderer.pais_seleccionado=None

    elif accion == "lanzar_misil":
        origen=renderer.pais_seleccionado
        destino=renderer.pais_objetivo
        if not origen or not destino or not juego.lanzar_misil(destino,desde=origen):
            renderer.mostrar_popup('MISIL NO DISPONIBLE','Revisá alcance (1-3), defensa, ejércitos y situación.')
        else:
            renderer.registrar_combate(origen,destino,None,juego,tipo='misil')
            renderer.pais_objetivo=None

    elif accion == "atacar_4":
        if renderer.pais_seleccionado and renderer.pais_objetivo:
            if renderer.pais_objetivo in juego.condominios:
                defensores=[i for i in juego.condominios[renderer.pais_objetivo] if i!=juego.turno_idx]
                if len(defensores)>1:
                    botones=[(juego.jugadores[i].color_nombre, f'atacar_condominio_{i}') for i in defensores]
                    renderer.mostrar_popup('ELEGIR GUARNICIÓN A ATACAR',
                        f'En {renderer.pais_objetivo} hay dos ocupantes. Elegí a cuál vas a atacar en esta tirada.',botones)
                    return
            res = juego.atacar(renderer.pais_seleccionado, renderer.pais_objetivo)
            if res["ok"]:
                renderer.registrar_combate(renderer.pais_seleccionado,
                    renderer.pais_objetivo,res,juego)
                renderer.mostrar_resultado_dados(res)
                if res.get("conquisto") and juego.conquista_pendiente:
                    renderer.mostrar_popup_conquista(
                        juego.conquista_pendiente["desde"],
                        juego.conquista_pendiente["hacia"],
                        juego.conquista_pendiente["max_pasar"],
                        juego.conquista_pendiente["disponibles"]
                    )
            else:
                renderer.mostrar_popup('ATAQUE INVÁLIDO',
                    'Revisá frontera, ejércitos, fase y tarjeta de situación.')
            renderer.pais_seleccionado = None
            renderer.pais_objetivo     = None
        else:
            renderer.mostrar_popup("ATACAR",
                                    "Selecciona origen (tuyo) y destino (enemigo) en el mapa.")

    elif accion == "reagrupar":
        if renderer.pais_seleccionado and renderer.pais_objetivo:
            desde = renderer.pais_seleccionado
            hacia = renderer.pais_objetivo
            if juego.es_propietario(desde,juego.turno_idx) and \
               juego.es_propietario(hacia,juego.turno_idx) and \
               juego.son_adyacentes(desde, hacia):
                # Mostrar popup para preguntar cuántos ejércitos mover
                max_mover = juego.ejercitos_de(desde,juego.turno_idx) - 1 - (juego.reagrupados_recibidos.get((desde,juego.turno_idx),0) if desde in juego.condominios else juego.reagrupados_recibidos.get(desde,0))
                if max_mover > 0:
                    renderer.mostrar_popup_reagrupar(desde, hacia, max_mover)
                else:
                    renderer.mostrar_popup("REAGRUPAR",
                                          f"No hay ejércitos disponibles para mover desde {desde}.\n"
                                          f"Se requiere dejar al menos 1 ejército en el territorio de origen.")
            else:
                renderer.mostrar_popup("REAGRUPAR",
                                        "Selecciona un pais propio origen y destino en el mapa.")
        else:
            renderer.mostrar_popup("REAGRUPAR",
                                    "Selecciona un pais propio origen y destino en el mapa.")

    elif accion == "reagrupar_misil":
        if renderer.pais_seleccionado and renderer.pais_objetivo:
            if juego.reagrupar_misil(renderer.pais_seleccionado,renderer.pais_objetivo):
                renderer.registrar_reagrupe(renderer.pais_seleccionado,renderer.pais_objetivo,1,juego,tipo='misil')
        renderer.pais_seleccionado=None
        renderer.pais_objetivo=None

    elif accion == "bot_turno":
        # Ejecutar turno del bot actual
        juego.turno_bot()
        renderer.pais_seleccionado = None
        renderer.pais_objetivo     = None

    renderer.construir_botones(juego)


def manejar_pactos(accion,juego,renderer):
    """Tramitación de pactos con aceptación explícita de bots y control del motor."""
    a=0  # Sólo el humano gestiona la interfaz, incluso fuera de su turno.
    origen=renderer.pais_seleccionado
    destino=renderer.pais_objetivo
    if accion=='pacto_reagrupe_omitir':
        juego.resolver_reagrupe_aliado()
        renderer.mostrar_popup('REAGRUPE CONJUNTO','Decidiste no trasladar más ejércitos.')
        return
    if accion.startswith('pacto_reagrupe_elegir_'):
        desde=accion[len('pacto_reagrupe_elegir_'):]
        renderer._reagrupe_aliado_desde=desde
        maximo=juego.ejercitos_de(desde,0)-1
        if maximo<1:return
        opciones=[('Mover 1','pacto_reagrupe_mover_1')]
        if maximo>=3:opciones.append(('Mover 3','pacto_reagrupe_mover_3'))
        if maximo>3:opciones.append((f'Máx. {maximo}',f'pacto_reagrupe_mover_{maximo}'))
        renderer.mostrar_popup('REAGRUPAR EN CONDOMINIO',
            f'En {desde} quedan {maximo+1} ejércitos. Elegí cuántos pasar, dejando 1 en origen.',
            opciones+[('Cancelar','pacto_reagrupe_omitir')])
        return
    if accion.startswith('pacto_reagrupe_mover_'):
        cantidad=int(accion.rsplit('_',1)[1])
        ok=juego.resolver_reagrupe_aliado(renderer._reagrupe_aliado_desde,cantidad)
        renderer.mostrar_popup('REAGRUPE CONJUNTO',
            f'Se trasladaron {cantidad} ejércitos al condominio.' if ok else 'No fue posible mover esa cantidad.')
        return
    if accion=='pacto_aceptar_bot' or accion=='pacto_rechazar_bot':
        aceptado = accion == 'pacto_aceptar_bot'
        resultado = juego.aceptar_propuesta_bot(aceptado)
        titulo, detalle = respuesta_propuesta_bot(resultado, aceptado)
        renderer.mostrar_popup(titulo, detalle)
        return
    if accion=='pacto_asaltos':
        lista=[x for x in juego.agresiones_pendientes if x['estado']=='pausada' and a in x['jugadores']]
        botones=[]
        for ag in lista:
            botones += [(f'Seguir #{ag["id"]}',f'pacto_seguir_{ag["id"]}'),
                        (f'Detener #{ag["id"]}',f'pacto_detener_{ag["id"]}')]
        renderer.mostrar_popup('ASALTOS VOLUNTARIOS',
            '\n'.join(f'#{ag["id"]}: {ag["destino"]} — {ag["resultado"]}' for ag in lista),
            botones+[('Cerrar','ok')])
        return
    if accion.startswith('pacto_seguir_'):
        agid=int(accion.rsplit('_',1)[1]);resultado=juego.ejecutar_agresion_conjunta(agid)
        renderer.mostrar_popup('ASALTO',resultado['resultado'] if resultado else 'Sólo se puede continuar en el turno del líder.')
        return
    if accion.startswith('pacto_detener_'):
        agid=int(accion.rsplit('_',1)[1]);ok=juego.cancelar_agresion_voluntaria(agid,a)
        renderer.mostrar_popup('ASALTO','Asalto detenido.' if ok else 'No se pudo detener.')
        return
    if accion=='pacto_romper_lista':
        pactos=[p for p in juego.pactos_vigentes() if a in p['jugadores'] and p['ruptura_por'] is None]
        zonas=[z for z in juego.zonas_internacionales if z['activa'] and a in z['jugadores']]
        opciones=[(f'Romper #{p["id"]}',f'pacto_romper_{p["id"]}') for p in pactos]
        opciones += [(f'Cancelar zona #{z["id"]}',f'pacto_cancelar_zona_{z["id"]}') for z in zonas]
        opciones=opciones[:11]+[('Volver','ver_pactos')]
        texto='\n'.join(juego.descripcion_pacto(p) for p in pactos) if pactos else 'No tenés pactos de no agresión para romper.'
        renderer.mostrar_popup('RUPTURA DE PACTOS',texto,opciones)
        return
    if accion.startswith('pacto_romper_'):
        idp=int(accion.split('_')[-1]);val=juego.romper_pacto(idp,a)
        renderer.mostrar_popup('RUPTURA ANUNCIADA',
            'La protección permanece hasta que finalice el próximo turno del otro firmante.' if val else 'No se puede romper el pacto.')
        return
    if accion.startswith('pacto_decidir_zona_'):
        trozos=accion.split('_')
        zona_id=int(trozos[3]);mantener=trozos[4]=='mantener'
        juego.decidir_zona_incumplida(zona_id,0,mantener)
        renderer.mostrar_popup('ZONA INTERNACIONAL','Decisión registrada.')
        return
    if accion.startswith('pacto_cancelar_zona_'):
        ok=juego.cancelar_zona_internacional(int(accion.split('_')[-1]),a)
        renderer.mostrar_popup('ZONA INTERNACIONAL','Zona cancelada.' if ok else 'No se pudo cancelar.')
        return
    if accion=='pacto_mundial_lista':
        opciones=[(j.color_nombre,f'pacto_mundial_con_{j.idx}') for j in juego.jugadores if not j.eliminado and j.idx!=a]
        renderer.mostrar_popup('PACTO MUNDIAL','Elegí el color con el cual proponer no agresión en todo el mundo.',opciones+[('Cancelar','ok')])
        return
    if accion.startswith('pacto_mundial_con_'):
        b=int(accion.rsplit('_',1)[1]);tipo='mundial'
    elif accion in ('pacto_pais','pacto_continente','pacto_frontera','pacto_mundial','pacto_zona','pacto_agresion'):
        if origen not in juego.tablero or destino not in juego.tablero or not juego.es_propietario(origen,a):
            renderer.mostrar_popup('SELECCIONÁ PAÍSES','Elegí un país tuyo de origen y otro país de destino antes de proponer.')
            return
        b=juego.tablero[destino]['propietario'];tipo=accion[6:]
    else:return
    if tipo=='agresion':
        # El aliado tiene que limitar con el mismo país tercero, y conservar
        # tropas para dejar una guarnición en el eventual condominio.
        candidatos=[]
        for q in juego.tablero[destino]['fronteras']:
            jidx=juego.tablero[q]['propietario']
            if (jidx is not None and jidx not in (a,b) and
                juego.ejercitos_de(q,jidx)>=2 and juego.jugadores[jidx].es_bot):
                candidatos.append((jidx,q))
        if origen in juego.condominios:
            for jidx in juego.condominios[origen]:
                if jidx!=a and jidx!=b and juego.jugadores[jidx].es_bot and juego.ejercitos_de(origen,jidx)>=2:
                    candidatos.insert(0,(jidx,origen))
        if not candidatos:
            renderer.mostrar_popup('PACTO DE AGRESIÓN','Se necesita un tercer jugador, aliado limítrofe al destino y con al menos 2 ejércitos.')
            return
        botones=[(f'{juego.jugadores[idx].color_nombre}: {p}',f'pacto_agredir_con_{idx}_{p}') for idx,p in candidatos[:7]]
        renderer.mostrar_popup('ATAQUE CONJUNTO',f'Atacar {destino} desde {origen}. Elegí socio y país agresor.',botones+[('Cancelar','ok')])
        return
    if tipo=='zona':
        res=juego.proponer_zona_internacional(a,b,destino) if b is not None and juego.bot_acepta_pacto(b,'zona',a) else None
    else:
        if b is None or not juego.bot_acepta_pacto(b,tipo,a):res=None
        else:
            kw={}
            if tipo=='pais':kw['paises']=(origen,destino)
            if tipo=='continente':kw['continente']=juego.tablero[origen]['continente']
            if tipo=='frontera':kw['continentes']=(juego.tablero[origen]['continente'],juego.tablero[destino]['continente'])
            res=juego.proponer_no_agresion(a,b,tipo,**kw)
    renderer.mostrar_popup('PACTO '+('FIRMADO' if res else 'NO ACORDADO'),
        ('Ambos aceptaron. El acuerdo es público y obligatorio hasta su ruptura reglamentaria.' if res else
         'El otro jugador rechazó la propuesta, o no se cumplen los requisitos del reglamento.'))


def resolver_pacto_agresion(accion,juego,renderer):
    if accion.startswith('pacto_agredir_con_'):
        resto=accion[len('pacto_agredir_con_'):]
        idx_s,pais=resto.split('_',1)
        b=int(idx_s)
        # Se puede fijar el ataque para el turno propio o el del aliado.
        botones=[('En mi turno',f'pacto_confirmar_agresion_{b}_{pais}_0'),
                 (f'Turno de {juego.jugadores[b].color_nombre}',f'pacto_confirmar_agresion_{b}_{pais}_{b}'),
                 ('Cancelar','ok')]
        renderer.mostrar_popup('CUÁNDO ATACAR',
            'Elegí durante el turno de qué firmante se realizará el asalto obligatorio. '
            'Al comenzar ese turno, ambos atacarán alternadamente.',botones)
        return True
    if not accion.startswith('pacto_confirmar_agresion_'):return False
    resto=accion[len('pacto_confirmar_agresion_'):]
    pre,lider_s=resto.rsplit('_',1)
    idx_s,pais=pre.split('_',1)
    a=0;b=int(idx_s);lider=int(lider_s)
    if not juego.bot_acepta_pacto(b,'agresion',a,renderer.pais_objetivo):
        renderer.mostrar_popup('PACTO RECHAZADO',f'{juego.jugadores[b].nombre} no aceptó el ataque conjunto.')
        return True
    ag=juego.proponer_agresion_conjunta(a,b,renderer.pais_seleccionado,pais,renderer.pais_objetivo,lider=lider)
    if ag:
        if juego.fase=='ATACAR' and juego.turno_idx==lider and ag['ronda']<=juego.ronda:
            resultado=juego.ejecutar_agresion_conjunta(ag['id'])
            mensaje=f'{resultado["tiradas"]} tiradas conjuntas. {resultado["resultado"]}'
        else:
            mensaje=(f'PACTO #{ag["id"]} confirmado. Ataque programado para la ronda '
                     f'{ag["ronda"]}, turno de {juego.jugadores[lider].nombre}.')
    else:mensaje='No se reúnen todas las condiciones reglamentarias.'
    renderer.mostrar_popup('ATAQUE CONJUNTO',mensaje)
    renderer.construir_botones(juego)
    return True

def manejar_accion_popup(accion, juego, renderer):
    """Maneja las respuestas de los popups interactivos."""
    if not accion:return
    if resolver_pacto_agresion(accion,juego,renderer):return
    if accion.startswith('pacto_') or accion=='ver_pactos':
        if accion=='ver_pactos':renderer.mostrar_pactos(juego)
        else:manejar_pactos(accion,juego,renderer)
        return
    if accion.startswith('atacar_condominio_'):
        defensa=int(accion.rsplit('_',1)[1])
        res=juego.atacar_condominio(renderer.pais_seleccionado,renderer.pais_objetivo,defensor_idx=defensa)
        if res['ok']:
            renderer.registrar_combate(renderer.pais_seleccionado,renderer.pais_objetivo,res,juego)
            renderer.mostrar_resultado_dados(res)
        else:renderer.mostrar_popup('ATAQUE NO PERMITIDO','Revisá pacto, guarnición y fase de ataque.')
        renderer.construir_botones(juego)
        return
    if accion.startswith("pasar_ejercitos_"):
        cant = int(accion.split("_")[-1])
        juego.resolver_conquista(cant)
        renderer.popup = None
        renderer.construir_botones(juego)
    elif accion.startswith("reagrupar_ajustar_"):
        # Manejar ajustes de cantidad para reagrupar
        if hasattr(renderer, '_reagrupar_state'):
            ajuste = int(accion.split("_")[-1])
            estado = renderer._reagrupar_state
            estado["cantidad_actual"] = max(1, min(estado["maximo_disponible"], estado["cantidad_actual"] + ajuste))
            # Actualizar el popup con la nueva cantidad
            desde = estado["desde"]
            hacia = estado["hacia"]
            maximo = estado["maximo_disponible"]
            actual = estado["cantidad_actual"]
            titulo = "REAGRUPAR EJÉRCITOS"
            mensaje = (f"Mover ejércitos de {desde} a {hacia}.\n"
                       f"En {desde} hay {maximo + 1} ejércitos (debes dejar al menos 1).\n"
                       f"Selecciona la cantidad a mover: {actual}")
            botones = [
                ("-10", "reagrupar_ajustar_-10"),
                ("-1", "reagrupar_ajustar_-1"),
                ("+1", "reagrupar_ajustar_+1"),
                ("+10", "reagrupar_ajustar_+10"),
                ("Máx", "reagrupar_maximo"),
                ("Confirmar", "reagrupar_confirmar")
            ]
            renderer.mostrar_popup(titulo, mensaje, botones)
    elif accion == "reagrupar_maximo":
        # Establecer cantidad al máximo disponible
        if hasattr(renderer, '_reagrupar_state'):
            estado = renderer._reagrupar_state
            estado["cantidad_actual"] = estado["maximo_disponible"]
            # Actualizar el popup
            desde = estado["desde"]
            hacia = estado["hacia"]
            maximo = estado["maximo_disponible"]
            actual = estado["cantidad_actual"]
            titulo = "REAGRUPAR EJÉRCITOS"
            mensaje = (f"Mover ejércitos de {desde} a {hacia}.\n"
                       f"En {desde} hay {maximo + 1} ejércitos (debes dejar al menos 1).\n"
                       f"Selecciona la cantidad a mover: {actual}")
            botones = [
                ("-10", "reagrupar_ajustar_-10"),
                ("-1", "reagrupar_ajustar_-1"),
                ("+1", "reagrupar_ajustar_+1"),
                ("+10", "reagrupar_ajustar_+10"),
                ("Máx", "reagrupar_maximo"),
                ("Confirmar", "reagrupar_confirmar")
            ]
            renderer.mostrar_popup(titulo, mensaje, botones)
    elif accion == "reagrupar_confirmar":
        # Confirmar y ejecutar el reagrupar
        if hasattr(renderer, '_reagrupar_state'):
            estado = renderer._reagrupar_state
            desde = estado["desde"]
            hacia = estado["hacia"]
            cantidad = estado["cantidad_actual"]
            if juego.reagrupar(desde, hacia, cantidad):
                renderer.registrar_reagrupe(desde,hacia,cantidad,juego,tipo='ejercitos')
            renderer.popup = None
            renderer.pais_seleccionado = None
            renderer.pais_objetivo     = None
            if hasattr(renderer, '_reagrupar_state'):
                delattr(renderer, '_reagrupar_state')
            renderer.construir_botones(juego)
    elif accion.startswith("reagrupar_ejercitos_"):
        # Mantener compatibilidad con el código antiguo (por si acaso)
        cant = int(accion.split("_")[-1])
        if juego.reagrupar(renderer.pais_seleccionado, renderer.pais_objetivo, cant):
            renderer.registrar_reagrupe(renderer.pais_seleccionado,renderer.pais_objetivo,cant,juego,tipo='ejercitos')
        renderer.popup = None
        renderer.pais_seleccionado = None
        renderer.pais_objetivo     = None
        renderer.construir_botones(juego)


def pantalla_victoria(renderer, juego, ganador_nombre):
    """Muestra pantalla de victoria hasta que el jugador presione tecla."""
    C_ACCENT = (255, 180, 0)
    C_TEXT   = (230, 230, 240)
    C_BG     = (15, 20, 35)

    running = True
    while running:
        renderer.screen.fill(C_BG)
        w = renderer.WIN_W
        tit = renderer.font_title.render("VICTORIA!", True, C_ACCENT)
        renderer.screen.blit(tit, ((w - tit.get_width()) // 2, 200))
        msg = renderer.font_xl.render(f"{ganador_nombre} ha conquistado el planeta!", True, C_TEXT)
        renderer.screen.blit(msg, ((w - msg.get_width()) // 2, 280))
        instr = renderer.font_md.render("Presiona cualquier tecla para salir.", True, (120, 130, 150))
        renderer.screen.blit(instr, ((w - instr.get_width()) // 2, 380))
        pygame.display.flip()
        renderer.clock.tick(30)

        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False


def main():
    pygame.init()
    renderer = Renderer()

    # Pantalla de menú con cantidad de jugadores y color humano
    n_jugadores, color_humano, incluir_eliminacion, animaciones_activas = renderer.pantalla_menu()
    renderer.animaciones_activas = animaciones_activas

    # Inicializar juego
    juego = JuegoTEG(n_jugadores=n_jugadores, color_humano=color_humano,
                    objetivos_eliminacion=incluir_eliminacion)
    renderer.construir_botones(juego)

    running = True
    siguiente_paso_bot = pygame.time.get_ticks() + 1100
    situacion_anunciada = 0
    while running:
        # El aviso se muestra ANTES de cualquier acción de la ronda (incluido el bot).
        if debe_mostrar_situacion(juego, situacion_anunciada, renderer):
            renderer.mostrar_popup_situacion(juego)
            situacion_anunciada = juego.ronda
            renderer.construir_botones(juego)
        # ─── Eventos ────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if (renderer.popup and renderer.popup.get('tipo') == 'pacto_propuesta'
                        and event.key in (pygame.K_a, pygame.K_r, pygame.K_RETURN)):
                    accion = ('pacto_rechazar_bot' if event.key == pygame.K_r
                              else 'pacto_aceptar_bot')
                    renderer.popup = None
                    manejar_accion_popup(accion, juego, renderer)
                elif event.key == pygame.K_ESCAPE:
                    if renderer.vista_tarjetas: renderer.vista_tarjetas=None
                    elif renderer.popup:
                        if not renderer.popup.get('obligatorio'):
                            renderer.popup=None
                    else: running=False
                elif event.key == pygame.K_t:
                    if renderer.vista_tarjetas: renderer.vista_tarjetas=None
                    elif not renderer.popup:renderer.abrir_tarjetas(juego)
                elif event.key == pygame.K_f:
                    renderer.cambiar_velocidad_bot()
                    renderer.construir_botones(juego)
                elif event.key == pygame.K_o:
                    if not renderer.popup and not renderer.vista_tarjetas:
                        renderer.mostrar_objetivos(juego)
                elif event.key == pygame.K_p:
                    if not renderer.popup and not renderer.vista_tarjetas:
                        renderer.mostrar_pactos(juego)
                elif event.key == pygame.K_h:
                    if not renderer.popup and not renderer.vista_tarjetas:
                        renderer.mostrar_historial(juego)
                elif renderer.vista_tarjetas or renderer.popup:
                    pass
                elif juego.conquista_pendiente:
                    max_p = juego.conquista_pendiente["max_pasar"]
                    if event.key in (pygame.K_1, pygame.K_KP1):
                        manejar_accion_popup("pasar_ejercitos_1", juego, renderer)
                    elif event.key in (pygame.K_2, pygame.K_KP2) and max_p >= 2:
                        manejar_accion_popup("pasar_ejercitos_2", juego, renderer)
                    elif event.key in (pygame.K_3, pygame.K_KP3) and max_p >= 3:
                        manejar_accion_popup("pasar_ejercitos_3", juego, renderer)
                elif event.key == pygame.K_SPACE:
                    # Pasar fase rapido
                    manejar_boton("pasar", juego, renderer)
                elif event.key == pygame.K_b:
                    # Forzar turno bot (para depuracion)
                    if juego.jugador_actual().es_bot:
                        manejar_boton("bot_turno", juego, renderer)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos

                # Pantalla de tarjetas: seleccioná mano de jugador y cartas para canje.
                if renderer.vista_tarjetas:
                    if event.button == 1:
                        resultado=renderer.click_vista_tarjetas(pos,juego)
                        if isinstance(resultado,tuple) and resultado[0]=='canjear_seleccion':
                            _,indices,continentes=resultado
                            ref=juego.canjear_tarjetas(indices,continentes)
                            if ref:
                                renderer.vista_tarjetas=None
                                renderer.mostrar_popup('CANJE EXITOSO',f'Selección válida. Incorporás {ref} ejércitos adicionales.')
                            else:
                                renderer.vista_tarjetas=None
                                renderer.mostrar_popup('CANJE INVÁLIDO','Revisá la combinación elegida.')
                    continue

                # Popup primero
                if renderer.popup:
                    if (renderer.popup.get('tipo') == 'pacto_propuesta' and
                        renderer.MAP_X <= pos[0] < renderer.MAP_X + renderer.MAP_W and event.button == 1):
                        # El mapa se puede consultar durante la negociación;
                        # ningún clic inicia ataques, refuerzos o turnos.
                        renderer.inspeccionar_pais_pacto(pos,juego)
                    elif event.button == 1:
                        accion_popup = renderer.click_popup(pos)
                        if accion_popup:
                            manejar_accion_popup(accion_popup, juego, renderer)
                    continue

                if juego.conquista_pendiente:
                    continue

                if renderer.menu_contextual:
                    if event.button==1:
                        accion_ctx=renderer.click_menu_contextual(pos)
                        if accion_ctx:
                            manejar_boton(accion_ctx,juego,renderer)
                        continue
                    if event.button==3:renderer.menu_contextual=None

                if event.button == 1:
                    # Verificar botones del panel
                    accion_btn = None
                    for btn in renderer.botones:
                        if btn.check_click(pos):
                            accion_btn = btn.accion
                            break

                    if accion_btn:
                        manejar_boton(accion_btn, juego, renderer)
                    elif renderer.MAP_X <= pos[0] < renderer.MAP_X + renderer.MAP_W:
                        manejar_clic_mapa(pos, juego, renderer)
                    if accion_btn=='velocidad_bot':
                        siguiente_paso_bot=pygame.time.get_ticks()+200

                elif event.button == 3:
                    nombre=renderer.pais_en_pos(pos,juego.tablero)
                    if nombre and not juego.jugador_actual().es_bot:
                        renderer._contexto_pais=nombre
                        if juego.fase==FASE_INCORPORAR:
                            renderer.pais_seleccionado=nombre
                            renderer.pais_objetivo=None
                        renderer.abrir_menu_contextual(nombre,pos,juego)
                        renderer.construir_botones(juego)

                elif event.button == 4:   # scroll arriba
                    renderer.scroll_log = min(renderer.scroll_log + 1,
                                              max(0, len(juego.historial) - 3))
                elif event.button == 5:   # scroll abajo
                    renderer.scroll_log = max(0, renderer.scroll_log - 1)

            elif event.type == pygame.MOUSEMOTION:
                renderer.update_hover(event.pos)

        # Compromisos de agresión firmados previamente: se ejecutan solos
        # al llegar al turno del líder, antes de otros ataques o decisiones bot.
        if (juego.fase==FASE_ATACAR and not renderer.popup and
            not renderer.vista_tarjetas and not juego.conquista_pendiente):
            pendientes=[ag for ag in juego.agresiones_pendientes if
                        ag['estado']=='pendiente' and ag['lider']==juego.turno_idx and
                        ag['ronda']<=juego.ronda]
            if pendientes:
                ag=pendientes[0]
                resultado=juego.ejecutar_agresion_conjunta(ag['id'])
                if resultado:
                    renderer.mostrar_popup('PACTO DE AGRESIÓN',
                        f'{ag["destino"]}: {resultado["resultado"]}. Tiradas: {resultado["tiradas"]}.')
                    renderer.construir_botones(juego)

        # ─── BOT: un movimiento por intervalo, sin bloquear los eventos ──
        jugador_actual = juego.jugador_actual()
        if juego.reagrupe_aliado_pendiente is not None and not renderer.popup:
            ag=next(x for x in juego.agresiones_pendientes if x['id']==juego.reagrupe_aliado_pendiente)
            vecinos=[p for p in juego.tablero[ag['destino']]['fronteras'] if
                     juego.es_propietario(p,0) and juego.ejercitos_de(p,0)>=2]
            opciones=[(f'Desde {p}',f'pacto_reagrupe_elegir_{p}') for p in vecinos[:6]]
            opciones.append(('No mover','pacto_reagrupe_omitir'))
            renderer.mostrar_popup('TU REAGRUPE EXTRA',
                f'Colaboraste en la conquista de {ag["destino"]}. '
                'Antes del siguiente turno podés pasar tropas tuyas al condominio.',opciones)
        if not renderer.popup and not renderer.vista_tarjetas:
            for z in juego.zonas_internacionales:
                if z['activa'] and z.get('decision_pendiente')==0:
                    renderer.mostrar_popup('INCUMPLIMIENTO DE ZONA',
                        f'{juego.jugadores[z["incumplio"]].nombre} no cumplió la conquista de {z["pais"]}. '
                        'Se aplicó su penalización. ¿Mantenés o cancelás el pacto?',
                        [('Mantener',f'pacto_decidir_zona_{z["id"]}_mantener'),
                         ('Cancelar',f'pacto_decidir_zona_{z["id"]}_cancelar')])
                    break
        if juego.propuesta_pendiente and not renderer.popup:
            pp=juego.propuesta_pendiente
            # Vista de decisión en panel derecho, con el MAPA DESPEJADO
            # y los territorios implicados identificados sobre sus fichas.
            renderer.mostrar_propuesta_pacto(juego, pp)
        ahora=pygame.time.get_ticks()
        espera=renderer.ms_entre_pasos_bot()
        if (jugador_actual.es_bot and juego.fase!='VICTORIA' and
            not renderer.popup and not renderer.vista_tarjetas and espera is not None and
            ahora>=siguiente_paso_bot):
            estado=juego.paso_bot()
            if estado:
                renderer.ultimo_evento_bot=estado['texto']
                renderer.pais_seleccionado=estado.get('pais')
                renderer.pais_objetivo=estado.get('destino')
                if estado.get('accion')=='canje':
                    renderer.registrar_canje(jugador_actual.nombre, estado.get('valor',0))
                if estado.get('accion')=='incorporar' and estado.get('pais'):
                    renderer.registrar_incorporacion(estado['pais'],estado.get('cantidad',1),juego,tipo='ejercitos',jugador_idx=jugador_actual.idx)
                if estado.get('accion')=='reagrupar' and estado.get('pais') and estado.get('destino'):
                    renderer.registrar_reagrupe(estado['pais'],estado['destino'],estado.get('cantidad',1),juego,tipo='ejercitos',jugador_idx=jugador_actual.idx)
                if estado.get('pais') and estado.get('destino'):
                    if estado.get('dados') and estado['dados'].get('ok'):
                        renderer.registrar_combate(estado['pais'],estado['destino'],
                            estado['dados'],juego)
                    elif estado.get('accion')=='misil' or 'MISIL' in estado.get('texto','').upper():
                        renderer.registrar_combate(estado['pais'],estado['destino'],
                            None,juego,tipo='misil')
                if estado.get('dados'):
                    renderer.mostrar_resultado_dados(estado['dados'],frames=65 if espera>500 else 26)
            siguiente_paso_bot=ahora+espera
            renderer.construir_botones(juego)
        elif not jugador_actual.es_bot:
            siguiente_paso_bot=ahora+1100

        # ─── Verificar victoria ──────────────────────────────────────
        if juego.fase == "VICTORIA":
            renderer.render(juego)
            pygame.time.delay(1000)
            ganador = juego.jugadores[juego.ganador_idx].nombre
            pantalla_victoria(renderer, juego, ganador)
            running = False

        # ─── Renderizar ──────────────────────────────────────────────
        renderer.render(juego)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
