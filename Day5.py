#!/usr/bin/env python
# coding: utf-8

# In[2]:


"""
Система аудита и анализа рисков для мониторинга банковских операций
"""

import json
import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


# ─────────────────────────────────────────────
# ПЕРЕЧИСЛЕНИЯ (Enums)
# ─────────────────────────────────────────────

class LogLevel(Enum):
    """Уровни важности лог-записей"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RiskLevel(Enum):
    """Уровни риска операции"""
    LOW = "низкий"
    MEDIUM = "средний"
    HIGH = "высокий"


class TransactionType(Enum):
    """Типы банковских операций"""
    TRANSFER = "перевод"
    WITHDRAWAL = "снятие"
    DEPOSIT = "пополнение"
    PAYMENT = "платёж"


# ─────────────────────────────────────────────
# СТРУКТУРЫ ДАННЫХ
# ─────────────────────────────────────────────

@dataclass
class Transaction:
    """Банковская транзакция"""
    transaction_id: str
    client_id: str
    amount: float
    transaction_type: TransactionType
    timestamp: datetime.datetime
    recipient_account: Optional[str] = None
    description: str = ""

    def is_night(self) -> bool:
        """Проверяет, выполнена ли операция ночью (00:00–06:00)"""
        return 0 <= self.timestamp.hour < 6

    def __str__(self):
        time_str = self.timestamp.strftime("%d.%m.%Y %H:%M")
        return (f"[{self.transaction_id}] {self.transaction_type.value.upper()} "
                f"на {self.amount:,.2f} ₽ | клиент {self.client_id} | {time_str}")


@dataclass
class LogEntry:
    """Запись аудит-лога"""
    level: LogLevel
    message: str
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    transaction_id: Optional[str] = None
    client_id: Optional[str] = None

    def __str__(self):
        time_str = self.timestamp.strftime("%d.%m.%Y %H:%M:%S")
        parts = [f"[{time_str}]", f"[{self.level.value}]"]
        if self.client_id:
            parts.append(f"[клиент {self.client_id}]")
        if self.transaction_id:
            parts.append(f"[tx:{self.transaction_id}]")
        parts.append(self.message)
        return " ".join(parts)


@dataclass
class RiskResult:
    """Результат анализа риска"""
    level: RiskLevel
    reasons: list[str]
    score: int  # суммарный балл риска

    def __str__(self):
        reasons_str = "; ".join(self.reasons) if self.reasons else "нет"
        return f"Риск: {self.level.value.upper()} (балл {self.score}) | Причины: {reasons_str}"


# ─────────────────────────────────────────────
# КЛАСС: AuditLog
# ─────────────────────────────────────────────

class AuditLog:
    """
    Система аудит-логирования.
    Хранит записи в памяти и записывает в файл.
    """

    LOG_FILE = "audit_log.txt"

    def __init__(self, log_to_file: bool = True):
        self._entries: list[LogEntry] = []
        self._log_to_file = log_to_file
        self._error_count: dict[str, int] = defaultdict(int)  # client_id → кол-во ошибок

    # ── Запись ──────────────────────────────

    def log(
        self,
        level: LogLevel,
        message: str,
        transaction_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> LogEntry:
        entry = LogEntry(
            level=level,
            message=message,
            transaction_id=transaction_id,
            client_id=client_id,
        )
        self._entries.append(entry)

        # считаем ошибки по клиенту
        if level in (LogLevel.ERROR, LogLevel.CRITICAL) and client_id:
            self._error_count[client_id] += 1

        # вывод в консоль
        print(entry)

        # запись в файл
        if self._log_to_file:
            with open(self.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(str(entry) + "\n")

        return entry

    def info(self, msg, **kw):     return self.log(LogLevel.INFO, msg, **kw)
    def warning(self, msg, **kw):  return self.log(LogLevel.WARNING, msg, **kw)
    def error(self, msg, **kw):    return self.log(LogLevel.ERROR, msg, **kw)
    def critical(self, msg, **kw): return self.log(LogLevel.CRITICAL, msg, **kw)

    # ── Фильтрация ──────────────────────────

    def filter(
        self,
        level: Optional[LogLevel] = None,
        client_id: Optional[str] = None,
        from_dt: Optional[datetime.datetime] = None,
        to_dt: Optional[datetime.datetime] = None,
    ) -> list[LogEntry]:
        result = self._entries
        if level:
            result = [e for e in result if e.level == level]
        if client_id:
            result = [e for e in result if e.client_id == client_id]
        if from_dt:
            result = [e for e in result if e.timestamp >= from_dt]
        if to_dt:
            result = [e for e in result if e.timestamp <= to_dt]
        return result

    # ── Статистика ошибок ───────────────────

    def error_stats(self) -> dict[str, int]:
        return dict(self._error_count)

    def all_entries(self) -> list[LogEntry]:
        return list(self._entries)


# ─────────────────────────────────────────────
# КЛАСС: RiskAnalyzer
# ─────────────────────────────────────────────

class RiskAnalyzer:
    """
    Анализатор рисков банковских операций.

    Критерии подозрительности:
      - Крупная сумма           → +30 баллов
      - Частые операции         → +25 баллов
      - Новый получатель        → +20 баллов
      - Ночное время (00–06)    → +15 баллов

    Уровни риска:
      0–20   → LOW
      21–45  → MEDIUM
      46+    → HIGH
    """

    LARGE_AMOUNT_THRESHOLD = 500_000      # ₽
    FREQUENT_OPS_LIMIT = 5                # операций за последние N минут
    FREQUENT_OPS_WINDOW_MIN = 10          # окно в минутах

    SCORE_LARGE_AMOUNT  = 30
    SCORE_FREQUENT_OPS  = 25
    SCORE_NEW_ACCOUNT   = 20
    SCORE_NIGHT_OP      = 15

    def __init__(self):
        # история операций по клиентам: client_id → [Transaction]
        self._history: dict[str, list[Transaction]] = defaultdict(list)
        # известные счета получателей по клиентам
        self._known_accounts: dict[str, set[str]] = defaultdict(set)

    def register_transaction(self, tx: Transaction):
        """Регистрирует транзакцию в истории (вызывать ДО анализа)"""
        self._history[tx.client_id].append(tx)
        if tx.recipient_account:
            self._known_accounts[tx.client_id].add(tx.recipient_account)

    def analyze(self, tx: Transaction) -> RiskResult:
        """Возвращает RiskResult для переданной транзакции"""
        score = 0
        reasons = []

        # 1. Крупная сумма
        if tx.amount >= self.LARGE_AMOUNT_THRESHOLD:
            score += self.SCORE_LARGE_AMOUNT
            reasons.append(f"крупная сумма {tx.amount:,.0f} ₽")

        # 2. Частые операции
        window_start = tx.timestamp - datetime.timedelta(minutes=self.FREQUENT_OPS_WINDOW_MIN)
        recent = [
            t for t in self._history[tx.client_id]
            if window_start <= t.timestamp <= tx.timestamp and t.transaction_id != tx.transaction_id
        ]
        if len(recent) >= self.FREQUENT_OPS_LIMIT:
            score += self.SCORE_FREQUENT_OPS
            reasons.append(f"частые операции ({len(recent)} за {self.FREQUENT_OPS_WINDOW_MIN} мин)")

        # 3. Новый получатель
        if tx.recipient_account:
            known = self._known_accounts[tx.client_id] - {tx.recipient_account}
            if tx.recipient_account not in known:
                score += self.SCORE_NEW_ACCOUNT
                reasons.append(f"новый счёт получателя {tx.recipient_account}")

        # 4. Ночное время
        if tx.is_night():
            score += self.SCORE_NIGHT_OP
            reasons.append(f"ночная операция ({tx.timestamp.strftime('%H:%M')})")

        # Определяем уровень риска
        if score <= 20:
            level = RiskLevel.LOW
        elif score <= 45:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.HIGH

        return RiskResult(level=level, reasons=reasons, score=score)


# ─────────────────────────────────────────────
# КЛАСС: Bank
# ─────────────────────────────────────────────

class Bank:
    """
    Банк — обрабатывает транзакции, блокирует опасные операции,
    генерирует отчёты аудита.
    """

    def __init__(self, name: str = "SecureBank"):
        self.name = name
        self.audit_log = AuditLog(log_to_file=True)
        self.risk_analyzer = RiskAnalyzer()

        self._processed: list[Transaction] = []    # успешные операции
        self._blocked: list[Transaction] = []      # заблокированные операции
        self._risk_results: dict[str, RiskResult] = {}  # tx_id → RiskResult

    # ── Обработка транзакции ────────────────

    def process(self, tx: Transaction) -> bool:
        """
        Обрабатывает транзакцию.
        Возвращает True если операция прошла, False если заблокирована.
        """
        self.audit_log.info(
            f"Получена транзакция: {tx}",
            transaction_id=tx.transaction_id,
            client_id=tx.client_id,
        )

        # Анализ риска
        self.risk_analyzer.register_transaction(tx)
        risk = self.risk_analyzer.analyze(tx)
        self._risk_results[tx.transaction_id] = risk

        if risk.level == RiskLevel.LOW:
            self.audit_log.info(
                f"Риск: {risk}",
                transaction_id=tx.transaction_id,
                client_id=tx.client_id,
            )
            self._processed.append(tx)
            return True

        elif risk.level == RiskLevel.MEDIUM:
            self.audit_log.warning(
                f"Подозрительная операция! {risk}",
                transaction_id=tx.transaction_id,
                client_id=tx.client_id,
            )
            # Средний риск — выполняем, но фиксируем
            self._processed.append(tx)
            return True

        else:  # HIGH
            self.audit_log.critical(
                f"ОПЕРАЦИЯ ЗАБЛОКИРОВАНА! {risk}",
                transaction_id=tx.transaction_id,
                client_id=tx.client_id,
            )
            self._blocked.append(tx)
            return False

    # ── Отчёты ─────────────────────────────

    def report_suspicious(self) -> str:
        """Отчёт по подозрительным операциям (MEDIUM и HIGH риск)"""
        lines = [f"\n{'═'*60}", f"  ОТЧЁТ: Подозрительные операции — {self.name}", f"{'═'*60}"]

        suspicious = [
            (tx, self._risk_results[tx.transaction_id])
            for tx in self._processed + self._blocked
            if tx.transaction_id in self._risk_results
            and self._risk_results[tx.transaction_id].level != RiskLevel.LOW
        ]

        if not suspicious:
            lines.append("  Подозрительных операций не обнаружено.")
        else:
            for tx, risk in sorted(suspicious, key=lambda x: x[1].score, reverse=True):
                status = "ЗАБЛОКИРОВАНА" if tx in self._blocked else "выполнена"
                lines.append(f"\n  {tx}")
                lines.append(f"  Статус : {status}")
                lines.append(f"  {risk}")

        lines.append(f"{'═'*60}\n")
        return "\n".join(lines)

    def report_client_risk_profile(self, client_id: str) -> str:
        """Риск-профиль конкретного клиента"""
        lines = [f"\n{'═'*60}", f"  РИСК-ПРОФИЛЬ КЛИЕНТА: {client_id}", f"{'═'*60}"]

        client_txs = [
            tx for tx in self._processed + self._blocked
            if tx.client_id == client_id
        ]

        if not client_txs:
            lines.append(f"  Операции клиента {client_id} не найдены.")
            lines.append(f"{'═'*60}\n")
            return "\n".join(lines)

        # Статистика
        total = len(client_txs)
        blocked = sum(1 for tx in client_txs if tx in self._blocked)
        total_amount = sum(tx.amount for tx in client_txs)
        high_risk = sum(
            1 for tx in client_txs
            if tx.transaction_id in self._risk_results
            and self._risk_results[tx.transaction_id].level == RiskLevel.HIGH
        )
        medium_risk = sum(
            1 for tx in client_txs
            if tx.transaction_id in self._risk_results
            and self._risk_results[tx.transaction_id].level == RiskLevel.MEDIUM
        )

        lines.append(f"  Всего операций   : {total}")
        lines.append(f"  Заблокировано    : {blocked}")
        lines.append(f"  Общая сумма      : {total_amount:,.2f} ₽")
        lines.append(f"  Высокий риск     : {high_risk}")
        lines.append(f"  Средний риск     : {medium_risk}")
        lines.append(f"\n  Детализация:")

        for tx in client_txs:
            risk = self._risk_results.get(tx.transaction_id)
            risk_str = f"[{risk.level.value}]" if risk else "[неизвестно]"
            status = "❌ БЛОК" if tx in self._blocked else "✓ OK"
            lines.append(f"    {status} {risk_str:12} {tx}")

        lines.append(f"{'═'*60}\n")
        return "\n".join(lines)

    def report_error_stats(self) -> str:
        """Статистика ошибок/критических событий по клиентам"""
        lines = [f"\n{'═'*60}", f"  ОТЧЁТ: Статистика ошибок — {self.name}", f"{'═'*60}"]

        stats = self.audit_log.error_stats()
        if not stats:
            lines.append("  Ошибок не зафиксировано.")
        else:
            for client_id, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  Клиент {client_id}: {count} критических событий")

        lines.append(f"\n  Всего заблокировано операций: {len(self._blocked)}")
        lines.append(f"  Всего выполнено операций   : {len(self._processed)}")
        lines.append(f"{'═'*60}\n")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# ТЕСТИРОВАНИЕ
# ─────────────────────────────────────────────

def make_dt(hour: int, minute: int = 0, day_offset: int = 0) -> datetime.datetime:
    """Вспомогательная функция для создания datetime"""
    base = datetime.datetime(2024, 6, 15, hour, minute)
    return base + datetime.timedelta(days=day_offset)


def run_tests():
    print("\n" + "="*60)
    print("  БАНКОВСКАЯ СИСТЕМА АУДИТА И АНАЛИЗА РИСКОВ")
    print("="*60 + "\n")

    bank = Bank("SecureBank RU")

    # ────────── Обычные транзакции ──────────
    normal_transactions = [
        Transaction("TX001", "client_A", 15_000,    TransactionType.PAYMENT,    make_dt(10, 30),
                    description="Оплата ЖКХ"),
        Transaction("TX002", "client_B", 5_000,     TransactionType.TRANSFER,   make_dt(12, 0),
                    recipient_account="ACC_001", description="Перевод другу"),
        Transaction("TX003", "client_A", 25_000,    TransactionType.WITHDRAWAL, make_dt(14, 15),
                    description="Снятие наличных"),
        Transaction("TX004", "client_C", 100_000,   TransactionType.DEPOSIT,    make_dt(9, 0),
                    description="Пополнение счёта"),
        Transaction("TX005", "client_B", 5_000,     TransactionType.TRANSFER,   make_dt(15, 0),
                    recipient_account="ACC_001", description="Повторный перевод другу"),
    ]

    # ────────── Подозрительные транзакции ──────────
    suspicious_transactions = [
        # Крупный перевод на новый счёт ночью → HIGH
        Transaction("TX006", "client_D", 800_000,   TransactionType.TRANSFER,   make_dt(2, 45),
                    recipient_account="ACC_NEW_999", description="Крупный ночной перевод"),

        # Серия частых операций → HIGH
        Transaction("TX007", "client_E", 10_000,    TransactionType.PAYMENT,    make_dt(11, 0)),
        Transaction("TX008", "client_E", 12_000,    TransactionType.PAYMENT,    make_dt(11, 2)),
        Transaction("TX009", "client_E", 9_000,     TransactionType.PAYMENT,    make_dt(11, 4)),
        Transaction("TX010", "client_E", 11_000,    TransactionType.PAYMENT,    make_dt(11, 6)),
        Transaction("TX011", "client_E", 8_000,     TransactionType.PAYMENT,    make_dt(11, 8)),
        Transaction("TX012", "client_E", 13_000,    TransactionType.PAYMENT,    make_dt(11, 9)),  # 6-я за 10 мин

        # Крупная сумма + новый получатель → MEDIUM/HIGH
        Transaction("TX013", "client_A", 600_000,   TransactionType.TRANSFER,   make_dt(16, 30),
                    recipient_account="ACC_OFFSHORE", description="Перевод за рубеж"),

        # Ночная операция с новым счётом → MEDIUM
        Transaction("TX014", "client_C", 30_000,    TransactionType.TRANSFER,   make_dt(3, 15),
                    recipient_account="ACC_UNKNOWN", description="Ночной перевод незнакомцу"),
    ]

    print("\n─── ОБЫЧНЫЕ ТРАНЗАКЦИИ ──────────────────────────────\n")
    for tx in normal_transactions:
        bank.process(tx)

    print("\n─── ПОДОЗРИТЕЛЬНЫЕ ТРАНЗАКЦИИ ───────────────────────\n")
    for tx in suspicious_transactions:
        bank.process(tx)

    # ────────── Отчёты ──────────
    print(bank.report_suspicious())
    print(bank.report_client_risk_profile("client_E"))
    print(bank.report_client_risk_profile("client_D"))
    print(bank.report_client_risk_profile("client_A"))
    print(bank.report_error_stats())

    # ────────── Демонстрация фильтрации лога ──────────
    print("─── ФИЛЬТР ЛОГА: только CRITICAL-записи ────────────\n")
    critical_entries = bank.audit_log.filter(level=LogLevel.CRITICAL)
    for entry in critical_entries:
        print(f"  {entry}")
    print()


if __name__ == "__main__":
    run_tests()


# In[ ]:




