import math
from decimal import Decimal
from typing import Dict

from hummingbot.connector.utils import split_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.order_candidate import OrderCandidate
from hummingbot.core.event.events import OrderFilledEvent
from hummingbot.core.rate_oracle.rate_oracle import RateOracle
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class SimpleVWAP(ScriptStrategyBase):
    last_ordered_ts = 0
    vwap: Dict = {
        "connector_name": "kucoin_paper_trade",
        "trading_pair": "ETH-USDT",
        "is_buy": True,
        "total_volume_usd": 100_000,
        "price_spread": 0.01,
        "volume_pct": 0.01,
        "order_delay_time": 5,
    }

    markets = {vwap["connector_name"]: {vwap["trading_pair"]}}

    def on_tick(self):
        # is time to buy (i.e., enough time has passed since the placement of the last order)
        if self.last_ordered_ts + self.vwap["order_delay_time"] < self.current_timestamp:
            # if VWAP not active
            if self.vwap.get("status") is None:
                # init VWAP
                self.init_vwap()
            # if VWAP active
            elif self.vwap["status"] == "ACTIVE":
                # create order candidate
                order: OrderCandidate = self.create_order()
                # adjust order to budget with BudgetChecker
                adjusted_order = self.vwap["connector"].budget_checker.adjust_candidate(order, all_or_none=False)
                # if balance NOT enough
                if math.isclose(adjusted_order.amount, Decimal(0), rel_tol=1e-4):
                    # LOG that NOT enough balance
                    self.logger().info("The balance is NOT enough to send the order")
                # if the balance is enough
                else:
                    # place the order
                    self.place_order(adjusted_order)
                    # update last_ordered_ts
                    # (should this NOT be done only in cases when the order gets actually created
                    # (i.e. have BuyOrderCreatedEvent or SellOrderCreatedEvent))
                    self.last_ordered_ts = self.current_timestamp

    def did_fill_order(self, event: OrderFilledEvent):
        if event.trading_pair == self.vwap["trading_pair"] and event.trade_type == self.vwap["trade_type"]:
            self.vwap["volume_remaining"] -= event.amount
            self.vwap["delta"] = 1 - self.vwap["volume_remaining"] / self.vwap["target_base_volume"]
            self.vwap["real_quote_volume"] += event.amount * event.price
            if math.isclose(self.vwap["delta"], Decimal(1), rel_tol=1e-4):
                self.vwap["status"] = "COMPLETED"

    def place_order(self, order: OrderCandidate):
        if order.order_side == TradeType.SELL:
            self.sell(
                connector_name=self.vwap["connector_name"],
                trading_pair=self.vwap["trading_pair"],
                amount=order.amount,
                order_type=order.order_type,
                price=order.price,
            )
        elif order.order_side == TradeType.BUY:
            self.buy(
                connector_name=self.vwap["connector_name"],
                trading_pair=self.vwap["trading_pair"],
                amount=order.amount,
                order_type=order.order_type,
                price=order.price,
            )

    def create_order(self):
        is_buy = self.vwap["is_buy"]
        price_spread = self.vwap["price_spread"]
        trading_pair = self.vwap["trading_pair"]

        # TODO: note that this is copied from the default VWAP example script
        mid_price = float(self.vwap["connector"].get_mid_price(self.vwap["trading_pair"]))
        price_multiplier = 1 + price_spread if is_buy else 1 - price_spread
        affected_mid_price = mid_price * price_multiplier

        result = self.vwap["connector"].get_volume_for_price(trading_pair, is_buy, affected_mid_price)

        volume = result.result_volume
        volume_affected = volume * self.vwap["volume_pct"]
        # this is to prevent buying more towards the end of the VWAP run than intended
        amount = min(volume_affected, self.vwap["volume_remaining"])

        amount_quantized = self.vwap["connector"].quantize_order_amount(trading_pair, amount)
        price_quantized = self.vwap["connector"].quantize_order_price(trading_pair, affected_mid_price)

        return OrderCandidate(
            trading_pair=trading_pair,
            is_maker=False,
            order_type=OrderType.MARKET,
            order_side=self.vwap["trade_type"],
            amount=amount_quantized,
            price=price_quantized,
        )

    def init_vwap(self):
        vwap = self.vwap.copy()
        vwap["connector"] = self.connectors[vwap["connector_name"]]
        # delta parameter determined whenever or NOT the VWAP process is completed
        vwap["delta"] = 0
        vwap["status"] = "ACTIVE"
        vwap["trade_type"] = TradeType.BUY if vwap["is_buy"] else TradeType.SELL

        base_asset, quote_asset = split_hb_trading_pair(vwap["trading_pair"])

        # is it not the case that this would only work if total_volume_usd was actually total_volume_USDT because:
        # base_conversion: "ETH-USDT"
        # quote_conversion: "USDT-USDT"
        # NOTE: made the change
        # note that need to change RateOracle to CoinGecko for USD conversion;
        # otherwise, base_conversion // quote_conversion would be received as None
        base_conversion_trading_pair = f"{base_asset}-USDT"
        quote_conversion_trading_pair = f"{quote_asset}-USDT"

        base_conversion = RateOracle().get_instance().get_pair_rate(base_conversion_trading_pair)
        quote_conversion = RateOracle().get_instance().get_pair_rate(quote_conversion_trading_pair)

        # start price: when the VWAP start
        vwap["start_price"] = vwap["connector"].get_mid_price(vwap["trading_pair"])

        # target base volume: target volume in base asset with the start price conversion
        vwap["target_base_volume"] = vwap["total_volume_usd"] / base_conversion

        # ideal quote volume: volume if the trade gets executed without slippage
        vwap["ideal_quote_volume"] = vwap["total_volume_usd"] / quote_conversion

        result = vwap["connector"].get_quote_volume_for_base_amount(
            vwap["trading_pair"], vwap["is_buy"], vwap["target_base_volume"]
        )

        # the same as target_base_volume // market order base volume: volume of base asset with a market order
        vwap["market_base_volume"] = result.query_volume
        # market order quote volume: volume of the quote asset with a market order
        # actual expected quote volume at the start
        vwap["market_quote_volume"] = result.result_volume

        # volume remaining: volume required to finish the VWAP
        vwap["volume_remaining"] = vwap["target_base_volume"]
        # real quote volume: the real performance of the strategy (i.e., the amount in quote spent)
        vwap["real_quote_volume"] = Decimal(0)

        self.vwap = vwap

        # ideal_quote_volume:   100_000 USDT (without slippage)
        #                       acquiring everything at the top level at the start of VWAP
        # market_quote_volume:  what would it actually cost at the start of VWAP to acquire all the coin in USDT
        #                       (because may need to clear multiple levels)
        # real_quote_volume:    how much quote was actually spent in USDT

        # target_base_volume = market_base_volume = 100_000 / base_conversion

        # basically, the VWAP algorithm is willing to spend the required amount of USDT in order to hit target_base_volume
        # that gets calculated by using start_price at the beginning of VWAP

    def format_status(self) -> str:
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = []
        warning_lines = []
        warning_lines.extend(self.network_warning(self.get_market_trading_pair_tuples()))

        balance_df = self.get_balance_df()
        lines.extend(["", "  Balances:"] + ["    " + line for line in balance_df.to_string(index=False).split("\n")])

        try:
            df = self.active_orders_df()
            lines.extend(["", "  Orders:"] + ["    " + line for line in df.to_string(index=False).split("\n")])
        except ValueError:
            lines.extend(["", "  No active maker orders."])

        lines.extend(
            ["", "VWAP info:"] + ["    " + key + ": " + value for key, value in self.vwap.items() if type(value) is str]
        )
        lines.extend(
            ["", "VWAP stats:"]
            + [
                "    " + key + ": " + str(value)
                for key, value in self.vwap.items()
                if type(value) in [int, float, Decimal]
            ]
        )

        warning_lines.extend(self.balance_warning(self.get_market_trading_pair_tuples()))
        if len(warning_lines) > 0:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)
        return "\n".join(lines)
