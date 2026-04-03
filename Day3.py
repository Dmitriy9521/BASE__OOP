#!/usr/bin/env python
# coding: utf-8

# In[6]:


from datetime import datetime
import uuid
from typing import Dict, List, Optional

# ====================== ИСКЛЮЧЕНИЯ ======================
class ClientUnderageError(Exception):
    """Ошибка: клиент младше 18 лет"""
    pass


class AuthenticationError(Exception):
    """Ошибка аутентификации клиента"""
    pass


class AccountNotFoundError(Exception):
    """Счёт не найден"""
    pass


class InvalidOperationError(Exception):
    """Некорректная операция"""
    pass


# ====================== 1. КЛАСС CLIENT ======================
class Client:
    """Класс клиента банка."""

    def __init__(self, full_name: str, age: int, contact: str):
        if age < 18:
            raise ClientUnderageError(f"Клиент {full_name} младше 18 лет. Регистрация запрещена.")

        self.client_id = f"CL-{uuid.uuid4().hex[:8].upper()}"
        self.full_name = full_name
        self.age = age
        self.contact = contact
        self.accounts: List[str] = []
        self.status = "active"
        self.failed_login_attempts = 0
        self.is_locked = False

    def add_account(self, account_id: str) -> None:
        if account_id not in self.accounts:
            self.accounts.append(account_id)

    def remove_account(self, account_id: str) -> None:
        if account_id in self.accounts:
            self.accounts.remove(account_id)

    def record_failed_login(self) -> None:
        self.failed_login_attempts += 1
        print(f"❌ Неудачная попытка входа для {self.full_name}. Попыток: {self.failed_login_attempts}/3")

        if self.failed_login_attempts >= 3:
            self.is_locked = True
            self.status = "blocked"
            print(f"🚫 Клиент {self.full_name} заблокирован после 3 неудачных попыток!")

    def reset_login_attempts(self) -> None:
        self.failed_login_attempts = 0

    def __str__(self) -> str:
        return (f"👤 Клиент: {self.full_name} | ID: {self.client_id} | "
                f"Возраст: {self.age} | Статус: {self.status} | "
                f"Счетов: {len(self.accounts)}")


