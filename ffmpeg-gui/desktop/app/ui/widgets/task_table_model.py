from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from shared.contracts import TaskRecord, operation_label

STATUS_ROLE = int(Qt.ItemDataRole.UserRole) + 1
PROGRESS_ROLE = int(Qt.ItemDataRole.UserRole) + 2


class TaskTableModel(QAbstractTableModel):
    HEADERS = ["状态", "操作", "输入文件", "输出文件", "进度", "消息"]

    def __init__(self) -> None:
        super().__init__()
        self._records: list[TaskRecord] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        record = self._records[index.row()]
        column = index.column()
        if role == STATUS_ROLE:
            return record.status
        if role == PROGRESS_ROLE:
            return record.progress
        if role == Qt.ItemDataRole.TextAlignmentRole and column in {0, 4}:
            return int(Qt.AlignmentFlag.AlignCenter)
        if role not in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole}:
            return None
        if column == 0:
            return record.status.value
        if column == 1:
            return operation_label(record.operation)
        if column == 2:
            return record.input_path.name if role == Qt.ItemDataRole.DisplayRole else str(record.input_path)
        if column == 3:
            if not record.output_path:
                return ""
            return record.output_path.name if role == Qt.ItemDataRole.DisplayRole else str(record.output_path)
        if column == 4:
            if record.progress is None:
                return "运行中"
            return f"{int(record.progress * 100)}%"
        if column == 5:
            return record.message
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def set_records(self, records: list[TaskRecord]) -> None:
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def append_record(self, record: TaskRecord) -> None:
        row = len(self._records)
        self.beginInsertRows(QModelIndex(), row, row)
        self._records.append(record)
        self.endInsertRows()

    def notify_record_changed(self, record: TaskRecord) -> None:
        try:
            row = self._records.index(record)
        except ValueError:
            return
        top_left = self.index(row, 0)
        bottom_right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.ToolTipRole,
                Qt.ItemDataRole.TextAlignmentRole,
                STATUS_ROLE,
                PROGRESS_ROLE,
            ],
        )

    def records(self) -> list[TaskRecord]:
        return list(self._records)

    def remove_records(self, task_ids: set[str]) -> int:
        if not task_ids:
            return 0
        rows_to_remove = [index for index, record in enumerate(self._records) if record.task_id in task_ids]
        if not rows_to_remove:
            return 0
        for row in reversed(rows_to_remove):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._records.pop(row)
            self.endRemoveRows()
        return len(rows_to_remove)
