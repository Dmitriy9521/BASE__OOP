#!/usr/bin/env python
# coding: utf-8

# In[2]:


import random
import time
import uuid
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ УТИЛИТЫ
# ══════════════════════════════════════════════════

class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GREY    = "\033[90m"

def c(text, color):
    return f"{color}{text}{Colors.RESET}"

def header(title):
    width = 62
    print()
    print(c("═" * width, Colors.CYAN))
    print(c(f"  {title}", Colors.BOLD + Colors.CYAN))
    print(c("═" * width, Colors.CYAN))

def subheader(title):
    print()
    print(c(f"  ── {title} ──", Colors.YELLOW + Colors.BOLD))

def log_ok(msg):
    print(c("  ✓ ", Colors.GREEN) + msg)

def log_err(msg):
    print(c("  ✗ ", Colors.RED) + msg)

def log_warn(msg):
    print(c("  ⚠ ", Colors.YELLOW) + msg)

def log_info(msg):
    print(c("  → ", Colors.BLUE) + msg)

def log_queue(msg):
    print(c("  ⏳ ", Colors.MAGENTA) + msg)


# ══════════════════════════════════════════════════
#  ПЕРЕЧИСЛЕНИЯ И СТАТУСЫ
# ══════════════════════════════════════════════════

class TransactionType(Enum):
    DEPOSIT    = "Пополнение"
    WITHDRAWAL = "Снятие"
    TRANSFER   = "Перевод"

class TransactionStatus(Enum):
    PENDING   = "В очереди"
    COMPLETED = "Выполнена"
    REJECTED  = "Отклонена"

class AccountType(Enum):
    CHECKING = "Расчётный"
    SAVINGS  = "Сберегательный"
    CREDIT   = "Кредитный"


# ══════════════════════════════════════════════════
#  МОДЕЛИ ДАННЫХ
# ══════════════════════════════════════════════════

@dataclass
class Transaction:
    tx_id:       str
    tx_type:     TransactionType
    amount:      float
    from_acc:    Optional[str]
    to_acc:      Optional[str]
    timestamp:   datetime
    status:      TransactionStatus = TransactionStatus.PENDING
    reject_reason: str = ""
    is_suspicious: bool = False

    def __str__(self):
        direction = ""
        if self.tx_type == TransactionType.TRANSFER:
            direction = f"{self.from_acc} → {self.to_acc}"
        elif self.tx_type == TransactionType.DEPOSIT:
            direction = f"→ {self.to_acc}"
        else:
            direction = f"{self.from_acc} →"

        status_color = {
            TransactionStatus.PENDING:   Colors.YELLOW,
            TransactionStatus.COMPLETED: Colors.GREEN,
            TransactionStatus.REJECTED:  Colors.RED,
        }[self.status]

        flag = c(" [ПОДОЗРИТЕЛЬНО]", Colors.RED + Colors.BOLD) if self.is_suspicious else ""
        return (
            f"  {c(self.tx_id[:8], Colors.GREY)}  "
            f"{c(self.tx_type.value, Colors.BLUE):<14}  "
            f"{c(f'{self.amount:>10.2f} ₽', Colors.WHITE)}  "
            f"{direction:<28}  "
            f"{c(self.status.value, status_color)}"
            f"{flag}"
        )


@dataclass
class Account:
    account_id:   str
    owner_id:     str
    account_type: AccountType
    balance:      float
    created_at:   datetime
    history:      list = field(default_factory=list)

    def deposit(self, amount: float) -> bool:
        if amount <= 0:
            return False
        self.balance += amount
        return True

    def withdraw(self, amount: float) -> bool:
        if amount <= 0 or self.balance < amount:
            return False
        self.balance -= amount
        return True


@dataclass
class Client:
    client_id: str
    name:      str
    email:     str
    phone:     str
    accounts:  list = field(default_factory=list)

    def total_balance(self, bank) -> float:
        return sum(
            bank.accounts[acc_id].balance
            for acc_id in self.accounts
            if acc_id in bank.accounts
        )


# ══════════════════════════════════════════════════
#  ОЧЕРЕДЬ ТРАНЗАКЦИЙ
# ══════════════════════════════════════════════════

class TransactionQueue:
    def __init__(self):
        self._queue: deque[Transaction] = deque()

    def enqueue(self, tx: Transaction):
        self._queue.append(tx)
        log_queue(
            f"Транзакция {c(tx.tx_id[:8], Colors.MAGENTA)} добавлена в очередь  "
            f"[{c(tx.tx_type.value, Colors.BLUE)}, {c(f'{tx.amount:.2f} ₽', Colors.WHITE)}]"
        )

    def dequeue(self) -> Optional[Transaction]:
        return self._queue.popleft() if self._queue else None

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def size(self) -> int:
        return len(self._queue)


# ══════════════════════════════════════════════════
#  АНТИФРОД / ДЕТЕКТОР ПОДОЗРИТЕЛЬНЫХ ОПЕРАЦИЙ
# ══════════════════════════════════════════════════

class FraudDetector:
    LARGE_AMOUNT_THRESHOLD = 100_000
    RAPID_TX_WINDOW_SEC    = 60
    RAPID_TX_COUNT         = 3

    def __init__(self):
        self._recent: dict[str, list[datetime]] = {}

    def check(self, tx: Transaction) -> tuple[bool, str]:
        reasons = []

        # Проверка на крупную сумму
        if tx.amount > self.LARGE_AMOUNT_THRESHOLD:
            reasons.append(f"крупная сумма ({tx.amount:.2f} ₽ > {self.LARGE_AMOUNT_THRESHOLD} ₽)")

        # Проверка на частые операции
        account_key = tx.from_acc or tx.to_acc
        if account_key:
            now = tx.timestamp
            self._recent.setdefault(account_key, [])
            recent_times = [
                t for t in self._recent[account_key]
                if (now - t).total_seconds() < self.RAPID_TX_WINDOW_SEC
            ]
            if len(recent_times) >= self.RAPID_TX_COUNT:
                reasons.append(f"частые операции ({len(recent_times)+1} за {self.RAPID_TX_WINDOW_SEC}с)")
            self._recent[account_key].append(now)

        # Подозрительные круглые суммы ночью
        if tx.amount % 10_000 == 0 and tx.amount >= 50_000:
            if tx.timestamp.hour < 6 or tx.timestamp.hour > 23:
                reasons.append("крупная круглая сумма в нерабочее время")

        is_suspicious = len(reasons) > 0
        return is_suspicious, "; ".join(reasons)


# ══════════════════════════════════════════════════
#  БАНК — ОСНОВНОЙ КЛАСС
# ══════════════════════════════════════════════════

