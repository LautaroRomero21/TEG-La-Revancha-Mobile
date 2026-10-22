"""Prueba real de construcción de pantallas Kivy, ejecutada con Xvfb en CI.

Verifica imports gráficos, carga del mapa y controles, además del motor.
No reemplaza una prueba en un dispositivo Android real.
"""
import os
import sys
import traceback

os.environ.setdefault("KIVY_NO_ARGS", "1")

def main():
    from kivy.core.window import Window
    from main import TegAndroid, PantallaInicio, VistaJuego

    app = TegAndroid()
    inicio = app.build()
    assert len(inicio.children) == 1
    assert isinstance(inicio.children[0], PantallaInicio), "No se creó la pantalla inicial"
    print("SMOKE: pantalla inicial Kivy renderizable.", flush=True)

    app.iniciar(2, 0, True, False)
    assert len(app.rootview.children) == 1
    juego = app.rootview.children[0]
    assert isinstance(juego, VistaJuego), "No se creó la pantalla de partida"
    juego.actualizar(1 / 24)
    juego.mapa.renderizar()
    assert len(juego.c.juego.tablero) == 72
    assert juego.children[0] is juego.lateral, "El panel no está a la derecha"
    assert juego.children[1] is juego.zona_mapa, "El mapa no está a la izquierda"
    assert juego.acciones.orientation == "vertical"
    assert not hasattr(juego, "hud"), "El encabezado redundante sigue presente"
    assert not hasattr(juego, "titulo_turnos"), "El titulo de turnos sigue presente"
    assert juego.scatter._callback_doble is not None
    assert not hasattr(juego, "texto_hud")
    assert len(juego.lista_turnos.children) == 2
    assert juego.c.resumen()["jugadores"][0][0] == juego.c.juego.jugadores[
        juego.c.juego.orden_visual_jugadores()[0]
    ].nombre

    # Cambiar el orden visual de ronda sin modificar la logica de turnos.
    j = juego.c.juego
    anterior = list(j.orden_ronda)
    j.orden_ronda = anterior[1:] + anterior[:1]
    juego.actualizar_orden_turnos()
    assert juego.lista_turnos.children[-1].children[0].text.startswith("1. " + j.jugadores[j.orden_ronda[0]].nombre)
    assert juego.c.resumen()["jugadores"][0][0] == j.jugadores[j.orden_ronda[0]].nombre
    print("SMOKE: mapa lateral y orden dinamico de rondas OK.", flush=True)
    print("SMOKE: vista de partida, recursos de mapa, controles y 72 países OK.", flush=True)

    Window.close()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
