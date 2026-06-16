from api.city_groups import expand_airport, CITY_GROUPS, AIRPORT_TO_GROUP

def test_expand_known_airport():
    # FCO should expand to the Rome group [FCO, CIA]
    res = expand_airport("FCO")
    assert "FCO" in res
    assert "CIA" in res
    assert len(res) == 2

def test_expand_unknown_airport():
    # XYZ is unknown, should return [XYZ]
    res = expand_airport("XYZ")
    assert res == ["XYZ"]

def test_no_duplicates_in_group():
    # Ensure there are no duplicate airport codes in any city group list
    for group, iatas in CITY_GROUPS.items():
        assert len(iatas) == len(set(iatas)), f"Group {group} contains duplicates"

def test_inverse_index_complete():
    # Every IATA in CITY_GROUPS should be present in the inverse index mapping
    for group, iatas in CITY_GROUPS.items():
        assert group in AIRPORT_TO_GROUP
        for iata in iatas:
            assert iata in AIRPORT_TO_GROUP
            assert AIRPORT_TO_GROUP[iata] == iatas
