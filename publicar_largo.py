#!/usr/bin/env python3
"""
publicar_largo.py — PANEL WEB EN EL ORDENADOR para subir los VÍDEOS LARGOS del canal a YouTube.
Es el hermano de publicar_movil.py (el de los Shorts), funciona solo y no toca nada suyo: ni pendientes/ del repo, ni
estado.json, ni TikTok. Solo librería estándar de Python.

DÓNDE ESTÁN LOS VÍDEOS LARGOS
  Un vídeo largo pesa 300–600 MB y GitHub no deja meter archivos de más de 100 MB en el repo. Por eso el kit
  de vídeos largos no los mete en una carpeta: los pone en la sección «Releases» del mismo repo
  (github.com/<tu repo>/releases), que es una zona de DESCARGAS que va aparte de los archivos y admite hasta 2 GB.
  Cada vídeo es una release llamada largo-<tema> con: largo_<tema>.mp4, .json (título, descripción, tags),
  _miniatura.png y _capitulos.txt. El panel las lee de ahí (el repo es público: no hace falta ninguna clave).
  Desde la v1.5 el kit los deja en la RAMA «largos» del mismo repo (una carpeta por vídeo): el panel la lee sola y,
  al pulsar Subir, descarga los archivos a largos/entrada/<carpeta>/. No tienes que descargar nada a mano.
  Si un vídeo te llega por el chat, mete sus archivos en una carpeta dentro de largos/entrada/ y también sale.

PREPARACIÓN (una vez)
  1. Pon en la misma carpeta el config.json del móvil (el de publicar_movil.py: ya trae la conexión con YouTube).
     O renombra config.ejemplo.json a config.json, pon youtube_client_id y youtube_client_secret y ejecuta
     python3 publicar_largo.py auth-youtube (abre el navegador y lo guarda solo).
  2. Python 3.8 o más nuevo (Windows, Mac o Linux). Nada que instalar. No necesita publicar_movil.py.

ACTUALIZACIÓN AUTOMÁTICA (v1.6)
  Al arrancar mira si en la rama «largos» del repo hay un publicar_largo.py con un número de versión más alto. Si lo hay,
  se descarga, comprueba que es un script válido, guarda el viejo como publicar_largo.anterior.py y arranca con el nuevo.
  Para desactivarlo: "auto_actualizar": false en config.json.

USO
  python3 publicar_largo.py            abre el PANEL en el navegador (igual que el del móvil)
  python3 publicar_largo.py estado     lo mismo en texto
  python3 publicar_largo.py prueba     comprueba la conexión con YouTube y con el repo, sin subir nada
  python3 publicar_largo.py borrar <nombre> [--archivos]   borra el vídeo de YouTube (y sus archivos del ordenador)
  python3 publicar_largo.py auth-youtube   autoriza el canal desde el ordenador (solo si no copiaste config.json)

QUÉ HACE AL SUBIR
  Descarga el vídeo (si viene del repo) a largos/<etiqueta>/, lo sube a YouTube en privado con la fecha que elijas
  (o privado sin fecha), categoría Educación, español, marca de contenido sintético, miniatura y capítulos en la
  descripción. Lo apunta en largos_estado.json para no subirlo dos veces. Solo YouTube: nunca TikTok.
"""
import json, os, sys, glob, time, secrets, threading, webbrowser, urllib.request, urllib.parse, urllib.error, ssl, shutil, subprocess
try:                     # si está instalado, usa los certificados del sistema (redes de empresa, antivirus que inspeccionan HTTPS)
    import truststore; truststore.inject_into_ssl()
except Exception:
    pass

