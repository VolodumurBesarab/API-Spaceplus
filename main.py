from start_program import StartProgram

start_program = StartProgram()

# start_program.start()

start_program.check_connection()

# Видаліть наступний рядок, оскільки ви вже імпортували клас StartProgram
# from start_program import import_product

# Приклад виклику методу імпорту товару з екземпляра класу StartProgram
if __name__ == '__main__':
    new_product_data = {
        "name": "Новий товар",
        "type": "simple",
        "regular_price": "10.00",
        "description": "Це новий товар",
        "short_description": "Новий товар для тестування",
        "categories": [{"id": 1}],
        "images": [{"src": "https://static4.winylownia.pl/pol_pl_PLACEBO-Placebo-LP-60305_1.jpg"}]
    }

    response = start_program.import_product(new_product_data)
    print('Відповідь API:', response)