from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from .constants import SUPPORTED_CURRENCIES


API_URL = "https://api.frankfurter.dev/v1/latest"
REQUEST_TIMEOUT = 10


class CurrencyConverterError(Exception):
    """Base exception for currency conversion errors."""


class UnsupportedCurrencyError(CurrencyConverterError):
    """Raised when a requested currency is not supported."""


class InvalidAmountError(CurrencyConverterError):
    """Raised when an amount is invalid."""


class CurrencyAPIError(CurrencyConverterError):
    """Raised when the external currency API request fails."""


class CurrencyConverter:
    @staticmethod
    def get_price(quote: str, base: str, amount: str) -> Decimal:
        quote = quote.strip().upper()
        base = base.strip().upper()

        if quote == base:
            raise CurrencyConverterError(
                f"Unable to convert {quote} to the same currency."
            )

        if quote not in SUPPORTED_CURRENCIES:
            raise UnsupportedCurrencyError(
                f"Unsupported currency: {quote}."
            )

        if base not in SUPPORTED_CURRENCIES:
            raise UnsupportedCurrencyError(
                f"Unsupported currency: {base}."
            )

        try:
            parsed_amount = Decimal(amount)
        except InvalidOperation as exc:
            raise InvalidAmountError(
                f"Invalid amount: {amount}."
            ) from exc

        if parsed_amount <= 0:
            raise InvalidAmountError(
                "Amount must be greater than zero."
            )

        try:
            response = requests.get(
                API_URL,
                params={
                    "base": quote,
                    "symbols": base,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise CurrencyAPIError(
                "The currency service request timed out."
            ) from exc
        except requests.RequestException as exc:
            raise CurrencyAPIError(
                "The currency service is currently unavailable."
            ) from exc

        try:
            data: dict[str, Any] = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise CurrencyAPIError(
                "The currency service returned an invalid response."
            ) from exc

        rates = data.get("rates")

        if not isinstance(rates, dict):
            raise CurrencyAPIError(
                "The currency service returned an unexpected response."
            )

        rate = rates.get(base)

        if rate is None:
            raise CurrencyAPIError(
                "The requested exchange rate was not found."
            )

        try:
            decimal_rate = Decimal(str(rate))
        except InvalidOperation as exc:
            raise CurrencyAPIError(
                "The currency service returned an invalid exchange rate."
            ) from exc

        return parsed_amount * decimal_rate