# ====================== 2. КЛАСС BANK ======================
class Bank:
    """Главный класс банка."""

    def __init__(self, bank_name: str = "xAI Bank"):
        self.bank_name = bank_name
        self.clients: Dict[str, Client] = {}
        self.accounts: Dict[str, dict] = {}
        self.suspicious_actions: List[str] = []

    def _is_night_time(self) -> bool:
        """Запрет операций с 00:00 до 05:00"""
        current_hour = datetime.now().hour
        if 0 <= current_hour < 5:
            print("⚠️ Операции запрещены в ночное время (00:00 - 05:00)")
            return True
        return False

    def add_client(self, full_name: str, age: int, contact: str) -> Client:
        """Регистрация нового клиента"""
        client = Client(full_name, age, contact)
        self.clients[client.client_id] = client
        print(f"✅ Клиент {full_name} успешно зарегистрирован (ID: {client.client_id})")
        return client

    def open_account(self, client_id: str, initial_balance: float = 0.0, currency: str = "RUB") -> str:
        """Открытие нового счёта"""
        if client_id not in self.clients:
            raise InvalidOperationError("Клиент не найден")

        if self._is_night_time():
            raise InvalidOperationError("Открытие счетов запрещено с 00:00 до 05:00")

        account_id = f"ACC-{uuid.uuid4().hex[:10].upper()}"

        self.accounts[account_id] = {
            "owner": self.clients[client_id].full_name,
            "client_id": client_id,
            "balance": initial_balance,
            "currency": currency,
            "status": "active",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.clients[client_id].add_account(account_id)
        print(f"✅ Открыт счёт {account_id} для клиента {self.clients[client_id].full_name}")
        return account_id

    def close_account(self, account_id: str) -> None:
        """Закрытие счёта"""
        if account_id not in self.accounts:
            raise AccountNotFoundError("Счёт не найден")

        if self.accounts[account_id]["balance"] != 0:
            raise InvalidOperationError("Нельзя закрыть счёт с ненулевым балансом")

        self.accounts[account_id]["status"] = "closed"
        client_id = self.accounts[account_id]["client_id"]
        self.clients[client_id].remove_account(account_id)
        print(f"✅ Счёт {account_id} закрыт.")

    def freeze_account(self, account_id: str) -> None:
        """Заморозка счёта"""
        if account_id not in self.accounts:
            raise AccountNotFoundError("Счёт не найден")
        self.accounts[account_id]["status"] = "frozen"
        print(f"❄️ Счёт {account_id} заморожен.")

    def unfreeze_account(self, account_id: str) -> None:
        """Разморозка счёта"""
        if account_id not in self.accounts:
            raise AccountNotFoundError("Счёт не найден")
        self.accounts[account_id]["status"] = "active"
        print(f"✅ Счёт {account_id} разморожен.")

    def authenticate_client(self, client_id: str) -> bool:
        """Аутентификация клиента"""
        if client_id not in self.clients:
            raise AuthenticationError("Клиент не найден")

        client = self.clients[client_id]

        if client.is_locked:
            raise AuthenticationError(f"Клиент {client.full_name} заблокирован")

        client.reset_login_attempts()
        print(f"✅ Успешная аутентификация: {client.full_name}")
        return True

    def search_accounts(self, client_id: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        """Поиск счетов по клиенту и/или статусу"""
        result = []
        for acc_id, acc_info in self.accounts.items():
            if (client_id is None or acc_info.get("client_id") == client_id) and \
               (status is None or acc_info.get("status") == status):
                result.append({"account_id": acc_id, **acc_info})
        return result

    def get_total_balance(self) -> float:
        """Общий баланс всех активных счетов"""
        total = sum(acc["balance"] for acc in self.accounts.values() if acc.get("status") == "active")
        print(f"💰 Общий баланс банка: {total:.2f} RUB")
        return total

    def get_clients_ranking(self) -> List[tuple]:
        """Рейтинг клиентов по суммарному балансу"""
        ranking = []
        for client in self.clients.values():
            client_total = sum(
                self.accounts[acc_id]["balance"]
                for acc_id in client.accounts
                if acc_id in self.accounts and self.accounts[acc_id].get("status") == "active"
            )
            ranking.append((client.full_name, client_total, len(client.accounts)))

        ranking.sort(key=lambda x: x[1], reverse=True)

        print("\n🏆 ТОП-5 клиентов по балансу:")
        for i, (name, balance, count) in enumerate(ranking[:5], 1):
            print(f"{i}. {name} — {balance:.2f} RUB ({count} счетов)")

        return ranking


# ====================== ТЕСТИРОВАНИЕ ======================

bank = Bank("xAI Bank")

# Создание клиентов
client1 = bank.add_client("Иван Иванов", 28, "+7-999-111-22-33")
client2 = bank.add_client("Мария Петрова", 22, "maria.petrova@gmail.com")

try:
    bank.add_client("Вася Пупкин", 15, "+7-999-000-00-00")
except ClientUnderageError as e:
    print(f"Ошибка: {e}")

print("\n" + "=" * 60)

# Открытие счетов
acc1 = bank.open_account(client1.client_id, initial_balance=150000)
acc2 = bank.open_account(client2.client_id, initial_balance=75000)
acc3 = bank.open_account(client1.client_id, initial_balance=50000)

print("\n" + "=" * 60)

# Аутентификация
bank.authenticate_client(client1.client_id)

# Симуляция неудачных попыток входа
print("\n--- Симуляция 3 неудачных попыток входа для client2 ---")
for _ in range(3):
    client2_obj = bank.clients.get(client2.client_id)
    if client2_obj:
        client2_obj.record_failed_login()

print("\n" + "=" * 60)

# Операции со счетами
bank.freeze_account(acc1)
bank.unfreeze_account(acc1)

# Итоговая информация
bank.get_total_balance()
bank.get_clients_ranking()


# In[ ]:




