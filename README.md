# MarcJuvantey_branch-queue

Sistema de turnos para una sucursal, con una cola independiente por tipo de
servicio (`deposito`, `retiro`, `gestion_cuenta`) y numeración global de tickets.

## Uso

```bash
python3 cli.py
```

## Archivos

- [branch_queue.py](branch_queue.py) — modelo `Ticket` y lógica `BranchQueue`
  (`issue_ticket`, `call_next`, `peek_next`, `list_waiting`, `stats`).
- [cli.py](cli.py) — menú de texto en bucle.
- [DESIGN.md](DESIGN.md) — notas de diseño: por qué colas separadas y qué pasa
  con dos agentes llamando a la vez.

## Ejemplo

```python
from branch_queue import BranchQueue

q = BranchQueue()
q.issue_ticket("Ana", "deposito")   # -> #001
q.issue_ticket("Beto", "retiro")    # -> #002 (numeración global)
q.call_next("deposito")             # -> Ticket #001 de Ana
q.stats()                           # {'deposito': 0, 'retiro': 1, ..., 'total': 1}
```
