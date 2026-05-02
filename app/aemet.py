import io
import tarfile
import httpx
import xml.etree.ElementTree as ET
from app.config import AEMET_API_KEY

AEMET_BASE = "https://opendata.aemet.es/opendata"
_tar_cache: dict[str, bytes] = {}

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

PROVINCIA_TO_CCAA = {
    "04": "61", "11": "61", "14": "61", "18": "61", "21": "61",
    "23": "61", "29": "61", "41": "61",
    "22": "62", "44": "62", "50": "62",
    "33": "63",
    "07": "64",
    "35": "65", "38": "65",
    "39": "66",
    "05": "67", "09": "67", "24": "67", "34": "67", "37": "67",
    "40": "67", "42": "67", "47": "67", "49": "67",
    "02": "68", "13": "68", "16": "68", "19": "68", "45": "68",
    "08": "69", "17": "69", "25": "69", "43": "69",
    "06": "70", "10": "70",
    "15": "71", "27": "71", "32": "71", "36": "71",
    "28": "72",
    "30": "73",
    "31": "74",
    "01": "75", "20": "75", "48": "75",
    "26": "76",
    "03": "77", "12": "77", "46": "77",
    "51": "78",
    "52": "79",
}

CCAA_CODES = {v: k for k, v in PROVINCIA_TO_CCAA.items()}

_client = httpx.Client(timeout=30.0)
CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


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


def clear_tar_cache():
    _tar_cache.clear()


def _aemet_get_bytes(endpoint: str) -> bytes:
    cached = _tar_cache.get(endpoint)
    if cached is not None:
        return cached
    url = f"{AEMET_BASE}{endpoint}"
    headers = {"api_key": AEMET_API_KEY}
    r = _client.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    if data.get("estado") == 200 and "datos" in data:
        datos_url = data["datos"]
        r2 = _client.get(datos_url, headers=headers)
        r2.raise_for_status()
        _tar_cache[endpoint] = r2.content
        return r2.content
    return b""


def _cap_xml_to_dicts(root: ET.Element) -> list[dict]:
    alerts = []
    for info in root.findall("cap:info", CAP_NS):
        areas = []
        for area in info.findall("cap:area", CAP_NS):
            desc = area.findtext("cap:areaDesc", "", CAP_NS)
            if desc:
                areas.append(desc)
        alerts.append({
            "identifier": root.findtext("cap:identifier", "", CAP_NS),
            "event": info.findtext("cap:event", "Alerta meteorológica", CAP_NS),
            "severity": info.findtext("cap:severity", "", CAP_NS),
            "headline": info.findtext("cap:headline", "", CAP_NS),
            "description": info.findtext("cap:description", "", CAP_NS),
            "effective": info.findtext("cap:effective", "", CAP_NS),
            "expires": info.findtext("cap:expires", "", CAP_NS),
            "areas": areas,
        })
    return alerts


def _cap_tar_to_dicts(tar_bytes: bytes) -> list[dict]:
    if not tar_bytes:
        return []
    alerts = []
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        for member in tar.getmembers():
            f = tar.extractfile(member)
            if f is None:
                continue
            try:
                xml_text = f.read().decode("utf-8")
                root = ET.fromstring(xml_text)
                alerts.extend(_cap_xml_to_dicts(root))
            except (ET.ParseError, UnicodeDecodeError, ValueError):
                continue
    return alerts


def get_alertas_provincia(codigo: str) -> list[dict]:
    try:
        ccaa = PROVINCIA_TO_CCAA.get(codigo)
        if not ccaa:
            return []
        endpoint = f"/api/avisos_cap/ultimoelaborado/area/{ccaa}"
        tar_bytes = _aemet_get_bytes(endpoint)
        return _cap_tar_to_dicts(tar_bytes)
    except Exception as e:
        print(f"Error obteniendo alertas para {codigo}: {e}")
        return []


def get_alertas_nacional() -> list[dict]:
    try:
        endpoint = "/api/avisos_cap/ultimoelaborado/area/esp"
        tar_bytes = _aemet_get_bytes(endpoint)
        return _cap_tar_to_dicts(tar_bytes)
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
    areas = alerta.get("areas", [])

    severity_emoji = {
        "Extreme": "🔴", "Severe": "🟠", "Moderate": "🟡", "Minor": "🟢"
    }.get(severity, "⚪")

    msg = f"{severity_emoji} *{event}*\n"
    msg += f"Severidad: {severity}\n"
    if headline:
        msg += f"{headline}\n"
    if description:
        msg += f"\n{description[:500]}\n"
    if areas:
        msg += f"\n📍 Zonas: {', '.join(areas[:3])}"
        if len(areas) > 3:
            msg += f" (+{len(areas) - 3} más)"
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
