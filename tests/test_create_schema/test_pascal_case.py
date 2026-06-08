from db_models.cli.create_schema import pascal_case


def test_single_word():
    assert pascal_case("example") == "Example"


def test_two_words():
    assert pascal_case("data_quality") == "DataQuality"


def test_three_words():
    assert pascal_case("order_line_item") == "OrderLineItem"
