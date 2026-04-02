#!/usr/bin/env python
# coding: utf-8

# In[6]:


from abc import ABC, abstractmethod
import uuid
from datetime import datetime
from typing import Optional, Dict

# ====================== ИСКЛЮЧЕНИЯ ======================
class AccountFrozenError(Exception):
    """Ошибка при операциях с замороженным счётом"""
    pass


class AccountClosedError(Exception):
    """Ошибка при операциях с закрытым счётом"""
    pass


class InvalidOperationError(Exception):
    """Ошибка некорректной операции"""
    pass


class InsufficientFundsError(Exception):
    """Ошибка при недостатке средств"""
    pass


# ====================== 1. АБСТРАКТНЫЙ БАЗОВЫЙ КЛАСС ======================
class AbstractAccount(ABC):
    """Абстрактный базовый класс для всех типов банковских счетов."""

    def __init__(self, owner: str, currency: str = "RUB", account_id: Optional[str] = None):
        self.account_id = account_id or self._generate_account_id()
        self.owner = owner
        self._balance: float = 0.0
        self._status = "active"
        self.currency = currency

    def _generate_account_id(self) -> str:
        """Генерация уникального короткого идентификатора"""
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
            raise AccountFrozenError(f"Счёт {self.account_id} заморожен.")
        if self._status == "closed":
            raise AccountClosedError(f"Счёт {self.account_id} закрыт.")

    def _validate_amount(self, amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise InvalidOperationError("Сумма должна быть числом")
        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть положительной")

    def get_balance(self) -> float:
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
        if self._balance != 0:
            raise InvalidOperationError("Нельзя закрыть счёт с ненулевым балансом")
        self._status = "closed"
        print(f"Счёт {self.account_id} закрыт.")


# ====================== 2. SAVINGS ACCOUNT ======================
class SavingsAccount(AbstractAccount):
    """Сберегательный счёт с минимальным остатком и начислением процентов."""

    def __init__(self, owner: str, min_balance: float = 1000.0, interest_rate: float = 0.05,
                 currency: str = "RUB", account_id: Optional[str] = None):
        super().__init__(owner, currency, account_id)
        self.min_balance = min_balance
        self.interest_rate = interest_rate

    def deposit(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        self._balance += amount
        print(f"✅ [Savings] Пополнение на {amount:.2f} {self.currency}. Баланс: {self._balance:.2f}")

    def withdraw(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        if self._balance - amount < self.min_balance:
            raise InsufficientFundsError(f"Нельзя опуститься ниже минимального остатка {self.min_balance:.2f}")
        self._balance -= amount
        print(f"✅ [Savings] Снятие {amount:.2f} {self.currency}. Баланс: {self._balance:.2f}")

    def apply_monthly_interest(self) -> None:
        if self._status != "active":
            return
        interest = self._balance * (self.interest_rate / 12)
        self._balance += interest
        print(f"📈 [Savings] Начислено процентов: +{interest:.2f} {self.currency}")

    def get_account_info(self) -> dict:
        return {
            "account_type": "SavingsAccount",
            "owner": self.owner,
            "balance": round(self._balance, 2),
            "currency": self.currency,
            "min_balance": self.min_balance,
            "interest_rate_%": round(self.interest_rate * 100, 2),
            "status": self._status
        }

    def __str__(self) -> str:
        return f"💰 Savings | {self.owner} | Баланс: {self._balance:.2f} {self.currency} | Ставка: {self.interest_rate*100:.1f}%"


# ====================== 3. PREMIUM ACCOUNT ======================
class PremiumAccount(AbstractAccount):
    """Премиум счёт с овердрафтом и месячной комиссией."""

    def __init__(self, owner: str, overdraft_limit: float = 50000.0,
                 monthly_fee: float = 299.0, currency: str = "RUB",
                 account_id: Optional[str] = None):
        super().__init__(owner, currency, account_id)
        self.overdraft_limit = overdraft_limit
        self.monthly_fee = monthly_fee

    def deposit(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        self._balance += amount
        print(f"✅ [Premium] Пополнение на {amount:.2f} {self.currency}")

    def withdraw(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        max_available = self._balance + self.overdraft_limit
        if amount > max_available:
            raise InsufficientFundsError(f"Превышен лимит овердрафта. Доступно: {max_available:.2f}")
        self._balance -= amount
        print(f"✅ [Premium] Снятие {amount:.2f} {self.currency}. Баланс: {self._balance:.2f}")

    def charge_monthly_fee(self) -> None:
        if self._status == "active" and self._balance >= self.monthly_fee:
            self._balance -= self.monthly_fee
            print(f"💸 [Premium] Списана комиссия {self.monthly_fee:.2f} {self.currency}")
        else:
            print(f"⚠️ [Premium] Не удалось списать комиссию — недостаточно средств")

    def get_account_info(self) -> dict:
        return {
            "account_type": "PremiumAccount",
            "owner": self.owner,
            "balance": round(self._balance, 2),
            "currency": self.currency,
            "overdraft_limit": self.overdraft_limit,
            "monthly_fee": self.monthly_fee,
            "status": self._status
        }

    def __str__(self) -> str:
        return f"⭐ Premium | {self.owner} | Баланс: {self._balance:.2f} {self.currency} | Овердрафт: {self.overdraft_limit:.2f}"


# ====================== 4. INVESTMENT ACCOUNT ======================
class InvestmentAccount(AbstractAccount):
    """Инвестиционный счёт с портфелем и прогнозом роста."""

    def __init__(self, owner: str, currency: str = "RUB", account_id: Optional[str] = None):
        super().__init__(owner, currency, account_id)
        self.portfolio: Dict[str, float] = {"stocks": 50.0, "bonds": 30.0, "etf": 20.0}
        self.expected_annual_return = 0.12

    def deposit(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        self._balance += amount
        print(f"✅ [Investment] Пополнение на {amount:.2f} {self.currency}")

    def withdraw(self, amount: float) -> None:
        self._check_status()
        self._validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError("Недостаточно средств на инвестиционном счёте")
        self._balance -= amount
        print(f"✅ [Investment] Снятие {amount:.2f} {self.currency}")

    def project_yearly_growth(self) -> float:
        projected = self._balance * (1 + self.expected_annual_return)
        growth = projected - self._balance
        print(f"📊 [Investment] Прогноз роста за год: +{growth:.2f} {self.currency}")
        return projected

    def get_account_info(self) -> dict:
        return {
            "account_type": "InvestmentAccount",
            "owner": self.owner,
            "balance": round(self._balance, 2),
            "currency": self.currency,
            "portfolio": self.portfolio,
            "expected_return_%": round(self.expected_annual_return * 100, 2),
            "status": self._status
        }

    def __str__(self) -> str:
        return f"📈 Investment | {self.owner} | Баланс: {self._balance:.2f} {self.currency} | Доходность: {self.expected_annual_return*100:.1f}%"


# ====================== ДЕМОНСТРАЦИЯ ======================

# Создаём счета
savings = SavingsAccount(owner="Анна Смирнова", min_balance=5000, interest_rate=0.06)
premium = PremiumAccount(owner="Дмитрий Ковалёв", overdraft_limit=100000, monthly_fee=399)
investment = InvestmentAccount(owner="Елена Морозова", currency="USD")

print(savings)
print(premium)
print(investment)
print("-" * 70)

# Тестируем каждый счёт
savings.deposit(30000)
savings.withdraw(10000)
savings.apply_monthly_interest()

print("\n" + "="*70)

premium.deposit(80000)
premium.withdraw(120000)   # используем овердрафт
premium.charge_monthly_fee()

print("\n" + "="*70)

investment.deposit(25000)
investment.project_yearly_growth()
investment.withdraw(5000)


# In[ ]:




