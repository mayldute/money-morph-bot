from decimal import Decimal
from typing import Any

import pytest
import requests

from money_morph_bot.converter import (
    API_URL,
    REQUEST_TIMEOUT,
    CurrencyAPIError,
    CurrencyConverter,
    CurrencyConverterError,
    InvalidAmountError,
    UnsupportedCurrencyError,
)


SUCCESSFUL_RESPONSE = {
    "amount": 1.0,
    "base": "USD",
    "date": "2026-07-14",
    "rates": {
        "EUR": 0.92,
    },
}


class FakeResponse:
    def __init__(
        self,
        json_data: dict[str, Any] | None = None,
        status_error: requests.RequestException | None = None,
        json_error: Exception | None = None,
    ) -> None:
        self._json_data = json_data
        self._status_error = status_error
        self._json_error = json_error

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self) -> dict[str, Any]:
        if self._json_error is not None:
            raise self._json_error

        if self._json_data is None:
            return {}

        return self._json_data


def test_get_price_returns_converted_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(json_data=SUCCESSFUL_RESPONSE)

    monkeypatch.setattr(requests, "get", fake_get)

    result = CurrencyConverter.get_price(
        quote="USD",
        base="EUR",
        amount="100",
    )

    assert result == Decimal("92.00")


def test_get_price_normalizes_currency_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(json_data=SUCCESSFUL_RESPONSE)

    monkeypatch.setattr(requests, "get", fake_get)

    result = CurrencyConverter.get_price(
        quote=" usd ",
        base=" eur ",
        amount="10",
    )

    assert result == Decimal("9.20")


def test_get_price_supports_decimal_amount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse(json_data=SUCCESSFUL_RESPONSE)

    monkeypatch.setattr(requests, "get", fake_get)

    result = CurrencyConverter.get_price(
        quote="USD",
        base="EUR",
        amount="10.50",
    )

    assert result == Decimal("9.660")


def test_get_price_sends_expected_request_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request: dict[str, Any] = {}

    def fake_get(
        url: str,
        **kwargs: Any,
    ) -> FakeResponse:
        captured_request["url"] = url
        captured_request.update(kwargs)

        return FakeResponse(json_data=SUCCESSFUL_RESPONSE)

    monkeypatch.setattr(requests, "get", fake_get)

    CurrencyConverter.get_price(
        quote="USD",
        base="EUR",
        amount="10",
    )

    assert captured_request["url"] == API_URL
    assert captured_request["params"] == {
        "base": "USD",
        "symbols": "EUR",
    }
    assert captured_request["timeout"] == REQUEST_TIMEOUT


def test_get_price_rejects_same_currency() -> None:
    with pytest.raises(
        CurrencyConverterError,
        match="Unable to convert USD to the same currency",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="USD",
            amount="100",
        )


def test_get_price_normalizes_codes_before_comparing_currencies() -> None:
    with pytest.raises(
        CurrencyConverterError,
        match="Unable to convert USD to the same currency",
    ):
        CurrencyConverter.get_price(
            quote=" usd ",
            base="USD",
            amount="100",
        )


@pytest.mark.parametrize(
    "currency",
    ["ABC", "XYZ", "ZZZ"],
)
def test_get_price_rejects_unsupported_quote_currency(
    currency: str,
) -> None:
    with pytest.raises(
        UnsupportedCurrencyError,
        match=f"Unsupported currency: {currency}",
    ):
        CurrencyConverter.get_price(
            quote=currency,
            base="EUR",
            amount="100",
        )


@pytest.mark.parametrize(
    "currency",
    ["ABC", "XYZ", "ZZZ"],
)
def test_get_price_rejects_unsupported_base_currency(
    currency: str,
) -> None:
    with pytest.raises(
        UnsupportedCurrencyError,
        match=f"Unsupported currency: {currency}",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base=currency,
            amount="100",
        )


@pytest.mark.parametrize(
    "amount",
    ["abc", "", "12,50"],
)
def test_get_price_rejects_non_numeric_amount(
    amount: str,
) -> None:
    with pytest.raises(
        InvalidAmountError,
        match="Invalid amount",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount=amount,
        )


@pytest.mark.parametrize(
    "amount",
    ["0", "-1", "-100.50"],
)
def test_get_price_rejects_non_positive_amount(
    amount: str,
) -> None:
    with pytest.raises(
        InvalidAmountError,
        match="Amount must be greater than zero",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount=amount,
        )


def test_get_price_handles_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        raise requests.Timeout

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(
        CurrencyAPIError,
        match="request timed out",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )


def test_get_price_handles_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        raise requests.ConnectionError

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(
        CurrencyAPIError,
        match="currently unavailable",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )


def test_get_price_handles_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        status_error=requests.HTTPError("500 Server Error"),
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        CurrencyAPIError,
        match="currently unavailable",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )


def test_get_price_handles_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        json_error=requests.exceptions.JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        CurrencyAPIError,
        match="invalid response",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )


@pytest.mark.parametrize(
    "json_data",
    [
        {},
        {"base": "USD"},
        {"rates": None},
        {"rates": []},
        {"rates": "invalid"},
    ],
)
def test_get_price_handles_invalid_rates_structure(
    monkeypatch: pytest.MonkeyPatch,
    json_data: dict[str, Any],
) -> None:
    response = FakeResponse(json_data=json_data)

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        CurrencyAPIError,
        match="unexpected response",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )


def test_get_price_handles_missing_exchange_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        json_data={
            "amount": 1.0,
            "base": "USD",
            "date": "2026-07-14",
            "rates": {},
        },
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        CurrencyAPIError,
        match="exchange rate was not found",
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )


@pytest.mark.parametrize(
    "rate",
    ["not-a-number", "", None],
)
def test_get_price_handles_invalid_exchange_rate(
    monkeypatch: pytest.MonkeyPatch,
    rate: str | None,
) -> None:
    response = FakeResponse(
        json_data={
            "amount": 1.0,
            "base": "USD",
            "date": "2026-07-14",
            "rates": {
                "EUR": rate,
            },
        },
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    expected_message = (
        "exchange rate was not found"
        if rate is None
        else "invalid exchange rate"
    )

    with pytest.raises(
        CurrencyAPIError,
        match=expected_message,
    ):
        CurrencyConverter.get_price(
            quote="USD",
            base="EUR",
            amount="100",
        )