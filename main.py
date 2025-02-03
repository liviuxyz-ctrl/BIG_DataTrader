import os
import time
import json
import logging
import numpy as np
import pandas as pd
import dask.dataframe as dd
import matplotlib.pyplot as plt
import cudf
import cupy as cp
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from dask import delayed, compute

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_sim.log'),
        logging.StreamHandler()
    ]
)


class EnhancedTradingSimulator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Advanced Crypto Trading Simulator")
        self.root.geometry("1400x1000")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Simulation parameters (money based)
        self.params = {
            'initial_budget': tk.DoubleVar(value=10000),
            'investment_per_trade': tk.DoubleVar(value=1000),
            'max_trades': tk.StringVar(value="")  # optional; if empty, calculated from budget
        }
        # Parameter for parallel partitions (for parallel strategy)
        self.parallel_partitions = tk.IntVar(value=4)

        # Strategy selection variable
        self.strategy_var = tk.StringVar(value="Evenly Spaced Buys")

        # Data variables
        self.df = None  # Filtered DataFrame (date-range applied) used in simulation
        self.full_df = None  # Full DataFrame loaded from CSV (used for refreshing)
        self.file_path = None
        self.file_list = []
        self.filtered_files = []
        self.final_value = 0
        self.roi = 0
        self.buy_signals = pd.DataFrame()
        self.trade_positions = []  # For moving average strategy
        self.execution_time = None  # For parallel simulation

        # Variable to show simulation results (bigger font)
        self.results_var = tk.StringVar()

        # Build UI with a Notebook (two tabs: Simulation and Benchmark)
        self.create_widgets()
        self.load_file_list()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Create Notebook widget
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Create Simulation tab and Benchmark tab frames
        self.simulation_tab = ttk.Frame(self.notebook)
        self.benchmark_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.simulation_tab, text="Simulation")
        self.notebook.add(self.benchmark_tab, text="Benchmark")

        # ---------------------
        # Simulation Tab Layout
        # ---------------------
        # Split simulation tab into two columns: left (controls) and right (visualization)
        sim_left_frame = ttk.Frame(self.simulation_tab, width=400)
        sim_left_frame.grid(row=0, column=0, sticky="ns")
        sim_right_frame = ttk.Frame(self.simulation_tab)
        sim_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.simulation_tab.grid_columnconfigure(1, weight=1)
        self.simulation_tab.grid_rowconfigure(0, weight=1)

        # --- Controls (Left Side) ---
        control_frame = ttk.LabelFrame(sim_left_frame, text="Controls", width=400)
        control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # File selection frame
        file_selector_frame = ttk.Frame(control_frame)
        file_selector_frame.pack(fill=tk.X, pady=5)
        self.search_var = tk.StringVar()
        ttk.Label(file_selector_frame, text="Search Files:").pack(side=tk.TOP, anchor=tk.W)
        search_entry = ttk.Entry(file_selector_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X)
        search_entry.bind('<KeyRelease>', self.filter_file_list)
        self.file_listbox = tk.Listbox(file_selector_frame, height=10)
        self.file_listbox.pack(fill=tk.X)
        ttk.Button(file_selector_frame, text="Confirm Selection", command=self.confirm_file_selection).pack(fill=tk.X,
                                                                                                            pady=5)

        # Date range filter using tkcalendar DateEntry
        date_frame = ttk.LabelFrame(control_frame, text="Date Range Filter")
        date_frame.pack(fill=tk.X, pady=5)
        ttk.Label(date_frame, text="Start:").grid(row=0, column=0, sticky=tk.W)
        self.start_date = DateEntry(date_frame, date_pattern='yyyy-mm-dd')
        self.start_date.grid(row=0, column=1, sticky="ew")
        ttk.Label(date_frame, text="End:").grid(row=1, column=0, sticky=tk.W)
        self.end_date = DateEntry(date_frame, date_pattern='yyyy-mm-dd')
        self.end_date.grid(row=1, column=1, sticky="ew")
        ttk.Button(date_frame, text="Refresh Date Range", command=self.refresh_date_range).grid(row=2, column=0,
                                                                                                columnspan=2,
                                                                                                sticky="ew", pady=5)

        # JSON Filter frame
        filter_frame = ttk.LabelFrame(control_frame, text="JSON Filter")
        filter_frame.pack(fill=tk.X, pady=5)
        self.filter_text = tk.Text(filter_frame, height=8)
        self.filter_text.pack(fill=tk.X)
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_json_filter).pack(fill=tk.X, pady=5)

        # Simulation parameters frame (money parameters)
        param_frame = ttk.LabelFrame(control_frame, text="Simulation Parameters")
        param_frame.pack(fill=tk.X, pady=5)
        self.create_labeled_param(param_frame, "Initial Budget ($):", 'initial_budget', 1000, 100000)
        self.create_labeled_param(param_frame, "Investment per Trade ($):", 'investment_per_trade', 100, 10000)
        frame = ttk.Frame(param_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Max Trades (optional):", width=25).pack(side=tk.LEFT)
        max_trades_entry = ttk.Entry(frame, textvariable=self.params['max_trades'])
        max_trades_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

        # Strategy selection frame
        strat_frame = ttk.LabelFrame(control_frame, text="Strategy Selection")
        strat_frame.pack(fill=tk.X, pady=5)
        ttk.Label(strat_frame, text="Strategy:").grid(row=0, column=0, sticky=tk.W)
        strat_options = ["Evenly Spaced Buys", "Moving Average Crossover", "Parallel Delayed Trades"]
        strat_combo = ttk.Combobox(strat_frame, textvariable=self.strategy_var, values=strat_options, state="readonly")
        strat_combo.grid(row=0, column=1, sticky="ew")
        ttk.Label(strat_frame, text="Parallel Partitions:").grid(row=1, column=0, sticky=tk.W)
        partitions_spin = ttk.Spinbox(strat_frame, from_=1, to=16, textvariable=self.parallel_partitions)
        partitions_spin.grid(row=1, column=1, sticky="ew")

        # Buttons frame for simulation and export
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Run Simulation", command=self.run_simulation).pack(side=tk.LEFT, expand=True)
        ttk.Button(button_frame, text="Export Results", command=self.export_results).pack(side=tk.LEFT, expand=True)
        ttk.Button(button_frame, text="Load Template", command=self.load_template).pack(side=tk.LEFT, expand=True)

        # Simulation Results (bigger font)
        results_frame = ttk.LabelFrame(control_frame, text="Simulation Results")
        results_frame.pack(fill=tk.BOTH, pady=10, expand=True)
        self.results_label = ttk.Label(results_frame, textvariable=self.results_var,
                                       anchor="center", font=("Helvetica", 14, "bold"), wraplength=350)
        self.results_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Visualization (Right Side) ---
        vis_frame = ttk.Frame(sim_right_frame)
        vis_frame.pack(fill=tk.BOTH, expand=True)
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=vis_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(sim_right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=2)

        # ----------------------
        # Benchmark Tab Layout
        # ----------------------
        bench_top_frame = ttk.Frame(self.benchmark_tab)
        bench_top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(bench_top_frame, text="Benchmark Parallel Simulation").pack(side=tk.LEFT, padx=5)
        ttk.Button(bench_top_frame, text="Run Benchmark", command=self.run_benchmark).pack(side=tk.LEFT, padx=5)

        bench_results_frame = ttk.Frame(self.benchmark_tab)
        bench_results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Create a Treeview widget to display benchmark results
        columns = ("Partitions", "Exec Time", "Final Value", "ROI")
        self.benchmark_tree = ttk.Treeview(bench_results_frame, columns=columns, show="headings")
        for col in columns:
            self.benchmark_tree.heading(col, text=col)
            self.benchmark_tree.column(col, anchor="center", width=100)
        self.benchmark_tree.pack(fill=tk.BOTH, expand=True)

    def create_labeled_param(self, parent, label, param, min_val, max_val):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
        spin = ttk.Spinbox(frame, from_=min_val, to=max_val, textvariable=self.params[param])
        spin.pack(side=tk.RIGHT, expand=True, fill=tk.X)

    def load_file_list(self):
        try:
            initial_dir = "./data"
            self.file_list = [os.path.join(root, f)
                              for root, _, files in os.walk(initial_dir)
                              for f in files if f.endswith(".csv")]
            self.filtered_files = self.file_list
            self.update_file_listbox()
            logging.info(f"Loaded {len(self.file_list)} CSV files")
        except Exception as e:
            logging.error(f"File list error: {str(e)}")

    def filter_file_list(self, event=None):
        try:
            query = self.search_var.get().lower()
            self.filtered_files = [f for f in self.file_list
                                   if query in os.path.basename(f).lower()]
            self.update_file_listbox()
        except Exception as e:
            logging.error(f"Filter error: {str(e)}")

    def update_file_listbox(self):
        self.file_listbox.delete(0, tk.END)
        for f in self.filtered_files:
            self.file_listbox.insert(tk.END, os.path.basename(f))

    def reset_simulation_state(self):
        """Clears previous simulation signals and results."""
        self.buy_signals = pd.DataFrame()
        self.trade_positions = []
        self.final_value = 0
        self.roi = 0
        self.execution_time = None
        self.results_var.set("")
        logging.info("Simulation state has been reset.")

    def confirm_file_selection(self):
        try:
            selected = self.file_listbox.curselection()
            if not selected:
                messagebox.showerror("Error", "No file selected")
                return
            self.file_path = self.filtered_files[selected[0]]
            logging.info(f"Selected file: {self.file_path}")
            self.status_var.set(f"Loaded: {os.path.basename(self.file_path)}")
            self.load_data()
            self.reset_simulation_state()
            self.plot_results()
        except Exception as e:
            logging.error(f"Selection error: {str(e)}")
            messagebox.showerror("Error", f"File load failed: {str(e)}")

    def update_date_range_inputs(self):
        try:
            if self.full_df is not None and not self.full_df.empty:
                min_date = self.full_df.index.min().date()
                max_date = self.full_df.index.max().date()
                self.start_date.set_date(min_date)
                self.end_date.set_date(max_date)
                logging.info(f"Date range updated to: {min_date} - {max_date}")
        except Exception as e:
            logging.error(f"Date update error: {str(e)}")

    def apply_json_filter(self):
        try:
            filter_json = self.filter_text.get("1.0", tk.END).strip()
            if not filter_json:
                return
            filter_dict = json.loads(filter_json)
            logging.info(f"Applying JSON filter: {filter_dict}")
            query_parts = []
            for col, condition in filter_dict.items():
                if isinstance(condition, dict):
                    for op, value in condition.items():
                        if op == 'gt':
                            query_parts.append(f"{col} > {value}")
                        elif op == 'lt':
                            query_parts.append(f"{col} < {value}")
                        elif op == 'eq':
                            query_parts.append(f"{col} == {value}")
            if query_parts:
                full_query = ' & '.join(query_parts)
                ddf = dd.from_pandas(self.df, npartitions=10)
                self.df = ddf.query(full_query).compute()
                logging.info(f"Filtered data shape: {self.df.shape}")
        except Exception as e:
            logging.error(f"Filter error: {str(e)}")
            messagebox.showerror("Filter Error", str(e))

    def load_data(self):
        try:
            if not self.file_path:
                return

            ddf = dd.read_csv(
                self.file_path,
                header=0,
                dtype={
                    'time': 'int64',
                    'open': 'float64',
                    'high': 'float64',
                    'low': 'float64',
                    'close': 'float64',
                    'volume': 'float64'
                },
                usecols=[0, 1, 2, 3, 4, 5]
            )
            ddf['time'] = dd.to_datetime(ddf['time'], unit='ms')
            ddf = ddf.set_index('time', sorted=True)
            computed_df = ddf.compute().sort_index()
            if computed_df.empty:
                raise ValueError("No data loaded from file")
            self.full_df = computed_df
            self.df = self.full_df.copy()
            logging.info(f"Full data loaded with shape: {self.full_df.shape}")
            self.update_date_range_inputs()
            start = pd.to_datetime(self.start_date.get_date())
            end = pd.to_datetime(self.end_date.get_date())
            self.df = self.full_df.loc[start:end]
            if self.df.empty:
                raise ValueError("No data loaded - check date range")
            logging.info(f"Data after applying date range ({start.date()} - {end.date()}): {self.df.shape}")
        except Exception as e:
            logging.error(f"Data load error: {str(e)}")
            messagebox.showerror("Data Load Error", str(e))
            raise

    def refresh_date_range(self):
        try:
            if self.full_df is None:
                logging.error("Full data not loaded; cannot refresh date range")
                messagebox.showerror("Error", "Full data not loaded. Please select a file first.")
                return
            start = pd.to_datetime(self.start_date.get_date())
            end = pd.to_datetime(self.end_date.get_date())
            new_df = self.full_df.loc[start:end]
            if new_df.empty:
                raise ValueError("No data in selected date range")
            self.reset_simulation_state()
            self.df = new_df
            logging.info(f"Data refreshed with new date range: {start.date()} - {end.date()}, shape: {self.df.shape}")
            messagebox.showinfo("Success", f"Data refreshed to new date range: {start.date()} - {end.date()}")
            self.plot_results()
        except Exception as e:
            logging.error(f"Error refreshing date range: {str(e)}")
            messagebox.showerror("Error", str(e))

    def generate_evenly_spaced_signals(self):
        try:
            self.buy_signals = self.df.copy()
            self.buy_signals['buy_signal'] = False
            total_rows = len(self.buy_signals)
            max_trades_str = self.params['max_trades'].get().strip()
            if max_trades_str:
                max_trades = int(max_trades_str)
                step = max(total_rows // max_trades, 1)
            else:
                step = 10
            self.buy_signals.iloc[::step, self.buy_signals.columns.get_loc('buy_signal')] = True
            logging.info(f"Generated evenly spaced buy signals with step {step}")
        except Exception as e:
            logging.error(f"Signal generation error: {str(e)}")
            raise

    def simulate_trading_evenly_spaced(self):
        try:
            self.generate_evenly_spaced_signals()
            budget = self.params['initial_budget'].get()
            per_trade = self.params['investment_per_trade'].get()
            max_trades_str = self.params['max_trades'].get().strip()
            if max_trades_str:
                max_trades = int(max_trades_str)
            else:
                max_trades = int(budget // per_trade)
            gdf = cudf.from_pandas(self.buy_signals)
            buy_points = gdf[gdf['buy_signal']].sort_index()
            if buy_points.empty:
                return budget, 0.0
            max_trades = min(len(buy_points), max_trades, int(budget // per_trade))
            shares = (per_trade / buy_points['close']).head(max_trades)
            total_invested = max_trades * per_trade
            final_price = gdf['close'].iloc[-1]
            final_value = (budget - total_invested) + (shares.sum() * final_price)
            roi = ((final_value - budget) / budget) * 100
            logging.info(f"Evenly Spaced Simulation complete: Final Value = ${final_value:.2f}, ROI = {roi:.2f}%")
            return float(final_value), float(roi)
        except Exception as e:
            logging.error(f"Evenly Spaced Simulation error: {str(e)}")
            raise

    def simulate_trading_moving_average(self):
        try:
            budget = self.params['initial_budget'].get()
            per_trade = self.params['investment_per_trade'].get()
            max_trades_str = self.params['max_trades'].get().strip()
            max_trades = int(max_trades_str) if max_trades_str else None
            in_position = False
            entry_price = 0
            trades_count = 0
            positions = []
            df = self.df.copy()
            df['short_ma'] = df['close'].rolling(window=5, min_periods=1).mean()
            df['long_ma'] = df['close'].rolling(window=20, min_periods=1).mean()

            for i in range(1, len(df)):
                if max_trades is not None and trades_count >= max_trades:
                    break
                prev_short = df['short_ma'].iloc[i - 1]
                prev_long = df['long_ma'].iloc[i - 1]
                curr_short = df['short_ma'].iloc[i]
                curr_long = df['long_ma'].iloc[i]
                price = df['close'].iloc[i]
                if not in_position and prev_short <= prev_long and curr_short > curr_long:
                    if budget >= per_trade:
                        in_position = True
                        entry_price = price
                        trades_count += 1
                        positions.append(
                            {'entry_date': df.index[i], 'entry_price': price, 'exit_date': None, 'exit_price': None})
                        budget -= per_trade
                        logging.info(f"Buy at {df.index[i]} for price {price}")
                elif in_position and prev_short >= prev_long and curr_short < curr_long:
                    in_position = False
                    shares = per_trade / entry_price
                    proceeds = shares * price
                    budget += proceeds
                    positions[-1]['exit_date'] = df.index[i]
                    positions[-1]['exit_price'] = price
                    logging.info(f"Sell at {df.index[i]} for price {price}")

            if in_position:
                price = df['close'].iloc[-1]
                shares = per_trade / entry_price
                proceeds = shares * price
                budget += proceeds
                positions[-1]['exit_date'] = df.index[-1]
                positions[-1]['exit_price'] = price
                logging.info(f"Final sell at {df.index[-1]} for price {price}")

            roi = ((budget - self.params['initial_budget'].get()) / self.params['initial_budget'].get()) * 100
            logging.info(f"Moving Average Simulation complete: Final Value = ${budget:.2f}, ROI = {roi:.2f}%")
            return float(budget), float(roi), positions
        except Exception as e:
            logging.error(f"Moving Average Simulation error: {str(e)}")
            raise

    def simulate_trading_parallel(self):
        try:
            budget = self.params['initial_budget'].get()
            per_trade = self.params['investment_per_trade'].get()
            max_trades_str = self.params['max_trades'].get().strip()
            if max_trades_str:
                max_trades = int(max_trades_str)
            else:
                max_trades = int(budget // per_trade)

            self.generate_evenly_spaced_signals()
            ddf = dd.from_pandas(self.buy_signals, npartitions=self.parallel_partitions.get())
            buy_points = ddf[ddf['buy_signal']].compute().sort_index()
            if buy_points.empty:
                return budget, 0.0, 0.0

            max_trades = min(len(buy_points), max_trades, int(budget // per_trade))
            trades = buy_points.head(max_trades)

            @delayed
            def compute_shares(price):
                return per_trade / price

            delayed_results = [compute_shares(price) for price in trades['close']]
            start_time = time.perf_counter()
            shares = compute(*delayed_results)
            end_time = time.perf_counter()
            exec_time = end_time - start_time
            total_shares = sum(shares)
            total_invested = max_trades * per_trade
            final_price = self.buy_signals['close'].iloc[-1]
            final_value = (budget - total_invested) + (total_shares * final_price)
            roi = ((final_value - budget) / budget) * 100
            logging.info(
                f"Parallel Simulation complete: Final Value = ${final_value:.2f}, ROI = {roi:.2f}% in {exec_time:.4f} sec")
            return float(final_value), float(roi), exec_time
        except Exception as e:
            logging.error(f"Parallel Simulation error: {str(e)}")
            raise

    def plot_results(self):
        try:
            self.ax.clear()
            self.ax.plot(self.df.index, self.df['close'], label='Price', color='navy', alpha=0.8)
            strategy = self.strategy_var.get()
            if strategy == "Moving Average Crossover" and self.trade_positions:
                buy_dates = [pos['entry_date'] for pos in self.trade_positions if pos['entry_date']]
                buy_prices = [pos['entry_price'] for pos in self.trade_positions if pos['entry_price']]
                sell_dates = [pos['exit_date'] for pos in self.trade_positions if pos['exit_date']]
                sell_prices = [pos['exit_price'] for pos in self.trade_positions if pos['exit_price']]
                self.ax.scatter(buy_dates, buy_prices, color='green', marker='^', s=100, label='Buy')
                self.ax.scatter(sell_dates, sell_prices, color='red', marker='v', s=100, label='Sell')
            else:
                if not self.buy_signals.empty:
                    buy_points = self.buy_signals[self.buy_signals['buy_signal']]
                    self.ax.scatter(buy_points.index, buy_points['close'], color='green', marker='^', s=100,
                                    label='Buy')
            self.ax.set_title(f"Trading Results (ROI: {self.roi:.2f}%)")
            self.ax.set_xlabel("Date")
            self.ax.set_ylabel("Price (USD)")
            self.ax.legend()
            self.ax.grid(alpha=0.3)
            self.canvas.draw()
            logging.info("Plot updated successfully.")
        except Exception as e:
            logging.error(f"Plot error: {str(e)}")

    def export_results(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            if self.strategy_var.get() == "Moving Average Crossover" and self.trade_positions:
                export_df = pd.DataFrame(self.trade_positions)
            else:
                export_df = self.buy_signals[self.buy_signals['buy_signal']].copy()
                export_df['trade_amount'] = self.params['investment_per_trade'].get()
                export_df['shares'] = export_df['trade_amount'] / export_df['close']
            export_df.to_csv(file_path)
            logging.info(f"Exported results to {file_path}")
            messagebox.showinfo("Success", "Results exported successfully")
        except Exception as e:
            logging.error(f"Export error: {str(e)}")
            messagebox.showerror("Export Failed", str(e))

    def load_template(self):
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            with open(file_path, 'r') as f:
                template = json.load(f)
            for key, value in template.items():
                if key in self.params:
                    self.params[key].set(value)
            self.load_data()
            self.reset_simulation_state()
            self.run_simulation()
            logging.info(f"Loaded template from {file_path}")
            messagebox.showinfo("Success", "Template loaded successfully")
        except Exception as e:
            logging.error(f"Template error: {str(e)}")
            messagebox.showerror("Load Failed", str(e))

    def run_simulation(self):
        try:
            self.status_var.set("Running simulation...")
            self.root.update()
            sim_start_time = time.perf_counter()
            strategy = self.strategy_var.get()
            if strategy == "Evenly Spaced Buys":
                self.final_value, self.roi = self.simulate_trading_evenly_spaced()
                self.trade_positions = []
                self.execution_time = None
            elif strategy == "Moving Average Crossover":
                self.final_value, self.roi, positions = self.simulate_trading_moving_average()
                self.trade_positions = positions
                self.execution_time = None
            elif strategy == "Parallel Delayed Trades":
                self.final_value, self.roi, exec_time = self.simulate_trading_parallel()
                self.trade_positions = []
                self.execution_time = exec_time
            sim_end_time = time.perf_counter()
            total_sim_time = sim_end_time - sim_start_time
            self.plot_results()
            results_msg = f"Final Value: ${self.final_value:,.2f}\nROI: {self.roi:.2f}%"
            if self.execution_time is not None:
                results_msg += f"\nParallel Exec Time: {self.execution_time:.4f} sec"
            results_msg += f"\nTotal Simulation Time: {total_sim_time:.4f} sec"
            self.results_var.set(results_msg)
            self.status_var.set("Simulation complete")
            logging.info(f"Simulation run complete: {results_msg}")
        except Exception as e:
            self.status_var.set("Simulation failed")
            logging.error(f"Run simulation error: {str(e)}")
            messagebox.showerror("Simulation Error", str(e))

    def run_benchmark(self):
        """Runs the parallel simulation with different partition levels and displays the results."""
        if self.full_df is None:
            messagebox.showerror("Error", "No data loaded. Please load a file in the Simulation tab first.")
            return

        # Clear previous benchmark results
        for row in self.benchmark_tree.get_children():
            self.benchmark_tree.delete(row)
        benchmark_results = []
        partition_levels = [1, 2, 4, 8, 16]
        for p in partition_levels:
            try:
                self.parallel_partitions.set(p)
                self.reset_simulation_state()
                # We call the parallel simulation
                final_value, roi, exec_time = self.simulate_trading_parallel()
                benchmark_results.append((p, exec_time, final_value, roi))
            except Exception as e:
                benchmark_results.append((p, None, None, None))
                logging.error(f"Benchmark error for partitions {p}: {str(e)}")
        # Update the Treeview with benchmark results
        for res in benchmark_results:
            p, exec_time, final_value, roi = res
            if exec_time is not None:
                self.benchmark_tree.insert("", tk.END,
                                           values=(p, f"{exec_time:.4f} sec", f"${final_value:,.2f}", f"{roi:.2f}%"))
            else:
                self.benchmark_tree.insert("", tk.END, values=(p, "Error", "Error", "Error"))
        logging.info("Benchmark run complete.")


if __name__ == "__main__":
    app = EnhancedTradingSimulator()
    app.root.mainloop()
