# QROS - Quant Prop Firm Backtesting Engine & VPS Deployment

This repository contains a robust scientific backtesting framework tailored for Prop Firm algorithmic trading (specifically catering to strict rules of firms like FundedNext and Funding Pips). It features Deflated Sharpe Ratio validations, dynamic transaction cost friction modeling, MT5 news scraping/filtering, and strict 4% Daily / 8% Max Drawdown governance.

## Features

- **Prop Firm Governance (`prop_firm_rules.py`)**: Strict tracking of max and daily drawdowns with automated cut-offs based on High Water Marks.
- **News Filtration (`news_filter.py`)**: Integrates directly with MT5 to bypass trading around high impact news windows.
- **Scientific Validation**: Calculates Effective Sample Sizes, Stationarity Block Bootstrapped Sharpe intervals, and corrects for Multiple Testing.
- **Transaction Modeling**: Dynamic slippage, realistic spreads, and swap modeling.

## Running Backtests Locally / on VPS

1. **Install Dependencies:**
   Ensure Python 3.10+ is installed on the VPS. Open PowerShell and run:
   ```powershell
   # Create Virtual Environment (using standard Python tools)
   python -m virtualenv venv

   # Activate Virtual Environment
   .\venv\Scripts\Activate.ps1

   # Install Requirements
   pip install -r requirements.txt
   pip install pyarrow pandas numpy scipy pyyaml pytest
   ```

2. **Execute a Backtest:**
   Create an execution script that imports the `ScientificBacktestEngine` and runs your strategy logic against a loaded dataset. Example PowerShell execution:
   ```powershell
   # Assuming you have an execution script called run_backtest.py
   $env:PYTHONPATH = ".\src"
   python run_backtest.py
   ```

## MT5 VPS Deployment (Windows)

If you are running this framework alongside a live MT5 terminal for execution or forward testing, ensure the following:
1. Ensure the `terminal64.exe` path in your adapter matches the VPS MT5 installation path (typically `C:\Program Files\MetaTrader 5\terminal64.exe`).
2. Run your MT5 terminal as Administrator.
3. Allow Auto Trading and DLL Imports in MT5 settings.