class Bank:
    def __init__(self, name: str):
        self.name      = name
        self.clients:  dict[str, Client]      = {}
        self.accounts: dict[str, Account]     = {}
        self.all_transactions: list[Transaction] = []
        self._queue    = TransactionQueue()
        self._fraud    = FraudDetector()
        self._stats    = {"completed": 0, "rejected": 0, "suspicious": 0}

    # ── Создание клиента ──────────────────────────
    def create_client(self, name: str, email: str, phone: str) -> Client:
        client = Client(
            client_id=str(uuid.uuid4()),
            name=name,
            email=email,
            phone=phone,
        )
        self.clients[client.client_id] = client
        return client

    # ── Создание счёта ────────────────────────────
    def create_account(self, client_id: str, account_type: AccountType,
                       initial_balance: float = 0.0) -> Account:
        acc = Account(
            account_id=f"ACC-{str(uuid.uuid4())[:6].upper()}",
            owner_id=client_id,
            account_type=account_type,
            balance=initial_balance,
            created_at=datetime.now() - timedelta(days=random.randint(0, 365)),
        )
        self.accounts[acc.account_id] = acc
        self.clients[client_id].accounts.append(acc.account_id)
        return acc

    # ── Формирование транзакции ───────────────────
    def _make_tx(self, tx_type, amount, from_acc=None, to_acc=None,
                 dt_offset_hours=0) -> Transaction:
        tx = Transaction(
            tx_id=str(uuid.uuid4()),
            tx_type=tx_type,
            amount=round(amount, 2),
            from_acc=from_acc,
            to_acc=to_acc,
            timestamp=datetime.now() - timedelta(hours=dt_offset_hours),
        )
        is_susp, reason = self._fraud.check(tx)
        tx.is_suspicious = is_susp
        if is_susp:
            log_warn(f"Антифрод: {c(tx.tx_id[:8], Colors.MAGENTA)} — {reason}")
            self._stats["suspicious"] += 1
        return tx

    # ── Постановка в очередь ──────────────────────
    def enqueue_deposit(self, account_id: str, amount: float, offset=0):
        tx = self._make_tx(TransactionType.DEPOSIT, amount, to_acc=account_id,
                           dt_offset_hours=offset)
        self._queue.enqueue(tx)
        return tx

    def enqueue_withdrawal(self, account_id: str, amount: float, offset=0):
        tx = self._make_tx(TransactionType.WITHDRAWAL, amount, from_acc=account_id,
                           dt_offset_hours=offset)
        self._queue.enqueue(tx)
        return tx

    def enqueue_transfer(self, from_id: str, to_id: str, amount: float, offset=0):
        tx = self._make_tx(TransactionType.TRANSFER, amount,
                           from_acc=from_id, to_acc=to_id, dt_offset_hours=offset)
        self._queue.enqueue(tx)
        return tx

    # ── Обработка одной транзакции ────────────────
    def _process_one(self, tx: Transaction):
        acc_from = self.accounts.get(tx.from_acc) if tx.from_acc else None
        acc_to   = self.accounts.get(tx.to_acc)   if tx.to_acc   else None

        def reject(reason: str):
            tx.status = TransactionStatus.REJECTED
            tx.reject_reason = reason
            self._stats["rejected"] += 1
            log_err(
                f"ОТКЛОНЕНА  {c(tx.tx_id[:8], Colors.GREY)}  "
                f"{tx.tx_type.value}  {tx.amount:.2f} ₽  — {c(reason, Colors.RED)}"
            )

        def complete():
            tx.status = TransactionStatus.COMPLETED
            self._stats["completed"] += 1
            flag = c(" ⚠ подозрительно", Colors.RED) if tx.is_suspicious else ""
            log_ok(
                f"ВЫПОЛНЕНА  {c(tx.tx_id[:8], Colors.GREY)}  "
                f"{tx.tx_type.value}  {c(f'{tx.amount:.2f} ₽', Colors.WHITE)}"
                f"{flag}"
            )

        if tx.tx_type == TransactionType.DEPOSIT:
            if acc_to is None:
                reject("счёт получателя не найден")
            elif tx.amount <= 0:
                reject("сумма должна быть положительной")
            else:
                acc_to.deposit(tx.amount)
                acc_to.history.append(tx)
                complete()

        elif tx.tx_type == TransactionType.WITHDRAWAL:
            if acc_from is None:
                reject("счёт отправителя не найден")
            elif acc_from.balance < tx.amount:
                reject(f"недостаточно средств (баланс: {acc_from.balance:.2f} ₽)")
            elif tx.amount <= 0:
                reject("сумма должна быть положительной")
            else:
                acc_from.withdraw(tx.amount)
                acc_from.history.append(tx)
                complete()

        elif tx.tx_type == TransactionType.TRANSFER:
            if acc_from is None:
                reject("счёт отправителя не найден")
            elif acc_to is None:
                reject("счёт получателя не найден")
            elif acc_from.balance < tx.amount:
                reject(f"недостаточно средств (баланс: {acc_from.balance:.2f} ₽)")
            elif tx.amount <= 0:
                reject("сумма должна быть положительной")
            else:
                acc_from.withdraw(tx.amount)
                acc_to.deposit(tx.amount)
                acc_from.history.append(tx)
                acc_to.history.append(tx)
                complete()

        self.all_transactions.append(tx)

    # ── Обработка всей очереди ────────────────────
    def process_queue(self):
        subheader("Обработка очереди транзакций")
        processed = 0
        while not self._queue.is_empty():
            tx = self._queue.dequeue()
            log_info(
                f"Извлечена из очереди: {c(tx.tx_id[:8], Colors.MAGENTA)}  "
                f"[{tx.tx_type.value}  {tx.amount:.2f} ₽]"
            )
            self._process_one(tx)
            processed += 1
        print()
        print(c(f"  Обработано транзакций: {processed}", Colors.CYAN))

    # ════════════════════════════════════════════
    #  ПОЛЬЗОВАТЕЛЬСКИЕ СЦЕНАРИИ
    # ════════════════════════════════════════════

    def show_client_accounts(self, client_id: str):
        client = self.clients.get(client_id)
        if not client:
            log_err("Клиент не найден")
            return
        subheader(f"Счета клиента: {c(client.name, Colors.BOLD)}")
        for acc_id in client.accounts:
            acc = self.accounts[acc_id]
            print(
                f"    {c(acc.account_id, Colors.CYAN)}  "
                f"{acc.account_type.value:<16}  "
                f"Баланс: {c(f'{acc.balance:>12.2f} ₽', Colors.GREEN)}"
            )
        total = client.total_balance(self)
        print(c(f"\n    Итого: {total:.2f} ₽", Colors.BOLD + Colors.WHITE))

    def show_account_history(self, account_id: str, limit: int = 10):
        acc = self.accounts.get(account_id)
        if not acc:
            log_err("Счёт не найден")
            return
        subheader(f"История счёта {c(account_id, Colors.CYAN)}")
        history = acc.history[-limit:]
        if not history:
            print("  (история пуста)")
            return
        print(f"  {'ID':10}  {'Тип':<14}  {'Сумма':>12}  {'Контрагент':<28}  Статус")
        print(c("  " + "─" * 80, Colors.GREY))
        for tx in history:
            print(tx)

    def show_suspicious(self):
        subheader("Подозрительные транзакции")
        suspicious = [tx for tx in self.all_transactions if tx.is_suspicious]
        if not suspicious:
            print("  (подозрительных операций не обнаружено)")
            return
        print(f"  {'ID':10}  {'Тип':<14}  {'Сумма':>12}  {'Стороны':<28}  Статус")
        print(c("  " + "─" * 80, Colors.GREY))
        for tx in suspicious:
            print(tx)

    # ════════════════════════════════════════════
    #  ОТЧЁТЫ
    # ════════════════════════════════════════════

    def report_top_clients(self, n: int = 3):
        subheader(f"Топ-{n} клиентов по балансу")
        ranked = sorted(
            self.clients.values(),
            key=lambda c: c.total_balance(self),
            reverse=True
        )[:n]
        for i, client in enumerate(ranked, 1):
            bal = client.total_balance(self)
            medal = ["🥇", "🥈", "🥉"][i - 1]
            print(
                f"  {medal}  {c(client.name, Colors.BOLD):<25}  "
                f"Баланс: {c(f'{bal:>12.2f} ₽', Colors.GREEN)}"
            )

    def report_transaction_stats(self):
        subheader("Статистика транзакций")
        total    = len(self.all_transactions)
        done     = self._stats["completed"]
        rejected = self._stats["rejected"]
        susp     = self._stats["suspicious"]

        amounts  = [tx.amount for tx in self.all_transactions if tx.status == TransactionStatus.COMPLETED]
        avg      = sum(amounts) / len(amounts) if amounts else 0
        max_tx   = max(amounts) if amounts else 0
        min_tx   = min(amounts) if amounts else 0

        print(f"  Всего транзакций:         {c(str(total), Colors.WHITE)}")
        print(f"  Выполнено:                {c(str(done), Colors.GREEN)}")
        print(f"  Отклонено:                {c(str(rejected), Colors.RED)}")
        print(f"  Подозрительных:           {c(str(susp), Colors.YELLOW)}")
        print(f"  Средняя сумма:            {c(f'{avg:.2f} ₽', Colors.CYAN)}")
        print(f"  Максимальная сумма:       {c(f'{max_tx:.2f} ₽', Colors.CYAN)}")
        print(f"  Минимальная сумма:        {c(f'{min_tx:.2f} ₽', Colors.CYAN)}")

        print()
        by_type = {}
        for tx in self.all_transactions:
            by_type.setdefault(tx.tx_type, 0)
            by_type[tx.tx_type] += 1
        for ttype, count in by_type.items():
            bar = "█" * (count * 2)
            print(f"  {ttype.value:<14}  {c(bar, Colors.BLUE)}  {count}")

    def report_total_balance(self):
        subheader("Общий баланс банка")
        total = sum(acc.balance for acc in self.accounts.values())
        by_type: dict[AccountType, float] = {}
        for acc in self.accounts.values():
            by_type.setdefault(acc.account_type, 0)
            by_type[acc.account_type] += acc.balance
        for atype, bal in by_type.items():
            print(f"  {atype.value:<18}  {c(f'{bal:>14.2f} ₽', Colors.GREEN)}")
        print(c(f"\n  ИТОГО:              {total:>14.2f} ₽", Colors.BOLD + Colors.WHITE))


