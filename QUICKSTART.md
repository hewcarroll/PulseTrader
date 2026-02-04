# PulseTrader Quick Start Guide

## Prerequisites

1. **Python 3.11+** installed
2. **Alpaca Paper Trading Account** (free at https://alpaca.markets/)

## Setup Steps

### 1. Get Your Alpaca Paper Trading Credentials

1. Go to https://alpaca.markets/ and sign up
2. Navigate to the "Paper Trading" section
3. Generate your API keys (you'll get a Key ID and Secret Key)

### 2. Create Your `.env` File

Create a file named `.env` in the root directory with your credentials:

```bash
# Alpaca Paper Trading Credentials
ALPACA_PAPER_API_KEY=your_paper_api_key_here
ALPACA_PAPER_API_SECRET=your_paper_secret_here
ALPACA_MODE=paper

# JWT Secret for Admin UI (generate a random string)
JWT_SECRET_KEY=your_random_secret_key_here

# Optional: Logging Level
LOG_LEVEL=INFO
```

**Important:** Never commit this file to git (it's already in .gitignore)

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Your Setup

Run the integration tests to make sure everything works:

```bash
# Test basic connection
python scripts/test_alpaca_connection.py

# Test market data retrieval
python scripts/test_market_data.py

# Test WebSocket streaming (optional)
python scripts/test_websocket_streaming.py

# Test order submission (paper trading - safe to run)
python scripts/test_order_submission.py
```

All tests should pass. If they don't, check your `.env` file credentials.

### 5. Run the Trading Bot

```bash
python services/orchestrator/run.py
```

## What Happens When You Start

The bot will:

1. **Validate Configuration** - Check that all required environment variables are present
2. **Connect to Alpaca** - Authenticate with your paper trading account
3. **Initialize Components**:
   - AlpacaClient (API wrapper)
   - AccountManager (tracks equity, cash, positions)
   - MarketDataFeed (retrieves price data)
   - OrderManager (submits orders with risk validation)
   - WebSocketClient (real-time market data streaming)
   - ConnectionHealthMonitor (monitors API health)
4. **Load Strategies**:
   - Crypto Momentum (BTC/USD, ETH/USD, SOL/USD)
   - Leveraged ETF Trend (TQQQ, SPXL, SOXL, etc.)
   - Stock Swing (disabled until equity >= $25k)
5. **Start Trading** - Strategies begin evaluating market conditions and placing trades

## Monitoring

### Console Output

The bot logs everything to the console:
- Account equity and tier information
- Strategy activations
- Order submissions and fills
- Risk checks
- Errors and warnings

### Log Files

Logs are saved to:
- `logs/system/pulsetrader_YYYY-MM-DD.log` - System logs
- `logs/trades/trades_YYYY-MM-DD.log` - Trade-specific logs

### Admin UI (Optional)

Start the web interface:

```bash
python ui/main.py
```

Then open http://localhost:8000 in your browser.

## Stopping the Bot

Press `Ctrl+C` to gracefully shut down. The bot will:
- Stop all strategies
- Disconnect from WebSocket
- Save final state
- Optionally close all positions (if configured)

## Configuration

Edit `config/main.yaml` to customize:
- Risk parameters (position sizing, stop losses)
- Strategy settings (entry/exit rules)
- Trading hours
- Position limits
- Emergency controls

## Safety Features

The bot includes multiple safety mechanisms:

1. **Kill Switch** - Set `emergency.kill_switch.enabled: true` to halt all trading
2. **Reserve Protection** - Always keeps 20% of equity in reserve
3. **Risk Validation** - Every order is validated before submission
4. **PDT Compliance** - Automatically adjusts behavior based on account size
5. **Preservation Mode** - Automatically triggered on excessive drawdown
6. **Connection Monitoring** - Detects API issues and enters safe mode

## Paper Trading vs Live

**You are currently in PAPER TRADING mode** - this uses virtual money and is completely safe.

To switch to live trading (NOT RECOMMENDED until thoroughly tested):
1. Get live API credentials from Alpaca
2. Update `.env` with live credentials
3. Change `ALPACA_MODE=live`
4. Update config to use live mode

**WARNING:** Live trading uses real money. Only switch after extensive paper trading.

## Troubleshooting

### "Missing Alpaca API credentials" Error
- Check that `.env` file exists in the root directory
- Verify `ALPACA_PAPER_API_KEY` and `ALPACA_PAPER_API_SECRET` are set
- Make sure there are no extra spaces or quotes around the values

### "Configuration validation failed" Error
- Check that all required environment variables are present
- Verify `JWT_SECRET_KEY` is set (can be any random string)

### Connection Errors
- Verify your internet connection
- Check Alpaca status page: https://status.alpaca.markets/
- Ensure your API keys are valid (regenerate if needed)

### No Trades Being Placed
- Check that strategies are enabled in `config/main.yaml`
- Verify market is open (crypto trades 24/7, stocks only during market hours)
- Check logs for risk validation failures
- Ensure you have sufficient buying power

## Next Steps

1. **Monitor Performance** - Watch the bot trade for a few days
2. **Analyze Results** - Review logs and daily reports
3. **Tune Parameters** - Adjust strategy settings based on performance
4. **Add Strategies** - Implement custom trading strategies
5. **Scale Up** - Once confident, consider live trading (with caution)

## Support

- Check logs in `logs/` directory for detailed error information
- Review integration test scripts in `scripts/` for examples
- Read the spec documents in `.kiro/specs/alpaca-paper-integration/`

## Important Notes

- This is paper trading - no real money is at risk
- Start with small position sizes to test
- Monitor the bot closely for the first few days
- Review all trades and understand why they were placed
- Never run live trading without extensive paper testing

Happy trading! 🚀
