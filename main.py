"""
Quiz #4 - NoSQL (llave-valor con Redis)

Escenario: una plataforma de streaming de videos necesita
  1. manejar sesiones de usuario que expiran solas,
  2. contar las reproducciones de cada video,
  3. mostrar un ranking de los videos mas vistos,
  4. guardar en cache una consulta lenta al catalogo.

Todas estas tareas se resuelven con Redis, que guarda pares llave -> valor
en memoria y ofrece operaciones rapidas sobre ellos.
"""

import json
import time
import uuid

import redis

# ---------------------------------------------------------------------------
# Conexion
# ---------------------------------------------------------------------------
# decode_responses=True hace que Redis devuelva texto (str) y no bytes.
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

SESION_TTL = 30 * 60   # una sesion dura 30 minutos
CACHE_TTL = 60         # el cache del catalogo dura 60 segundos


# ---------------------------------------------------------------------------
# 1. Sesiones de usuario: SET con expiracion (TTL)
# ---------------------------------------------------------------------------
def crear_sesion(usuario, ttl=SESION_TTL):
    """Guarda sesion:<token> -> usuario. Redis la borra solo cuando vence el TTL."""
    token = uuid.uuid4().hex
    r.set(f"sesion:{token}", usuario, ex=ttl)
    return token


def obtener_usuario(token):
    """Devuelve el usuario dueno de la sesion, o None si no existe o ya expiro."""
    return r.get(f"sesion:{token}")


def cerrar_sesion(token):
    r.delete(f"sesion:{token}")


# ---------------------------------------------------------------------------
# 2 y 3. Contador de reproducciones y ranking: INCR y ZINCRBY
# ---------------------------------------------------------------------------
def registrar_reproduccion(video_id):
    """Suma una vista. INCR es atomico: dos usuarios a la vez no se pisan."""
    r.incr(f"vistas:{video_id}")
    r.zincrby("ranking:videos", 1, video_id)


def vistas(video_id):
    return int(r.get(f"vistas:{video_id}") or 0)


def top_videos(n=3):
    """Los n videos mas vistos, de mayor a menor."""
    return r.zrevrange("ranking:videos", 0, n - 1, withscores=True)


# ---------------------------------------------------------------------------
# 4. Cache de una consulta lenta: patron cache-aside con GET / SET + TTL
# ---------------------------------------------------------------------------
def consultar_catalogo_lento(genero):
    """Simula una consulta pesada a otra base de datos (tarda 0.5 s)."""
    time.sleep(0.5)
    catalogo = {
        "accion": ["Rapido y Curioso", "Mision Posible"],
        "comedia": ["Dos Tontos", "La Mascara"],
    }
    return catalogo.get(genero, [])


def catalogo(genero):
    """Primero busca en Redis; si no esta, consulta lo lento y lo guarda."""
    clave = f"cache:catalogo:{genero}"
    guardado = r.get(clave)
    if guardado is not None:
        return json.loads(guardado), True            # acierto de cache
    datos = consultar_catalogo_lento(genero)
    r.set(clave, json.dumps(datos), ex=CACHE_TTL)    # el valor se guarda como texto JSON
    return datos, False                              # fallo de cache


# ---------------------------------------------------------------------------
# Utilidades de la demo
# ---------------------------------------------------------------------------
def limpiar():
    """Borra solo las llaves de esta demo, sin tocar otras cosas de Redis."""
    for patron in ("sesion:*", "vistas:*", "cache:*"):
        for clave in r.scan_iter(patron):
            r.delete(clave)
    r.delete("ranking:videos")


def demo():
    limpiar()

    print("=== 1. Sesiones con expiracion automatica ===")
    token = crear_sesion("ana")
    print(f"Sesion creada: {token[:8]}... -> usuario: {obtener_usuario(token)}")
    print(f"Tiempo de vida restante: {r.ttl(f'sesion:{token}')} segundos")
    corta = crear_sesion("luis", ttl=2)
    print(f"Sesion corta de 'luis' (2 s): {obtener_usuario(corta)}")
    time.sleep(3)
    print(f"Despues de 3 s: {obtener_usuario(corta)}  (Redis la borro solo)")
    cerrar_sesion(token)
    print(f"Despues de cerrar la sesion de ana: {obtener_usuario(token)}")

    print("\n=== 2. Contador de reproducciones ===")
    for video in ["v1", "v2", "v1", "v3", "v1", "v2"]:
        registrar_reproduccion(video)
    for video in ["v1", "v2", "v3"]:
        print(f"Vistas de {video}: {vistas(video)}")

    print("\n=== 3. Ranking de los mas vistos ===")
    for puesto, (video, puntos) in enumerate(top_videos(3), start=1):
        print(f"{puesto}. {video} con {int(puntos)} vistas")

    print("\n=== 4. Cache de una consulta lenta ===")
    for intento in (1, 2):
        inicio = time.perf_counter()
        datos, acierto = catalogo("accion")
        ms = (time.perf_counter() - inicio) * 1000
        origen = "CACHE (Redis)" if acierto else "consulta lenta"
        print(f"Intento {intento}: {datos} en {ms:.1f} ms, origen: {origen}")

    limpiar()


if __name__ == "__main__":
    try:
        r.ping()
    except redis.exceptions.ConnectionError:
        raise SystemExit(
            "No se pudo conectar a Redis en localhost:6379.\n"
            "Inicia el servidor con:  docker compose up -d"
        )
    demo()
