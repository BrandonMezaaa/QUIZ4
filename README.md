# Quiz #4: NoSQL con Redis (llave-valor)

**CE 2103 - Algoritmos y Estructuras de Datos II**

## Tipo de base de datos elegido

**Llave-valor**, usando **Redis** desde un programa en **Python**.

Una base llave-valor funciona como un diccionario gigante: cada dato se guarda bajo una llave única y se recupera pidiendo esa llave. No tiene tablas, columnas ni relaciones.

## Escenario: una plataforma de streaming de videos

Una plataforma de videos tiene cuatro necesidades que se repiten miles de veces por segundo:

| # | Problema | Qué se necesita |
|---|---|---|
| 1 | **Sesiones de usuario** | Saber rápido quién es el usuario que hace cada petición, y que la sesión se cierre sola a los 30 minutos. |
| 2 | **Contar reproducciones** | Sumar una vista cada vez que alguien reproduce un video, sin perder cuentas cuando muchos usuarios lo hacen a la vez. |
| 3 | **Ranking de más vistos** | Mostrar el top de videos siempre actualizado. |
| 4 | **Consultas lentas al catálogo** | Evitar repetir una consulta pesada cuando miles de usuarios piden lo mismo. |

Ninguna de estas necesidades requiere relaciones entre tablas ni consultas complejas. Siempre se sabe la llave de lo que se busca (el token de la sesión, el id del video, el género del catálogo). Ese es el caso ideal para una base llave-valor.

## Por qué llave-valor y no una base relacional

- **Acceso directo por llave.** Buscar una sesión es `GET sesion:<token>`, una operación de costo constante O(1). No hay que recorrer tablas ni armar `JOIN`.
- **Expiración automática (TTL).** Redis borra solo las llaves vencidas. En SQL habría que programar un proceso que limpie las sesiones viejas.
- **Contadores atómicos.** `INCR` suma uno sin que dos usuarios simultáneos se pisen. En SQL hay que usar transacciones o bloqueos.
- **Velocidad.** Redis guarda los datos en memoria, por eso responde en fracciones de milisegundo.
- **Sin esquema.** No hay que definir tablas antes de guardar. Cada llave puede tener un valor distinto.

## Cómo se usó Redis para cada problema

| Problema | Comando de Redis | Función en `src/main.py` | Complejidad |
|---|---|---|---|
| Crear sesión con vencimiento | `SET sesion:<token> <usuario> EX 1800` | `crear_sesion()` | O(1) |
| Consultar o cerrar sesión | `GET` / `DEL` | `obtener_usuario()`, `cerrar_sesion()` | O(1) |
| Contar una reproducción | `INCR vistas:<video>` | `registrar_reproduccion()` | O(1) |
| Ranking de más vistos | `ZINCRBY ranking:videos 1 <video>` y `ZREVRANGE` | `registrar_reproduccion()`, `top_videos()` | O(log n) y O(log n + k), con k = videos pedidos |
| Cache del catálogo | `GET` y luego `SET cache:catalogo:<género> <json> EX 60` | `catalogo()` | O(1) |

Detalles de cada uno:

1. **Sesiones.** La llave es `sesion:<token>` y el valor es el nombre del usuario. Al crearla se le pone un TTL de 30 minutos, así que Redis la elimina sin que el programa haga nada.
2. **Contador.** La llave `vistas:<video>` guarda un número. Cada reproducción hace `INCR`.
3. **Ranking.** Redis permite que un valor sea un *conjunto ordenado* (sorted set), donde cada elemento tiene una puntuación. Con `ZINCRBY` se suma una vista y el conjunto se mantiene ordenado, así que obtener el top es una sola consulta.
4. **Cache.** Se usa el patrón *cache-aside*: primero se busca en Redis; si no está, se hace la consulta lenta y se guarda el resultado (como texto JSON) con un TTL de 60 segundos. Así la siguiente petición ya no repite la consulta pesada.

## Cómo ejecutarlo

Requisitos: Python 3 y Docker (para levantar Redis).

```bash
# 1. Levantar Redis
docker compose up -d

# 2. Instalar el cliente de Python
pip install -r requirements.txt

# 3. Ejecutar la demostración
python src/main.py
```

Para apagar Redis al terminar: `docker compose down`.

## Salida de ejemplo

Esta es la salida real de una ejecución (los milisegundos pueden variar):

```text
=== 1. Sesiones con expiracion automatica ===
Sesion creada: 6936ad41... -> usuario: ana
Tiempo de vida restante: 1800 segundos
Sesion corta de 'luis' (2 s): luis
Despues de 3 s: None  (Redis la borro solo)
Despues de cerrar la sesion de ana: None

=== 2. Contador de reproducciones ===
Vistas de v1: 3
Vistas de v2: 2
Vistas de v3: 1

=== 3. Ranking de los mas vistos ===
1. v1 con 3 vistas
2. v2 con 2 vistas
3. v3 con 1 vistas

=== 4. Cache de una consulta lenta ===
Intento 1: ['Rapido y Curioso', 'Mision Posible'] en 500.7 ms, origen: consulta lenta
Intento 2: ['Rapido y Curioso', 'Mision Posible'] en 0.3 ms, origen: CACHE (Redis)
```

Qué muestra cada bloque:

1. La sesión de `luis` dura 2 segundos y después de 3 segundos ya no existe, porque Redis la borró sola.
2. Las vistas se acumulan correctamente por video.
3. El ranking sale ordenado de mayor a menor sin que el programa tenga que ordenar nada.
4. La primera consulta tarda unos 500 ms (simula una base lenta) y la segunda, servida desde Redis, tarda menos de 1 ms.

## Limitaciones

Una base llave-valor **no es buena** cuando se necesitan consultas del tipo "todos los videos del género X con más de 100 vistas y subidos este mes" o relaciones entre muchos datos. Para eso conviene una base relacional o de documentos. En una plataforma real, Redis acompaña a la base principal (donde viven los usuarios, videos y pagos) y se encarga de lo que requiere velocidad.

Además, Redis guarda los datos en memoria. Puede escribirlos a disco de forma periódica, pero por diseño es mejor para datos temporales o que se pueden reconstruir (sesiones, contadores, cache).

## Estructura del repositorio

```text
.
├── README.md
├── docker-compose.yml     # levanta Redis
├── requirements.txt       # cliente redis-py
├── salida_ejemplo.txt     # salida real de la ejecución
└── src/
    └── main.py            # programa de la demostración
```
