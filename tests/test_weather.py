from weather import code_to_icon


def test_clear_sky_maps_to_sun():
    assert code_to_icon(0) == "sun"


def test_partly_cloudy_maps_to_cloud():
    # WMO codes 1, 2, 3 = mainly clear, partly cloudy, overcast
    assert code_to_icon(2) == "cloud"
    assert code_to_icon(3) == "cloud"


def test_fog_maps_to_fog():
    # 45 = fog, 48 = depositing rime fog
    assert code_to_icon(45) == "fog"
    assert code_to_icon(48) == "fog"


def test_drizzle_and_rain_map_to_rain():
    # 51-67 covers drizzle, rain
    assert code_to_icon(51) == "rain"
    assert code_to_icon(61) == "rain"
    assert code_to_icon(65) == "rain"


def test_snow_maps_to_snow():
    # 71-77 covers snow
    assert code_to_icon(71) == "snow"
    assert code_to_icon(75) == "snow"


def test_showers_map_to_rain():
    # 80-82 = rain showers
    assert code_to_icon(80) == "rain"


def test_snow_showers_map_to_snow():
    # 85-86 = snow showers
    assert code_to_icon(85) == "snow"


def test_thunderstorm_maps_to_rain():
    # 95-99 = thunderstorms (we lump into rain since we don't have a storm icon)
    assert code_to_icon(95) == "rain"


def test_unknown_code_maps_to_unknown():
    assert code_to_icon(999) == "unknown"
    assert code_to_icon(-1) == "unknown"
