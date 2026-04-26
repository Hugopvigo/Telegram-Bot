import httpx
from app.config import AEMET_API_KEY

AEMET_BASE = "https://opendata.aemet.es/opendata"

PROVINCIAS = {
    "A Coruña": "15", "Álava": "01", "Albacete": "02", "Alicante": "03",
    "Almería": "04", "Asturias": "33", "Ávila": "05", "Badajoz": "06",
    "Barcelona": "08", "Bizkaia": "48", "Burgos": "09", "Cáceres": "10",
    "Cádiz": "11", "Cantabria": "39", "Castellón": "12", "Ciudad Real": "13",
    "Córdoba": "14", "Cuenca": "16", "Girona": "17", "Granada": "18",
    "Guadalajara": "19", "Gipuzkoa": "20", "Huelva": "21", "Huesca": "22",
    "Illes Balears": "07", "Jaén": "23", "La Rioja": "26", "Las Palmas": "35",
    "León": "24", "Lleida": "25", "Lugo": "27", "Madrid": "28",
    "Málaga": "29", "Murcia": "30", "Navarra": "31", "Ourense": "32",
    "Palencia": "34", "Pontevedra": "36", "Salamanca": "37", "Santa Cruz de Tenerife": "38",
    "Segovia": "40", "Sevilla": "41", "Soria": "42", "Tarragona": "43",
    "Teruel": "44", "Toledo": "45", "Valencia": "46", "Valladolid": "47",
    "Zamora": "49", "Zaragoza": "50", "Ceuta": "51", "Melilla": "52",
}

PROVINCIA_CODES = {v: k for k, v in PROVINCIAS.items()}

_client = httpx.Client(timeout=30.0)


def _aemet_get(endpoint: str) -> dict:
    url = f"{AEMET_BASE}{endpoint}"
    headers = {"api_key": AEMET_API_KEY}
    r = _client.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    if data.get("estado") == 200 and "datos" in data:
        datos_url = data["datos"]
        r2 = _client.get(datos_url, headers=headers)
        r2.raise_for_status()
        return r2.json()
    return data


def get_alertas_provincia(codigo: str) -> list[dict]:
    endpoint = f"/api/avisos_cap/{codigo}"
    try:
        return _aemet_get(endpoint)
    except Exception as e:
        print(f"Error obteniendo alertas para {codigo}: {e}")
        return []


def get_alertas_nacional() -> list[dict]:
    endpoint = "/api/avisos_cap/es"
    try:
        return _aemet_get(endpoint)
    except Exception as e:
        print(f"Error obteniendo alertas nacionales: {e}")
        return []


def format_alerta(alerta: dict) -> str:
    event = alerta.get("event", "Alerta meteorológica")
    severity = alerta.get("severity", "")
    headline = alerta.get("headline", "")
    description = alerta.get("description", "")
    effective = alerta.get("effective", "")
    expires = alerta.get("expires", "")

    severity_emoji = {
        "Extreme": "🔴", "Severe": "🟠", "Moderate": "🟡", "Minor": "🟢"
    }.get(severity, "⚪")

    msg = f"{severity_emoji} *{event}*\n"
    msg += f"Severidad: {severity}\n"
    if headline:
        msg += f"{headline}\n"
    if description:
        msg += f"\n{description[:500]}\n"
    if effective:
        msg += f"\n🕐 Desde: {effective}"
    if expires:
        msg += f"\n🕐 Hasta: {expires}"

    return msg


def search_provincia(query: str) -> str | None:
    q = query.lower()
    for nombre, codigo in PROVINCIAS.items():
        if q in nombre.lower():
            return codigo
    return None
