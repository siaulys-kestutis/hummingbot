from hummingbot.strategy.script_strategy_base import ScriptStrategyBase

trading_pair = "ETH-USDT"
trading_pair_DYP = "DYP-USDT"


class LogPrice(ScriptStrategyBase):
    markets = {
        # "binance_paper_trade": {trading_pair_DYP},
        "kucoin_paper_trade": {trading_pair_DYP}
        # "gate_io_paper_trade": {trading_pair_DYP}
    }

    def on_tick(self):
        for connector_name, connector in self.connectors.items():
            # best_ask = connector.get_price(trading_pair_DYP, is_buy=True)
            connector.get_order_book(trading_pair_DYP)
            self.logger().info(
                f"Connector: {connector_name} "
                f" || best ask: {connector.get_price(trading_pair_DYP, is_buy=True)} "
                f" || best bid: {connector.get_price(trading_pair_DYP, is_buy=False)} "
                f" || mid price: {connector.get_mid_price(trading_pair_DYP)}"
            )
            # self.logger().info(f"Connector: {connector_name}")
            # self.logger().info(f"Best ask: {connector.get_price(trading_pair, is_buy=True)}")
            # self.logger().info(f"Best bid: {connector.get_price(trading_pair, is_buy=False)}")
            # self.logger().info(f"Mid price: {connector.get_mid_price(trading_pair)}")
