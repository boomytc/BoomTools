from __future__ import annotations

from dataclasses import dataclass, field

from shared.contracts import TaskRecord


@dataclass
class TaskState:
    records: list[TaskRecord] = field(default_factory=list)

    def add(self, record: TaskRecord) -> None:
        self.records.append(record)

    def remove_records(self, task_ids: set[str]) -> None:
        if not task_ids:
            return
        self.records = [record for record in self.records if record.task_id not in task_ids]

    def latest(self) -> TaskRecord | None:
        return self.records[-1] if self.records else None
