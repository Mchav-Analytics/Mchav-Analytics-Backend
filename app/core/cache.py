# app/core/cache.py
# Módulo de almacenamiento en caché en memoria de corto ciclo (ShortLivedCache)
# Provee almacenamiento en caché thread-safe con expiración automática basada en Time-To-Live (TTL)

import threading
from datetime import datetime, timedelta
from typing import Any, Optional

class ShortLivedCache:
    """
    Caché thread-safe en memoria para almacenar respuestas temporales de la API REST de Jira.
    Evita llamadas repetidas a la API externa en periodos breves (TTL por defecto: 60 segundos).
    """

    def __init__(self, ttl_seconds: int = 60):
        """Inicializa el almacén en memoria, la duración de TTL y el cerrojo (Lock) de concurrencia."""
        self._store = {}                   # Diccionario interno de almacenamiento: {key: (data, expires_at)}
        self._ttl = ttl_seconds            # Tiempo de vida en segundos de las entradas
        self._lock = threading.Lock()      # Cerrojo de hilos para operaciones thread-safe

    def get(self, key: str) -> Optional[Any]:
        """
        Recupera un valor de la caché por su clave.
        Verifica si la entrada ha expirado; de ser así, la elimina del almacén y retorna None.
        """
        with self._lock:                   # Garantizar acceso exclusivo de lectura/escritura
            if key in self._store:
                data, expires_at = self._store[key]
                if datetime.now() > expires_at:
                    del self._store[key]    # Eliminar entrada caducada
                    return None
                return data                 # Retornar datos válidos
            return None

    def set(self, key: str, value: Any) -> None:
        """
        Guarda o actualiza un valor en la caché asociado a una clave, calculando la fecha límite de expiración.
        """
        with self._lock:                   # Garantizar exclusión mutua durante la modificación
            expires_at = datetime.now() + timedelta(seconds=self._ttl)
            self._store[key] = (value, expires_at)

    def clear(self) -> None:
        """Limpia completamente todas las entradas del almacén en memoria."""
        with self._lock:
            self._store.clear()
