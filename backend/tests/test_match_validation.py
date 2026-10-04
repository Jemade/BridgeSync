import pytest
from pydantic import ValidationError
from app.schemas import MatchInput
from test_product import create, csv_upload


def test_pasted_reference_matches_order(client):
    create(client)
    assert csv_upload(client, "PAY-PASTED,UNKNOWN,129.00,USD\n").status_code == 200
    payment = client.get("/api/payments").json()["items"][0]
    response = client.post(
        "/api/payments/" + payment["id"] + "/match", json={"order_reference": "  ORD-001\t"}
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/payments").json()["items"][0]["order_reference"] == "ORD-001"


@pytest.mark.parametrize("value", [" ", "\t\n"])
def test_blank_match_reference_is_rejected(value):
    with pytest.raises(ValidationError):
        MatchInput(order_reference=value)
