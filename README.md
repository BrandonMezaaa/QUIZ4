# Quiz #4: NoSQL con Redis (Llave-Valor)

**Institución:** Tecnológico de Costa Rica  
**Curso:** Algoritmos y Estructuras de Datos II (CE 2103)  
**Tema:** Base de datos NoSQL - Tipo Llave-Valor (Redis)

---

## 1. Escenario (Contexto del problema)
Se simula el backend de una **plataforma de streaming de videos**, la cual enfrenta altas concurrencias y requiere operaciones sumamente rápidas que no se benefician de las complejidades de una base de datos relacional tradicional (como tablas normalizadas o `JOIN`s pesados). 

Las necesidades específicas del escenario son:
1. **Gestión de sesiones de usuario:** Validar tokens de usuario de forma instantánea y permitir que expiren automáticamente tras un tiempo de inactividad.
2. **Contadores de reproducciones:** Registrar vistas concurrentes en tiempo real para los videos sin generar bloqueos de escritura.
3. **Ranking de videos más vistos:** Mantener un top dinámico actualizado al instante.
4. **Caché de consultas pesadas:** Evitar cuellos de botella al consultar catálogos repetitivos.

---

## 2. Cómo se usó Redis para resolverlo

Se utilizó **Redis** (modelo llave-valor) debido a su almacenamiento en memoria y su alto rendimiento con operaciones de tiempo constante $O(1)$.

| Necesidad | Estructura / Comando en Redis | Explicación de uso |
| :--- | :--- | :--- |
| **Sesiones** | `SET sesion:<token> <usuario> EX 1800` | Almacena la llave del token apuntando al usuario. Usa **TTL automático** (`EX`), eliminando la sesión a los 30 minutos sin intervención manual. |
| **Vistas** | `INCR vistas:<video>` | Incrementa de forma atómica y segura el contador de reproducciones de un video sin riesgo de condiciones de carrera. |
| **Ranking** | `ZINCRBY ranking:videos 1 <video>` | Utiliza un *Sorted Set* (conjunto ordenado) para sumar puntajes y mantener un ranking ordenado automáticamente. |
| **Caché** | `SETEX cache:catalogo:<genero> 60 <datos>` | Almacena el resultado JSON de consultas costosas por 60 segundos aplicando el patrón *cache-aside*. |

---

## 3. Instrucciones de ejecución

### Requisitos previos
* Python 3
* Docker y Docker Compose

### Pasos
```bash
# 1. Levantar el servicio de Redis
docker compose up -d

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la demostración
python src/main.py
