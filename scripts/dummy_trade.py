from decimal import Decimal

from hummingbot.client.hummingbot_application import HummingbotApplication
from hummingbot.core.data_type.common import OrderType
from hummingbot.core.event.events import BuyOrderCreatedEvent
from hummingbot.core.rate_oracle.rate_oracle import RateOracle
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class Trade(ScriptStrategyBase):
    exchange = "kucoin_paper_trade"
    base = "ETH"
    quote = "USDT"
    trading_pair = f"{base}-{quote}"
    markets = {exchange: {trading_pair}}
    order_amount_USDT = Decimal(100)
    orders_created = 0
    orders_to_create = 3

    def on_tick(self):
        if self.orders_created < self.orders_to_create:
            conversion_rate = RateOracle().get_instance().get_pair_rate(f"{self.base}-USD")
            # rate = self.connectors[self.exchange].rate_oracle.get_rate(self.base)
            base_amount = self.order_amount_USDT / conversion_rate
            price = self.connectors[self.exchange].get_mid_price(self.trading_pair) * Decimal(0.99)
            self.buy(
                connector_name=self.exchange,
                trading_pair=self.trading_pair,
                amount=base_amount,
                order_type=OrderType.LIMIT,
                price=price,
            )

    def did_create_buy_order(self, event: BuyOrderCreatedEvent):
        if event.trading_pair == self.trading_pair:
            self.orders_created += 1
            self.logger().info(
                f"timestamp: {event.timestamp} | "
                f"exchange_order_id: {event.exchange_order_id} | "
                f"order_id: {event.order_id}"
            )
            if self.orders_created == self.orders_to_create:
                self.logger().info("All three orders created!")
                HummingbotApplication.main_application().stop()
