from my_app import app, db
from my_app.models import RecommendationParameters
import pandas as pd

with app.app_context():
    data: list[RecommendationParameters] = RecommendationParameters.query.all()

    data_list = []
    for row in data:
        data_list.append({
            'материал': row.material.name,
            'покрытие': row.coating.name,
            'Инструмент': row.tool.name,
            'Обороты шпинделя': row.spindle_speed,
            'Подача стола': row.feed_table,
            'Наклеп': row.hardening,
            'Микротвердость': row.micro_hardness,
            'Стойкость': row.durability,
            'Длина пути': row.durability*row.feed_table
        })


    df = pd.DataFrame(data_list)
    df.to_csv('Recommendation.csv', index=False, encoding='utf-8')
    df.to_excel('Recommendation_parameters.xlsx', index=False)


