from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.connector.exchange.cube.cube_ws_protobufs import trade_pb2
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "SOL-USDC"

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0004"),
    taker_percent_fee_decimal=Decimal("0.0008"),
    buy_percent_fee_deducted_from_returns=True,
)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information
    :param exchange_info: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    # example:
    # {
    #     "marketId": 100025,
    #     "symbol": "DOGEUSDC",
    #     "baseAssetId": 21,
    #     "baseLotSize": "10000000",
    #     "quoteAssetId": 7,
    #     "quoteLotSize": "1",
    #     "priceDisplayDecimals": 5,
    #     "protectionPriceLevels": 2500,
    #     "priceBandBidPct": 25,
    #     "priceBandAskPct": 400,
    #     "priceTickSize": "0.00001",
    #     "quantityTickSize": "0.1",
    #     "disabled": false,
    #     "feeTableId": 2
    # }

    disable_info: bool = exchange_info.get("disabled", False)

    return not disable_info


def raw_units_to_number(raw_units: trade_pb2.RawUnits):
    # Guard against empty raw_units

    return raw_units.word0 + (raw_units.word1 << 64) + (raw_units.word2 << 128) + (raw_units.word3 << 192)


class CubeConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="cube", const=True, client_data=None)
    cube_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Cube Exchange API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )
    cube_api_secret: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Cube Exchange API secret",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )
    cube_subaccount_id: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Cube Exchange Subaccount ID",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )
    domain = Field(
        default="live",
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Cube environment (live or staging)",
            is_secure=False,
            is_connect_key=True,
            prompt_on_new=True,
        ),
    )

    class Config:
        title = "cube"


KEYS = CubeConfigMap.construct()
