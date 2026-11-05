#!/usr/bin/env python3
"""
publicar_movil.py — programa cada Short en YouTube y TikTok (vía Buffer), marcado como contenido IA.
Solo librería estándar de Python (sin SDKs): funciona en Android (Termux) y iPhone (a-Shell / Pythonista).

FLUJO
  1. La tarea diaria de Claude deja short_X.mp4 + short_X.json en la carpeta `pendientes/` de tu repo PÚBLICO de vídeos.
  2. Este script, en tu móvil y a la hora que elijas (cron / Atajos), para cada vídeo nuevo:
     - YouTube: lo sube en privado con `publishAt` (se publica solo a la hora fijada) y
       `containsSyntheticMedia = true` (aviso de "contenido alterado o sintético").
     - TikTok: crea en Buffer una publicación programada (`dueAt`) con `isAiGenerated = true`
       (etiqueta "Creator labeled as AI-generated"). Buffer descarga el vídeo del repo a esa hora.
  3. Apunta lo hecho en estado.json para no repetir nunca.

SEGURIDAD
  - Tus claves viven SOLO en config.json, en el móvil. Este script nunca las envía a GitHub ni a Claude.
  - El repo público solo contiene vídeos, fichas .json y este script en scripts/ (que no lleva ningún secreto).
  - No subas config.json ni estado.json a ningún sitio. Este archivo no contiene ningún secreto.

COMANDOS
  python3 publicar_movil.py init            crea config.json de ejemplo
  python3 publicar_movil.py auth-youtube    autoriza tu canal (una vez) y guarda el refresh token
  python3 publicar_movil.py buffer-canales  muestra tus canales de Buffer para copiar el id de TikTok
  python3 publicar_movil.py run --dry-run   enseña lo que haría, sin subir nada
  python3 publicar_movil.py run             programa los vídeos pendientes
  python3 publicar_movil.py run --en 20     prueba: YouTube se publica dentro de 20 minutos
  python3 publicar_movil.py web             PANEL: abre index.html para ver los vídeos del repo, cuáles están
                                            programados y programarlos tú con fecha y hora (siempre como contenido IA)
  python3 publicar_movil.py actualizar      descarga la última versión del script del repo (también lo hace solo al arrancar)
  python3 publicar_movil.py estado          comprueba en YouTube y Buffer si cada vídeo se subió de verdad,
                                            si ya se publicó, si pusiste el comentario y si lo marcaste como fijado

PROGRAMACIÓN CALCULADA (v2.5)
  - El día y la hora por defecto NO vienen de la ficha: se calculan cada vez a partir de lo que ya está
    programado (estado.json + comprobación en YouTube/Buffer). Cada vídeo sin programar recibe el siguiente
    hueco libre en las `horas_buenas` de config.json (por defecto 13:00 y 19:30), con >= `separacion_horas`
    entre vídeos, y los vídeos se reparten por orden de creación (el más antiguo, primero).
  - La ficha puede traer "creado" (AAAA-MM-DDTHH:MM, para ordenar), "caduca" (no se propone después) y
    "no_antes" (AAAA-MM-DD, no se propone antes). "publicar_en" de fichas antiguas se ignora.
  - El panel ordena los vídeos por fecha de creación (el más antiguo arriba en «Por subir»/«En cola»).

v2.6
  - TikTok se programa a la MISMA hora que YouTube (el panel copia la hora de YouTube en TikTok y la sigue si la
    cambias; se puede tocar a mano). Para volver a un desfase: "tiktok_desfase_min": 30 en config.json.
  - La pestaña «En cola» ordena por fecha de publicación programada, de la más reciente (más lejana) a la más antigua.

v2.7
  - La pestaña «En cola» ordena por fecha de publicación programada de la más próxima a la más lejana (como «Por subir»:
    lo primero que sale, arriba). Cuenta solo las plataformas que aún no se han publicado.

AUTOACTUALIZACIÓN (v2.4)
  - Al lanzar web, run o estado mira scripts/publicar_movil.py en tu repo (github_repo). Si trae una VERSION mayor,
    comprueba que el código es válido, se sustituye a sí mismo y sigue con la versión nueva. config.json y
    estado.json no se tocan. Para desactivarlo: "auto_actualizar": false en config.json.

COMPROBACIÓN (v2)
  - YouTube: pregunta a la API si el vídeo existe, si terminó de procesarse, si falló o lo rechazaron,
    si sigue programado o ya es público, y si tu canal ya ha publicado el comentario.
    Necesita permiso de lectura/comentarios: si autorizaste con la versión anterior, ejecuta auth-youtube otra vez.
  - TikTok: pregunta a Buffer el estado del post (en cola, publicado o con error) y su enlace.
  - Fijar: ni YouTube ni TikTok dejan fijar un comentario por API ni dicen si está fijado. El panel te dice cuándo
    toca, publica el comentario de YouTube por ti si quieres, y tú pulsas «Ya lo fijé» al fijarlo en la app.
  - Si un vídeo no existe o falló, el panel deja volver a subirlo.

PANEL (web)
  - El panel va dentro de este script (no hace falta copiar nada más). Si pones un index.html al lado, usa ese.
  - Solo escucha en 127.0.0.1 y exige un token aleatorio por sesión: nada se expone fuera del móvil
    y ninguna web puede programar vídeos por ti.
  - Pythonista: se abre en su navegador interno. a-Shell: se abre con `internalbrowser`. Ordenador: navegador normal.
  - Para cerrarlo, detén el script.
"""
import json, os, sys, time, secrets, hashlib, base64, threading, webbrowser
import urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

AQUI = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(AQUI, "config.json")
ESTADO = os.path.join(AQUI, "estado.json")
UA = "shorts-publisher/1.0"
VERSION = "2.7"   # se ve en el panel: si no lo ves, el móvil sigue con un script o un index.html antiguos

EJEMPLO = {
    "github_repo": "TU_USUARIO/shorts-media",      # repo PÚBLICO con la carpeta pendientes/
    "github_rama": "main",
    "carpeta": "pendientes",
    "hora_youtube": "19:30",                       # hora de España (prueba; cámbiala cuando quieras)
    "hora_tiktok": "19:30",                        # v2.6: se usa la misma hora que YouTube (ver tiktok_desfase_min)
    "tiktok_desfase_min": 0,                       # minutos de TikTok después de YouTube (0 = misma hora)
    "margen_minutos": 20,                          # si hoy ya ha pasado la hora (o falta menos), se programa para mañana
    "separacion_horas": 6,                         # mínimo entre dos vídeos programados en YouTube
    "horas_buenas": ["13:00", "19:30"],            # horas de España en las que se proponen huecos (mediodía y prime time)
    "youtube_client_id": "",
    "youtube_client_secret": "",
    "youtube_refresh_token": "",                   # lo rellena auth-youtube
    "buffer_api_key": "",
    "buffer_tiktok_channel_id": "",                # sale de buffer-canales
    "categoria_youtube": "27",                     # 27 = Educación
    "auto_actualizar": True                        # al arrancar, se actualiza solo desde scripts/ del repo
}

# ---------------- utilidades ----------------
def leer(p, defecto):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError: return defecto

