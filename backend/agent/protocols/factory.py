"""
ProtocolFactory — maps HRRP condition keys to protocol instances.

Adding a new condition: create a BaseProtocol subclass,
then register it here. Nothing else needs to change.
"""
from exceptions import ProtocolNotFoundError
from .base import BaseProtocol
from .copd import COPDProtocol
from .heart_failure import HeartFailureProtocol
from .orthopedic import OrthopedicProtocol
from .pneumonia import PneumoniaProtocol


class ProtocolFactory:
    _registry: dict[str, type[BaseProtocol]] = {
        HeartFailureProtocol.condition_key: HeartFailureProtocol,
        PneumoniaProtocol.condition_key: PneumoniaProtocol,
        COPDProtocol.condition_key: COPDProtocol,
        OrthopedicProtocol.condition_key: OrthopedicProtocol,
    }

    @classmethod
    def get(cls, condition_key: str | None) -> BaseProtocol:
        """Return the protocol for the given condition, falling back to base."""
        if condition_key and condition_key in cls._registry:
            return cls._registry[condition_key]()
        # General post-discharge protocol for non-HRRP conditions
        return BaseProtocol()  # type: ignore[abstract]  # uses default checklist

    @classmethod
    def register(cls, protocol_class: type[BaseProtocol]) -> None:
        """Register a new protocol at runtime (useful for testing / plugins)."""
        cls._registry[protocol_class.condition_key] = protocol_class

    @classmethod
    def supported_conditions(cls) -> list[str]:
        return list(cls._registry.keys())
