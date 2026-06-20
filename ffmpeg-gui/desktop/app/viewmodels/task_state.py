from __future__ import annotations

from dataclasses import dataclass, field

from shared.contracts import TaskRecord


@dataclass
class TaskState:
    records: list[TaskRecord] = field(default_factory=list)

    def add(self, record: TaskRecord) -> None:
        self.records.append(record)

    def latest(self) -> TaskRecord | None:
        return self.records[-1] if self.records else None
