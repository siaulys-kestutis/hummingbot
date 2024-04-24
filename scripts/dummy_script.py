from hummingbot.strategy.script_strategy_base import ScriptStrategyBase


class DummyScript(ScriptStrategyBase):
    markets = {"binance_paper_trade": {"ETH-USDT", "BTC-USDT"}}

    def on_tick(self):
        self.logger().info("Hello World")
