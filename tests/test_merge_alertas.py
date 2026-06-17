from app.aemet import merge_alertas


# Datos reales de la elaboración AEMET de las 09:33 del 17/06/2026 (Madrid).
# Cuatro avisos amarillos de temperaturas máximas: 2 zonas x 2 días de validez.
def _amarillo(area, expires):
    return {
        "identifier": f"id-{area}-{expires}",
        "event": "Aviso de temperaturas máximas de nivel amarillo",
        "severity": "Moderate",
        "certainty": "Likely",
        "headline": "Aviso de temperaturas máximas de nivel amarillo. " + area,
        "description": "Temperatura máxima: 36 ºC.",
        "effective": "2026-06-17T11:33:56+02:00",
        "expires": expires,
        "areas": [area],
    }


CASO_REAL = [
    _amarillo("Metropolitana y Henares", "2026-06-17T20:59:59+02:00"),
    _amarillo("Metropolitana y Henares", "2026-06-18T20:59:59+02:00"),
    _amarillo("Sur, Vegas y Oeste", "2026-06-17T20:59:59+02:00"),
    _amarillo("Sur, Vegas y Oeste", "2026-06-18T20:59:59+02:00"),
]


def test_colapsa_mismo_evento_severidad_zona_a_un_aviso():
    merged = merge_alertas(CASO_REAL)
    assert len(merged) == 2


def test_usa_expires_maximo_del_grupo():
    merged = merge_alertas(CASO_REAL)
    by_area = {a["areas"][0]: a for a in merged}
    assert by_area["Metropolitana y Henares"]["expires"] == "2026-06-18T20:59:59+02:00"
    assert by_area["Sur, Vegas y Oeste"]["expires"] == "2026-06-18T20:59:59+02:00"


def test_usa_effective_minimo_del_grupo():
    alerts = [
        _amarillo("Sierra de Madrid", "2026-06-18T20:59:59+02:00"),
        {**_amarillo("Sierra de Madrid", "2026-06-17T20:59:59+02:00"),
         "effective": "2026-06-17T09:00:00+02:00"},
    ]
    merged = merge_alertas(alerts)
    assert len(merged) == 1
    assert merged[0]["effective"] == "2026-06-17T09:00:00+02:00"


def test_clave_dedup_estable_por_grupo():
    merged = merge_alertas(CASO_REAL)
    keys = {a["dedup_key"] for a in merged}
    assert len(keys) == 2
    # La clave no depende del identifier crudo de AEMET (que cambia por día/elaboración)
    for a in merged:
        assert "id-" not in a["dedup_key"]
    # Reejecutar con los mismos datos da la misma clave (idempotente)
    again = merge_alertas(CASO_REAL)
    assert {a["dedup_key"] for a in again} == keys


def test_distinta_severidad_no_se_mezcla():
    alerts = [
        _amarillo("Metropolitana y Henares", "2026-06-18T20:59:59+02:00"),
        {**_amarillo("Metropolitana y Henares", "2026-06-18T20:59:59+02:00"),
         "severity": "Severe"},
    ]
    merged = merge_alertas(alerts)
    assert len(merged) == 2


def test_orden_de_areas_no_afecta_al_grupo():
    a1 = {**_amarillo("x", "2026-06-18T20:59:59+02:00"),
          "areas": ["Sur, Vegas y Oeste", "Metropolitana y Henares"]}
    a2 = {**_amarillo("x", "2026-06-17T20:59:59+02:00"),
          "areas": ["Metropolitana y Henares", "Sur, Vegas y Oeste"]}
    merged = merge_alertas([a1, a2])
    assert len(merged) == 1
