import pytest

from my_app.services.calculations import calculate_cutting_parameters


def test_calculate_cutting_parameters_returns_expected_values():
    result = calculate_cutting_parameters(10, 20, 30, 100, 0.1)

    assert result.cutting_force > 0
    assert result.cutting_temperature > 0
    assert result.tool_life > 0


@pytest.mark.parametrize('speed, feed', [(0, 0.1), (100, 0), (-1, 0.1)])
def test_calculate_cutting_parameters_rejects_non_positive_inputs(speed, feed):
    with pytest.raises(ValueError):
        calculate_cutting_parameters(10, 20, 30, speed, feed)
