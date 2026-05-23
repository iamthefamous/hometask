from app.utils.normalization import extract_canonical_person_name


def test_extracts_short_name_from_role_suffix():
    value = "Aisha Malik Consumer News Reporter"
    assert extract_canonical_person_name(value) == "Aisha Malik"


def test_extracts_short_name_from_bio_text():
    value = (
        "Amanda Silberling Senior Writer Amanda Silberling is a senior writer at TechCrunch. "
        "You can contact by emailing amanda@techcrunch.com."
    )
    assert extract_canonical_person_name(value) == "Amanda Silberling"


def test_returns_none_for_non_name_string():
    assert extract_canonical_person_name("Audience Development Manager") is None
