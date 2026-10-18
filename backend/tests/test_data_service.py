from app.services.data_service import shift_from_hour

def test_shift_boundaries():
    assert shift_from_hour(0) == "Night"
    assert shift_from_hour(5) == "Night"
    assert shift_from_hour(6) == "Morning"
    assert shift_from_hour(11) == "Morning"
    assert shift_from_hour(12) == "Afternoon"
    assert shift_from_hour(16) == "Afternoon"
    assert shift_from_hour(17) == "Evening"
    assert shift_from_hour(23) == "Evening"