def guardar(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    try: os.chmod(p, 0o600)
    except OSError: pass

def http(url, data=None, headers=None, method=None, raw=False, timeout=120):
    h = {"User-Agent": UA}; h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return (r, body) if raw else (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"ERROR HTTP {e.code} en {url.split('?')[0]}\n{msg}")

def hora_espana(fecha, hhmm):
    """datetime UTC de una hora local de España (CET/CEST) sin depender de tzdata."""
    def ultimo_domingo(y, m):
        d = datetime(y, m + 1, 1) - timedelta(days=1) if m < 12 else datetime(y, 12, 31)
        return d - timedelta(days=(d.weekday() + 1) % 7)
    y = fecha.year
    ini = ultimo_domingo(y, 3).replace(hour=1, tzinfo=timezone.utc)     # 01:00 UTC
    fin = ultimo_domingo(y, 10).replace(hour=1, tzinfo=timezone.utc)
    h, m = map(int, hhmm.split(":"))
    for off in (2, 1):   # prueba verano y luego invierno
        u = datetime(y, fecha.month, fecha.day, h, m, tzinfo=timezone.utc) - timedelta(hours=off)
        if (ini <= u < fin) == (off == 2): return u
    return datetime(y, fecha.month, fecha.day, h, m, tzinfo=timezone.utc) - timedelta(hours=1)

def proxima(hhmm, margen):
    ahora = datetime.now(timezone.utc)
    hoy = ahora.date()
    for dias in range(0, 3):
        t = hora_espana(hoy + timedelta(days=dias), hhmm)
        if t - ahora >= timedelta(minutes=margen): return t
    raise SystemExit("No se pudo calcular la hora de publicación")

def iso(t): return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")

# ---------------- YouTube (API REST a pelo) ----------------
# upload: subir · force-ssl: leer el estado de tus vídeos y publicar el comentario (no se usa para nada más)
SCOPE = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"
YT_API = "https://www.googleapis.com/youtube/v3/"
_tok = {"v": None, "exp": 0.0}

class SinPermiso(Exception):
    """El refresh token no tiene permiso de lectura (autorizado con la versión anterior) o ha caducado."""

def _es_sin_permiso(msg):
    return any(s in msg for s in ("insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
                                  "insufficient authentication scopes", "insufficientScope"))

def auth_youtube(cfg):
    if not cfg["youtube_client_id"] or not cfg["youtube_client_secret"]:
        raise SystemExit("Rellena youtube_client_id y youtube_client_secret en config.json")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_urlsafe(16); res = {}
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state: res.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("Listo. Ya puedes volver a la terminal.".encode())
        def log_message(self, *a): pass
    srv = HTTPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
    redirect = f"http://127.0.0.1:{port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(dict(
        client_id=cfg["youtube_client_id"], redirect_uri=redirect, response_type="code", scope=SCOPE,
        access_type="offline", prompt="consent select_account", state=state, code_challenge=challenge, code_challenge_method="S256"))
    print("Abre este enlace en el navegador del móvil y autoriza tu canal:\n\n" + url + "\n")
    if os.path.exists("/data/data/com.termux"):          # Android: el servidor local recoge el código solo
        os.system(f"termux-open-url '{url}' >/dev/null 2>&1")
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        while "code" not in res and "error" not in res: time.sleep(0.3)
        srv.shutdown()
    else:                                                 # iPhone: al salir de la app el servidor se duerme -> pegar la URL
        srv.server_close()
        print("Cuando Safari muestre 'no se puede conectar' con una dirección 127.0.0.1,\n"
              "copia esa dirección COMPLETA de la barra y pégala aquí.\n")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(input("URL: ").strip()).query)
        if q.get("state", [""])[0] != state: raise SystemExit("La URL no corresponde a esta autorización. Repite auth-youtube.")
        res.update({k: v[0] for k, v in q.items()})
    if "error" in res: raise SystemExit("Autorización cancelada: " + res["error"])
    tok = http("https://oauth2.googleapis.com/token", urllib.parse.urlencode(dict(
        code=res["code"], client_id=cfg["youtube_client_id"], client_secret=cfg["youtube_client_secret"],
        redirect_uri=redirect, grant_type="authorization_code", code_verifier=verifier)).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"})
    if "refresh_token" not in tok: raise SystemExit("Google no devolvió refresh_token. Repite auth-youtube.")
    cfg["youtube_refresh_token"] = tok["refresh_token"]; cfg["youtube_scopes"] = tok.get("scope", "")
    guardar(CFG, cfg); _tok["v"] = None
    if "force-ssl" not in cfg["youtube_scopes"]:
        print("AVISO: no marcaste el permiso de gestionar tu cuenta de YouTube: podrás subir, pero no comprobar ni comentar.")
    print("OK: refresh token guardado en config.json (solo en este móvil).")
    try:
        _chk["canal"] = None
        print(f"Canal autorizado: «{canal_autorizado(cfg)[1]}». Si no es el tuyo, repite auth-youtube y elige la cuenta del canal.")
    except (SinPermiso, SystemExit) as e: print("No pude leer el nombre del canal:", str(e)[:200])

def token_youtube(cfg):
    if _tok["v"] and time.time() < _tok["exp"]: return _tok["v"]
    try:
        tok = http("https://oauth2.googleapis.com/token", urllib.parse.urlencode(dict(
            client_id=cfg["youtube_client_id"], client_secret=cfg["youtube_client_secret"],
            refresh_token=cfg["youtube_refresh_token"], grant_type="refresh_token")).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"})
    except SystemExit as e:
        if "invalid_grant" in str(e):
            raise SystemExit("La autorización de YouTube ha caducado o se ha revocado: ejecuta auth-youtube otra vez.")
        raise
    _tok["v"], _tok["exp"] = tok["access_token"], time.time() + int(tok.get("expires_in", 3600)) - 120
    return _tok["v"]

def yt_api(cfg, metodo, params, body=None):
    """Llamada a la YouTube Data API con tu token. Lanza SinPermiso si falta el permiso de lectura/comentarios."""
    url = YT_API + metodo + "?" + urllib.parse.urlencode(params)
    h = {"Authorization": f"Bearer {token_youtube(cfg)}"}
    if body is not None: h["Content-Type"] = "application/json; charset=UTF-8"
    try:
        return http(url, json.dumps(body).encode() if body is not None else None, h, "POST" if body is not None else "GET", timeout=60)
    except SystemExit as e:
        if _es_sin_permiso(str(e)): raise SinPermiso(str(e))
        raise

def canal_autorizado(cfg):
    """(id, nombre) del canal de YouTube al que pertenece la autorización guardada."""
    if not _chk.get("canal"):
        it = yt_api(cfg, "channels", {"part": "snippet", "mine": "true"}).get("items", [])
        _chk["canal"] = (it[0]["id"], it[0]["snippet"]["title"]) if it else ("", "")
    return _chk["canal"]

def comprobar_youtube(cfg, ids):
    """Estado REAL de cada vídeo en YouTube -> {id: {estado, detalle, canal, publica}}.
    estado: programado | procesando | publicado | privado | privado_atascado | oculto | no_existe | fallo | rechazado"""
    res, ahora = {}, datetime.now(timezone.utc)
    ids = list(dict.fromkeys(i for i in ids if i))
    for k in range(0, len(ids), 50):
        lote = ids[k:k + 50]
        r = yt_api(cfg, "videos", {"part": "status,snippet", "id": ",".join(lote), "maxResults": 50})
        for it in r.get("items", []):
            st = it.get("status", {})
            up, priv, pub = st.get("uploadStatus"), st.get("privacyStatus"), st.get("publishAt")
            d = {"canal": it.get("snippet", {}).get("channelId"), "publica": pub, "detalle": ""}
            if up == "failed":     d.update(estado="fallo", detalle=st.get("failureReason", ""))
            elif up == "rejected": d.update(estado="rechazado", detalle=st.get("rejectionReason", ""))
            elif up == "deleted":  d.update(estado="no_existe")
            elif priv == "public": d.update(estado="publicado")
            elif priv == "unlisted": d.update(estado="oculto")
            elif pub:
                cuando = datetime.strptime(pub[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                if cuando <= ahora: d.update(estado="privado_atascado")
                elif up == "processed": d.update(estado="programado")
                else: d.update(estado="procesando")
            else: d.update(estado="privado")
            res[it["id"]] = d
        faltan = [i for i in lote if i not in res]
        if faltan:   # un vídeo privado de OTRO canal tampoco aparece: dilo para no confundirlo con «borrado»
            cid, nom = canal_autorizado(cfg)
            for i in faltan:
                res[i] = {"estado": "no_existe", "canal": None, "publica": None,
                          "detalle": f"No aparece en el canal autorizado «{nom or '?'}». Si ese no es tu canal, repite auth-youtube eligiendo el correcto."}
    return res

def comentario_propio(cfg, vid, canal, texto):
    """Id del comentario que TU canal ha dejado en el vídeo (o None). No dice si está fijado: la API no lo expone."""
    if not canal: return None
    def buscar(extra):
        try:
            r = yt_api(cfg, "commentThreads", dict({"part": "snippet", "videoId": vid, "maxResults": 100,
                                                    "textFormat": "plainText"}, **extra))
        except SystemExit as e:
            if "commentsDisabled" in str(e) or "HTTP 403" in str(e) or "HTTP 404" in str(e): return None
            raise
        for it in r.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            if s.get("authorChannelId", {}).get("value") == canal: return it["id"]
        return None
    return buscar({"order": "time"}) or (buscar({"searchTerms": texto[:40]}) if texto else None)

def publicar_comentario(cfg, vid, texto):
    r = yt_api(cfg, "commentThreads", {"part": "snippet"},
               {"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": texto}}}})
    return r["id"]

def subir_youtube(cfg, video, meta, cuando):
    yt = meta.get("youtube", meta)
    body = {"snippet": {"title": yt["titulo"][:100], "description": yt.get("descripcion", "")[:5000],
                        "tags": yt.get("tags", []), "categoryId": cfg.get("categoria_youtube", "27"),
                        "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            "status": {"privacyStatus": "private", "publishAt": iso(cuando),
                       "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
    at = token_youtube(cfg)
    r, _ = http("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                json.dumps(body).encode(), {"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(video))}, "POST", raw=True)
    up = r.headers["Location"]
    res = http(up, video, {"Authorization": f"Bearer {at}", "Content-Type": "video/mp4"}, "PUT", timeout=600)
    st = res.get("status", {})
    if not st.get("containsSyntheticMedia"):
        print("  AVISO: YouTube no ha confirmado la marca de contenido sintético; revísala en YouTube Studio.")
    return res["id"]

# ---------------- TikTok vía Buffer (GraphQL a pelo) ----------------
def buffer(cfg, query):
    r = http("https://api.buffer.com", json.dumps({"query": query}).encode(),
             {"Authorization": f"Bearer {cfg['buffer_api_key']}", "Content-Type": "application/json"}, "POST")
    if r.get("errors"): raise SystemExit("ERROR Buffer: " + json.dumps(r["errors"], ensure_ascii=False)[:800])
    return r["data"]

def buffer_canales(cfg):
    orgs = buffer(cfg, "query { account { organizations { id name } } }")["account"]["organizations"]
    for o in orgs:
        chs = buffer(cfg, 'query { channels(input: { organizationId: %s }) { id name service } }' % json.dumps(o["id"]))["channels"]
        for c in chs: print(f"{c['service']:<10} {c['name']:<30} id = {c['id']}")

def gq(s): return json.dumps(s, ensure_ascii=False)   # cadena GraphQL (emojis tal cual, sin pares \\u)

def canal_tiktok(cfg):
    """Busca solo el canal de TikTok en Buffer la primera vez y lo guarda en config.json."""
    if cfg.get("buffer_tiktok_channel_id"): return cfg["buffer_tiktok_channel_id"]
    for o in buffer(cfg, "query { account { organizations { id name } } }")["account"]["organizations"]:
        for c in buffer(cfg, 'query { channels(input: { organizationId: %s }) { id name service } }' % gq(o["id"]))["channels"]:
            if c["service"].lower() == "tiktok":
                cfg["buffer_tiktok_channel_id"], cfg["buffer_org_id"] = c["id"], o["id"]
                guardar(CFG, {k: v for k, v in cfg.items() if v != EJEMPLO.get(k) or k == "buffer_tiktok_channel_id"})
                print(f"  Canal de TikTok en Buffer: {c['name']} ({c['id']})"); return c["id"]
    raise SystemExit("No hay ningún canal de TikTok conectado en Buffer")

def org_buffer(cfg):
    """Organización de Buffer que tiene el canal de TikTok (se guarda en config.json la primera vez)."""
    if cfg.get("buffer_org_id"): return cfg["buffer_org_id"]
    canal = canal_tiktok(cfg)
    if cfg.get("buffer_org_id"): return cfg["buffer_org_id"]
    for o in buffer(cfg, "query { account { organizations { id name } } }")["account"]["organizations"]:
        chs = buffer(cfg, 'query { channels(input: { organizationId: %s }) { id } }' % gq(o["id"]))["channels"]
        if any(c["id"] == canal for c in chs):
            cfg["buffer_org_id"] = o["id"]
            guardar(CFG, {k: v for k, v in cfg.items() if v != EJEMPLO.get(k) or k == "buffer_org_id"})
            return o["id"]
    raise SystemExit("No encuentro en Buffer la organización del canal de TikTok")

def comprobar_buffer(cfg, posts):
    """Estado REAL de cada post de TikTok en Buffer -> {id: {estado, link}}.
    posts = {id: dueAt ISO}. estado: en_cola | publicando | publicado | error | borrador | no_encontrado"""
    if not posts: return {}
    desde = (datetime.strptime(min(posts.values())[:10], "%Y-%m-%d") - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00Z")
    base = """query { posts(first: 100, input: { organizationId: %s,
        filter: { channelIds: [%s], dueAt: { start: %s } }, sort: { field: dueAt, direction: desc } }) {
        edges { node { %s } } pageInfo { hasNextPage } } }"""
    org, canal = org_buffer(cfg), canal_tiktok(cfg)
    try: r = buffer(cfg, base % (gq(org), gq(canal), gq(desde), "id status dueAt sentAt externalLink"))
    except SystemExit:   # por si algún campo opcional no existe en tu cuenta: lo mínimo
        r = buffer(cfg, base % (gq(org), gq(canal), gq(desde), "id status dueAt"))
    nodos = {e["node"]["id"]: e["node"] for e in r["posts"]["edges"]}
    completo = not r["posts"]["pageInfo"].get("hasNextPage")
    mapa = {"sent": "publicado", "scheduled": "en_cola", "sending": "publicando", "error": "error",
            "draft": "borrador", "needs_approval": "borrador"}
    res = {}
    for pid in posts:
        n = nodos.get(pid)
        if n: res[pid] = {"estado": mapa.get(str(n.get("status", "")).lower(), str(n.get("status", ""))),
                          "link": n.get("externalLink") or ""}
        elif completo: res[pid] = {"estado": "no_encontrado", "link": ""}
    return res

def programar_tiktok(cfg, meta, url_video, cuando):
    tt = meta.get("tiktok", {})
    canal_tiktok(cfg)
    texto = (tt.get("caption", "") + " " + " ".join(tt.get("hashtags", []))).strip()
    q = """mutation { createPost(input: {
      text: %s, channelId: %s, schedulingType: automatic, mode: customScheduled, dueAt: %s,
      assets: [{ video: { url: %s } }],
      metadata: { tiktok: { isAiGenerated: true } }
    }) { ... on PostActionSuccess { post { id dueAt } } ... on MutationError { message } } }""" % (
        gq(texto), gq(cfg["buffer_tiktok_channel_id"]), gq(iso(cuando)), gq(url_video))
    r = buffer(cfg, q)["createPost"]
    if "post" not in r: raise SystemExit("ERROR Buffer: " + r.get("message", str(r)))
    return r["post"]["id"]

# ---------------- repo público de vídeos ----------------
def pendientes(cfg):
    api = f"https://api.github.com/repos/{cfg['github_repo']}/contents/{cfg['carpeta']}?ref={cfg['github_rama']}"
    try:
        items = http(api, headers={"Accept": "application/vnd.github+json"})
    except SystemExit as e:
        if "HTTP 404" in str(e):
            print(f"No hay vídeos pendientes todavía (la carpeta {cfg['carpeta']}/ aún no existe en el repo)."); return []
        raise
    nombres = {i["name"] for i in items if i["type"] == "file"}
    raw = f"https://raw.githubusercontent.com/{cfg['github_repo']}/{cfg['github_rama']}/{cfg['carpeta']}/"
    return [(n[:-4], raw + n, raw + n[:-4] + ".json") for n in sorted(nombres) if n.endswith(".mp4") and n[:-4] + ".json" in nombres]

def run(cfg, dry):
    faltan = [k for k in ("github_repo", "youtube_refresh_token") if not cfg.get(k) or "TU_USUARIO" in str(cfg.get(k))]
    if faltan and not dry: raise SystemExit("Faltan datos en config.json: " + ", ".join(faltan))
    con_tiktok = bool(cfg.get("buffer_api_key"))
    if not con_tiktok: print("TikTok: Buffer aún sin configurar -> solo YouTube (TikTok se programará cuando lo configures).")
    en_min = None
    if "--en" in sys.argv:     # prueba: publicar en YouTube dentro de N minutos (mínimo 20)
        en_min = max(20, int(sys.argv[sys.argv.index("--en") + 1]))
    est = leer(ESTADO, {})
    lista = pendientes(cfg)
    if not lista: print("Nada que programar hoy.")
    # mismo reparto que el panel: huecos con >= separacion_horas entre vídeos
    plan = {v["nombre"]: (v["ficha_fecha"], v["ficha_hora_yt"], v["ficha_hora_tt"])
            for v in listar(cfg)["videos"] if v.get("ficha_auto")} if lista else {}
    for nombre, url_mp4, url_json in lista:
        e = est.get(nombre, {})
        if e.get("youtube") and (e.get("tiktok") or not con_tiktok): continue
        meta = http(url_json)
        f_fecha, f_hyt, f_htt = plan.get(nombre) or (None, cfg["hora_youtube"], cfg["hora_tiktok"])
        hoy_es = _iso_local(datetime.now(timezone.utc).replace(second=0, microsecond=0))[:10]
        if meta.get("caduca") and str(meta["caduca"]) < hoy_es:
            print(f"{nombre}: caducado el {meta['caduca']} -> no se programa"); continue
        if f_fecha and f_fecha >= hoy_es:      # hueco calculado (siguiente libre según lo programado)
            d = datetime.strptime(f_fecha, "%Y-%m-%d").date()
            t_yt, t_tt = hora_espana(d, f_hyt), hora_espana(d, f_htt)
            minimo = datetime.now(timezone.utc) + timedelta(minutes=cfg["margen_minutos"])
            if t_yt < minimo: t_yt = proxima(f_hyt, cfg["margen_minutos"])
            if t_tt < minimo: t_tt = proxima(f_htt, cfg["margen_minutos"])
        else:
            t_yt = proxima(f_hyt, cfg["margen_minutos"])
            t_tt = proxima(f_htt, cfg["margen_minutos"])
        if en_min: t_yt = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=en_min)
        t_tt = t_yt + _offset_tiktok(cfg)              # v2.6: TikTok a la misma hora que YouTube (+ desfase opcional)
        print(f"{nombre}: YouTube {iso(t_yt)} UTC · TikTok {iso(t_tt)} UTC · marcado como IA")
        cy, ct = comentarios(meta)
        e["titulo"] = meta.get("youtube", meta).get("titulo", ""); e["comentario_yt"], e["comentario_tt"] = cy, ct
        if cy: print(f"  📌 Comentario a fijar en YouTube: {cy}")
        if ct and ct != cy: print(f"  📌 Comentario a fijar en TikTok: {ct}")
        if dry: continue
        if not e.get("youtube"):
            _, video = http(url_mp4, raw=True, timeout=300)
            e["youtube"] = subir_youtube(cfg, video, meta, t_yt); e["youtube_hora"] = iso(t_yt)
            est[nombre] = e; guardar(ESTADO, est)
            print(f"  YouTube OK -> https://youtube.com/shorts/{e['youtube']}")
        if con_tiktok and not e.get("tiktok"):
            e["tiktok"] = programar_tiktok(cfg, meta, url_mp4, t_tt); e["tiktok_hora"] = iso(t_tt)
            est[nombre] = e; guardar(ESTADO, est)
            print(f"  TikTok (Buffer) OK -> post {e['tiktok']}")
    if not dry and lista: print("\nPara comprobar que de verdad están subidos (y qué comentario falta fijar): python3 publicar_movil.py estado")
    try: os.system('termux-notification --title "Shorts" --content "Publicaciones programadas" >/dev/null 2>&1')
    except Exception: pass

# ---------------- panel web (index.html) ----------------
PANEL_HTML = '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<title>Panel de Shorts</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&display=swap">\n<style>\n:root{\n  --bg:#f3f1fa; --surface:#ffffff; --ink:#1c1830; --soft:#5e587a; --rule:#dcd7ec;\n  --teal:#00927a; --gold:#a8730a; --red:#c2304f; --violet:#2a1748;\n  --chip:#ebe8f6;\n  --display:"Bricolage Grotesque",ui-rounded,system-ui,sans-serif;\n  --text:"Atkinson Hyperlegible",system-ui,-apple-system,sans-serif;\n  color-scheme:light;\n}\n@media (prefers-color-scheme:dark){:root{\n  --bg:#0f0d22; --surface:#1a1633; --ink:#f2effc; --soft:#a9a3c8; --rule:#2d2850;\n  --teal:#00d6aa; --gold:#ffc400; --red:#ff6b86; --violet:#20123a; --chip:#241f42;\n  color-scheme:dark}\n  .tabs button[aria-pressed=true]{background:#33295e}}\n*{box-sizing:border-box}\nhtml{-webkit-text-size-adjust:100%}\nbody{margin:0;background:var(--bg);color:var(--ink);font:17px/1.45 var(--text)}\n.wrap{max-width:720px;margin:0 auto;padding:calc(env(safe-area-inset-top) + 20px) max(16px,env(safe-area-inset-right)) calc(env(safe-area-inset-bottom) + 40px) max(16px,env(safe-area-inset-left))}\n\nheader{display:flex;align-items:flex-end;justify-content:space-between;gap:12px}\nh1{font:800 30px/1.05 var(--display);letter-spacing:-.02em;margin:0}\n.reload{font:700 15px var(--text);color:var(--ink);background:var(--chip);border:0;border-radius:999px;padding:10px 16px;cursor:pointer;min-height:44px}\n.links{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 18px}\n.link{display:inline-flex;align-items:center;gap:6px;font-size:14px;color:var(--soft);background:var(--chip);border-radius:999px;padding:5px 12px}\n.link b{color:var(--ink);font-weight:700}\n.dot{width:8px;height:8px;border-radius:50%;background:var(--soft)}\n.dot.on{background:var(--teal)} .dot.off{background:var(--red)}\n\n.tabs{display:grid;grid-template-columns:repeat(4,1fr);background:var(--chip);border-radius:14px;padding:4px;gap:4px;position:sticky;top:env(safe-area-inset-top);z-index:2}\n.tabs button{font:700 14px/1.15 var(--text);color:var(--soft);background:none;border:0;border-radius:10px;padding:8px 2px;cursor:pointer;min-height:44px}\n.tabs button[aria-pressed=true]{background:var(--surface);color:var(--ink);box-shadow:0 1px 0 var(--rule)}\n.tabs .n{font-family:var(--display);font-weight:800;margin-left:3px}\n.tabs .n.hot{color:var(--red)}\n\n.list{list-style:none;margin:16px 0 0;padding:0}\n.item{display:grid;grid-template-columns:96px 1fr;gap:14px;padding:16px 0;border-bottom:1px solid var(--rule)}\n.thumb{position:relative;width:96px;aspect-ratio:9/16;border-radius:12px;overflow:hidden;background:linear-gradient(180deg,#0c0e1e,#200c2e);align-self:start}\n.thumb video{width:100%;height:100%;object-fit:cover;display:block}\n.thumb .gone{position:absolute;inset:0;display:grid;place-items:center;text-align:center;font-size:12px;color:#b9b3d6;padding:8px}\n.info{min-width:0}\n.title{font:600 19px/1.2 var(--display);margin:0 0 2px;overflow-wrap:anywhere}\n.file{font-size:13px;color:var(--soft);margin:0 0 10px;overflow-wrap:anywhere}\n.rails{display:grid;gap:6px;margin:0 0 12px}\n.rail{display:grid;grid-template-columns:76px 1fr;align-items:baseline;gap:8px;font-size:15px}\n.rail .p{font-weight:700}\n.st{color:var(--soft)}\n.st.ok{color:var(--teal);font-weight:700}\n.st.live{color:var(--gold);font-weight:700}\n.st.err{color:var(--red)}\n.st.err small{display:block;font-size:13px;opacity:.9;overflow-wrap:anywhere}\n.go{font:700 16px var(--text);color:#fff;background:var(--violet);border:0;border-radius:12px;padding:11px 18px;min-height:44px;cursor:pointer}\n@media (prefers-color-scheme:dark){.go{background:var(--teal);color:#06231d}}\n.go:disabled{opacity:.45;cursor:default}\n.pin{background:var(--chip);border-radius:12px;padding:10px 12px;margin:0 0 12px}\n.pin+.pin{margin-top:-4px}\n.pin .h{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--soft);text-transform:uppercase;letter-spacing:.04em}\n.pin p{margin:6px 0 0;font-size:16px;overflow-wrap:anywhere}\n.prow{display:grid;grid-template-columns:76px 1fr;gap:8px;align-items:start;margin-top:10px;padding-top:10px;border-top:1px solid var(--rule);font-size:14px}\n.prow .p{font-weight:700;font-size:15px}\n.prow .s{color:var(--soft)}\n.prow .s.ok{color:var(--teal);font-weight:700}\n.prow .s.todo{color:var(--gold);font-weight:700}\n.prow .s small{display:block;font-weight:400;color:var(--soft);margin-top:2px}\n.btns{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px;margin-top:2px}\n.mini{font:700 14px var(--text);color:#fff;background:var(--violet);border:0;border-radius:999px;padding:7px 14px;min-height:36px;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center}\n@media (prefers-color-scheme:dark){.mini{background:var(--teal);color:#06231d}}\n.mini.sec{background:var(--surface);color:var(--ink);border:1px solid var(--rule)}\n.mini:disabled{opacity:.45;cursor:default}\n.ver{color:inherit;font-weight:700;margin-left:6px;white-space:nowrap}\n.when{display:block;font-size:12px;color:var(--soft);font-weight:400}\n.banner{background:var(--chip);border-left:4px solid var(--red);border-radius:10px;padding:10px 12px;margin:0 0 14px;font-size:14px}\n.copy{font:700 14px var(--text);color:var(--ink);background:var(--surface);border:1px solid var(--rule);border-radius:999px;padding:6px 14px;min-height:36px;cursor:pointer}\n\n.empty,.alert{padding:28px 4px;color:var(--soft)}\n.alert{color:var(--red)}\n.empty b{display:block;color:var(--ink);font:600 20px var(--display);margin-bottom:4px}\n\ndialog{border:0;padding:0;margin:auto auto 0;width:100%;max-width:560px;background:var(--surface);color:var(--ink);border-radius:22px 22px 0 0}\ndialog::backdrop{background:rgba(15,10,35,.55)}\n@media (min-width:600px){dialog{margin:auto;border-radius:22px}}\n.sheet{padding:22px 20px calc(env(safe-area-inset-bottom) + 20px)}\n.sheet h2{font:800 24px/1.1 var(--display);margin:0 0 4px}\n.sheet .sub{color:var(--soft);font-size:14px;margin:0 0 18px;overflow-wrap:anywhere}\n.field{display:grid;gap:6px;margin-bottom:14px}\n.field>span{font-weight:700;font-size:15px}\ninput[type=date],input[type=time]{font:17px var(--text);color:var(--ink);background:var(--bg);border:1px solid var(--rule);border-radius:12px;padding:10px 12px;min-height:46px;width:100%}\n.plat{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px;padding:12px 0;border-top:1px solid var(--rule)}\n.plat input[type=checkbox]{width:24px;height:24px;accent-color:var(--teal);margin:0}\n.plat label{font-weight:700}\n.plat .why{grid-column:2/4;font-size:13px;color:var(--soft);margin-top:-8px}\n.plat input[type=time]{width:150px}\n.ia{display:flex;gap:10px;align-items:flex-start;background:var(--chip);border-radius:12px;padding:12px 14px;margin:8px 0 18px;font-size:15px}\n.ia svg{flex:none;margin-top:2px}\n.actions{display:flex;gap:10px}\n.actions .go{flex:1}\n.cancel{font:700 16px var(--text);background:none;color:var(--soft);border:1px solid var(--rule);border-radius:12px;padding:11px 18px;min-height:44px;cursor:pointer}\n.msg{margin:12px 0 0;font-size:15px;min-height:1.4em}\n.msg.err{color:var(--red)} .msg.ok{color:var(--teal);font-weight:700}\n\n.toast{position:fixed;left:50%;bottom:calc(env(safe-area-inset-bottom) + 18px);transform:translate(-50%,140%);background:var(--ink);color:var(--bg);padding:12px 18px;border-radius:14px;font-weight:700;transition:transform .25s ease;max-width:calc(100% - 32px);z-index:5}\n.toast.show{transform:translate(-50%,0)}\n:focus-visible{outline:3px solid var(--teal);outline-offset:2px}\n@media (prefers-reduced-motion:reduce){.toast{transition:none}}\n</style>\n</head>\n<body>\n<div class="wrap">\n  <header>\n    <h1>Vídeos del canal</h1>\n    <button class="reload" id="reload" type="button">Recargar</button>\n  </header>\n  <div class="links" id="links"></div>\n  <div id="avisos"></div>\n\n  <div class="tabs" role="group" aria-label="Filtrar vídeos">\n    <button type="button" data-f="pend" aria-pressed="true">Por subir<span class="n" id="n-pend"></span></button>\n    <button type="button" data-f="prog" aria-pressed="false">En cola<span class="n" id="n-prog"></span></button>\n    <button type="button" data-f="fijar" aria-pressed="false">Por fijar<span class="n" id="n-fijar"></span></button>\n    <button type="button" data-f="all" aria-pressed="false">Todos<span class="n" id="n-all"></span></button>\n  </div>\n\n  <ul class="list" id="list" aria-live="polite"></ul>\n</div>\n\n<dialog id="dlg" aria-labelledby="dlg-t">\n  <form class="sheet" id="form" method="dialog">\n    <h2 id="dlg-t">Programar vídeo</h2>\n    <p class="sub" id="dlg-sub"></p>\n    <label class="field"><span>Día</span><input type="date" id="f-date" required></label>\n    <div class="plat">\n      <input type="checkbox" id="f-yt">\n      <label for="f-yt">YouTube Shorts</label>\n      <input type="time" id="f-yth" aria-label="Hora de YouTube">\n      <span class="why" id="why-yt"></span>\n    </div>\n    <div class="plat">\n      <input type="checkbox" id="f-tt">\n      <label for="f-tt">TikTok</label>\n      <input type="time" id="f-tth" aria-label="Hora de TikTok">\n      <span class="why" id="why-tt"></span>\n    </div>\n    <div class="ia">\n      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5Zm-3 8V7a3 3 0 0 1 6 0v3H9Z"/></svg>\n      <span>Se marca siempre como <b>contenido generado por IA</b>: «contenido alterado o sintético» en YouTube y etiqueta IA en TikTok.</span>\n    </div>\n    <div class="actions">\n      <button class="cancel" type="button" id="f-cancel">Cancelar</button>\n      <button class="go" type="submit" id="f-go">Programar</button>\n    </div>\n    <p class="msg" id="f-msg" role="status"></p>\n  </form>\n</dialog>\n\n<div class="toast" id="toast" role="status"></div>\n\n<script>\nconst TOKEN = "__TOKEN__";\nconst $ = s => document.querySelector(s);\nlet data = null, filtro = "pend", actual = null, ocupado = false;\n\nconst MES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];\nfunction bonita(s){ // "2026-11-05T19:30" -> "5 nov, 19:30"\n  const [d,h] = s.split("T"); const [y,m,dd] = d.split("-");\n  return `${+dd} ${MES[+m-1]}, ${h}`;\n}\nconst pasada = s => s && data && s <= data.ahora;\nfunction dia(s){ const [y,m,d] = s.split("-"); return `${+d} ${MES[+m-1]}` }\nconst caducado = v => !!v.caduca && data && v.caduca < data.ahora.slice(0,10);\nfunction propuesta(v){\n  if(caducado(v)) return `<p class="file" style="color:var(--red);font-weight:700">⚠️ Caducado el ${dia(v.caduca)}: no lo programes</p>`;\n  if(!v.ficha_fecha && !v.caduca) return "";\n  const p = v.ficha_fecha ? `📅 Siguiente hueco libre: ${bonita(v.ficha_fecha + "T" + v.ficha_hora_yt)}` : "";\n  const c = v.caduca ? `caduca el ${dia(v.caduca)}` : "";\n  return `<p class="file">${[p, c].filter(Boolean).join(" · ")}</p>`;\n}\n\nasync function api(path, opts={}){\n  const r = await fetch(path, {...opts, headers:{"X-Token":TOKEN, "Content-Type":"application/json"}});\n  let j = {}; try{ j = await r.json() }catch{}\n  if(!r.ok) throw new Error(j.error || `Error ${r.status}`);\n  return j;\n}\n\n// Por subir: le falta una plataforma, o la comprobación dice que no está / falló y hay que repetirla\nfunction pendiente(v){\n  if(!v.en_repo) return false;\n  return !v.youtube || v.youtube_rehacer || (data.tiktok_ok && (!v.tiktok || v.tiktok_rehacer));\n}\n// En cola: subido y esperando su hora (o con un aviso que revisar)\nfunction programado(v){\n  return (!!v.youtube && !v.youtube_rehacer && !v.yt_publicado) || (!!v.tiktok && !v.tiktok_rehacer && !v.tt_publicado);\n}\n// Por fijar: ya publicado en alguna plataforma y sin marcar como fijado\nconst faltaYT = v => !!v.youtube && v.yt_publicado && !v.fijado_yt;\nconst faltaTT = v => !!v.tiktok && v.tt_publicado && !v.fijado_tt;\nconst porFijar = v => faltaYT(v) || faltaTT(v);\n\nconst YT_TXT = {\n  programado:  ["ok",   "✓ Subido · se publica el "],\n  procesando:  ["live", "Subido, procesándose · "],\n  publicado:   ["ok",   "✓ Publicado · "],\n  oculto:      ["live", "Subido como oculto · "],\n  privado:     ["err",  "Subido pero privado, sin fecha", "Ponle fecha en YouTube Studio."],\n  privado_atascado: ["err", "Ya pasó la hora y sigue privado", "Míralo en YouTube Studio."],\n  no_existe:   ["err",  "No está en YouTube", "Se borró o la subida no terminó: vuelve a subirlo."],\n  fallo:       ["err",  "La subida falló en YouTube", "Vuelve a subirlo."],\n  rechazado:   ["err",  "YouTube lo ha rechazado", ""],\n};\nconst TT_TXT = {\n  en_cola:     ["ok",   "✓ En cola de Buffer · "],\n  publicando:  ["live", "Publicándose · "],\n  publicado:   ["ok",   "✓ Publicado · "],\n  borrador:    ["err",  "Borrador en Buffer", "No se publicará solo: apruébalo en Buffer."],\n  error:       ["err",  "Buffer no pudo publicarlo", "Míralo en Buffer o vuelve a programarlo."],\n  no_encontrado: ["err","No está en Buffer", "Se borró: vuelve a programarlo."],\n};\nfunction rail(nombre, id, hora, err, conectado, est, detalle, link, comprobado){\n  let cls = "st", txt = "Sin programar";\n  if(id && est && (nombre === "YouTube" ? YT_TXT : TT_TXT)[est]){\n    const [c, t, ayuda] = (nombre === "YouTube" ? YT_TXT : TT_TXT)[est];\n    cls += " " + c;\n    txt = t.endsWith(" ") ? t + bonita(hora) : t;\n    if(link) txt += ` <a class="ver" href="${esc(link)}" target="_blank" rel="noopener">Ver ↗</a>`;\n    const extra = [ayuda, detalle].filter(Boolean).map(esc).join(" ");\n    if(extra) txt += `<small>${extra}</small>`;\n    if(comprobado) txt += `<span class="when">comprobado ${bonita(comprobado)}</span>`;\n  }\n  else if(id){ cls += pasada(hora) ? " live" : " ok"; txt = (pasada(hora) ? "Debería estar publicado · " : "Programado · ") + bonita(hora) + `<span class="when">sin comprobar</span>` }\n  else if(err){ cls += " err"; txt = `Falló<small>${esc(err).slice(0,220)}</small>` }\n  else if(!conectado){ txt = "Sin configurar" }\n  return `<div class="rail"><span class="p">${nombre}</span><span class="${cls}">${txt}</span></div>`;\n}\nfunction esc(s){ return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;"}[c])) }\n\nconst ytURL = v => `https://youtube.com/shorts/${v.youtube}`;\n// estado del comentario fijado en una plataforma\nfunction fila(v, plat){\n  const yt = plat === "youtube";\n  if(yt ? !v.youtube : !v.tiktok) return "";\n  const pub = yt ? v.yt_publicado : v.tt_publicado, fij = yt ? v.fijado_yt : v.fijado_tt;\n  const n = esc(v.nombre), nombre = yt ? "YouTube" : "TikTok";\n  let st, btns = "";\n  if(fij){\n    st = `<span class="s ok">✓ Fijado</span>`;\n    btns = `<button class="mini sec" type="button" data-fij="${plat}" data-v="0" data-n="${n}">Deshacer</button>`;\n  } else if(!pub){\n    st = `<span class="s">Se fija cuando se publique</span>`;\n  } else if(yt){\n    st = v.yt_comentario\n      ? `<span class="s todo">Comentario puesto · falta fijarlo<small>En la app: abre el Short → comentarios → ⋮ en tu comentario → Fijar.</small></span>`\n      : `<span class="s todo">Falta el comentario${data.avisos && data.avisos.youtube ? "" : " (aún no lo veo en el vídeo)"}<small>Publícalo desde aquí y luego fíjalo en la app.</small></span>`;\n    if(!v.yt_comentario && v.comentario_yt) btns += `<button class="mini" type="button" data-com="${n}">Publicar comentario</button>`;\n    btns += `<a class="mini sec" href="${ytURL(v)}" target="_blank" rel="noopener">Abrir</a>`;\n    btns += `<button class="mini${v.yt_comentario ? "" : " sec"}" type="button" data-fij="youtube" data-v="1" data-n="${n}">Ya lo fijé</button>`;\n  } else {\n    st = `<span class="s todo">Falta ponerlo y fijarlo<small>En la app: comenta, mantén pulsado tu comentario → Fijar.</small></span>`;\n    if(v.tt_link) btns += `<a class="mini sec" href="${esc(v.tt_link)}" target="_blank" rel="noopener">Abrir</a>`;\n    btns += `<button class="mini" type="button" data-fij="tiktok" data-v="1" data-n="${n}">Ya lo fijé</button>`;\n  }\n  return `<div class="prow"><span class="p">${nombre}</span><div>${st}</div>${btns ? `<div class="btns">${btns}</div>` : ""}</div>`;\n}\nfunction pin(etq, txt, filas){\n  if(!txt) return `<div class="pin"><div class="h"><span>📌 ${etq}</span></div><p class="s" style="color:var(--soft)">La ficha no trae comentario: escribe tú uno y fíjalo.</p>${filas}</div>`;\n  return `<div class="pin"><div class="h"><span>📌 ${etq}</span><button class="copy" type="button" data-c="${esc(txt)}">Copiar</button></div><p>${esc(txt)}</p>${filas}</div>`;\n}\nfunction pins(v){\n  const y = v.comentario_yt, t = v.comentario_tt || y;\n  if(!y && !t) return pin("Comentario para fijar", "", fila(v,"youtube") + fila(v,"tiktok"));\n  if(y === t) return pin("Comentario para fijar", y, fila(v,"youtube") + fila(v,"tiktok"));\n  return pin("Fijar en YouTube", y, fila(v,"youtube")) + pin("Fijar en TikTok", t, fila(v,"tiktok"));\n}\nasync function copiar(b){\n  const t = b.dataset.c;\n  try{ await navigator.clipboard.writeText(t) }\n  catch{ const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select(); document.execCommand("copy"); a.remove() }\n  toast("Comentario copiado");\n}\n\nfunction pintar(){\n  const vs = data.videos;\n  $("#n-pend").textContent = vs.filter(pendiente).length;\n  $("#n-prog").textContent = vs.filter(programado).length;\n  const nf = vs.filter(porFijar).length;\n  $("#n-fijar").textContent = nf; $("#n-fijar").classList.toggle("hot", nf > 0);\n  $("#n-all").textContent = vs.length;\n  const lista = vs.filter(v => filtro==="all" ? true : filtro==="pend" ? pendiente(v) : filtro==="fijar" ? porFijar(v) : programado(v));\n  if(filtro==="prog"){   // v2.7: En cola, como en «Por subir»: la publicación programada más próxima arriba\n    const cuando = v => [v.youtube && !v.youtube_rehacer && !v.yt_publicado ? v.youtube_hora : "", v.tiktok && !v.tiktok_rehacer && !v.tt_publicado ? v.tiktok_hora : ""].filter(Boolean).sort()[0] || "9999";\n    lista.sort((a, b) => cuando(a).localeCompare(cuando(b)) || a.nombre.localeCompare(b.nombre));\n  }\n  const ul = $("#list");\n  if(data.error_repo){ ul.innerHTML = `<li class="alert">No se pudo leer el repo ${esc(data.repo)}: ${esc(data.error_repo)}</li>`; return }\n  if(!lista.length){\n    ul.innerHTML = filtro==="pend"\n      ? `<li class="empty"><b>Nada por programar</b>Cuando la tarea diaria suba un vídeo a ${esc(data.carpeta)}/, aparecerá aquí.</li>`\n      : filtro==="fijar"\n      ? `<li class="empty"><b>Nada por fijar</b>Cuando un vídeo se publique, aquí te dirá qué comentario fijar y dónde.</li>`\n      : `<li class="empty"><b>Nada en cola</b>Programa uno desde «Por subir».</li>`;\n    return;\n  }\n  ul.innerHTML = lista.map(v => `\n    <li class="item">\n      <div class="thumb">${v.mp4\n        ? `<video src="${esc(v.mp4)}#t=0.1" preload="metadata" playsinline controls muted></video>`\n        : `<div class="gone">Ya no está en el repo</div>`}</div>\n      <div class="info">\n        <p class="title">${esc(v.titulo || v.nombre)}</p>\n        <p class="file">${esc(v.nombre)}.mp4${v.creado ? " · creado " + bonita(v.creado.length > 10 ? v.creado : v.creado + "T00:00").replace(", 00:00","") : ""}${v.error_ficha ? " · la ficha .json no se pudo leer" : ""}</p>\n        ${v.en_repo && !v.youtube ? propuesta(v) : ""}\n        <div class="rails">\n          ${rail("YouTube", v.youtube, v.youtube_hora, v.error_youtube, data.youtube_ok, v.yt_estado, v.yt_detalle, v.youtube && v.yt_estado !== "no_existe" ? ytURL(v) : "", v.yt_comprobado)}\n          ${rail("TikTok", v.tiktok, v.tiktok_hora, v.error_tiktok, data.tiktok_ok, v.tt_estado, "", v.tt_link, v.tt_comprobado)}\n        </div>\n        ${pins(v)}\n        ${v.en_repo && (!v.youtube || !v.tiktok || v.youtube_rehacer || v.tiktok_rehacer) && !v.error_ficha && !caducado(v)\n          ? `<button class="go" type="button" data-n="${esc(v.nombre)}">${v.youtube_rehacer || v.tiktok_rehacer ? "Volver a subir" : "Programar"}</button>` : ""}\n      </div>\n    </li>`).join("");\n}\n\nfunction enlaces(){\n  $("#links").innerHTML = `\n    <span class="link"><span class="dot ${data.youtube_ok?"on":"off"}"></span><b>YouTube</b>${data.youtube_ok ? (data.yt_canal ? "canal «" + esc(data.yt_canal) + "»" : "conectado") : "sin autorizar"}</span>\n    <span class="link"><span class="dot ${data.tiktok_ok?"on":"off"}"></span><b>TikTok</b>${data.tiktok_ok?"vía Buffer":"sin configurar"}</span>\n    <span class="link"><b>Repo</b>${esc(data.repo || "sin configurar")}/${esc(data.carpeta||"")}</span>\n    <span class="link"><b>v${esc(data.version || "?")}</b></span>\n    ${data.comprobado ? `<span class="link"><b>Comprobado</b>${bonita(data.comprobado).split(", ")[1]}</span>` : ""}`;\n  const av = data.avisos || {};\n  $("#avisos").innerHTML = Object.entries(av).map(([k,t]) => `<p class="banner"><b>${k === "youtube" ? "YouTube" : "TikTok"}:</b> ${esc(t)}</p>`).join("");\n}\n\nasync function cargar(recargar){\n  $("#reload").disabled = true; $("#reload").textContent = "Cargando…";\n  try{\n    const primera = !data;\n    data = await api("/api/estado" + (recargar ? "?recargar=1" : ""));\n    if(primera && !data.videos.some(pendiente) && data.videos.some(porFijar)) elegir("fijar");\n    enlaces(); pintar();\n  }catch(e){\n    $("#list").innerHTML = `<li class="alert">${esc(e.message)}. Si cerraste el script, vuelve a lanzarlo con «web».</li>`;\n  }finally{ $("#reload").disabled = false; $("#reload").textContent = "Recargar" }\n}\n\nfunction sumaMin(hhmm, n){ const [h,m] = hhmm.split(":").map(Number); const t = (h*60+m+n) % 1440; return String(Math.floor(t/60)).padStart(2,"0")+":"+String(t%60).padStart(2,"0") }\nfunction sumaDia(ymd, n){ const d = new Date(ymd+"T12:00"); d.setDate(d.getDate()+n); return d.toISOString().slice(0,10) }\nfunction abrir(nombre){\n  actual = data.videos.find(v => v.nombre === nombre);\n  const hoy = data.ahora.slice(0,10), ahoraH = data.ahora.slice(11);\n  // si hoy ya no da tiempo (15 min de margen) para la hora por defecto, propone mañana\n  // día y horas: el siguiente hueco libre que calcula el script con lo ya programado (v2.5); si no hay, config.json\n  const hy = actual.ficha_hora_yt || data.hora_youtube, ht = sumaMin(hy, data.desfase_tt || 0);   // v2.6: TikTok = hora de YouTube\n  const [hh,mm] = ahoraH.split(":").map(Number), [dh,dm] = hy.split(":").map(Number);\n  const porDefecto = (dh*60+dm) - (hh*60+mm) >= 20 ? hoy : sumaDia(hoy,1);\n  $("#f-date").value = actual.ficha_fecha && actual.ficha_fecha >= porDefecto ? actual.ficha_fecha : porDefecto;\n  $("#f-date").min = hoy;\n  if(actual.caduca) $("#f-date").max = actual.caduca; else $("#f-date").removeAttribute("max");\n  $("#f-yth").value = hy; $("#f-tth").value = ht;\n  const yt = $("#f-yt"), tt = $("#f-tt");\n  yt.disabled = (!!actual.youtube && !actual.youtube_rehacer) || !data.youtube_ok; yt.checked = !yt.disabled;\n  tt.disabled = (!!actual.tiktok && !actual.tiktok_rehacer) || !data.tiktok_ok;   tt.checked = !tt.disabled;\n  $("#why-yt").textContent = actual.youtube_rehacer ? "La subida anterior no está en YouTube: se sube de nuevo"\n    : actual.youtube ? "Ya programado: " + bonita(actual.youtube_hora) : !data.youtube_ok ? "Autoriza el canal con auth-youtube" : "";\n  $("#why-tt").textContent = actual.tiktok_rehacer ? "El post anterior no está en Buffer: se programa de nuevo"\n    : actual.tiktok ? "Ya programado: " + bonita(actual.tiktok_hora) : !data.tiktok_ok ? "Pon buffer_api_key en config.json" : "";\n  sync();\n  $("#dlg-sub").textContent = actual.titulo || actual.nombre;\n  $("#f-msg").textContent = ""; $("#f-msg").className = "msg";\n  if(!$("#dlg").open) $("#dlg").showModal();\n}\nfunction sync(){\n  $("#f-yth").disabled = $("#f-yt").disabled || !$("#f-yt").checked;\n  $("#f-tth").disabled = $("#f-tt").disabled || !$("#f-tt").checked;\n  $("#f-go").disabled = ocupado || (!$("#f-yt").checked && !$("#f-tt").checked);\n}\n["#f-yt","#f-tt"].forEach(s => $(s).addEventListener("change", sync));\n$("#f-yth").addEventListener("input", () => { if($("#f-yth").value) $("#f-tth").value = sumaMin($("#f-yth").value, data.desfase_tt || 0) });   // TikTok sigue a YouTube\n\n$("#form").addEventListener("submit", async ev => {\n  ev.preventDefault();\n  const d = $("#f-date").value, yt = $("#f-yt").checked && !$("#f-yt").disabled, tt = $("#f-tt").checked && !$("#f-tt").disabled;\n  const cuerpo = {nombre: actual.nombre, youtube: yt, tiktok: tt,\n                  youtube_hora: `${d}T${$("#f-yth").value}`, tiktok_hora: `${d}T${$("#f-tth").value}`};\n  if(actual.caduca && d > actual.caduca){ msg(`Este vídeo caduca el ${dia(actual.caduca)}: elige un día anterior.`, true); return }\n  if(yt){   // aviso si queda a menos de N horas de otro vídeo ya programado en YouTube\n    const sep = data.separacion_horas || 6, t = new Date(cuerpo.youtube_hora);\n    const cerca = data.videos.find(o => o.nombre !== actual.nombre && o.youtube && !o.youtube_rehacer && o.youtube_hora\n                                   && Math.abs(new Date(o.youtube_hora) - t) < sep * 36e5);\n    if(cerca && !confirm(`Queda a menos de ${sep} h de «${cerca.titulo || cerca.nombre}» (${bonita(cerca.youtube_hora)}). ¿Programar igualmente?`)) return;\n  }\n  for(const [on,h,p] of [[yt,cuerpo.youtube_hora,"YouTube"],[tt,cuerpo.tiktok_hora,"TikTok"]])\n    if(on && h <= data.ahora){ msg(`La hora de ${p} ya ha pasado.`, true); return }\n  ocupado = true; sync();\n  msg(yt ? "Subiendo a YouTube… puede tardar un par de minutos." : "Programando en TikTok…");\n  try{\n    const r = await api("/api/programar", {method:"POST", body: JSON.stringify(cuerpo)});\n    await cargar(false);\n    if(r.ok){ $("#dlg").close(); toast(r.youtube ? "Subido y comprobado en YouTube" : "Programado"); }\n    else{\n      const partes = [];\n      if(r.youtube) partes.push("YouTube programado.");\n      if(r.error_youtube) partes.push("YouTube falló: " + r.error_youtube);\n      if(r.tiktok) partes.push("TikTok programado.");\n      if(r.error_tiktok) partes.push("TikTok falló: " + r.error_tiktok);\n      abrir(actual.nombre); msg(partes.join(" "), true);\n    }\n  }catch(e){ msg(e.message, true); await cargar(false) }\n  finally{ ocupado = false; sync() }\n});\nfunction msg(t, err){ const m = $("#f-msg"); m.textContent = t; m.className = "msg" + (err ? " err" : "") }\nfunction toast(t){ const el = $("#toast"); el.textContent = t; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 2200) }\n\n$("#f-cancel").addEventListener("click", () => { if(!ocupado) $("#dlg").close() });\n$("#dlg").addEventListener("cancel", e => { if(ocupado) e.preventDefault() });\n$("#list").addEventListener("click", async e => {\n  const c = e.target.closest("button[data-c]"); if(c){ copiar(c); return }\n  const f = e.target.closest("button[data-fij]");\n  if(f){\n    f.disabled = true;\n    try{ await api("/api/fijado", {method:"POST", body: JSON.stringify({nombre: f.dataset.n, plataforma: f.dataset.fij, valor: f.dataset.v === "1"})});\n         toast(f.dataset.v === "1" ? "Marcado como fijado" : "Desmarcado"); await cargar(false) }\n    catch(err){ toast(err.message); f.disabled = false }\n    return;\n  }\n  const m = e.target.closest("button[data-com]");\n  if(m){\n    m.disabled = true; m.textContent = "Publicando…";\n    try{ const r = await api("/api/comentar", {method:"POST", body: JSON.stringify({nombre: m.dataset.com})});\n         toast(r.ya_estaba ? "Ya estaba puesto: ahora fíjalo en la app" : "Comentario publicado: ahora fíjalo en la app"); await cargar(false) }\n    catch(err){ toast(err.message); m.disabled = false; m.textContent = "Publicar comentario" }\n    return;\n  }\n  const b = e.target.closest("button[data-n]"); if(b) abrir(b.dataset.n) });\nfunction elegir(f){\n  filtro = f;\n  document.querySelectorAll(".tabs button").forEach(x => x.setAttribute("aria-pressed", x.dataset.f===f));\n}\ndocument.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => { elegir(b.dataset.f); if(data) pintar() }));\n$("#reload").addEventListener("click", () => cargar(true));\ncargar(false);\n</script>\n</body>\n</html>\n'   # lo rellena el empaquetado con index.html
_metas = {}                      # caché de fichas .json del repo
_lock = threading.Lock()         # una programación cada vez
_lock_estado = threading.Lock()  # lecturas/escrituras de estado.json entre hilos del panel

def guardar_video(nombre, cambios):
    """Mezcla `cambios` en la entrada del vídeo releyendo estado.json (None borra la clave). Devuelve la entrada."""
    with _lock_estado:
        est = leer(ESTADO, {}); e = est.setdefault(nombre, {})
        for k, v in cambios.items():
            if v is None: e.pop(k, None)
            else: e[k] = v
        guardar(ESTADO, est)
        return dict(e)

def _iso_local(t_utc):
    """'2026-11-05T19:30' en hora de España a partir de un datetime UTC."""
    for off in (1, 2):
        loc = (t_utc + timedelta(hours=off)).replace(tzinfo=None)
        if hora_espana(loc.date(), loc.strftime("%H:%M")) == t_utc.replace(second=0, microsecond=0):
            return loc.strftime("%Y-%m-%dT%H:%M")
    return (t_utc + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")

def _iso_a_local(s):
    try: return _iso_local(datetime.strptime(s[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc))
    except Exception: return s

def comentarios(m):
    """Comentario para fijar de YouTube y TikTok según la ficha (claves youtube/tiktok.comentario_fijado)."""
    yt = m.get("youtube", m); tt = m.get("tiktok", {})
    cy = yt.get("comentario_fijado") or m.get("comentario_fijado") or ""
    return cy, tt.get("comentario_fijado") or cy

def plan_ficha(m, cfg):
    """v2.5: la ficha ya NO fija el día (publicar_en se ignora). Solo da las horas por defecto; el día lo calcula
    proponer_dias() con lo que ya está programado. Devuelve (None, 'HH:MM' YouTube, 'HH:MM' TikTok)."""
    return None, cfg["hora_youtube"], cfg["hora_tiktok"]

def creado_ficha(m, e=None):
    """Fecha de creación para ordenar: "creado" de la ficha; si no trae, la primera hora programada o vacío."""
    c = str(m.get("creado") or "").strip()[:16]
    if len(c) >= 10 and c[4:5] == "-": return c
    e = e or {}
    return _iso_a_local(e["youtube_hora"])[:16] if e.get("youtube_hora") else ""

REHACER_YT = ("no_existe", "fallo", "rechazado")      # se puede volver a subir
REHACER_TT = ("no_encontrado", "error")
_chk = {"t": 0.0, "avisos": {}}

def comprobar(cfg, forzar=False, cada=180):
    """Pregunta a YouTube y Buffer por todos los vídeos programados y guarda el resultado en estado.json.
    Como mucho una vez cada `cada` segundos salvo forzar. Devuelve avisos {youtube, tiktok} si algo no se pudo comprobar."""
    if not forzar and time.time() - _chk["t"] < cada: return _chk["avisos"]
    est, avisos, ahora = leer(ESTADO, {}), {}, iso(datetime.now(timezone.utc))
    # --- YouTube ---
    vids = {e["youtube"]: n for n, e in est.items() if e.get("youtube")}
    if vids and cfg.get("youtube_refresh_token"):
        try:
            res = comprobar_youtube(cfg, list(vids))
            for vid, n in vids.items():
                e, d = est[n], res.get(vid)
                if not d: continue
                e["yt_check"] = dict(d, t=ahora)
                if d["estado"] == "publicado" and not e.get("yt_comentario") and e.get("comentario_yt"):
                    c = comentario_propio(cfg, vid, d.get("canal"), e.get("comentario_yt", ""))
                    if c: e["yt_comentario"] = c
        except SinPermiso:
            avisos["youtube"] = ("Para comprobar si se ha subido y si está el comentario, vuelve a ejecutar "
                                 "auth-youtube (ahora pide también permiso de lectura y comentarios).")
        except SystemExit as e:
            avisos["youtube"] = "No se pudo comprobar YouTube: " + str(e)[:300]
    # --- TikTok (Buffer) ---
    posts = {e["tiktok"]: (e.get("tiktok_hora") or ahora) for e in est.values() if e.get("tiktok")}
    if posts and cfg.get("buffer_api_key"):
        try:
            res = comprobar_buffer(cfg, posts)
            for n, e in est.items():
                if e.get("tiktok") in res: e["tt_check"] = dict(res[e["tiktok"]], t=ahora)
        except SystemExit as e:
            avisos["tiktok"] = "No se pudo comprobar Buffer: " + str(e)[:300]
    # guarda sin pisar lo que otro hilo haya escrito mientras tanto (solo los campos de la comprobación)
    with _lock_estado:
        actual = leer(ESTADO, {})
        for n, e in est.items():
            if n in actual:
                for k in ("yt_check", "yt_comentario", "tt_check"):
                    if k in e: actual[n][k] = e[k]
        guardar(ESTADO, actual)
    if cfg.get("youtube_refresh_token") and "youtube" not in avisos:
        try: canal_autorizado(cfg)
        except (SinPermiso, SystemExit): pass
    _chk.update(t=time.time(), avisos=avisos)
    return avisos

def estado_video(e, cfg):
    """Campos de comprobación para el panel (y para el comando estado)."""
    yc, tc = e.get("yt_check") or {}, e.get("tt_check") or {}
    ahora = iso(datetime.now(timezone.utc))
    # sin comprobación (permiso viejo o sin red): se supone publicado cuando pasa la hora
    yt_pub = yc.get("estado") == "publicado" if yc else bool(e.get("youtube") and e.get("youtube_hora", "~") <= ahora)
    tt_pub = tc.get("estado") == "publicado" if tc else bool(e.get("tiktok") and e.get("tiktok_hora", "~") <= ahora)
    return dict(
        yt_estado=yc.get("estado") if e.get("youtube") else None, yt_detalle=yc.get("detalle", ""),
        yt_comprobado=_iso_a_local(yc["t"]) if yc.get("t") else None,
        yt_publicado=yt_pub, yt_comentario=bool(e.get("yt_comentario")), fijado_yt=bool(e.get("fijado_yt")),
        youtube_rehacer=bool(e.get("youtube")) and yc.get("estado") in REHACER_YT,
        tt_estado=tc.get("estado") if e.get("tiktok") else None, tt_link=tc.get("link", ""),
        tt_comprobado=_iso_a_local(tc["t"]) if tc.get("t") else None,
        tt_publicado=tt_pub, fijado_tt=bool(e.get("fijado_tt")),
        tiktok_rehacer=bool(e.get("tiktok")) and tc.get("estado") in REHACER_TT)

def listar(cfg, forzar=False):
    avisos = comprobar(cfg, forzar)
    est = leer(ESTADO, {})
    try:
        lista = pendientes(cfg) if cfg.get("github_repo") and "TU_USUARIO" not in cfg["github_repo"] else []
        error_repo = None
    except SystemExit as e:
        lista, error_repo = [], str(e)
    videos, vistos = [], set()
    for nombre, url_mp4, url_json in lista:
        vistos.add(nombre)
        if nombre not in _metas:
            try: _metas[nombre] = http(url_json)
            except SystemExit as e: _metas[nombre] = {"_error": str(e)}
        m = _metas[nombre]; yt = m.get("youtube", m); tt = m.get("tiktok", {})
        e = est.get(nombre, {}); cy, ct = comentarios(m)
        f_fecha, f_hyt, f_htt = plan_ficha(m, cfg)
        videos.append(dict(nombre=nombre, mp4=url_mp4, en_repo=True,
            titulo=yt.get("titulo", ""), caption=tt.get("caption", ""), error_ficha=m.get("_error"),
            comentario_yt=cy, comentario_tt=ct,
            ficha_fecha=f_fecha, ficha_hora_yt=f_hyt, ficha_hora_tt=f_htt, caduca=m.get("caduca"),
            no_antes=m.get("no_antes"), creado=creado_ficha(m, e),
            youtube=e.get("youtube"), youtube_hora=_iso_a_local(e["youtube_hora"]) if e.get("youtube_hora") else None,
            tiktok=e.get("tiktok"), tiktok_hora=_iso_a_local(e["tiktok_hora"]) if e.get("tiktok_hora") else None,
            error_youtube=e.get("error_youtube"), error_tiktok=e.get("error_tiktok"), **estado_video(e, cfg)))
    for nombre, e in est.items():     # ya programados que no siguen en el repo
        if nombre in vistos: continue
        videos.append(dict(nombre=nombre, mp4=None, en_repo=False, titulo=e.get("titulo", ""), caption="",
            creado=creado_ficha({}, e),
            comentario_yt=e.get("comentario_yt", ""), comentario_tt=e.get("comentario_tt", ""),
            youtube=e.get("youtube"), youtube_hora=_iso_a_local(e["youtube_hora"]) if e.get("youtube_hora") else None,
            tiktok=e.get("tiktok"), tiktok_hora=_iso_a_local(e["tiktok_hora"]) if e.get("tiktok_hora") else None,
            error_youtube=e.get("error_youtube"), error_tiktok=e.get("error_tiktok"), **estado_video(e, cfg)))
    proponer_dias(videos, cfg)
    # orden por fecha de creación (el más antiguo primero); sin fecha, al final y por nombre
    videos.sort(key=lambda v: (v.get("creado") or "9999", v["nombre"]))
    return dict(version=VERSION, yt_canal=(_chk.get("canal") or ("", ""))[1], separacion_horas=float(cfg.get("separacion_horas", 6)), repo=cfg.get("github_repo"), carpeta=cfg.get("carpeta"), error_repo=error_repo,
                youtube_ok=bool(cfg.get("youtube_refresh_token")), tiktok_ok=bool(cfg.get("buffer_api_key")),
                hora_youtube=cfg["hora_youtube"], hora_tiktok=cfg["hora_tiktok"], desfase_tt=int(_offset_tiktok(cfg).total_seconds() // 60),
                ahora=_iso_local(datetime.now(timezone.utc).replace(second=0, microsecond=0)), videos=videos,
                avisos=avisos, comprobado=_iso_local(datetime.fromtimestamp(_chk["t"], timezone.utc)) if _chk["t"] else None)

def _offset_tiktok(cfg):
    """v2.6: TikTok a la misma hora que YouTube; "tiktok_desfase_min" en config.json para retrasarlo (0-180)."""
    try: m = int(cfg.get("tiktok_desfase_min", 0) or 0)
    except (TypeError, ValueError): m = 0
    return timedelta(minutes=max(0, min(180, m)))

def siguiente_hueco(cfg, ocupados, caduca=None, desde=None):
    """Primer momento a una «hora buena» que esté a >= separacion_horas de TODO lo ocupado.
    Rellena huecos entre lo ya programado; si no hay, cae en la primera hora buena >= último + separación."""
    sep = timedelta(hours=float(cfg.get("separacion_horas", 6)))
    minimo = datetime.now(timezone.utc) + timedelta(minutes=cfg["margen_minutos"])
    horas = sorted(cfg.get("horas_buenas") or [cfg["hora_youtube"]])
    dia = datetime.strptime(_iso_local(minimo)[:10], "%Y-%m-%d").date()
    try:
        if desde: dia = max(dia, datetime.strptime(str(desde)[:10], "%Y-%m-%d").date())
    except ValueError: pass
    for _ in range(120):
        if caduca and dia.isoformat() > str(caduca): return None
        for h in horas:
            t = hora_espana(dia, h)
            if t >= minimo and all(abs(t - o) >= sep for o in ocupados): return t
        dia += timedelta(days=1)
    return None

def proponer_dias(videos, cfg):
    """v2.5: a TODOS los vídeos sin programar les calcula día y hora: el siguiente hueco libre (horas_buenas, con
    >= separacion_horas) respecto a lo que YA está programado en YouTube y a lo ya propuesto, por orden de
    creación (el más antiguo primero; si dos caducan, antes el que caduca antes). Respeta caduca y no_antes."""
    off = _offset_tiktok(cfg)
    ocupados = [_a_utc(v["youtube_hora"]) for v in videos if v.get("youtube") and not v.get("youtube_rehacer") and v.get("youtube_hora")]
    sin_dia = [v for v in videos if v.get("en_repo") and (not v.get("youtube") or v.get("youtube_rehacer"))
               and not v.get("error_ficha")]
    sin_dia.sort(key=lambda v: (v.get("creado") or "9999", v["nombre"]))
    for v in sin_dia:
        t = siguiente_hueco(cfg, ocupados, v.get("caduca"), v.get("no_antes"))
        if not t: continue
        loc = _iso_local(t)
        v.update(ficha_fecha=loc[:10], ficha_hora_yt=loc[11:16], ficha_hora_tt=_iso_local(t + off)[11:16], ficha_auto=True)
        ocupados.append(t)

def _a_utc(fecha_hora):
    """'2026-11-05T19:30' (hora de España) -> datetime UTC."""
    d = datetime.strptime(fecha_hora, "%Y-%m-%dT%H:%M")
    return hora_espana(d.date(), d.strftime("%H:%M"))

def programar_uno(cfg, p):
    """Programa un vídeo del repo. Siempre como contenido generado por IA (no hay forma de desactivarlo).
    Si la comprobación dice que el vídeo no existe / falló (o el post de Buffer no está / dio error), deja volver a subirlo."""
    nombre = p.get("nombre", "")
    item = next((x for x in pendientes(cfg) if x[0] == nombre), None)
    if not item: raise SystemExit(f"{nombre} no está en {cfg['carpeta']}/ del repo")
    _, url_mp4, url_json = item
    meta = _metas.get(nombre) or http(url_json); _metas[nombre] = meta
    cy, ct = comentarios(meta)    # se guardan para seguir viéndolos cuando el vídeo salga del repo
    e = guardar_video(nombre, {"titulo": meta.get("youtube", meta).get("titulo", ""), "comentario_yt": cy, "comentario_tt": ct})
    ev = estado_video(e, cfg)
    if not p.get("youtube") and not p.get("tiktok"): raise SystemExit("Elige YouTube, TikTok o los dos")
    minimo = datetime.now(timezone.utc) + timedelta(minutes=15)
    plan = {}
    # 1) comprobar todo antes de subir nada
    if p.get("youtube"):
        if e.get("youtube") and not ev["youtube_rehacer"]: raise SystemExit("Ya está programado en YouTube")
        if not cfg.get("youtube_refresh_token"): raise SystemExit("YouTube sin autorizar: ejecuta auth-youtube")
        plan["youtube"] = _a_utc(p["youtube_hora"])
    if p.get("tiktok"):
        if e.get("tiktok") and not ev["tiktok_rehacer"]: raise SystemExit("Ya está programado en TikTok")
        if not cfg.get("buffer_api_key"): raise SystemExit("Buffer sin configurar: pon buffer_api_key en config.json")
        plan["tiktok"] = _a_utc(p["tiktok_hora"])
    for k, t in plan.items():
        if t < minimo: raise SystemExit(f"La hora de {'YouTube' if k == 'youtube' else 'TikTok'} tiene que ser al menos 15 minutos en el futuro")
    # 2) programar cada plataforma por separado: si una falla, la otra sigue y se guarda
    res = {}
    if "youtube" in plan:
        previo = {}
        if e.get("youtube"):   # volver a subir: se apunta el intento anterior y se limpia su estado
            previo = {"youtube_anteriores": e.get("youtube_anteriores", []) + [e["youtube"]],
                      "youtube": None, "youtube_hora": None, "yt_check": None, "yt_comentario": None, "fijado_yt": None}
        try:
            _, video = http(url_mp4, raw=True, timeout=300)
            vid = subir_youtube(cfg, video, meta, plan["youtube"])
            cambios = dict(previo, youtube=vid, youtube_hora=iso(plan["youtube"]), error_youtube=None)
            try:    # ¿de verdad está en YouTube? (si el permiso es el antiguo, se comprobará más tarde)
                d = comprobar_youtube(cfg, [vid])[vid]; cambios["yt_check"] = dict(d, t=iso(datetime.now(timezone.utc)))
                if d["estado"] in REHACER_YT: res["error_youtube"] = f"YouTube dice que el vídeo está en estado «{d['estado']}» {d['detalle']}".strip()
            except (SinPermiso, SystemExit): pass
            guardar_video(nombre, cambios); res["youtube"] = vid
        except SystemExit as err:
            res["error_youtube"] = str(err)
            guardar_video(nombre, dict(previo, error_youtube=str(err)) if previo else {"error_youtube": str(err)})
    if "tiktok" in plan:
        previo = {}
        if e.get("tiktok"):
            previo = {"tiktok_anteriores": e.get("tiktok_anteriores", []) + [e["tiktok"]],
                      "tiktok": None, "tiktok_hora": None, "tt_check": None, "fijado_tt": None}
        try:
            pid = programar_tiktok(cfg, meta, url_mp4, plan["tiktok"])
            guardar_video(nombre, dict(previo, tiktok=pid, tiktok_hora=iso(plan["tiktok"]), error_tiktok=None))
            res["tiktok"] = pid
        except SystemExit as err:
            res["error_tiktok"] = str(err)
            guardar_video(nombre, dict(previo, error_tiktok=str(err)) if previo else {"error_tiktok": str(err)})
    _chk["t"] = 0   # la próxima carga del panel vuelve a preguntar a YouTube y Buffer
    return res

def marcar_fijado(p):
    nombre, plat = p.get("nombre", ""), p.get("plataforma")
    if plat not in ("youtube", "tiktok"): raise SystemExit("Plataforma no válida")
    if nombre not in leer(ESTADO, {}): raise SystemExit(f"{nombre} no está programado")
    clave = "fijado_yt" if plat == "youtube" else "fijado_tt"
    guardar_video(nombre, {clave: iso(datetime.now(timezone.utc)) if p.get("valor", True) else None})
    return {"ok": True}

def comentar(cfg, p):
    """Publica en YouTube el comentario de la ficha con tu canal (luego hay que fijarlo a mano en la app)."""
    nombre = p.get("nombre", "")
    e = leer(ESTADO, {}).get(nombre)
    if not e or not e.get("youtube"): raise SystemExit("Ese vídeo no está en YouTube")
    texto = (p.get("texto") or e.get("comentario_yt") or "").strip()
    if not texto: raise SystemExit("La ficha no trae comentario para fijar")
    try:
        d = comprobar_youtube(cfg, [e["youtube"]])[e["youtube"]]
        if d["estado"] != "publicado":
            raise SystemExit("El vídeo aún no es público: YouTube no deja comentar hasta que se publique")
        ya = comentario_propio(cfg, e["youtube"], d.get("canal"), texto)
        cid = ya or publicar_comentario(cfg, e["youtube"], texto)
    except SinPermiso:
        raise SystemExit("Falta permiso para comentar: ejecuta auth-youtube otra vez")
    guardar_video(nombre, {"yt_comentario": cid, "yt_check": dict(d, t=iso(datetime.now(timezone.utc)))})
    return {"ok": True, "ya_estaba": bool(ya)}

def informe(cfg):
    """Comando `estado`: lo mismo que enseña el panel, en texto."""
    d = listar(cfg, forzar=True)
    for k, v in d["avisos"].items(): print(f"⚠️  {k}: {v}")
    TXT = {"programado": "✓ subido y programado", "procesando": "subido, procesándose", "publicado": "✓ publicado",
           "privado": "⚠️ subido pero privado sin fecha", "privado_atascado": "⚠️ ya pasó la hora y sigue privado",
           "oculto": "oculto (no listado)", "no_existe": "✗ NO está en YouTube", "fallo": "✗ la subida falló",
           "rechazado": "✗ rechazado", "en_cola": "✓ en cola de Buffer", "publicando": "publicándose",
           "error": "✗ Buffer dio error", "borrador": "⚠️ borrador (no se publicará solo)", "no_encontrado": "✗ no está en Buffer"}
    for v in d["videos"]:
        if not v.get("youtube") and not v.get("tiktok"): continue
        print(f"\n{v['nombre']}  {v['titulo']}")
        if v.get("youtube"):
            est = TXT.get(v["yt_estado"], "sin comprobar")
            fij = "📌 fijado" if v["fijado_yt"] else ("comentario puesto, falta fijarlo" if v["yt_comentario"]
                  else "falta comentario y fijarlo") if v["yt_publicado"] else "se fija al publicarse"
            print(f"  YouTube  {est} · {v["youtube_hora"].replace("T", " ")} · https://youtube.com/shorts/{v['youtube']} · {fij}"
                  + (f" ({v['yt_detalle']})" if v["yt_detalle"] else ""))
        if v.get("tiktok"):
            est = TXT.get(v["tt_estado"], "sin comprobar")
            fij = "📌 fijado" if v["fijado_tt"] else "falta fijarlo" if v["tt_publicado"] else "se fija al publicarse"
            print(f"  TikTok   {est} · {v["tiktok_hora"].replace("T", " ")} · {fij}" + (f" · {v['tt_link']}" if v["tt_link"] else ""))

def web(cfg, puerto=8765):
    token = secrets.token_urlsafe(18)
    junto = os.path.join(AQUI, "index.html")
    def pagina():
        if os.path.exists(junto):
            with open(junto, encoding="utf-8") as f: html = f.read()
            if 'data-f="fijar"' in html: return html
            print("AVISO: el index.html que tienes junto al script es de una versión antigua: uso el panel integrado. Bórralo.")
        return PANEL_HTML
    class H(BaseHTTPRequestHandler):
        def _ok_host(self):
            return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")
        def _json(self, code, data):
            b = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers()
            self.wfile.write(b)
        def _auth(self):
            return self._ok_host() and secrets.compare_digest(self.headers.get("X-Token", ""), token)
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path in ("/", "/index.html"):
                if not self._ok_host() or urllib.parse.parse_qs(u.query).get("t", [""])[0] != token:
                    self.send_response(403); self.end_headers(); self.wfile.write(b"Abre la URL que muestra el script."); return
                b = pagina().replace("__TOKEN__", token).encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers()
                self.wfile.write(b); return
            if u.path == "/api/estado":
                if not self._auth(): return self._json(403, {"error": "token"})
                forzar = "recargar" in u.query
                if forzar: _metas.clear()
                try: return self._json(200, listar(cfg, forzar))
                except Exception as e: return self._json(500, {"error": f"{type(e).__name__}: {e}"})
            self.send_response(404); self.end_headers()
        def do_POST(self):
            rutas = {"/api/programar": lambda p: programar_uno(cfg, p),
                     "/api/fijado": marcar_fijado, "/api/comentar": lambda p: comentar(cfg, p)}
            if self.path not in rutas or not self._auth(): return self._json(403, {"error": "token"})
            p = {}
            try:
                p = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
                if self.path == "/api/fijado": return self._json(200, marcar_fijado(p))
                if not _lock.acquire(blocking=False): return self._json(409, {"error": "Ya hay otra operación en marcha"})
                try: r = rutas[self.path](p)
                finally: _lock.release()
                print(f"{self.path[5:]} {p.get('nombre')}: {r}")
                return self._json(200, {"ok": not any(k.startswith("error") for k in r), **r})
            except SystemExit as e:
                print(f"ERROR {p.get('nombre', '')}: {e}")
                return self._json(400, {"error": str(e)})
            except Exception as e:
                return self._json(500, {"error": f"{type(e).__name__}: {e}"})
        def log_message(self, *a): pass
    try: srv = ThreadingHTTPServer(("127.0.0.1", puerto), H)
    except OSError: srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={token}"
    print(f"publicar_movil.py v{VERSION}")
    print("Panel en marcha (Ctrl+C o detener el script para cerrarlo):\n\n" + url + "\n")
    def abrir():
        time.sleep(0.5)
        try:
            import console  # noqa: F401  -> solo existe en Pythonista: su navegador interno mantiene vivo el script
            webbrowser.open(url); return
        except ImportError: pass
        if sys.platform == "ios" or os.environ.get("APPDIR"):   # a-Shell
            if os.system(f"internalbrowser '{url}'") == 0: return
        try: webbrowser.open(url)
        except Exception: pass
    threading.Thread(target=abrir, daemon=True).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("Panel cerrado.")

# ---------------- autoactualización desde el repo ----------------
def _ver(v): return tuple(int(x) for x in str(v).split(".") if x.isdigit())

def actualizar(cfg, forzar=False):
    """Si scripts/publicar_movil.py del repo trae una VERSION mayor, se sustituye y la ejecuta. Devuelve True si lo hizo."""
    repo = cfg.get("github_repo", "")
    if not repo or "TU_USUARIO" in repo: return False
    url = f"https://raw.githubusercontent.com/{repo}/{cfg.get('github_rama', 'main')}/scripts/publicar_movil.py"
    try:
        _, nuevo = http(url, raw=True, timeout=20)
        codigo = nuevo.decode("utf-8")
    except (SystemExit, Exception) as e:
        if forzar: print("No se pudo descargar la versión del repo:", str(e)[:200])
        return False
    import re
    m = re.search(r'^VERSION = "([0-9.]+)"', codigo, re.M)
    if not m or "def web(" not in codigo:
        if forzar: print("El archivo del repo no parece este script: no lo uso.")
        return False
    if _ver(m.group(1)) <= _ver(VERSION):
        if forzar: print(f"Ya tienes la última versión (v{VERSION}).")
        return False
    try: compile(codigo, __file__, "exec")
    except SyntaxError as e:
        print(f"La v{m.group(1)} del repo tiene un error ({e}); sigo con la v{VERSION}."); return False
    yo = os.path.abspath(__file__)
    try:
        with open(yo, encoding="utf-8") as f: viejo = f.read()
        with open(yo + ".anterior", "w", encoding="utf-8") as f: f.write(viejo)   # copia por si acaso
        tmp = yo + ".nuevo"
        with open(tmp, "w", encoding="utf-8") as f: f.write(codigo)
        os.replace(tmp, yo)
    except OSError as e:
        print("No pude escribir la versión nueva:", e); return False
    print(f"Actualizado de v{VERSION} a v{m.group(1)} (la anterior queda en publicar_movil.py.anterior).")
    return True

def _relanzar():
    """Ejecuta el script recién descargado en este mismo proceso (funciona también en Pythonista y a-Shell)."""
    yo = os.path.abspath(__file__)
    with open(yo, encoding="utf-8") as f: codigo = f.read()
    exec(compile(codigo, yo, "exec"), {"__name__": "__main__", "__file__": yo, "__builtins__": __builtins__})

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "init":
        if os.path.exists(CFG): raise SystemExit("config.json ya existe")
        guardar(CFG, EJEMPLO); print("Creado config.json. Rellénalo (solo vive en este móvil)."); sys.exit()
    # los valores vacíos de config.json no pisan los que ya trae el script
    cfg = dict(EJEMPLO, **{k: v for k, v in leer(CFG, {}).items() if v not in ("", None)})
    if cmd == "actualizar":
        if actualizar(cfg, forzar=True): print("Listo: la próxima vez que lo lances ya usa la versión nueva.")
        sys.exit()
    if cmd in ("web", "run", "estado") and cfg.get("auto_actualizar", True) and actualizar(cfg):
        _relanzar(); sys.exit()
    if cmd == "auth-youtube": auth_youtube(cfg)
    elif cmd == "buffer-canales": buffer_canales(cfg)
    elif cmd == "run": run(cfg, "--dry-run" in sys.argv)
    elif cmd == "web": web(cfg)
    elif cmd == "estado": informe(cfg)
    else: print(__doc__)
