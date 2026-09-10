"""Menú de texto para operar la cola de turnos de la sucursal.

Uso:
    python cli.py
"""

from __future__ import annotations

from branch_queue import SERVICE_TYPES, BranchQueue, BranchQueueError

MENU = """
==========================================
  SUCURSAL — GESTIÓN DE TURNOS
==========================================
1) Emitir un nuevo ticket
2) Llamar al siguiente cliente
3) Ver la lista de espera
4) Ver estadísticas
5) Salir
"""


def pedir_servicio(prompt: str = "Tipo de servicio") -> str:
    """Pide un tipo de servicio, aceptando el número de la lista o su nombre."""
    print(f"\n{prompt}:")
    for i, servicio in enumerate(SERVICE_TYPES, start=1):
        print(f"  {i}) {servicio}")
    respuesta = input("> ").strip()
    if respuesta.isdigit() and 1 <= int(respuesta) <= len(SERVICE_TYPES):
        return SERVICE_TYPES[int(respuesta) - 1]
    return respuesta  # BranchQueue valida y avisa si no existe


def emitir(queue: BranchQueue) -> None:
    nombre = input("\nNombre del cliente: ").strip()
    servicio = pedir_servicio()
    ticket = queue.issue_ticket(nombre, servicio)
    print(f"\n✔ Ticket emitido: {ticket}")


def llamar(queue: BranchQueue) -> None:
    servicio = pedir_servicio("¿Para qué servicio llama?")
    ticket = queue.call_next(servicio)
    print(f"\n📢 Atendiendo a {ticket.client_name} — ticket #{ticket.number:03d}")


def ver_espera(queue: BranchQueue) -> None:
    print("\n--- LISTA DE ESPERA ---")
    for servicio, tickets in queue.list_waiting().items():
        print(f"\n{servicio} ({len(tickets)} en espera):")
        if not tickets:
            print("  (vacía)")
        for posicion, ticket in enumerate(tickets, start=1):
            print(f"  {posicion}. {ticket}")


def ver_stats(queue: BranchQueue) -> None:
    resumen = queue.stats()
    print("\n--- ESTADÍSTICAS ---")
    for servicio in SERVICE_TYPES:
        print(f"  {servicio}: {resumen[servicio]}")
    print(f"  TOTAL: {resumen['total']}")


def main() -> None:
    queue = BranchQueue()
    acciones = {"1": emitir, "2": llamar, "3": ver_espera, "4": ver_stats}

    while True:
        print(MENU)
        opcion = input("Elige una opción: ").strip()

        if opcion == "5":
            print("\nHasta luego.")
            return
        if opcion not in acciones:
            print("\n⚠ Opción no válida, elige del 1 al 5.")
            continue

        try:
            acciones[opcion](queue)
        except BranchQueueError as exc:
            # Cola vacía o servicio inválido: se informa y el menú continúa.
            print(f"\n⚠ {exc}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n\nHasta luego.")
