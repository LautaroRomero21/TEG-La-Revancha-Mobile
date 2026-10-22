"""Mensajes de resultados diplomáticos, sin dependencias gráficas."""


def respuesta_propuesta_bot(resultado, aceptado):
    """Separa un pacto de NO AGRESIÓN de una AGRESIÓN conjunta.

    Un pacto usa las claves `tipo`, `paises`, `id` y NO lleva `estado` ni
    `tiradas`. Sólo una agresión conjunta contiene esos campos.
    """
    if not aceptado:
        return 'PACTO RECHAZADO', 'Rechazaste el pacto. Ninguna restricción fue registrada.'
    if not resultado:
        return ('PACTO NO FIRMADO',
                'No se pudo formalizar el acuerdo: alguna condición ya no se cumple.')
    if isinstance(resultado, dict):
        if resultado.get('tipo') == 'pais' and resultado.get('paises'):
            p1, p2 = resultado['paises']
            return ('PACTO FIRMADO',
                    f'No agresión firmada entre {p1} y {p2}. '
                    'Es pública y obligatoria hasta su ruptura reglamentaria.')
        if 'estado' in resultado:
            return ('ATAQUE CONJUNTO',
                    f'Ataque conjunto sobre {resultado.get("destino", "el objetivo")}: '
                    f'{resultado["estado"]}. Tiradas: {resultado.get("tiradas", 0)}. '
                    f'{resultado.get("resultado", "")}')
    return 'PACTO FIRMADO', 'Pacto firmado y obligatorio.'