# ══════════════════════════════════════════════════
#  ИНИЦИАЛИЗАЦИЯ ДЕМОНСТРАЦИИ
# ══════════════════════════════════════════════════

def run_demo():
    print()
    print(c("╔══════════════════════════════════════════════════════════════════╗", Colors.CYAN))
    print(c("║     🏦  БАНКОВСКАЯ СИСТЕМА — Полная демонстрация               ║", Colors.CYAN + Colors.BOLD))
    print(c("╚══════════════════════════════════════════════════════════════════╝", Colors.CYAN))

    # ── 1. Создание банка и клиентов ──────────────
    header("1. ИНИЦИАЛИЗАЦИЯ: БАНК, КЛИЕНТЫ, СЧЕТА")

    bank = Bank("ПитонБанк")
    log_ok(f"Банк {c(bank.name, Colors.BOLD)} создан")

    clients_data = [
        ("Алексей Петров",    "alex@mail.ru",    "+7-900-111-22-33"),
        ("Мария Сидорова",    "maria@gmail.com", "+7-900-222-33-44"),
        ("Иван Козлов",       "ivan@yandex.ru",  "+7-900-333-44-55"),
        ("Ольга Новикова",    "olga@mail.ru",    "+7-900-444-55-66"),
        ("Дмитрий Волков",    "dima@gmail.com",  "+7-900-555-66-77"),
        ("Екатерина Зайцева", "kate@inbox.ru",   "+7-900-666-77-88"),
        ("Сергей Морозов",    "sergey@mail.ru",  "+7-900-777-88-99"),
    ]

    clients = []
    for name, email, phone in clients_data:
        c_obj = bank.create_client(name, email, phone)
        clients.append(c_obj)
        log_ok(f"Клиент: {c(name, Colors.BOLD)}  [{c_obj.client_id[:8]}]")

    subheader("Создание счетов")
    account_ids = []

    account_config = [
        # (client_index, account_type, initial_balance)
        (0, AccountType.CHECKING,  150_000),
        (0, AccountType.SAVINGS,   300_000),
        (1, AccountType.CHECKING,   80_000),
        (1, AccountType.CREDIT,     50_000),
        (2, AccountType.CHECKING,  200_000),
        (2, AccountType.SAVINGS,   120_000),
        (3, AccountType.CHECKING,   45_000),
        (4, AccountType.CHECKING,  500_000),
        (4, AccountType.SAVINGS,   250_000),
        (4, AccountType.CREDIT,    100_000),
        (5, AccountType.CHECKING,   30_000),
        (5, AccountType.SAVINGS,    90_000),
        (6, AccountType.CHECKING,  175_000),
    ]

    for ci, atype, balance in account_config:
        acc = bank.create_account(clients[ci].client_id, atype, balance)
        account_ids.append(acc.account_id)
        log_ok(
            f"  Счёт {c(acc.account_id, Colors.CYAN)}  {atype.value:<16}  "
            f"Баланс: {c(f'{balance:,.0f} ₽', Colors.GREEN)}  "
            f"→ {c(clients[ci].name, Colors.BOLD)}"
        )

    print(c(f"\n  Создано клиентов: {len(clients)},  счетов: {len(account_ids)}", Colors.CYAN))

    # ── 2. Симуляция транзакций ───────────────────
    header("2. СИМУЛЯЦИЯ ТРАНЗАКЦИЙ (постановка в очередь)")

    random.seed(42)

    # Нормальные транзакции
    normal_txs = [
        # Пополнения
        ("deposit",   account_ids[0],  None,           25_000, 5),
        ("deposit",   account_ids[2],  None,           15_000, 4),
        ("deposit",   account_ids[4],  None,           10_000, 3),
        ("deposit",   account_ids[6],  None,            8_500, 2),
        ("deposit",   account_ids[8],  None,           50_000, 1),
        # Снятия
        ("withdraw",  account_ids[0],  None,            5_000, 10),
        ("withdraw",  account_ids[2],  None,           12_000, 9),
        ("withdraw",  account_ids[4],  None,            3_000, 8),
        ("withdraw",  account_ids[6],  None,            7_500, 7),
        ("withdraw",  account_ids[8],  None,           20_000, 6),
        # Переводы
        ("transfer",  account_ids[0],  account_ids[2], 30_000, 15),
        ("transfer",  account_ids[4],  account_ids[6], 45_000, 14),
        ("transfer",  account_ids[8],  account_ids[10], 9_000, 13),
        ("transfer",  account_ids[2],  account_ids[4], 11_000, 12),
        ("transfer",  account_ids[1],  account_ids[3], 22_000, 11),
        ("transfer",  account_ids[6],  account_ids[1],  4_000, 20),
        ("transfer",  account_ids[3],  account_ids[5],  6_500, 19),
        ("transfer",  account_ids[7],  account_ids[9], 18_000, 18),
        ("transfer",  account_ids[9],  account_ids[11], 7_000, 17),
        ("transfer",  account_ids[11], account_ids[0], 12_500, 16),
    ]

    # Ошибочные транзакции
    error_txs = [
        ("withdraw",  account_ids[10], None,          500_000, 25),  # нет денег
        ("withdraw",  account_ids[11], None,          200_000, 24),  # нет денег
        ("deposit",   "ACC-NONEXIST",  None,            1_000, 23),  # несуществующий счёт
        ("withdraw",  account_ids[5],  None,           -500,   22),  # отрицательная сумма
        ("transfer",  account_ids[6],  "ACC-INVALID",  5_000,  21),  # неверный получатель
    ]

    # Подозрительные транзакции
    suspicious_txs = [
        ("deposit",   account_ids[7],  None,          150_000,  2),   # крупная сумма
        ("withdraw",  account_ids[7],  None,          120_000,  2),   # крупная сумма
        ("transfer",  account_ids[7],  account_ids[1], 200_000, 1),   # очень крупный перевод
        ("deposit",   account_ids[7],  None,           50_000,  0),   # частые операции
        ("deposit",   account_ids[7],  None,           50_000,  0),   # частые операции подряд
    ]

    def enqueue_batch(txs, label):
        subheader(label)
        for op, a, b, amount, offset in txs:
            if op == "deposit":
                bank.enqueue_deposit(a, amount, offset)
            elif op == "withdraw":
                bank.enqueue_withdrawal(a, amount, offset)
            elif op == "transfer":
                bank.enqueue_transfer(a, b, amount, offset)

    enqueue_batch(normal_txs,     "Обычные транзакции")
    enqueue_batch(error_txs,      "Ошибочные транзакции (ожидаем отклонение)")
    enqueue_batch(suspicious_txs, "Подозрительные транзакции (антифрод)")

    print(c(f"\n  В очереди: {bank._queue.size()} транзакций", Colors.CYAN))

    # ── 3. Обработка очереди ─────────────────────
    header("3. ОБРАБОТКА ОЧЕРЕДИ")
    bank.process_queue()

    # ── 4. Пользовательские сценарии ─────────────
    header("4. ПОЛЬЗОВАТЕЛЬСКИЕ СЦЕНАРИИ")

    # Показать счета каждого клиента
    subheader("Все клиенты и их счета")
    for cl in clients:
        bank.show_client_accounts(cl.client_id)

    # История конкретного счёта
    header("5. ИСТОРИЯ СЧЁТА")
    bank.show_account_history(account_ids[7], limit=10)  # счёт Дмитрия (много операций)
    bank.show_account_history(account_ids[0], limit=8)

    # Подозрительные операции
    header("6. ПОДОЗРИТЕЛЬНЫЕ ОПЕРАЦИИ")
    bank.show_suspicious()

    # ── 5. Отчёты ────────────────────────────────
    header("7. ОТЧЁТЫ")
    bank.report_top_clients(3)
    bank.report_transaction_stats()
    bank.report_total_balance()

    print()
    print(c("═" * 62, Colors.CYAN))
    print(c("  ✅  Демонстрация завершена успешно", Colors.GREEN + Colors.BOLD))
    print(c("═" * 62, Colors.CYAN))
    print()


if __name__ == "__main__":
    run_demo()


# In[ ]:




