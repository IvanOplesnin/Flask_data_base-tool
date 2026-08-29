import random

from my_app import app, db
from my_app.models import Experiments, WearTables

app.app_context().push()

exp_s: list[Experiments] = Experiments.query.all()


def add_wear_table(experiment: Experiments):
    step_length = experiment.length_path / 10
    x = [0]
    x.extend([x * step_length for x in range(1, 11)])
    y = [0]
    y.append(round(random.uniform(0.07, 0.12), 3))
    start = y[1]
    for i in range(9):
        if i < 7:
            new_start = round(start + random.uniform(0.015, 0.03), 3)
        else:
            new_start = round(start + random.uniform(0.06, 0.08), 3)
        y.append(new_start)
        start = new_start

    new_table = list(zip(x, y))
    for length, wear in new_table:
        wear_table = WearTables(
            length=length,
            wear=wear,
            experiment_id=experiment.id
        )
        db.session.add(wear_table)
    db.session.commit()


for experiment in exp_s:
    add_wear_table(experiment)

# wear_table = WearTables.query.all()
# for i in wear_table:
#     db.session.delete(i)
# db.session.commit()