def _es_ssl(e):
    r = getattr(e, "reason", e)
    return isinstance(r, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(e)

def _curl():
    """curl del sistema (Windows 10/11 lo trae y verifica con los certificados de Windows, como el navegador)."""
    return shutil.which("curl.exe") or shutil.which("curl")
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

AQUI = os.path.dirname(os.path.abspath(__file__))

VERSION = "1.6"
RAMA = "largos"            # v1.5: rama del repo con una carpeta por vídeo (lo que deja el kit; no hace falta Releases)
ESTADO = os.path.join(AQUI, "largos_estado.json")
CARPETA = os.path.join(AQUI, "largos")
ENTRADA = os.path.join(CARPETA, "entrada")
PREFIJO = "largo-"
CHUNK = 8 << 20
_lock = threading.Lock()
_prog = {"nombre": None, "fase": "", "pct": 0, "error": None}


# ---------------------------------------------------------------- conexión (independiente: no necesita publicar_movil.py)
class _M:
    """Lo mínimo para hablar con YouTube y GitHub. Usa el mismo config.json que publicar_movil.py."""
    CFG = os.path.join(AQUI, "config.json")
    UA = "publicar-largo/1.1"
    SCOPE = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"
    EJEMPLO = {"github_repo": "datoloco54-boop/shorts-media", "youtube_client_id": "", "youtube_client_secret": "",
               "youtube_refresh_token": "", "categoria_youtube": "27"}
    _tok = {"v": None, "exp": 0}
    _canal = {}

    @staticmethod
    def leer(p, defecto):
        try:
            with open(p, encoding="utf-8") as f: return json.load(f)
        except (OSError, ValueError): return defecto

    @staticmethod
    def guardar(p, d):
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)

    @staticmethod
    def http(url, data=None, headers=None, method=None, raw=False, timeout=120):
        h = {"User-Agent": _M.UA}; h.update(headers or {})
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        if data is None and not raw and _M.usar_curl:
            return _M.curl_json(url, h, timeout)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                return (r, body) if raw else (json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            raise SystemExit("ERROR HTTP %s en %s\n%s" % (e.code, url.split("?")[0], e.read().decode("utf-8", "replace")[:800]))
        except urllib.error.URLError as e:
            if data is None and not raw and _es_ssl(e) and _curl():
                _M.usar_curl = True                      # a partir de ahora, las lecturas van por curl
                return _M.curl_json(url, h, timeout)
            if _es_ssl(e):
                raise SystemExit("Python no puede verificar el certificado HTTPS de " + url.split("/")[2] +
                                 " (red de empresa o antivirus). Prueba: pip install truststore")
            raise SystemExit("Sin conexión con %s: %s" % (url.split("/")[2], e.reason))

    usar_curl = False

    @staticmethod
    def curl_json(url, headers, timeout):
        cmd = [_curl(), "-sSL", "--fail-with-body", "--max-time", str(timeout)]
        for k, v in headers.items(): cmd += ["-H", "%s: %s" % (k, v)]
        r = subprocess.run(cmd + [url], capture_output=True)
        if r.returncode != 0:
            raise SystemExit("ERROR en %s (curl %s)\n%s" % (url.split("?")[0], r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")[:600]))
        return json.loads(r.stdout) if r.stdout.strip() else {}

    @staticmethod
    def hora_espana(fecha, hhmm):
        """datetime UTC de una hora de España (CET/CEST), sin depender de tzdata (va igual en Windows)."""
        def ultimo_domingo(y, m):
            d = datetime(y, m + 1, 1) - timedelta(days=1)
            return d - timedelta(days=(d.weekday() + 1) % 7)
        y = fecha.year
        ini = ultimo_domingo(y, 3).replace(hour=1, tzinfo=timezone.utc)
        fin = ultimo_domingo(y, 10).replace(hour=1, tzinfo=timezone.utc)
        h, m = map(int, hhmm.split(":"))
        for off in (2, 1):
            u = datetime(y, fecha.month, fecha.day, h, m, tzinfo=timezone.utc) - timedelta(hours=off)
            if (ini <= u < fin) == (off == 2): return u
        return datetime(y, fecha.month, fecha.day, h, m, tzinfo=timezone.utc) - timedelta(hours=1)

    @staticmethod
    def iso(t): return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    @staticmethod
    def token_youtube(cfg):
        if _M._tok["v"] and time.time() < _M._tok["exp"]: return _M._tok["v"]
        try:
            t = _M.http("https://oauth2.googleapis.com/token", urllib.parse.urlencode(dict(
                client_id=cfg["youtube_client_id"], client_secret=cfg["youtube_client_secret"],
                refresh_token=cfg["youtube_refresh_token"], grant_type="refresh_token")).encode(),
                {"Content-Type": "application/x-www-form-urlencoded"})
        except SystemExit as e:
            if "invalid_grant" in str(e):
                raise SystemExit("La autorización de YouTube ha caducado: python3 publicar_largo.py auth-youtube")
            raise
        _M._tok.update(v=t["access_token"], exp=time.time() + int(t.get("expires_in", 3600)) - 120)
        return _M._tok["v"]

    @staticmethod
    def yt(cfg, metodo, params):
        return _M.http("https://www.googleapis.com/youtube/v3/" + metodo + "?" + urllib.parse.urlencode(params),
                       headers={"Authorization": "Bearer " + _M.token_youtube(cfg)}, timeout=60)

    @staticmethod
    def canal_autorizado(cfg):
        if not _M._canal:
            it = _M.yt(cfg, "channels", {"part": "snippet", "mine": "true"}).get("items", [])
            _M._canal["v"] = (it[0]["id"], it[0]["snippet"]["title"]) if it else ("", "")
        return _M._canal["v"]

    @staticmethod
    def comprobar_youtube(cfg, ids):
        res, ahora = {}, datetime.now(timezone.utc)
        ids = list(dict.fromkeys(i for i in ids if i))
        for k in range(0, len(ids), 50):
            lote = ids[k:k + 50]
            r = _M.yt(cfg, "videos", {"part": "status", "id": ",".join(lote), "maxResults": 50})
            for it in r.get("items", []):
                st = it.get("status", {}); up, priv, pub = st.get("uploadStatus"), st.get("privacyStatus"), st.get("publishAt")
                if up == "failed": e = "fallo"
                elif up == "rejected": e = "rechazado"
                elif priv == "public": e = "publicado"
                elif priv == "unlisted": e = "oculto"
                elif pub:
                    cuando = datetime.strptime(pub[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    e = "privado_atascado" if cuando <= ahora else ("programado" if up == "processed" else "procesando")
                else: e = "privado"
                res[it["id"]] = {"estado": e}
            for i in lote: res.setdefault(i, {"estado": "no_existe"})
        return res

    @staticmethod
    def pedir_cliente(cfg):
        """Consigue el ID y el secreto del cliente OAuth: de un client_secret*.json descargado de Google Cloud
        (se busca en esta carpeta y en Descargas) o pegándolos en la terminal. Los guarda en config.json."""
        cands = glob.glob(os.path.join(AQUI, "client_secret*.json")) + \
                glob.glob(os.path.join(os.path.expanduser("~"), "Downloads", "client_secret*.json")) + \
                glob.glob(os.path.join(os.path.expanduser("~"), "Descargas", "client_secret*.json"))
        cid = sec = ""
        for c in sorted(cands, key=os.path.getmtime, reverse=True):
            d = _M.leer(c, {}); d = d.get("installed") or d.get("web") or {}
            if d.get("client_id") and d.get("client_secret"):
                cid, sec = d["client_id"], d["client_secret"]; print("Uso el cliente de", c); break
        if not cid:
            print("Necesito el ID de cliente y el secreto de Google Cloud (los mismos que usa el móvil).")
            print("Dónde están: https://console.cloud.google.com/apis/credentials → tu ID de cliente OAuth.")
            print("Si no ves el secreto, pulsa «Añadir secreto» en ese cliente (o descarga su JSON y déjalo en esta carpeta).\n")
            cid = input("ID de cliente (acaba en .apps.googleusercontent.com): ").strip()
            sec = input("Secreto del cliente: ").strip()
        if not cid.endswith(".apps.googleusercontent.com") or not sec:
            raise SystemExit("Eso no parece un ID de cliente de Google. Repite: python3 publicar_largo.py auth-youtube")
        todo = _M.leer(_M.CFG, dict(_M.EJEMPLO)); todo.update(youtube_client_id=cid, youtube_client_secret=sec)
        todo.setdefault("github_repo", _M.EJEMPLO["github_repo"]); _M.guardar(_M.CFG, todo)
        cfg.update(youtube_client_id=cid, youtube_client_secret=sec)
        print("Guardado en config.json.\n")

    @staticmethod
    def auth_youtube(cfg):
        """Autoriza el canal desde el ordenador: abre el navegador y recoge el código solo."""
        import hashlib, base64
        if not cfg.get("youtube_client_id") or not cfg.get("youtube_client_secret"):
            _M.pedir_cliente(cfg)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        state, res = secrets.token_urlsafe(16), {}
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if q.get("state", [""])[0] == state: res.update({k: v[0] for k, v in q.items()})
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
                self.wfile.write("Listo. Ya puedes cerrar esta pestaña y volver a la terminal.".encode())
            def log_message(self, *a): pass
        from http.server import HTTPServer
        srv = HTTPServer(("127.0.0.1", 0), H); redirect = "http://127.0.0.1:%d" % srv.server_address[1]
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(dict(
            client_id=cfg["youtube_client_id"], redirect_uri=redirect, response_type="code", scope=_M.SCOPE,
            access_type="offline", prompt="consent select_account", state=state, code_challenge=challenge, code_challenge_method="S256"))
        print("Se abre el navegador para autorizar el canal. Si no se abre, copia este enlace:\n\n" + url + "\n")
        webbrowser.open(url)
        while "code" not in res and "error" not in res: srv.handle_request()
        srv.server_close()
        if "error" in res: raise SystemExit("Autorización cancelada: " + res["error"])
        t = _M.http("https://oauth2.googleapis.com/token", urllib.parse.urlencode(dict(
            code=res["code"], client_id=cfg["youtube_client_id"], client_secret=cfg["youtube_client_secret"],
            redirect_uri=redirect, grant_type="authorization_code", code_verifier=verifier)).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"})
        if "refresh_token" not in t: raise SystemExit("Google no devolvió refresh_token. Repite auth-youtube.")
        todo = _M.leer(_M.CFG, {}); todo["youtube_refresh_token"] = t["refresh_token"]; _M.guardar(_M.CFG, todo)
        cfg["youtube_refresh_token"] = t["refresh_token"]
        nombre = _M.canal_autorizado(cfg)[1]
        if nombre: print("OK: autorizado. Canal: «%s»" % nombre)
        else: print("OJO: esa cuenta de Google no tiene canal de YouTube. Repite auth-youtube y, en la pantalla de Google,\n"
                    "elige el CANAL Dato Loco (sale como cuenta aparte con su foto) en vez de tu cuenta personal.")

M = _M

def cfg_actual():
    return dict(M.EJEMPLO, **{k: v for k, v in M.leer(M.CFG, {}).items() if v not in ("", None)})

def estado(): return M.leer(ESTADO, {})


# ---------------------------------------------------------------- de dónde salen los vídeos
def releases(repo):
    out, page = [], 1
    while True:
        r = M.http(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}",
                   headers={"Accept": "application/vnd.github+json"}, timeout=30)
        if not r: break
        out += [x for x in r if x.get("tag_name", "").startswith(PREFIJO) and not x.get("draft")]
        if len(r) < 100: break
        page += 1
    return out

def rama(repo):
    """Vídeos de la rama «largos»: {carpeta: {archivo: (bytes, url)}}. Sin la rama, {}."""
    try:
        t = M.http(f"https://api.github.com/repos/{repo}/git/trees/{RAMA}?recursive=1",
                   headers={"Accept": "application/vnd.github+json"}, timeout=30)
    except SystemExit as e:
        if "HTTP 404" in str(e) or "HTTP 409" in str(e) or "(curl 22)" in str(e): return {}
        raise
    out = {}
    for it in t.get("tree", []):
        partes = it.get("path", "").split("/")
        if it.get("type") != "blob" or len(partes) != 2: continue
        url = f"https://raw.githubusercontent.com/{repo}/{RAMA}/" + urllib.parse.quote(it["path"])
        out.setdefault(partes[0], {})[partes[1]] = (it.get("size", 0), url)
    return {k: v for k, v in out.items() if any(n.endswith(".mp4") for n in v)}

def _asset(rel, *finales):
    for a in rel.get("assets", []):
        if any(a["name"].endswith(f) for f in finales): return a
    return None

def videos(cfg):
    """Lista unificada: releases del repo + carpetas de largos/entrada/."""
    vs, errores = [], {}
    if cfg.get("github_repo") and "TU_USUARIO" not in cfg["github_repo"]:
        try:
            for r in releases(cfg["github_repo"]):
                mp4, js = _asset(r, ".mp4"), _asset(r, ".json")
                mini = _asset(r, "_miniatura.png", "_miniatura.jpg")
                meta = {}
                if js:
                    try: meta = M.http(js["browser_download_url"], timeout=30)
                    except SystemExit: meta = {}
                vs.append(dict(nombre=r["tag_name"], origen="repo", titulo=(meta.get("youtube", meta) or {}).get("titulo") or r.get("name") or r["tag_name"],
                               mb=sum(a.get("size", 0) for a in r.get("assets", [])) // (1 << 20),
                               mini=mini["browser_download_url"] if mini else "", completo=bool(mp4 and js),
                               creado=meta.get("creado") or r.get("published_at", "")[:16], publicar_en=meta.get("publicar_en", "")))
        except SystemExit as e:
            errores["repo"] = str(e)[:300]
    else:
        errores["repo"] = "Pon github_repo en config.json (p. ej. datoloco54-boop/shorts-media)."
    os.makedirs(ENTRADA, exist_ok=True)
    if cfg.get("github_repo") and "TU_USUARIO" not in cfg["github_repo"]:
        try:
            for carpeta, fs in sorted(rama(cfg["github_repo"]).items()):
                if piezas(os.path.join(ENTRADA, carpeta)): continue          # ya descargado: sale como carpeta local
                js = next((u for n, (_, u) in fs.items() if n.endswith(".json")), None)
                mini = next((u for n, (_, u) in fs.items() if "miniatura" in n), "")
                meta = {}
                if js:
                    try: meta = M.http(js, timeout=30)
                    except SystemExit: meta = {}
                vs.append(dict(nombre="local:" + carpeta, origen="rama", titulo=(meta.get("youtube", meta) or {}).get("titulo") or carpeta,
                               mb=sum(b for b, _ in fs.values()) // (1 << 20), mini=mini, completo=bool(js),
                               creado=meta.get("creado", ""), publicar_en=meta.get("publicar_en", "")))
        except SystemExit as e:
            errores["rama"] = str(e)[:300]
    for d in sorted(glob.glob(os.path.join(ENTRADA, "*"))):
        if not os.path.isdir(d): continue
        p = piezas(d)
        if not p: continue
        meta = M.leer(p["ficha"], {}) if p["ficha"] else {}
        vs.append(dict(nombre="local:" + os.path.basename(d), origen="carpeta", titulo=(meta.get("youtube", meta) or {}).get("titulo") or os.path.basename(d),
                       mb=os.path.getsize(p["mp4"]) // (1 << 20), mini=("/f/" + urllib.parse.quote(os.path.relpath(p["mini"], CARPETA))) if p["mini"] else "",
                       completo=bool(p["ficha"]), creado=meta.get("creado", ""), publicar_en=meta.get("publicar_en", "")))
    st = estado()
    for v in vs: v.update(st.get(v["nombre"], {}))
    vs.sort(key=lambda v: v.get("creado") or "")
    return vs, errores

def piezas(carpeta):
    mp4s = sorted(glob.glob(os.path.join(carpeta, "*.mp4")))
    if not mp4s: return None
    base = mp4s[0][:-4]
    js = base + ".json" if os.path.exists(base + ".json") else next(iter(glob.glob(os.path.join(carpeta, "*.json"))), None)
    mini = next(iter(glob.glob(os.path.join(carpeta, "*miniatura*"))), None)
    caps = next(iter(glob.glob(os.path.join(carpeta, "*capitulos*.txt"))), None)
    return dict(mp4=mp4s[0], ficha=js, mini=mini, caps=caps)

def _https_ok(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers={"User-Agent": M.UA}), timeout=20).close(); return True
    except urllib.error.HTTPError: return True
    except urllib.error.URLError as e:
        if _es_ssl(e) and _curl(): M.usar_curl = True; return False
        raise

def descargar(url, destino, etiqueta):
    if os.path.exists(destino): return
    tmp = destino + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": M.UA})
    if M.usar_curl or not _https_ok(url):          # red que Python no sabe verificar: descarga con curl
        _prog.update(fase=f"Descargando {etiqueta} (sin %)", pct=0)
        r = subprocess.run([_curl(), "-sSL", "--fail", "-A", M.UA, "-o", tmp, url])
        if r.returncode != 0: raise SystemExit(f"No se pudo descargar {etiqueta} (curl {r.returncode}).")
        os.replace(tmp, destino); return
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total, hecho = int(r.headers.get("Content-Length") or 0), 0
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b); hecho += len(b)
            if total: _prog.update(fase=f"Descargando {etiqueta}", pct=hecho * 100 // total)
    os.replace(tmp, destino)

def preparar(cfg, nombre):
    """Deja el vídeo en una carpeta local y devuelve sus piezas."""
    if nombre.startswith("local:"):
        d = os.path.join(ENTRADA, nombre[6:])
        if not piezas(d):                                   # todavía en la rama «largos» del repo: se descarga ahora
            fs = rama(cfg["github_repo"]).get(nombre[6:])
            if not fs: raise SystemExit(f"No encuentro {nombre[6:]} ni en largos/entrada/ ni en la rama «{RAMA}» del repo.")
            os.makedirs(d, exist_ok=True)
            for n, (b, url) in sorted(fs.items(), key=lambda x: x[0].endswith(".mp4")):   # el MP4, el último
                dst = os.path.join(d, n)
                if os.path.exists(dst) and os.path.getsize(dst) != b: os.remove(dst)
                descargar(url, dst, n)
        return piezas(d)
    rel = next((r for r in releases(cfg["github_repo"]) if r["tag_name"] == nombre), None)
    if not rel: raise SystemExit(f"{nombre} ya no está en el repo.")
    d = os.path.join(CARPETA, nombre); os.makedirs(d, exist_ok=True)
    for a in rel.get("assets", []):
        dst = os.path.join(d, a["name"])
        if os.path.exists(dst) and os.path.getsize(dst) != a.get("size"): os.remove(dst)
        descargar(a["browser_download_url"], dst, a["name"])
    return piezas(d)


# ---------------------------------------------------------------- YouTube
def cuerpo(cfg, meta, caps, cuando):
    yt = meta.get("youtube", meta)
    desc = yt.get("descripcion", "")
    if caps and "0:00" not in desc: desc = desc.rstrip() + "\n\nCapítulos:\n" + caps.strip()
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if cuando: status["publishAt"] = M.iso(cuando)
    return {"snippet": {"title": yt["titulo"][:100], "description": desc[:5000], "tags": yt.get("tags", [])[:30],
                        "categoryId": cfg.get("categoria_youtube", "27"), "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            "status": status}

def subir_grande(cfg, ruta, body):
    """Subida reanudable por trozos de 8 MB (vale para vídeos de varios GB) con reintentos."""
    total = os.path.getsize(ruta)
    r, _ = M.http("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                  json.dumps(body).encode(), {"Authorization": f"Bearer {M.token_youtube(cfg)}",
                  "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4",
                  "X-Upload-Content-Length": str(total)}, "POST", raw=True)
    up, pos, fallos = r.headers["Location"], 0, 0
    with open(ruta, "rb") as f:
        while True:
            f.seek(pos); trozo = f.read(CHUNK); fin = pos + len(trozo) - 1
            req = urllib.request.Request(up, data=trozo, method="PUT", headers={
                "Authorization": f"Bearer {M.token_youtube(cfg)}", "Content-Type": "video/mp4",
                "Content-Range": f"bytes {pos}-{fin}/{total}", "User-Agent": M.UA})
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    return json.loads(resp.read())                       # 200/201: terminado
            except urllib.error.HTTPError as e:
                if e.code == 308:                                         # trozo aceptado: sigue
                    rng = e.headers.get("Range"); pos = int(rng.split("-")[1]) + 1 if rng else 0; fallos = 0
                    _prog.update(fase="Subiendo a YouTube", pct=pos * 100 // total); continue
                if e.code in (500, 502, 503, 504) and fallos < 5: pass
                else: raise SystemExit(f"YouTube rechazó la subida (HTTP {e.code}): {e.read().decode('utf-8', 'replace')[:400]}")
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if fallos >= 5: raise SystemExit("Se cortó la conexión varias veces subiendo el vídeo. Vuelve a intentarlo.")
            fallos += 1; time.sleep(2 ** fallos)
            q = urllib.request.Request(up, data=b"", method="PUT", headers={      # ¿hasta dónde llegó?
                "Authorization": f"Bearer {M.token_youtube(cfg)}", "Content-Range": f"bytes */{total}", "User-Agent": M.UA})
            try:
                with urllib.request.urlopen(q, timeout=60) as resp: return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code == 308:
                    rng = e.headers.get("Range"); pos = int(rng.split("-")[1]) + 1 if rng else 0
            except Exception: pass

def poner_miniatura(cfg, vid, ruta):
    tipo = "image/png" if ruta.endswith(".png") else "image/jpeg"
    with open(ruta, "rb") as f: img = f.read()
    try:
        M.http(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}", img,
               {"Authorization": f"Bearer {M.token_youtube(cfg)}", "Content-Type": tipo}, "POST")
        return None
    except SystemExit as e:
        return "Miniatura no aplicada (¿canal verificado por teléfono?). Ponla a mano en YouTube Studio." if "403" in str(e) else str(e)[:200]

def subir(cfg, nombre, cuando_txt):
    """cuando_txt: 'AAAA-MM-DDTHH:MM' hora de España, o '' para privado sin fecha."""
    if estado().get(nombre, {}).get("youtube"): raise SystemExit("Ese vídeo ya está subido.")
    if estado().get(nombre, {}).get("borrado"): recuperar(nombre)
    cuando = None
    if cuando_txt:
        d, h = cuando_txt.split("T")
        cuando = M.hora_espana(datetime.strptime(d, "%Y-%m-%d"), h)
        if cuando <= datetime.now(timezone.utc) + timedelta(minutes=15):
            raise SystemExit("Elige una hora con al menos 15 minutos de margen.")
    _prog.update(nombre=nombre, fase="Preparando", pct=0, error=None)
    p = preparar(cfg, nombre)
    if not p or not p["ficha"]: raise SystemExit("Faltan archivos: hace falta el .mp4 y su .json.")
    meta = M.leer(p["ficha"], {})
    caps = open(p["caps"], encoding="utf-8").read() if p["caps"] else ""
    res = subir_grande(cfg, p["mp4"], cuerpo(cfg, meta, caps, cuando))
    vid = res["id"]
    aviso = poner_miniatura(cfg, vid, p["mini"]) if p["mini"] else "Sin miniatura en la ficha."
    st = estado()
    st[nombre] = {"youtube": vid, "hora": cuando_txt or "", "subido": datetime.now().strftime("%Y-%m-%dT%H:%M"), "aviso": aviso or ""}
    M.guardar(ESTADO, st)
    _prog.update(fase="Hecho", pct=100)
    return st[nombre]

def borrar(cfg, nombre, archivos=False):
    """Borra el vídeo de YouTube (si se subió) y lo quita del panel. archivos=True borra además sus archivos del ordenador.
    Un vídeo que sigue en Releases del repo queda como «Borrado» en «Todos» (se puede recuperar para subirlo otra vez)."""
    st = estado(); e = st.get(nombre, {})
    if e.get("youtube"):
        try:
            M.http("https://www.googleapis.com/youtube/v3/videos?id=" + e["youtube"], None,
                   {"Authorization": "Bearer " + M.token_youtube(cfg)}, "DELETE", raw=True, timeout=60)
        except SystemExit as err:
            if "HTTP 404" not in str(err):
                if "403" in str(err): raise SystemExit("YouTube no deja borrarlo con este permiso: repite auth-youtube y vuelve a probar.")
                raise
    if archivos:
        d = os.path.join(ENTRADA, nombre[6:]) if nombre.startswith("local:") else os.path.join(CARPETA, nombre)
        if os.path.realpath(d).startswith(os.path.realpath(CARPETA)) and os.path.isdir(d): shutil.rmtree(d, ignore_errors=True)
    if nombre.startswith("local:") and archivos: st.pop(nombre, None)
    else: st[nombre] = {"borrado": datetime.now().strftime("%Y-%m-%dT%H:%M"), "youtube_borrado": e.get("youtube", "")}
    M.guardar(ESTADO, st)
    return {"ok": True}

def recuperar(nombre):
    st = estado(); st.pop(nombre, None); M.guardar(ESTADO, st); return {"ok": True}

def comprobar(cfg, vs):
    ids = [v["youtube"] for v in vs if v.get("youtube")]
    if not ids: return
    try: res = M.comprobar_youtube(cfg, ids)
    except Exception: return
    for v in vs:
        if v.get("youtube") in res: v["yt_estado"] = res[v["youtube"]]["estado"]


# ---------------------------------------------------------------- panel
PANEL = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel de vídeos largos</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&display=swap">
<style>
:root{--bg:#f3f1fa;--surface:#fff;--ink:#1c1830;--soft:#5e587a;--rule:#dcd7ec;--teal:#00927a;--gold:#a8730a;--red:#c2304f;--violet:#2a1748;--chip:#ebe8f6;
--display:"Bricolage Grotesque",ui-rounded,system-ui,sans-serif;--text:"Atkinson Hyperlegible",system-ui,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0f0d22;--surface:#1a1633;--ink:#f2effc;--soft:#a9a3c8;--rule:#2d2850;--teal:#00d6aa;--gold:#ffc400;--red:#ff6b86;--violet:#20123a;--chip:#241f42;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.45 var(--text)}
.wrap{max-width:860px;margin:0 auto;padding:24px 16px 48px}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:12px}
h1{font:800 30px/1.05 var(--display);letter-spacing:-.02em;margin:0}
.reload{font:700 15px var(--text);color:var(--ink);background:var(--chip);border:0;border-radius:999px;padding:10px 16px;cursor:pointer}
.links{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 18px}
.link{display:inline-flex;align-items:center;gap:6px;font-size:14px;color:var(--soft);background:var(--chip);border-radius:999px;padding:5px 12px}
.link b{color:var(--ink)}.dot{width:8px;height:8px;border-radius:50%;background:var(--red)}.dot.on{background:var(--teal)}
.banner{background:var(--chip);border-left:4px solid var(--red);border-radius:10px;padding:10px 12px;margin:0 0 14px;font-size:14px}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);background:var(--chip);border-radius:14px;padding:4px;gap:4px}
.tabs button{font:700 14px var(--text);color:var(--soft);background:none;border:0;border-radius:10px;padding:10px 2px;cursor:pointer}
.tabs button[aria-pressed=true]{background:var(--surface);color:var(--ink)}.n{font-family:var(--display);font-weight:800;margin-left:4px}
.list{list-style:none;margin:16px 0 0;padding:0}
.item{display:grid;grid-template-columns:240px 1fr;gap:16px;padding:16px 0;border-bottom:1px solid var(--rule)}
@media (max-width:620px){.item{grid-template-columns:1fr}}
.thumb{width:100%;aspect-ratio:16/9;border-radius:12px;overflow:hidden;background:linear-gradient(135deg,#0c0e1e,#200c2e);display:grid;place-items:center;color:#b9b3d6;font-size:13px}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.info{min-width:0}.title{font:600 20px/1.2 var(--display);margin:0 0 4px;overflow-wrap:anywhere}
.file{font-size:13px;color:var(--soft);margin:0 0 10px}
.st{font-size:15px;margin:0 0 12px}.ok{color:var(--teal);font-weight:700}.live{color:var(--gold);font-weight:700}.err{color:var(--red)}
.go{font:700 16px var(--text);color:#fff;background:var(--violet);border:0;border-radius:12px;padding:11px 18px;cursor:pointer}
@media (prefers-color-scheme:dark){.go{background:var(--teal);color:#06231d}}.go:disabled{opacity:.45;cursor:default}
.acc{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.del{font:700 14px var(--text);color:var(--red);background:none;border:1px solid var(--rule);border-radius:12px;padding:10px 14px;cursor:pointer}
.mini{font:700 14px var(--text);color:var(--ink);background:var(--surface);border:1px solid var(--rule);border-radius:999px;padding:7px 14px;text-decoration:none;display:inline-flex}
.bar{height:10px;border-radius:999px;background:var(--chip);overflow:hidden;margin:8px 0}.bar i{display:block;height:100%;background:var(--teal);width:0}
.empty{padding:28px 4px;color:var(--soft)}.empty b{display:block;color:var(--ink);font:600 20px var(--display);margin-bottom:4px}
dialog{border:0;padding:0;width:100%;max-width:520px;background:var(--surface);color:var(--ink);border-radius:22px}
dialog::backdrop{background:rgba(15,10,35,.55)}.sheet{padding:22px 20px}
.sheet h2{font:800 24px/1.1 var(--display);margin:0 0 4px}.sub{color:var(--soft);font-size:14px;margin:0 0 18px}
.field{display:grid;gap:6px;margin-bottom:14px}.field>span{font-weight:700;font-size:15px}
input[type=date],input[type=time]{font:17px var(--text);color:var(--ink);background:var(--bg);border:1px solid var(--rule);border-radius:12px;padding:10px 12px;width:100%}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.chk{display:flex;gap:10px;align-items:center;margin:0 0 14px;font-weight:700}
.ia{background:var(--chip);border-radius:12px;padding:12px 14px;margin:0 0 18px;font-size:15px}
.actions{display:flex;gap:10px}.actions .go{flex:1}
.cancel{font:700 16px var(--text);background:none;color:var(--soft);border:1px solid var(--rule);border-radius:12px;padding:11px 18px;cursor:pointer}
.msg{margin:12px 0 0;font-size:15px;min-height:1.4em}.msg.err{color:var(--red)}
:focus-visible{outline:3px solid var(--teal);outline-offset:2px}
</style></head><body><div class="wrap">
<header><h1>Vídeos largos</h1><button class="reload" id="reload" type="button">Recargar</button></header>
<div class="links" id="links"></div><div id="avisos"></div>
<div class="tabs" role="group" aria-label="Filtrar">
<button type="button" data-f="pend" aria-pressed="true">Por subir<span class="n" id="n-pend"></span></button>
<button type="button" data-f="hecho" aria-pressed="false">Subidos<span class="n" id="n-hecho"></span></button>
<button type="button" data-f="all" aria-pressed="false">Todos<span class="n" id="n-all"></span></button></div>
<ul class="list" id="list" aria-live="polite"></ul></div>
<dialog id="dlg"><form class="sheet" id="form" method="dialog">
<h2>Subir a YouTube</h2><p class="sub" id="dlg-sub"></p>
<label class="chk"><input type="checkbox" id="f-prog" checked> Programar la publicación</label>
<div class="row" id="f-when"><label class="field"><span>Día</span><input type="date" id="f-date"></label>
<label class="field"><span>Hora (España)</span><input type="time" id="f-time" value="19:30"></label></div>
<div class="ia">Se sube <b>privado</b> (y se publica solo a esa hora si lo programas), con miniatura, capítulos y la marca de <b>contenido alterado o sintético</b>. Solo YouTube.</div>
<div class="bar" hidden id="bar"><i id="bar-i"></i></div>
<div class="actions"><button class="cancel" type="button" id="f-cancel">Cancelar</button><button class="go" type="submit" id="f-go">Subir</button></div>
<p class="msg" id="f-msg" role="status"></p></form></dialog>
<script>
const TOKEN="__TOKEN__",$=s=>document.querySelector(s);let data=null,filtro="pend",actual=null,ocupado=false;
const MES=["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const bonita=s=>{if(!s)return"";const[d,h]=s.split("T");const[y,m,dd]=d.split("-");return `${+dd} ${MES[+m-1]} ${y}${h?", "+h:""}`};
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
async function api(p,o={}){const r=await fetch(p,{...o,headers:{"X-Token":TOKEN,"Content-Type":"application/json"}});let j={};try{j=await r.json()}catch{}if(!r.ok)throw new Error(j.error||`Error ${r.status}`);return j}
const hecho=v=>!!v.youtube&&!v.borrado, pend=v=>!v.youtube&&!v.borrado;
const EST={programado:["ok","✓ Subido · se publica el "],procesando:["live","Subido, procesándose"],publicado:["ok","✓ Publicado"],privado:["live","Subido como privado, sin fecha"],privado_atascado:["err","Ya pasó la hora y sigue privado"],no_existe:["err","No está en YouTube"],fallo:["err","La subida falló en YouTube"],rechazado:["err","YouTube lo ha rechazado"],oculto:["live","Subido como oculto"]};
function estadoTxt(v){
  if(v.borrado)return `<p class="st err">Borrado el ${bonita(v.borrado)}${v.youtube_borrado?" (también de YouTube)":""}</p>`;
  if(!v.youtube)return v.completo?`<p class="st">Sin subir</p>`:`<p class="st err">Faltan archivos (hace falta el .mp4 y el .json)</p>`;
  const e=EST[v.yt_estado];let t=e?`<span class="${e[0]}">${e[1]}${e[1].endsWith(" ")?bonita(v.hora):""}</span>`:`<span class="ok">✓ Subido ${v.hora?"· programado para el "+bonita(v.hora):"· privado"}</span>`;
  t+=` <a class="mini" href="https://studio.youtube.com/video/${esc(v.youtube)}/edit" target="_blank" rel="noopener">Abrir en Studio ↗</a>`;
  if(v.aviso)t+=`<br><small class="err">${esc(v.aviso)}</small>`;return `<p class="st">${t}</p>`}
function pintar(){const vs=data.videos;$("#n-pend").textContent=vs.filter(pend).length;$("#n-hecho").textContent=vs.filter(hecho).length;$("#n-all").textContent=vs.length;
  const l=vs.filter(v=>filtro==="all"||(filtro==="pend"?pend(v):hecho(v)));
  if(!l.length){$("#list").innerHTML=filtro==="pend"?`<li class="empty"><b>Nada por subir</b>Cuando el kit de vídeos largos publique uno en el repo (Releases) o metas sus archivos en largos/entrada/, aparecerá aquí.</li>`:`<li class="empty"><b>Ninguno todavía</b></li>`;return}
  $("#list").innerHTML=l.map(v=>`<li class="item"><div class="thumb">${v.mini?`<img src="${esc(v.mini)}" alt="">`:"Sin miniatura"}</div><div class="info">
  <p class="title">${esc(v.titulo)}</p><p class="file">${esc(v.nombre)} · ${v.mb} MB · ${v.origen==="repo"?"del repo":v.origen==="rama"?"del repo (se descarga al subir)":"de largos/entrada"}${v.creado?" · creado "+bonita(v.creado):""}</p>
  ${estadoTxt(v)}<div class="acc">${pend(v)&&v.completo?`<button class="go" type="button" data-n="${esc(v.nombre)}">Subir</button>`:""}
  ${hecho(v)?`<button class="del" type="button" data-b="${esc(v.nombre)}" data-yt="1">Borrar de YouTube</button>`:""}
  ${pend(v)?`<button class="del" type="button" data-b="${esc(v.nombre)}" data-yt="0">Quitar</button>`:""}
  ${v.borrado?`<button class="mini" type="button" data-r="${esc(v.nombre)}">Recuperar</button>`:""}</div></div></li>`).join("")}
function enlaces(){$("#links").innerHTML=`<span class="link"><span class="dot ${data.youtube_ok?"on":""}"></span><b>YouTube</b>${data.youtube_ok?(data.canal?"canal «"+esc(data.canal)+"»":"conectado"):"sin autorizar"}</span>
 <span class="link"><b>Repo</b>${esc(data.repo||"sin configurar")} · Releases</span><span class="link"><b>v${esc(data.version)}</b></span>`;
 $("#avisos").innerHTML=Object.values(data.avisos||{}).map(t=>`<p class="banner">${esc(t)}</p>`).join("")}
async function cargar(){$("#reload").disabled=true;$("#reload").textContent="Cargando…";try{data=await api("/api/estado");enlaces();pintar()}catch(e){$("#list").innerHTML=`<li class="empty"><b>No se pudo cargar</b>${esc(e.message)}</li>`}finally{$("#reload").disabled=false;$("#reload").textContent="Recargar"}}
function manana(){const d=new Date();d.setDate(d.getDate()+1);return d.toISOString().slice(0,10)}
function abrir(n){actual=data.videos.find(v=>v.nombre===n);$("#dlg-sub").textContent=actual.titulo;
  const p=actual.publicar_en?actual.publicar_en.slice(0,16):"";$("#f-date").value=p?p.slice(0,10):manana();$("#f-time").value=p?p.slice(11,16):"19:30";
  $("#f-date").min=new Date().toISOString().slice(0,10);$("#f-msg").textContent="";$("#bar").hidden=true;$("#dlg").showModal()}
$("#f-prog").addEventListener("change",()=>{$("#f-when").style.opacity=$("#f-prog").checked?1:.4});
async function seguir(){while(ocupado){try{const p=await api("/api/progreso");$("#bar-i").style.width=p.pct+"%";$("#f-msg").textContent=`${p.fase}… ${p.pct} %`}catch{}await new Promise(r=>setTimeout(r,1000))}}
$("#form").addEventListener("submit",async ev=>{ev.preventDefault();
  const cuando=$("#f-prog").checked?`${$("#f-date").value}T${$("#f-time").value}`:"";
  ocupado=true;$("#f-go").disabled=true;$("#bar").hidden=false;$("#f-msg").className="msg";seguir();
  try{await api("/api/subir",{method:"POST",body:JSON.stringify({nombre:actual.nombre,cuando})});ocupado=false;$("#dlg").close();await cargar()}
  catch(e){ocupado=false;$("#f-msg").textContent=e.message;$("#f-msg").className="msg err"}finally{$("#f-go").disabled=false}});
$("#f-cancel").addEventListener("click",()=>{if(!ocupado)$("#dlg").close()});$("#dlg").addEventListener("cancel",e=>{if(ocupado)e.preventDefault()});
$("#list").addEventListener("click",async e=>{
  const r=e.target.closest("button[data-r]");if(r){await api("/api/recuperar",{method:"POST",body:JSON.stringify({nombre:r.dataset.r})});await cargar();return}
  const d=e.target.closest("button[data-b]");
  if(d){const v=data.videos.find(x=>x.nombre===d.dataset.b);const yt=d.dataset.yt==="1";
    if(!confirm(yt?`¿Borrar «${v.titulo}» de YouTube? No se puede deshacer.`:`¿Quitar «${v.titulo}» del panel?`))return;
    const arch=confirm("¿Borrar también sus archivos de este ordenador?");
    d.disabled=true;d.textContent="Borrando…";
    try{await api("/api/borrar",{method:"POST",body:JSON.stringify({nombre:v.nombre,archivos:arch})});await cargar()}
    catch(err){alert(err.message);d.disabled=false;d.textContent=yt?"Borrar de YouTube":"Quitar"}return}
  const b=e.target.closest("button[data-n]");if(b)abrir(b.dataset.n)});
document.querySelectorAll(".tabs button").forEach(b=>b.addEventListener("click",()=>{filtro=b.dataset.f;document.querySelectorAll(".tabs button").forEach(x=>x.setAttribute("aria-pressed",x===b));if(data)pintar()}));
$("#reload").addEventListener("click",cargar);cargar();
</script></body></html>"""

def listar(cfg):
    vs, err = videos(cfg)
    avisos = dict(err)
    ok = bool(cfg.get("youtube_refresh_token"))
    canal = ""
    if ok:
        try: canal = M.canal_autorizado(cfg)[1]; comprobar(cfg, vs)
        except Exception as e: avisos["youtube"] = "No pude leer el canal: " + str(e)[:200]
    else:
        avisos["youtube"] = "Falta autorizar YouTube: copia el config.json del móvil o ejecuta python3 publicar_largo.py auth-youtube."
    return {"videos": vs, "youtube_ok": ok, "canal": canal, "repo": cfg.get("github_repo"), "version": VERSION, "avisos": avisos}

def web(puerto=8766):
    token = secrets.token_urlsafe(18)
    class H(BaseHTTPRequestHandler):
        def _host(self): return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")
        def _auth(self): return self._host() and secrets.compare_digest(self.headers.get("X-Token", ""), token)
        def _json(self, code, d):
            b = json.dumps(d, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/":
                if not self._host() or urllib.parse.parse_qs(u.query).get("t", [""])[0] != token:
                    self.send_response(403); self.end_headers(); self.wfile.write(b"Abre la URL que muestra el script."); return
                b = PANEL.replace("__TOKEN__", token).encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
            if u.path.startswith("/f/") and self._host():           # miniaturas de largos/entrada
                ruta = os.path.realpath(os.path.join(CARPETA, urllib.parse.unquote(u.path[3:])))
                if ruta.startswith(os.path.realpath(CARPETA)) and os.path.isfile(ruta):
                    with open(ruta, "rb") as f: b = f.read()
                    self.send_response(200); self.send_header("Content-Type", "image/png" if ruta.endswith(".png") else "image/jpeg")
                    self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
            if u.path == "/api/estado":
                if not self._auth(): return self._json(403, {"error": "token"})
                try: return self._json(200, listar(cfg_actual()))
                except Exception as e: return self._json(500, {"error": f"{type(e).__name__}: {e}"})
            if u.path == "/api/progreso":
                if not self._auth(): return self._json(403, {"error": "token"})
                return self._json(200, _prog)
            self.send_response(404); self.end_headers()
        def do_POST(self):
            if self.path not in ("/api/subir", "/api/borrar", "/api/recuperar") or not self._auth(): return self._json(403, {"error": "token"})
            p = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
            if self.path != "/api/subir":
                try:
                    r = borrar(cfg_actual(), p["nombre"], bool(p.get("archivos"))) if self.path == "/api/borrar" else recuperar(p["nombre"])
                    print(self.path[5:], p["nombre"]); return self._json(200, r)
                except SystemExit as e: return self._json(400, {"error": str(e)})
            if not _lock.acquire(blocking=False): return self._json(409, {"error": "Ya hay una subida en marcha"})
            try:
                r = subir(cfg_actual(), p["nombre"], p.get("cuando", ""))
                print(f"Subido {p['nombre']} → https://youtu.be/{r['youtube']}"); return self._json(200, r)
            except SystemExit as e:
                _prog.update(error=str(e)); print("ERROR:", e); return self._json(400, {"error": str(e)})
            except Exception as e:
                return self._json(500, {"error": f"{type(e).__name__}: {e}"})
            finally: _lock.release()
        def log_message(self, *a): pass
    try: srv = ThreadingHTTPServer(("127.0.0.1", puerto), H)
    except OSError: srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={token}"
    print(f"publicar_largo.py v{VERSION}\nPanel en marcha (Ctrl+C para cerrarlo):\n\n{url}\n")
    threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)), daemon=True).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("Panel cerrado.")

def texto():
    d = listar(cfg_actual())
    for k, t in d["avisos"].items(): print("AVISO:", t)
    if not d["videos"]: print("No hay vídeos largos (ni en el repo ni en largos/entrada/)."); return
    for v in d["videos"]:
        s = f"subido → https://youtu.be/{v['youtube']} ({v.get('yt_estado') or v.get('hora') or 'privado'})" if v.get("youtube") else ("pendiente" if v["completo"] else "faltan archivos")
        print(f"{v['nombre']:<34} {v['mb']:>5} MB  {s}" + ("  (en el repo: se descarga al subir)" if v.get("origen") == "rama" and not v.get("youtube") else ""))

def prueba():
    cfg = cfg_actual(); bien = True
    print(f"config.json: {M.CFG}")
    try:
        if not cfg.get("youtube_refresh_token"):
            print("YouTube: SIN AUTORIZAR → python3 publicar_largo.py auth-youtube"); bien = False
        else:
            nombre = M.canal_autorizado(cfg)[1]
            if nombre: print("YouTube: canal «%s»" % nombre)
            else:
                bien = False
                print("YouTube: la cuenta autorizada NO tiene canal. Repite  python3 publicar_largo.py auth-youtube  y en Google\n"
                      "         elige el canal Dato Loco (sale aparte, con su foto), no tu cuenta personal.")
    except BaseException as e: print("YouTube: ERROR", str(e)[:300]); bien = False
    try: print(f"Repo {cfg.get('github_repo')}: {len(releases(cfg['github_repo']))} vídeo(s) en Releases y {len(rama(cfg['github_repo']))} en la rama «{RAMA}»")
    except BaseException as e: print("Repo: ERROR", str(e)[:300]); bien = False
    os.makedirs(ENTRADA, exist_ok=True); print("Carpeta para vídeos que te lleguen por el chat:", ENTRADA)
    print("Todo listo: abre el panel con  python3 publicar_largo.py" if bien else "Arregla lo de arriba y repite la prueba.")

def _ver(v): return tuple(int(x) for x in str(v).split(".") if x.isdigit())

def auto_actualizar():
    """Si la rama «largos» del repo trae una versión más nueva de este script, la instala y vuelve a arrancar."""
    cfg = cfg_actual()
    if cfg.get("auto_actualizar") is False or os.environ.get("PUBLICAR_LARGO_ACTUALIZADO"): return
    repo = cfg.get("github_repo", "")
    if not repo or "TU_USUARIO" in repo: return
    url = f"https://raw.githubusercontent.com/{repo}/{RAMA}/publicar_largo.py"
    try:
        if M.usar_curl:
            r = subprocess.run([_curl(), "-sSL", "--fail", "--max-time", "20", url], capture_output=True)
            if r.returncode != 0: return
            nuevo = r.stdout
        else:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": M.UA}), timeout=20) as r: nuevo = r.read()
        txt = nuevo.decode("utf-8")
        v = next((l.split("=")[1].strip().strip('"') for l in txt.splitlines() if l.startswith("VERSION =")), "")
        if not v or _ver(v) <= _ver(VERSION): return
        compile(txt, "publicar_largo.py", "exec")                       # que sea un script válido antes de tocar nada
    except Exception:
        return                                                          # sin conexión o raro: sigue con la versión actual
    yo = os.path.abspath(__file__)
    shutil.copy2(yo, os.path.join(AQUI, "publicar_largo.anterior.py"))
    tmp = yo + ".nuevo"
    with open(tmp, "wb") as f: f.write(nuevo)
    os.replace(tmp, yo)
    print(f"publicar_largo.py actualizado: {VERSION} → {v} (el anterior queda en publicar_largo.anterior.py)")
    os.environ["PUBLICAR_LARGO_ACTUALIZADO"] = "1"
    sys.exit(subprocess.call([sys.executable, yo] + sys.argv[1:]))

if __name__ == "__main__":
    auto_actualizar()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "web"
    {"borrar": lambda: (print(borrar(cfg_actual(), sys.argv[2], "--archivos" in sys.argv)) if len(sys.argv) > 2 else print("Uso: python3 publicar_largo.py borrar <nombre> [--archivos]")),
     "web": web, "estado": texto, "prueba": prueba, "auth-youtube": lambda: _M.auth_youtube(cfg_actual())}.get(cmd, lambda: print(__doc__))()
