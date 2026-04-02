#!/usr/bin/env python
# coding: utf-8

# In[1]:


from abc import ABC, abstractmethod
import uuid
from datetime import datetime
from typing import Optional


# ====================== ИСКЛЮЧЕНИЯ ======================
class AccountFrozenError(Exception):
    pass

class AccountClosedError(Exception):
    pass

class InvalidOperationError(Exception):
    pass

class InsufficientFundsError(Exception):
    pass


# ====================== АБСТРАКТНЫЙ КЛАСС ======================
class AbstractAccount(ABC):

    def __init__(self, owner: str, account_id: Optional[str] = None):
        self.account_id = account_id or self._generate_account_id()
        self.owner = owner
        self._balance: float = 0.0
        self._status = "active"
        self.currency = "RUB"

    def _generate_account_id(self) -> str:
        short_id = str(uuid.uuid4())[:12].upper()
        return f"ACC-{short_id}"

    @abstractmethod
    def deposit(self, amount: float) -> None:
        pass

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        pass

    @abstractmethod
    def get_account_info(self) -> dict:
        pass

    def _check_status(self) -> None:
        if self._status == "frozen":
            raise AccountFrozenError(f"Счёт {self.account_id} заморожен. Операции запрещены.")
        if self._status == "closed":
            raise AccountClosedError(f"Счёт {self.account_id} закрыт. Операции невозможны.")

    def _validate_amount(self, amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("Сумма должна быть числом")
        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть положительной")

    def get_balance(self) -> float:
        """Возвращает текущий баланс"""
        return self._balance

    def get_status(self) -> str:
        return self._status

    def freeze(self) -> None:
        self._status = "frozen"
        print(f"Счёт {self.account_id} заморожен.")

    def unfreeze(self) -> None:
        if self._status == "closed":
            raise InvalidOperationError("Нельзя разморозить закрытый счёт")
        self._status = "active"
        print(f"Счёт {self.account_id} разморожен.")

    def close(self) -> None:
        if self._balance > 0:
            raise InvalidOperationError("Нельзя закрыть счёт с положительным балансом")
        self._status = "closed"
        print(f"Счёт {self.account_id} закрыт.")


# ====================== КОНКРЕТНЫЙ КЛАСС ======================
class BankAccount(AbstractAccount):

    SUPPORTED_CURRENCIES = {"RUB", "USD", "EUR", "KZT", "CNY"}

    def __init__(self, owner: str, currency: str = "RUB", account_id: Optional[str] = None):
        super().__init__(owner, account_id)
        if currency not in self.SUPPORTED_CURRENCIES:
            raise InvalidOperationError(f"Неподдерживаемая валюта: {currency}")
        self.currency = currency

    def deposit(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        self._balance += amount
        print(f"✅ Пополнение на {amount:.2f} {self.currency}. Новый баланс: {self._balance:.2f} {self.currency}")

    def withdraw(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(f"Недостаточно средств. Баланс: {self._balance:.2f} {self.currency}")
        self._balance -= amount
        print(f"✅ Снятие {amount:.2f} {self.currency}. Новый баланс: {self._balance:.2f} {self.currency}")

    def get_account_info(self) -> dict:
        return {
            "account_id": self.account_id,
            "owner": self.owner,
            "balance": round(self._balance, 2),
            "currency": self.currency,
            "status": self._status
        }

    def __str__(self) -> str:
        last_digits = self.account_id[-4:]
        status_ru = {"active": "Активен", "frozen": "Заморожен", "closed": "Закрыт"}.get(self._status, self._status)
        return (f"🏦 {self.__class__.__name__} | Владелец: {self.owner} | "
                f"№ ...{last_digits} | Статус: {status_ru} | Баланс: {self._balance:.2f} {self.currency}")


# ====================== ДЕМОНСТРАЦИЯ ======================
print("=== Запуск демонстрации ===\n")

acc1 = BankAccount(owner="Иван Иванов", currency="RUB")
print(acc1)
print(f"Начальный баланс: {acc1.get_balance():.2f} {acc1.currency}\n")

acc1.deposit(15000)
acc1.withdraw(3200)
print(f"Текущий баланс: {acc1.get_balance():.2f} {acc1.currency}\n")


# In[ ]:




