from hummingbot.strategy.script_strategy_base import ScriptStrategyBase

trading_pair = "ETH-USDT"


class DummyStatus(ScriptStrategyBase):
    markets = {
        "binance_paper_trade": {trading_pair},
        "kucoin_paper_trade": {trading_pair},
        "gate_io_paper_trade": {trading_pair},
    }

    def format_status(self) -> str:
        if not self.ready_to_trade:
            return "Market connectors are not ready."
        lines = []
        warning_lines = []
        warning_lines.extend(self.network_warning(self.get_market_trading_pair_tuples()))

        balance_df = self.get_balance_df()
        market_status_df = self.get_market_status_df_with_depth()

        lines.extend(["", "  Balances:"] + ["    " + line for line in balance_df.to_string(index=False).split("\n")])
        lines.extend(
            ["", "  Data Frame:"] + ["    " + line for line in market_status_df.to_string(index=False).split("\n")]
        )

        # try:
        #     df = self.active_orders_df()
        #     lines.extend(["", "  Orders:"] + ["    " + line for line in df.to_string(index=False).split("\n")])
        # except ValueError:
        #     lines.extend(["", "  No active maker orders."])

        warning_lines.extend(self.balance_warning(self.get_market_trading_pair_tuples()))
        if len(warning_lines) > 0:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)
        return "\n".join(lines)

    def get_market_status_df_with_depth(self):
        trading_pairs = self.get_market_trading_pair_tuples()
        market_status_df = self.market_status_data_frame(trading_pairs)
        market_status_df["Exchange"] = market_status_df.apply(
            lambda x: x["Exchange"].strip("PaperTrade") + "paper_trade", axis=1
        )

        one_percent_up = (
            lambda x: self.connectors[x["Exchange"]]
            .get_volume_for_price(x["Market"], True, x["Mid Price"] * 1.01)
            .result_volume
        )
        one_percent_down = (
            lambda x: self.connectors[x["Exchange"]]
            .get_volume_for_price(x["Market"], False, x["Mid Price"] * 0.99)
            .result_volume
        )

        market_status_df["Vol (+1)"] = market_status_df.apply(one_percent_up, axis=1)
        market_status_df["Vol (+1) video"] = market_status_df.apply(
            lambda x: self.get_volume_for_percentage_from_mid_price(x, 0.01), axis=1
        )

        market_status_df["Vol (-1)"] = market_status_df.apply(one_percent_down, axis=1)
        market_status_df["Vol (-1) video"] = market_status_df.apply(
            lambda x: self.get_volume_for_percentage_from_mid_price(x, -0.01), axis=1
        )

        return market_status_df

    def get_volume_for_percentage_from_mid_price(self, row, percentage):
        price = row["Mid Price"] * (1 + percentage)
        is_buy = percentage > 0
        market = row["Market"]
        return self.connectors[row["Exchange"]].get_volume_for_price(market, is_buy, price).result_volume
