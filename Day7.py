#!/usr/bin/env python
# coding: utf-8

# In[2]:


import json
import csv
from collections import defaultdict
import matplotlib.pyplot as plt


class ReportBuilder:
    """Система генерации отчётов и визуализации данных банковской системы."""

    def __init__(self):
        """Инициализация с тестовыми данными банковской системы."""
        # Данные клиентов
        self.clients = [
            {
                "id": 1,
                "name": "Иван Иванов",
                "balance": 150000,
                "transactions": [
                    {"date": "2025-01-15", "amount": 50000},
                    {"date": "2025-02-10", "amount": 30000},
                    {"date": "2025-03-05", "amount": -20000},
                ],
            },
            {
                "id": 2,
                "name": "Мария Петрова",
                "balance": 80000,
                "transactions": [
                    {"date": "2025-01-20", "amount": 40000},
                    {"date": "2025-02-15", "amount": -10000},
                ],
            },
            {
                "id": 3,
                "name": "Алексей Сидоров",
                "balance": 250000,
                "transactions": [
                    {"date": "2025-01-10", "amount": 100000},
                    {"date": "2025-02-20", "amount": 50000},
                    {"date": "2025-03-01", "amount": -30000},
                ],
            },
        ]

        # Данные банка
        self.bank_data = {"name": "СберБанк"}

        # Данные по рискам
        self.risks = {
            "overall_risk": 0.22,
            "client_risks": {1: 0.15, 2: 0.45, 3: 0.05},
        }

    def build_report(self, report_type: str) -> dict:
        """Формирует структурированные данные отчёта (для JSON/CSV)."""
        # Нормализация типа отчёта (поддержка русского и английского)
        rt = report_type.lower().strip()
        if "клиент" in rt or rt == "client":
            return {"type": "client", "clients": self.clients[:]}
        elif "банк" in rt or rt == "bank":
            total_balance = sum(c["balance"] for c in self.clients)
            return {
                "type": "bank",
                "bank_name": self.bank_data["name"],
                "total_clients": len(self.clients),
                "total_balance": total_balance,
                "clients": [
                    {"name": c["name"], "balance": c["balance"]} for c in self.clients
                ],
            }
        elif "риск" in rt or rt == "risks":
            client_risks_list = []
            for cid, risk in self.risks["client_risks"].items():
                client_name = next(
                    (c["name"] for c in self.clients if c["id"] == cid),
                    f"Клиент {cid}",
                )
                client_risks_list.append({"name": client_name, "risk": risk})
            return {
                "type": "risks",
                "overall_risk": self.risks["overall_risk"],
                "client_risks": client_risks_list,
            }
        else:
            raise ValueError(f"Неизвестный тип отчёта: {report_type}")

    def generate_text_report(self, report_type: str) -> str:
        """Формирует текстовый отчёт."""
        report_data = self.build_report(report_type)

        if report_data["type"] == "client":
            text = "=== ТЕКСТОВЫЙ ОТЧЁТ ПО КЛИЕНТАМ ===\n\n"
            for client in report_data["clients"]:
                text += f"Клиент: {client['name']} (ID: {client.get('id', 'N/A')})\n"
                text += f"Баланс: {client['balance']} руб.\n"
                text += "Транзакции:\n"
                for tx in client.get("transactions", []):
                    text += f"   {tx['date']}: {tx['amount']:+} руб.\n"
                text += "\n" + "-" * 50 + "\n"
            return text

        elif report_data["type"] == "bank":
            text = "=== ТЕКСТОВЫЙ ОТЧЁТ ПО БАНКУ ===\n"
            text += f"Банк: {report_data['bank_name']}\n"
            text += f"Количество клиентов: {report_data['total_clients']}\n"
            text += f"Общий баланс: {report_data['total_balance']} руб.\n\n"
            text += "Клиенты:\n"
            for c in report_data["clients"]:
                text += f" - {c['name']}: {c['balance']} руб.\n"
            return text

        elif report_data["type"] == "risks":
            text = "=== ТЕКСТОВЫЙ ОТЧЁТ ПО РИСКАМ ===\n"
            text += f"Общий уровень риска: {report_data['overall_risk'] * 100:.1f}%\n\n"
            text += "Риски по клиентам:\n"
            for cr in report_data["client_risks"]:
                text += f" - {cr['name']}: {cr['risk'] * 100:.1f}%\n"
            return text

        return "Ошибка формирования текстового отчёта"

    def export_to_json(self, report_type: str, filename: str = None):
        """Экспорт отчёта в JSON."""
        if filename is None:
            filename = f"report_{report_type.replace(' ', '_')}.json"
        report_data = self.build_report(report_type)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
        print(f"✅ JSON-отчёт сохранён: {filename}")

    def export_to_csv(self, report_type: str, filename: str = None):
        """Экспорт отчёта в CSV (табличный формат)."""
        if filename is None:
            filename = f"report_{report_type.replace(' ', '_')}.csv"
        report_data = self.build_report(report_type)

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if report_data["type"] == "client":
                writer.writerow(["Клиент", "Баланс (руб.)"])
                for client in report_data["clients"]:
                    writer.writerow([client["name"], client["balance"]])

            elif report_data["type"] == "bank":
                writer.writerow(["Параметр", "Значение"])
                writer.writerow(["Банк", report_data["bank_name"]])
                writer.writerow(["Количество клиентов", report_data["total_clients"]])
                writer.writerow(["Общий баланс", report_data["total_balance"]])
                writer.writerow([])
                writer.writerow(["Клиент", "Баланс"])
                for c in report_data["clients"]:
                    writer.writerow([c["name"], c["balance"]])

            elif report_data["type"] == "risks":
                writer.writerow(["Клиент", "Риск (%)"])
                for cr in report_data["client_risks"]:
                    writer.writerow([cr["name"], round(cr["risk"] * 100, 2)])

        print(f"✅ CSV-отчёт сохранён: {filename}")

    def save_charts(self):
        """Сохранение всех требуемых диаграмм с помощью matplotlib."""

        # 1. Круговая диаграмма (распределение балансов по клиентам)
        labels = [c["name"] for c in self.clients]
        sizes = [c["balance"] for c in self.clients]
        plt.figure(figsize=(8, 6))
        plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
        plt.title("Распределение балансов по клиентам")
        plt.axis("equal")
        plt.savefig("pie_balance_distribution.png")
        plt.close()
        print("✅ Круговая диаграмма сохранена: pie_balance_distribution.png")

        # 2. Столбчатая диаграмма (балансы клиентов)
        names = [c["name"] for c in self.clients]
        balances = [c["balance"] for c in self.clients]
        plt.figure(figsize=(10, 6))
        plt.bar(names, balances, color="skyblue")
        plt.title("Сравнение балансов клиентов")
        plt.xlabel("Клиенты")
        plt.ylabel("Баланс (руб.)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig("bar_client_balances.png")
        plt.close()
        print("✅ Столбчатая диаграмма сохранена: bar_client_balances.png")

        # 3. График движения баланса (линейный)
        all_transactions = []
        for client in self.clients:
            for tx in client.get("transactions", []):
                all_transactions.append(tx)

        if all_transactions:
            all_transactions.sort(key=lambda x: x["date"])

            # Текущий общий баланс
            current_total = sum(c["balance"] for c in self.clients)
            # Сумма всех транзакций (для расчёта начального баланса)
            total_tx_sum = sum(tx["amount"] for tx in all_transactions)
            initial_balance = current_total - total_tx_sum

            # Группировка изменений по датам
            date_changes = defaultdict(int)
            for tx in all_transactions:
                date_changes[tx["date"]] += tx["amount"]

            sorted_dates = sorted(date_changes.keys())
            running_balance = initial_balance
            dates = []
            balance_values = []

            for date in sorted_dates:
                running_balance += date_changes[date]
                dates.append(date)
                balance_values.append(running_balance)

            plt.figure(figsize=(10, 6))
            plt.plot(dates, balance_values, marker="o", linestyle="-", color="green")
            plt.title("Движение баланса банковской системы")
            plt.xlabel("Дата")
            plt.ylabel("Баланс (руб.)")
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig("line_balance_movement.png")
            plt.close()
            print("✅ График движения баланса сохранён: line_balance_movement.png")
        else:
            print("⚠️ Нет транзакций для графика движения баланса.")


# ===================== ТЕСТИРОВАНИЕ =====================
if __name__ == "__main__":
    print("🚀 Запуск системы генерации отчётов банковской системы...\n")

    builder = ReportBuilder()

    # 1. Генерация текстовых отчётов
    print("1. Текстовый отчёт по клиенту:")
    print(builder.generate_text_report("по клиенту"))
    print("\n2. Текстовый отчёт по банку:")
    print(builder.generate_text_report("по банку"))
    print("\n3. Текстовый отчёт по рискам:")
    print(builder.generate_text_report("по рискам"))

    # 2. Экспорт в JSON и CSV
    builder.export_to_json("по клиенту")
    builder.export_to_json("по банку")
    builder.export_to_json("по рискам")
    builder.export_to_csv("по банку")
    builder.export_to_csv("по рискам")

    # 3. Сохранение графиков
    builder.save_charts()

    print("\n🎉 Все требования домашнего задания выполнены!")
    print("📁 Сгенерированные файлы:")
    print("   • report_*.json")
    print("   • report_*.csv")
    print("   • pie_balance_distribution.png")
    print("   • bar_client_balances.png")
    print("   • line_balance_movement.png")


# In[ ]:




