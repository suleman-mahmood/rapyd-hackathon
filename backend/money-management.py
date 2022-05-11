import requests
import matplotlib.pyplot as plt
import numpy as np
from random import randint
from datetime import datetime


class Trading:
    def __init__(self):
        # The number of candles for which you want to pull data from Binance API
        # This value should be in multiples of 1000
        self.LIMIT = 8000
        self.ATR_PERIOD = 14
        self.ATR_FACTOR = 1
        self.CURRENCY_PAIR = "STXUSDT"
        self.TIMEFRAME = "5m"
        self.BALANCE = 100

        self.close_prices = []
        self.range_prices = []
        self.atr = []

        self.bankrupt = False
        self.multiple_data = []

        # Graph Parameters
        self.total_trade_amounts = []
        self.total_volatility = []
        self.running_trade_pnl = []
        self.running_balance = []

        # Rechecking LIMIT and converting it to a multiple of 1000
        self.LIMIT = int(int(self.LIMIT / 1000) * 1000)

        self.pull_data_from_api()
        self.calculate_atr()

    def pull_data_from_api(self):
        # Go back one month
        start_time = int(datetime.timestamp(datetime.now())) - 30*24*60*60

        for i in range(0, int(self.LIMIT / 1000)):
            params = {
                "symbol": self.CURRENCY_PAIR,
                "interval": self.TIMEFRAME,
                "limit": self.LIMIT,
                "startTime": start_time,
            }

            if self.TIMEFRAME == "1m":
                start_time += (60) * 1000
            elif self.TIMEFRAME == "5m":
                start_time += (5*60) * 1000
            elif self.TIMEFRAME == "15m":
                start_time += (15*60) * 1000
            elif self.TIMEFRAME == "30m":
                start_time += (30*60) * 1000
            elif self.TIMEFRAME == "1h":
                start_time += (60*60) * 1000
            elif self.TIMEFRAME == "4h":
                start_time += (4*60*60) * 1000

            response = requests.get(
                "https://api.binance.com/api/v3/klines", params=params)
            data = response.json()

            # Extract close price from the data and convert it into numpy array
            self.close_prices += [float(price[4]) for price in data]

            # Calculate range for each candle and convert it into numpy array
            self.range_prices += [(float(price[2]) - float(price[1]))
                                  for price in data]

    def calculate_atr(self):
        self.atr = [None] * self.LIMIT
        for i in range(self.ATR_PERIOD - 1, self.LIMIT):
            sum_values = 0
            for j in range(i - self.ATR_PERIOD + 1, i):
                sum_values += self.range_prices[j]

            sum_values /= self.ATR_PERIOD
            self.atr[i] = float(sum_values)

    def half_martingale(self, is_print=True):
        # Reset class variables
        self.total_trade_amounts = []
        self.total_volatility = []
        self.running_trade_pnl = []
        self.running_balance = []
        self.bankrupt = False

        PERCENTAGE_RISK = 5 / 100

        in_trade = False  # Whether you are in trade or not
        take_profit = 0
        stop_loss = 0
        trade_type = 0
        opening_price = 0
        gross_profit = self.BALANCE
        winners = 0  # Total number of winners
        loosers = 0  # Total number of loosers
        trade_amount = 0  # The amount of trade you want to take
        profit_grid = [
            PERCENTAGE_RISK * self.BALANCE,
            PERCENTAGE_RISK * self.BALANCE,
            PERCENTAGE_RISK * self.BALANCE,
            PERCENTAGE_RISK * self.BALANCE
        ]

        highest_balance = -1
        lowest_balance = self.BALANCE * 10
        max_trade_amount = -1

        for i in range(self.ATR_PERIOD - 1, self.LIMIT):
            if not in_trade:
                in_trade = True
                trade_type = randint(0, 1)
                opening_price = self.close_prices[i]

                if gross_profit < lowest_balance:
                    lowest_balance = gross_profit

                if gross_profit > highest_balance:
                    highest_balance = gross_profit

                # Adjust grid and calculate trade amount to put in next trade
                if len(profit_grid) == 0:
                    # Reset profit grid
                    profit_grid = [
                        PERCENTAGE_RISK * self.BALANCE,
                        PERCENTAGE_RISK * self.BALANCE,
                        PERCENTAGE_RISK * self.BALANCE,
                        PERCENTAGE_RISK * self.BALANCE
                    ]
                    trade_amount = profit_grid[0] + profit_grid[-1]
                elif len(profit_grid) == 1:
                    trade_amount = profit_grid[0]
                else:
                    trade_amount = profit_grid[0] + profit_grid[-1]

                if gross_profit < 0:
                    if is_print:
                        print("BANKRUPT!!!")
                        print("Running Balance:", gross_profit)
                        print("Grid:", profit_grid)
                    self.bankrupt = True
                    break

                if trade_amount > max_trade_amount:
                    max_trade_amount = trade_amount
                self.total_trade_amounts.append(trade_amount)

                volatility = self.atr[i] * self.ATR_FACTOR
                self.total_volatility.append(volatility)

                if trade_type == 1:
                    take_profit = self.close_prices[i] + volatility
                    stop_loss = self.close_prices[i] - volatility
                else:
                    take_profit = self.close_prices[i] - volatility
                    stop_loss = self.close_prices[i] + volatility

            else:
                if trade_type == 1:
                    if self.close_prices[i] >= take_profit:
                        winners += 1
                        in_trade = False
                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount
                        gross_profit += curr_trade_pnl
                        self.running_balance.append(gross_profit)
                        self.running_trade_pnl.append(curr_trade_pnl)

                        if len(profit_grid) == 1:
                            profit_grid = []
                        else:
                            profit_grid = profit_grid[1:-1]

                    elif self.close_prices[i] <= stop_loss:
                        loosers += 1
                        in_trade = False
                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount
                        gross_profit -= curr_trade_pnl
                        self.running_balance.append(gross_profit)
                        self.running_trade_pnl.append(-1 * curr_trade_pnl)
                        profit_grid.append(trade_amount)

                else:
                    if self.close_prices[i] <= take_profit:
                        winners += 1
                        in_trade = False
                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount
                        gross_profit += curr_trade_pnl
                        self.running_balance.append(gross_profit)
                        self.running_trade_pnl.append(curr_trade_pnl)
                        if len(profit_grid) == 1:
                            profit_grid = []
                        else:
                            profit_grid = profit_grid[1:-1]
                    elif self.close_prices[i] >= stop_loss:
                        loosers += 1
                        in_trade = False
                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount
                        gross_profit -= curr_trade_pnl
                        self.running_balance.append(gross_profit)
                        self.running_trade_pnl.append(-1 * curr_trade_pnl)
                        profit_grid.append(trade_amount)

        # Print Statistics
        if is_print:
            print("Winners:", winners)
            print("Loosers:", loosers)
            print("Initial Balance:", self.BALANCE)
            print("Final Balance:", gross_profit)
            print("Net Profit/Loss:", gross_profit - self.BALANCE)
            print("Highest Balance:", highest_balance)
            print("Lowest Balance:", lowest_balance)
            print("Max Trade Amount:", max_trade_amount)

        return {
            "final_balance": gross_profit,
            "net_pnl": gross_profit - self.BALANCE,
            "highest_balance": highest_balance,
            "lowest_balance": lowest_balance,
            "max_trade_amount": max_trade_amount,
            "bankrupt": self.bankrupt,
        }

    def half_martingale_multiple(self):
        number_of_trials = 10000
        self.multiple_data = []
        last_value = 0

        for i in range(0, number_of_trials):
            self.multiple_data.append(self.half_martingale(is_print=False))

            if (int((i / number_of_trials) * 100) % 5) == 0 and last_value != int((i / number_of_trials) * 100):
                print("Progress:", int((i / number_of_trials) * 100))
                last_value = int((i / number_of_trials) * 100)

        number_of_bankruptcies = 0
        number_of_wins = 0
        net_money_index = 0

        for item in self.multiple_data:
            if item["bankrupt"]:
                number_of_bankruptcies += 1

            if item["net_pnl"] >= 0:
                number_of_wins += 1
                net_money_index += item["net_pnl"]

        number_of_losses = number_of_trials - number_of_wins
        net_money_index /= (self.BALANCE * number_of_losses)

        # Print Statistics
        print("Number of Bankrupts:", number_of_bankruptcies)
        print("Percentage of Bankrupts:",
              (number_of_bankruptcies / number_of_trials) * 100)

        print("Number of Wins:", number_of_wins)
        print("Percentage of Wins:", (number_of_wins / number_of_trials) * 100)

        print("Net Money Index:", net_money_index)

    def martingale(self):
        PERCENTAGE_RISK = 1 / 100

        in_trade = False  # Whether you are in trade or not
        trade_type = 0
        opening_price = 0
        gross_profit = self.BALANCE
        # The amount of trade you want to take
        trade_amount = self.BALANCE * PERCENTAGE_RISK
        winners = 0  # Total number of winners
        loosers = 0  # Total number of loosers

        # upper_limit = 100

        for i in range(self.ATR_PERIOD - 1, self.LIMIT):
            if not in_trade:
                in_trade = True
                trade_type = randint(0, 1)
                opening_price = self.close_prices[i]

                if trade_amount > gross_profit:
                    print(trade_amount, gross_profit)
                    self.bankrupt = True
                    break

                self.total_trade_amounts.append(trade_amount)

                volatility = self.atr[i] * self.ATR_FACTOR
                self.total_volatility.append(volatility)

                if trade_type == 1:
                    take_profit = self.close_prices[i] + volatility
                    stop_loss = self.close_prices[i] - volatility
                else:
                    take_profit = self.close_prices[i] - volatility
                    stop_loss = self.close_prices[i] + volatility

            else:
                if trade_type == 1:
                    if self.close_prices[i] >= take_profit:
                        winners += 1
                        in_trade = False

                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount
                        gross_profit += curr_trade_pnl

                        # The amount of trade you want to take
                        trade_amount = self.BALANCE * PERCENTAGE_RISK

                        self.running_trade_pnl.append(curr_trade_pnl)

                    elif self.close_prices[i] <= stop_loss:
                        loosers += 1
                        in_trade = False

                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount

                        gross_profit -= curr_trade_pnl
                        trade_amount = 2 * curr_trade_pnl  # Double trade amount loss on a losing trade

                        self.running_trade_pnl.append(-1 * curr_trade_pnl)

                else:
                    if self.close_prices[i] <= take_profit:
                        winners += 1
                        in_trade = False

                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount
                        gross_profit += curr_trade_pnl

                        # The amount of trade you want to take
                        trade_amount = self.BALANCE * PERCENTAGE_RISK

                        self.running_trade_pnl.append(curr_trade_pnl)

                    elif self.close_prices[i] >= stop_loss:
                        loosers += 1
                        in_trade = False

                        curr_trade_pnl = abs(
                            self.close_prices[i] - opening_price) * trade_amount

                        gross_profit -= curr_trade_pnl
                        trade_amount = 2 * curr_trade_pnl  # Double trade amount loss on a losing trade

                        self.running_trade_pnl.append(-1 * curr_trade_pnl)

        # Print Statistics
        print("Winners:", winners)
        print("Loosers:", loosers)
        print("Initial Balance:", self.BALANCE)
        print("Final Balance:", gross_profit)
        print("Net Profit/Loss:", gross_profit - self.BALANCE)

    def plot_graph(self):

        x = np.arange(0, len(self.total_trade_amounts), 1)
        plt.plot(x, self.total_trade_amounts, label="Trade Amounts")

        x = np.arange(0, len(self.running_trade_pnl), 1)
        plt.plot(x, self.running_trade_pnl, label="Running PNL")

        x = np.arange(0, len(self.total_volatility), 1)
        plt.plot(x, self.total_volatility, label="Total Volatility")

        x = np.arange(0, len(self.running_balance), 1)
        plt.plot(x, self.running_balance, label="Running Balance")

        plt.legend()
        plt.show()

    def plot_graph_of_multiple(self):

        # y = [data_item["final_balance"] for data_item in self.multiple_data]
        # x = np.arange(0, len(y), 1)
        # plt.plot(x, y, label="final_balance")

        y = [data_item["net_pnl"] for data_item in self.multiple_data]
        x = np.arange(0, len(y), 1)
        plt.plot(x, y, label="net_pnl")

        # y = [data_item["highest_balance"] for data_item in self.multiple_data]
        # x = np.arange(0, len(y), 1)
        # plt.plot(x, y, label="highest_balance")

        # y = [data_item["lowest_balance"] for data_item in self.multiple_data]
        # x = np.arange(0, len(y), 1)
        # plt.plot(x, y, label="lowest_balance")

        # y = [data_item["max_trade_amount"] for data_item in self.multiple_data]
        # x = np.arange(0, len(y), 1)
        # plt.plot(x, y, label="max_trade_amount")

        plt.legend()
        plt.show()


def main():
    bot = Trading()

    # bot.martingale()
    # bot.plot_graph()

    bot.half_martingale()
    bot.plot_graph()

    # bot.half_martingale_multiple()
    # bot.plot_graph_of_multiple()


if __name__ == "__main__":
    main()

# winner_result = []
# looser_result = []
# PL_result = []

# Plot the graph of close values
# x = np.arange(0, LIMIT, 1)
# y = close_prices
# plt.plot(x, y, label="prices")
# plt.show()

# x = np.arange(0, len(winner_result), 1)
# plt.plot(x, winner_result, label="winning trades")
# plt.plot(x, looser_result, label="loosing trades")
# plt.plot(x, PL_result, label="profit and loss")
# plt.show()
