#!/usr/bin/env python
# coding: utf-8

# In[4]:


from datetime import datetime
import uuid
from enum import Enum
from typing import Optional, List
import time


# ====================== 1. ПЕРЕЧИСЛЕНИЯ ======================
class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    EXTERNAL = "external"


class TransactionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ====================== 2. КЛАСС TRANSACTION ======================
class Transaction:
    """Класс одной транзакции."""

    def __init__(self,
                 transaction_type: TransactionType,
                 amount: float,
                 currency: str = "RUB",
                 sender_account: Optional[str] = None,
                 receiver_account: Optional[str] = None,
                 commission: float = 0.0):

        self.transaction_id = f"TX-{uuid.uuid4().hex[:12].upper()}"
        self.type = transaction_type
        self.amount = amount
        self.currency = currency
        self.commission = commission
        self.sender_account = sender_account
        self.receiver_account = receiver_account
        self.status = TransactionStatus.PENDING
        self.failure_reason: Optional[str] = None
        self.created_at = datetime.now()
        self.processed_at: Optional[datetime] = None

    def calculate_total_amount(self) -> float:
        return self.amount + self.commission

    def mark_as_completed(self) -> None:
        self.status = TransactionStatus.COMPLETED
        self.processed_at = datetime.now()
        print(f"✅ Транзакция {self.transaction_id} успешно выполнена")

    def mark_as_failed(self, reason: str) -> None:
        self.status = TransactionStatus.FAILED
        self.failure_reason = reason
        self.processed_at = datetime.now()
        print(f"❌ Транзакция {self.transaction_id} провалена: {reason}")

    def mark_as_cancelled(self, reason: str = "Отменено пользователем") -> None:
        self.status = TransactionStatus.CANCELLED
        self.failure_reason = reason
        self.processed_at = datetime.now()
        print(f"⛔ Транзакция {self.transaction_id} отменена: {reason}")

    def __str__(self) -> str:
        return (f"[{self.transaction_id}] {self.type.value.upper()} | "
                f"{self.amount:.2f} {self.currency} | Статус: {self.status.value}")


# ====================== 3. КЛАСС TRANSACTIONQUEUE ======================
class TransactionQueue:
    """Очередь транзакций с приоритетом и отложенным выполнением."""

    def __init__(self):
        self.queue: List[Transaction] = []
        self.delayed: List[Transaction] = []
        self.cancelled: List[Transaction] = []

    def add_transaction(self, transaction: Transaction, priority: bool = False) -> None:
        if priority:
            self.queue.insert(0, transaction)
            print(f"➕ Приоритетная транзакция добавлена: {transaction.transaction_id}")
        else:
            self.queue.append(transaction)
            print(f"➕ Транзакция добавлена в очередь: {transaction.transaction_id}")

    def add_delayed(self, transaction: Transaction) -> None:
        self.delayed.append(transaction)
        print(f"⏳ Транзакция {transaction.transaction_id} отложена")

    def get_next(self) -> Optional[Transaction]:
        if self.queue:
            return self.queue.pop(0)
        return None

    def cancel_transaction(self, transaction_id: str, reason: str = "Отменено") -> bool:
        for i, tx in enumerate(self.queue):
            if tx.transaction_id == transaction_id:
                tx.mark_as_cancelled(reason)
                self.cancelled.append(self.queue.pop(i))
                return True
        return False

    def process_delayed(self) -> List[Transaction]:
        ready = self.delayed[:]
        self.delayed.clear()
        self.queue.extend(ready)
        print(f"⏰ Перемещено {len(ready)} отложенных транзакций в очередь")
        return ready

    def __len__(self) -> int:
        return len(self.queue)


# ====================== 4. КЛАСС TRANSACTIONPROCESSOR ======================
class TransactionProcessor:
    """Обработчик транзакций с комиссиями и повторными попытками."""

    def __init__(self):
        self.commission_rates = {"internal": 0.0, "external": 0.015}
        self.max_retries = 3

    def calculate_commission(self, transaction: Transaction) -> float:
        if transaction.type == TransactionType.EXTERNAL:
            return round(transaction.amount * self.commission_rates["external"], 2)
        return 0.0

    def process_transaction(self, transaction: Transaction) -> bool:
        """Обработка одной транзакции"""
        print(f"\n🔄 Обработка: {transaction}")

        transaction.status = TransactionStatus.PROCESSING
        transaction.commission = self.calculate_commission(transaction)

        # Симуляция обработки
        time.sleep(0.3)

        # Здесь можно добавить проверки (замороженный счёт, минус и т.д.)
        if transaction.amount <= 0:
            transaction.mark_as_failed("Отрицательная или нулевая сумма")
            return False

        transaction.mark_as_completed()
        return True


# ====================== 5. ТЕСТИРОВАНИЕ ======================

    queue = TransactionQueue()
    processor = TransactionProcessor()

    # Создаём 10 транзакций
    test_transactions = [
        Transaction(TransactionType.DEPOSIT, 50000, "RUB"),
        Transaction(TransactionType.TRANSFER, 15000, "RUB", "ACC-001", "ACC-002"),
        Transaction(TransactionType.EXTERNAL, 30000, "RUB", "ACC-002"),
        Transaction(TransactionType.WITHDRAWAL, 8000, "RUB", "ACC-001"),
        Transaction(TransactionType.TRANSFER, 25000, "USD", "ACC-003", "ACC-004"),
        Transaction(TransactionType.EXTERNAL, 12000, "EUR", "ACC-005"),
        Transaction(TransactionType.DEPOSIT, 100000, "RUB"),
        Transaction(TransactionType.TRANSFER, 45000, "RUB", "ACC-002", "ACC-007"),
        Transaction(TransactionType.WITHDRAWAL, 5000, "RUB", "ACC-008"),
        Transaction(TransactionType.EXTERNAL, 75000, "RUB", "ACC-009"),
    ]

    print("📥 Добавляем транзакции в очередь...\n")
    for i, tx in enumerate(test_transactions):
        is_priority = (i % 3 == 0)   # каждая 3-я транзакция — приоритетная
        queue.add_transaction(tx, priority=is_priority)

    # Добавляем одну отложенную транзакцию
    delayed = Transaction(TransactionType.TRANSFER, 20000, "RUB", "ACC-010", "ACC-011")
    queue.add_delayed(delayed)

    print(f"\n📊 В очереди: {len(queue)} транзакций\n")

    # Обработка основной очереди
    print("🚀 Обработка очереди...\n")
    processed = 0

    while len(queue) > 0:
        tx = queue.get_next()
        if tx:
            processor.process_transaction(tx)
            processed += 1

    # Обработка отложенных
    print("\n" + "="*70)
    queue.process_delayed()

    while len(queue) > 0:
        tx = queue.get_next()
        if tx:
            processor.process_transaction(tx)
            processed += 1

    print("\n" + "="*70)
    print(f"✅ Всего обработано транзакций: {processed}")
    print(f"🎯 Успешно завершено: {processed}")


# In[ ]:




