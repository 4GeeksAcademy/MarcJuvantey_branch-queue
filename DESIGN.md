# Notas de diseño

## Por qué una cola separada por tipo de servicio

Con **una única cola compartida**, `call_next("retiro")` tendría que recorrer la
cola desde el frente buscando el primer ticket cuyo `service_type` coincida y
después eliminarlo del medio de la estructura. Eso es O(n) sobre el número de
clientes en espera, y el peor caso es justo el que más duele: una sucursal con
muchos depósitos encolados y un solo agente de retiros que debe saltarse a todos
ellos en cada llamada.

Con **una cola por tipo de servicio** el siguiente cliente de un servicio es
siempre el elemento del frente de su propia cola, así que `call_next` y
`peek_next` son O(1): no hay búsqueda ni filtrado, solo un `popleft()`. Cada
cola es un `collections.deque` precisamente por eso — sobre una `list`, sacar
del frente con `pop(0)` obliga a desplazar todos los elementos restantes y
volvería a ser O(n), perdiendo la ventaja. Además:

- El orden FIFO por servicio queda garantizado por la estructura misma, no por
  un filtro que hay que recordar aplicar bien.
- `stats()` y `list_waiting()` salen directos de cada cola, sin agrupar nada.
- Cada agente toca solo la cola de su servicio, lo que reduce la contención
  cuando varios trabajan a la vez.

El precio es un diccionario de colas en lugar de una lista, y un contador
**global** de tickets aparte (`_next_number`) para que la numeración siga siendo
única en toda la sucursal aunque las colas estén separadas.

## Dos agentes del mismo servicio llamando a la vez

Si dos agentes ejecutan `call_next("retiro")` simultáneamente, la operación
"leer el frente de la cola" y "retirarlo de la cola" no es atómica por sí sola.
El intercalado peligroso es:

1. Agente A lee el frente → ticket #7.
2. Agente B lee el frente → ticket #7 (todavía no se ha retirado).
3. A retira el frente; B retira el frente.

Resultado: **el mismo cliente #7 es llamado dos veces** y el cliente #8 se pierde
o se salta su turno.

**La mutación que debe ocurrir primero es la retirada del ticket de la cola.**
Es decir: comprobar que la cola no está vacía, extraer el ticket (mutando el
estado) y solo después devolverlo al agente para anunciarlo. La lectura y la
extracción tienen que formar una sola operación indivisible.

En este código eso se consigue con un `threading.Lock` en `BranchQueue`: la
comprobación de cola vacía y el `popleft()` ocurren dentro del mismo bloque `with
self._lock`, de modo que el segundo agente que llegue encuentra la cola ya
modificada y recibe el ticket siguiente (o un `EmptyQueueError` si no queda
nadie). El mismo lock protege `issue_ticket`, para que dos emisiones concurrentes
no lean el mismo valor de `_next_number` y acaben repartiendo números
duplicados.

En un sistema distribuido (varias terminales contra un servidor) el equivalente
sería que la extracción fuese una operación atómica del almacén: un `UPDATE ...
RETURNING` con bloqueo de fila, un `BRPOP` de Redis, o una transacción con
reintento — nunca un "leer, luego borrar" en dos pasos separados.

## Otras decisiones

- `call_next` **lanza** `EmptyQueueError` cuando no hay nadie esperando, tal y
  como pide el enunciado; `peek_next` devuelve `None`, porque consultar una cola
  vacía es una pregunta legítima y no un error. La CLI captura
  `BranchQueueError` en el bucle del menú, así que ninguno de los dos casos
  rompe el programa.
- Los tipos de servicio se normalizan (`strip().lower()`) antes de validarse, y
  un tipo desconocido se rechaza en la emisión con un mensaje que enumera los
  válidos.
- `Ticket` es un dataclass congelado (`frozen=True`): un turno ya emitido es un
  hecho histórico y no debería mutarse.
- `list_waiting()` devuelve copias (`list(cola)`), para que quien consulte no
  pueda alterar los `deque` internos por accidente.
- Solo biblioteca estándar: `collections.deque` para las colas, `datetime` para
  la marca de tiempo del ticket, `dataclasses` para el modelo y `threading` para
  el lock. Ninguna dependencia externa.
