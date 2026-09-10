"""Sistema de gestión de turnos (tickets) para una sucursal bancaria.

Contiene el modelo de datos (`Ticket`) y la lógica de colas (`BranchQueue`).
La interacción por consola vive en `cli.py`, de modo que esta capa puede
reutilizarse desde una API, tests u otra interfaz sin cambios.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

#: Tipos de servicio válidos. El orden define el orden de presentación.
SERVICE_TYPES = ("deposito", "retiro", "gestion_cuenta")


class BranchQueueError(Exception):
    """Error base del módulo, para poder capturarlo todo desde la CLI."""


class InvalidServiceTypeError(BranchQueueError, ValueError):
    """El tipo de servicio solicitado no existe."""


class EmptyQueueError(BranchQueueError, LookupError):
    """Se intentó atender una cola que no tiene clientes esperando."""


@dataclass(frozen=True)
class Ticket:
    """Un turno emitido para un cliente.

    `number` es globalmente secuencial: no se reinicia por tipo de servicio,
    así que dos clientes nunca comparten número aunque estén en colas distintas.
    """

    number: int
    client_name: str
    service_type: str
    issued_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        hora = self.issued_at.strftime("%H:%M:%S")
        return f"#{self.number:03d} {self.client_name} ({self.service_type}) — {hora}"


class BranchQueue:
    """Gestiona una cola independiente por tipo de servicio.

    Mantiene un contador global de tickets y un `threading.Lock` que hace
    atómicas las operaciones de emisión y llamada (ver DESIGN.md).
    """

    def __init__(self, service_types=SERVICE_TYPES) -> None:
        self._service_types = tuple(service_types)
        self._queues: Dict[str, List[Ticket]] = {s: [] for s in self._service_types}
        self._next_number = 1
        self._lock = threading.Lock()

    @property
    def service_types(self) -> tuple:
        return self._service_types

    def _validate(self, service_type: str) -> str:
        """Normaliza y valida un tipo de servicio, o lanza un error claro."""
        clave = str(service_type).strip().lower()
        if clave not in self._queues:
            validos = ", ".join(self._service_types)
            raise InvalidServiceTypeError(
                f"Tipo de servicio inválido: {service_type!r}. Válidos: {validos}."
            )
        return clave

    # --- Operaciones de cola -------------------------------------------------

    def issue_ticket(self, client_name: str, service_type: str) -> Ticket:
        """Emite un ticket y lo encola en la cola del servicio correspondiente."""
        clave = self._validate(service_type)
        nombre = str(client_name).strip()
        if not nombre:
            raise BranchQueueError("El nombre del cliente no puede estar vacío.")

        with self._lock:
            ticket = Ticket(
                number=self._next_number,
                client_name=nombre,
                service_type=clave,
                issued_at=datetime.now(),
            )
            self._next_number += 1
            self._queues[clave].append(ticket)
        return ticket

    def call_next(self, service_type: str) -> Ticket:
        """Desencola y devuelve el siguiente cliente del servicio dado.

        Lanza `EmptyQueueError` si no hay nadie esperando; la CLI lo captura,
        de modo que una cola vacía nunca rompe el programa.
        """
        clave = self._validate(service_type)
        with self._lock:
            cola = self._queues[clave]
            if not cola:
                raise EmptyQueueError(
                    f"No hay clientes esperando en la cola de '{clave}'."
                )
            # La mutación (retirar el ticket) ocurre dentro del lock y antes
            # de devolverlo: dos agentes nunca reciben el mismo cliente.
            return cola.pop(0)

    def peek_next(self, service_type: str) -> Optional[Ticket]:
        """Devuelve el siguiente cliente sin retirarlo, o `None` si no hay."""
        clave = self._validate(service_type)
        with self._lock:
            cola = self._queues[clave]
            return cola[0] if cola else None

    def list_waiting(self) -> Dict[str, List[Ticket]]:
        """Devuelve {tipo_de_servicio: lista ordenada de tickets en espera}."""
        with self._lock:
            return {s: list(cola) for s, cola in self._queues.items()}

    def stats(self) -> Dict[str, int]:
        """Devuelve el número de clientes por servicio más la clave 'total'."""
        with self._lock:
            resumen = {s: len(cola) for s, cola in self._queues.items()}
            resumen["total"] = sum(resumen.values())
        return resumen
