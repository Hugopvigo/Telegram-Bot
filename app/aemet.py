import io
import tarfile
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
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


SEVERITY_ORDER = {"Minor": 0, "Moderate": 1, "Severe": 2, "Extreme": 3}
MIN_NOTIFY_SEVERITY = "Moderate"

SEVERITY_ES = {
    "Minor": "Verde",
    "Moderate": "Amarillo",
    "Severe": "Naranja",
    "Extreme": "Rojo",
}

CERTAINTY_ES = {
    "Observed": "Observado",
    "Likely": "Probable",
    "Possible": "Posible",
    "Unlikely": "Improbable",
    "Unknown": "Desconocido",
}


def _cap_xml_to_dicts(root: ET.Element) -> list[dict]:
    alerts = []
    for info in root.findall("cap:info", CAP_NS):
        lang = info.findtext("cap:language", "", CAP_NS)
        if lang and not lang.startswith("es"):
            continue
        areas = []
        for area in info.findall("cap:area", CAP_NS):
            desc = area.findtext("cap:areaDesc", "", CAP_NS)
            if desc:
                areas.append(desc)
        alerts.append({
            "identifier": root.findtext("cap:identifier", "", CAP_NS),
            "event": info.findtext("cap:event", "Alerta meteorológica", CAP_NS),
            "severity": info.findtext("cap:severity", "", CAP_NS),
            "certainty": info.findtext("cap:certainty", "", CAP_NS),
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
    seen: set[str] = set()
    alerts = []
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        for member in tar.getmembers():
            f = tar.extractfile(member)
            if f is None:
                continue
            try:
                xml_text = f.read().decode("utf-8")
                root = ET.fromstring(xml_text)
                for alert in _cap_xml_to_dicts(root):
                    key = alert.get("identifier") or f"{alert['event']}|{alert['effective']}|{alert['expires']}"
                    if key in seen:
                        continue
                    seen.add(key)
                    alerts.append(alert)
            except (ET.ParseError, UnicodeDecodeError, ValueError):
                continue
    return alerts


def get_alertas_provincia(codigo: str, min_severity: str | None = None) -> list[dict]:
    try:
        ccaa = PROVINCIA_TO_CCAA.get(codigo)
        if not ccaa:
            return []
        endpoint = f"/api/avisos_cap/ultimoelaborado/area/{ccaa}"
        tar_bytes = _aemet_get_bytes(endpoint)
        alerts = _cap_tar_to_dicts(tar_bytes)
        if min_severity:
            min_level = SEVERITY_ORDER.get(min_severity, 0)
            alerts = [a for a in alerts if SEVERITY_ORDER.get(a.get("severity", ""), 0) >= min_level]
        return alerts
    except Exception as e:
        print(f"Error obteniendo alertas para {codigo}: {e}")
        return []


def get_alertas_nacional(min_severity: str | None = None) -> list[dict]:
    try:
        endpoint = "/api/avisos_cap/ultimoelaborado/area/esp"
        tar_bytes = _aemet_get_bytes(endpoint)
        alerts = _cap_tar_to_dicts(tar_bytes)
        if min_severity:
            min_level = SEVERITY_ORDER.get(min_severity, 0)
            alerts = [a for a in alerts if SEVERITY_ORDER.get(a.get("severity", ""), 0) >= min_level]
        return alerts
    except Exception as e:
        print(f"Error obteniendo alertas nacionales: {e}")
        return []


def _parse_dt(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


def merge_alertas(alertas: list[dict]) -> list[dict]:
    """Agrupa avisos que comparten (event, severity, areas) en uno solo.

    AEMET emite un CAP por zona y por día de validez, así que un mismo
    fenómeno+nivel+zona llega partido en varios avisos que solo difieren en la
    fecha de fin. Los colapsamos en un único aviso con el rango completo
    (effective mínimo .. expires máximo) y una clave de deduplicación estable
    que no depende del identifier crudo de AEMET (que cambia por día/elaboración).
    """
    groups: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for a in alertas:
        key = (
            a.get("event", ""),
            a.get("severity", ""),
            tuple(sorted(a.get("areas") or [])),
        )
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(a)

    merged: list[dict] = []
    for key in order:
        items = groups[key]
        earliest = min(items, key=lambda x: _parse_dt(x.get("effective", "")) or datetime.max)
        latest = max(items, key=lambda x: _parse_dt(x.get("expires", "")) or datetime.min)
        base = dict(latest)
        base["effective"] = earliest.get("effective", "")
        base["expires"] = latest.get("expires", "")
        event, severity, areas = key
        base["dedup_key"] = f"{event}|{severity}|{','.join(areas)}|{base['expires']}"
        merged.append(base)
    return merged


def _fmt_dt(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return iso


def format_alerta(alerta: dict) -> str:
    event = alerta.get("event", "Alerta meteorológica")
    severity = alerta.get("severity", "")
    headline = alerta.get("headline", "")
    description = alerta.get("description", "")
    effective = _fmt_dt(alerta.get("effective", ""))
    expires = _fmt_dt(alerta.get("expires", ""))
    areas = alerta.get("areas", [])

    severity_emoji = {
        "Extreme": "🔴", "Severe": "🟠", "Moderate": "🟡", "Minor": "🟢"
    }.get(severity, "⚪")
    severity_label = SEVERITY_ES.get(severity, severity)
    certainty = alerta.get("certainty", "")
    certainty_label = CERTAINTY_ES.get(certainty, certainty)

    msg = f"{severity_emoji} *{event}*\n"
    msg += f"Nivel: {severity_label}"
    if certainty_label:
        msg += f" · {certainty_label}"
    msg += "\n"
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


SEVERITY_COLORS = {
    "Extreme": "#FF0000",
    "Severe": "#FF8C00",
    "Moderate": "#FFD700",
    "Minor": "#00AA00",
}


def format_alerta_rich(alerta: dict) -> str:
    event = alerta.get("event", "Alerta meteorológica")
    severity = alerta.get("severity", "")
    headline = alerta.get("headline", "")
    description = alerta.get("description", "")
    effective = _fmt_dt(alerta.get("effective", ""))
    expires = _fmt_dt(alerta.get("expires", ""))
    areas = alerta.get("areas", [])
    certainty = alerta.get("certainty", "")

    severity_emoji = {
        "Extreme": "🔴", "Severe": "🟠",
        "Moderate": "🟡", "Minor": "🟢",
    }.get(severity, "⚪")
    severity_label = SEVERITY_ES.get(severity, severity)
    certainty_label = CERTAINTY_ES.get(certainty, certainty)

    html = f"<h3>{severity_emoji} {event}</h3>\n"
    html += "<p>"
    html += f"<b>Nivel:</b> {severity_label}"
    if certainty_label:
        html += f" · {certainty_label}"
    html += "</p>\n"

    if headline:
        html += f"<p><i>{headline}</i></p>\n"

    if description:
        html += "<details>\n<summary>Descripción completa</summary>\n"
        html += f"<p>{description[:500]}</p>\n</details>\n"

    if areas:
        zonas = ", ".join(areas[:3])
        if len(areas) > 3:
            zonas += f" (+{len(areas) - 3} más)"
        html += f"<p>📍 <b>Zonas:</b> {zonas}</p>\n"

    footer_parts = []
    if effective:
        footer_parts.append(f"🕐 Desde: {effective}")
    if expires:
        footer_parts.append(f"🕐 Hasta: {expires}")
    if footer_parts:
        html += f"<footer>{' · '.join(footer_parts)}</footer>\n"

    return html


def format_alerta_rich_full(provincia_name: str, alertas_list: list[dict]) -> str:
    html = f"<h2>⚠ Alertas para {provincia_name}</h2>\n"
    for i, a in enumerate(alertas_list):
        html += format_alerta_rich(a)
        if i < len(alertas_list) - 1:
            html += "<hr/>\n"
    html += "<footer>📡 Fuente: AEMET</footer>\n"
    return html


def format_provincias_rich() -> str:
    nombres = sorted(PROVINCIAS.keys())
    html = "<h2>🗺 Provincias disponibles</h2>\n"
    html += '<table striped>\n<tr><th>Provincia</th><th>Código</th></tr>\n'
    for n in nombres:
        html += f"<tr><td>{n}</td><td>{PROVINCIAS[n]}</td></tr>\n"
    html += "</table>\n"
    return html


def format_start_rich() -> str:
    return """<h2>🌤 AlertasMeteo Bot</h2>
<p>Te notifico cuando <b>AEMET</b> emita alertas meteorológicas en tu provincia.</p>
<table bordered>
<tr><th>Comando</th><th>Qué hace</th></tr>
<tr><td><code>/suscribir</code></td><td>Suscribirte a alertas</td></tr>
<tr><td><code>/provincias</code></td><td>Ver las 52 provincias</td></tr>
<tr><td><code>/alertas</code></td><td>Alertas actuales de tu provincia</td></tr>
<tr><td><code>/alertas_nacionales</code></td><td>Alertas de toda España</td></tr>
<tr><td><code>/clima</code></td><td>Pronóstico del tiempo</td></tr>
<tr><td><code>/estado</code></td><td>Tu suscripción actual</td></tr>
<tr><td><code>/cancelar</code></td><td>Darse de baja</td></tr>
</table>"""


def format_estado_rich(provincia_name: str) -> str:
    return f"""<h2>📍 Tu suscripción</h2>
<table bordered>
<tr><td><b>Provincia</b></td><td>{provincia_name}</td></tr>
<tr><td><b>Estado</b></td><td>✅ Activa</td></tr>
</table>
<p>Usa <code>/alertas</code> para ver alertas actuales.</p>"""


def format_nacional_rich(alertas_list: list[dict]) -> str:
    if not alertas_list:
        return "<h2>✅ Sin alertas</h2>\n<p>No hay alertas activas en España.</p>"

    html = "<h2>🗺 Alertas nacionales</h2>\n"
    html += '<table bordered striped>\n<tr><th>Nivel</th><th>Evento</th><th>Zonas</th></tr>\n'

    by_severity: dict[str, list[dict]] = {"Extreme": [], "Severe": [], "Moderate": [], "Minor": []}
    for a in alertas_list:
        sev = a.get("severity", "Minor")
        by_severity.setdefault(sev, []).append(a)

    for sev in ["Extreme", "Severe", "Moderate", "Minor"]:
        for a in by_severity[sev]:
            emoji = {"Extreme": "🔴", "Severe": "🟠", "Moderate": "🟡", "Minor": "🟢"}.get(sev, "⚪")
            event = a.get("event", "Alerta")
            areas = a.get("areas", [])
            zonas = ", ".join(areas[:2])
            if len(areas) > 2:
                zonas += f" (+{len(areas) - 2})"
            html += f"<tr><td>{emoji}</td><td>{event}</td><td>{zonas}</td></tr>\n"

    html += "</table>\n"
    html += f"<footer>📡 {len(alertas_list)} alertas activas · Fuente: AEMET</footer>\n"
    return html
