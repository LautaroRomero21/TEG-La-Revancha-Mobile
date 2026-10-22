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
    print("SMOKE: vista de partida, recursos de mapa, controles y 72 países OK.", flush=True)

    Window.close()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
