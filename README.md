# Advanced Crypto Trading Simulator

## Overview

The **Advanced Crypto Trading Simulator** is a powerful Python application designed to simulate various cryptocurrency trading strategies on historical data and benchmark their performance using parallel processing. The application features a graphical user interface built with Tkinter and is organized into two main tabs:

- **Simulation Tab:** Run different trading strategies on selected CSV data files. View detailed visualizations, trade signals, and performance metrics (e.g., final portfolio value, ROI, execution times).
- **Benchmark Tab:** Evaluate and compare the performance of the parallel simulation across different partition levels. The results are displayed in a user-friendly table.

This project leverages several powerful libraries, including Dask for parallel computations, TKCalendar for date selection, and Matplotlib for plotting results.

## Features

- **File Selection:** Search and select CSV files that contain historical trading data.
- **Date Range Filtering:** Automatically update and refresh the simulation based on the data's available date range.
- **Multiple Trading Strategies:** Choose from strategies such as:
  - *Evenly Spaced Buys*
  - *Moving Average Crossover*
  - *Parallel Delayed Trades*
- **Benchmarking:** Run benchmarks on the parallel simulation with varying partition levels to compare execution speeds.
- **Visualization:** View interactive charts with price data and buy/sell signals.
- **Export Functionality:** Export simulation results to CSV files.
- **Detailed Logging:** All major steps are logged to `trading_sim.log` for troubleshooting.

## Installation

### Prerequisites

- **Python 3.x** (Tested with Python 3.8+)
- A working installation of [pip](https://pip.pypa.io/en/stable/installation/)

### Install Required Packages

Use the following command to install the required packages:

```bash
pip install tkcalendar dask pandas numpy matplotlib
```

### Optional (For GPU Acceleration)

If you have a compatible GPU and want to take advantage of GPU-accelerated libraries, consider installing:
- [CuPy](https://docs.cupy.dev/en/stable/install.html)
- [cuDF](https://rapids.ai/start.html)

Refer to their documentation for detailed installation instructions.

## Setup and Running the Simulator

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/liviuxyz-ctrl/BIG_DataTrader/
   cd advanced-trading-simulator
   ```

2. **Prepare Your Data:**

   Place your CSV files in the `data` directory. Your CSV files should have the following columns (with a header):

   ```
   time,open,high,low,close,volume
   ```

   > **Note:**  
   > The `time` column must be in Unix timestamp format (milliseconds).

3. **Run the Application:**

   Launch the simulator by running:

   ```bash
   python trading_simulator.py
   ```

## Usage

### Simulation Tab

- **File Selection:**  
  Use the file search box to filter and select a CSV file from the list. Click **"Confirm Selection"** to load the file.

- **Date Range Filtering:**  
  After loading the file, the date selectors will update automatically based on the data. You can change the start and end dates, then click **"Refresh Date Range"** to update the data.

- **Set Parameters:**  
  Choose your initial budget, investment per trade, (optionally) maximum trades, and select the desired trading strategy.  
  For the **Parallel Delayed Trades** strategy, set the number of parallel partitions.

- **Run Simulation:**  
  Click **"Run Simulation"** to execute the strategy. The chart will update with price data and buy/sell signals. Detailed simulation results (including execution times) will be shown in the **Simulation Results** section.

- **Export & Template:**  
  Use the **"Export Results"** button to save simulation data as a CSV file. The **"Load Template"** button allows you to load preconfigured parameters from a JSON file.

### Benchmark Tab

- **Run Benchmark:**  
  Switch to the **Benchmark** tab. Click **"Run Benchmark"** to evaluate the parallel simulation performance using different partition levels (e.g., 1, 2, 4, 8, 16).  
  The results, including execution times, final portfolio values, and ROI, will be displayed in a table.

## Screenshots

*Place your images in the `images/` folder and update the paths below.*

![image](https://github.com/user-attachments/assets/aed4d142-e547-4d53-8841-173f3579de6f)

*Figure 1: Simulation tab interface with file selection, parameter controls, and chart visualization.*

![image](https://github.com/user-attachments/assets/df32c66f-4597-465b-a07e-e8c60d2d9372)

*Figure 2: Benchmark tab showing performance metrics across different parallel partition levels.*

## Logging and Troubleshooting

All significant actions and errors are logged to `trading_sim.log` in the project directory. If you encounter any issues, please review this log file for more detailed error messages and debugging information.

## Contributing

Contributions are welcome! If you have suggestions for improvements or bug fixes, please open an issue or submit a pull request. Ensure your changes include proper logging and follow the existing coding style.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
```
