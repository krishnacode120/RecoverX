from dataclasses import asdict, dataclass, field
from enum import StrEnum
from threading import Event
from typing import Callable
import uuid


class RecoveryError(Exception):
    pass


class Cancelled(RecoveryError):
    pass


class Status(StrEnum):
    VERIFIED = "Verified intact"
    LIKELY = "Likely recoverable"
    PARTIAL = "Partially recoverable"
    DAMAGED = "Damaged"
    UNCERTAIN = "Uncertain"
    UNRECOVERABLE = "Unrecoverable with currently accessible information"


@dataclass(frozen=True)
class Extent:
    offset: int
    length: int


@dataclass
class Candidate:
    name: str
    kind: str
    size: int
    extents: list[Extent]
    method: str
    status: str = Status.UNCERTAIN
    reasons: list[str] = field(default_factory=list)
    original_path: str | None = None
    sha256: str | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["extents"] = [Extent(**e) for e in data["extents"]]
        return cls(**data)


@dataclass
class Control:
    cancelled: Event = field(default_factory=Event)
    paused: Event = field(default_factory=Event)

    def check(self):
        while self.paused.is_set():
            if self.cancelled.wait(0.1):
                raise Cancelled("Operation cancelled")
        if self.cancelled.is_set():
            raise Cancelled("Operation cancelled")


Progress = Callable[[int, int, str], None]


def no_progress(done: int, total: int, phase: str):
    pass
