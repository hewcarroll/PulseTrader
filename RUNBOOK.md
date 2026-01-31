# PulseTrader.01 Operational Runbook

## Table of Contents
1. Initial Setup
2. Configuration
3. Paper Trading Launch
4. Switching to Live Trading
5. Monitoring
6. Troubleshooting
7. Emergency Procedures

## Initial Setup
### Prerequisites
- Python 3.11 or higher
- Alpaca brokerage account (paper and/or live)
- Docker (optional, recommended)
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/hewcarroll/PulseTrader.git
cd PulseTrader
```

### Step 2: Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
cp env/.env.example .env
```
Edit `.env` with your credentials. Critical variables to set:
- `ALPACA_PAPER_API_KEY` and `ALPACA_PAPER_API_SECRET`
- `ADMIN_PASSWORD`
- `JWT_SECRET_KEY`

### Step 5: Generate TOTP Secret
```bash
python scripts/generate_totp.py
```

### Step 6: Initialize Database
```bash
./scripts/setup.sh
```

## Configuration
Edit `config/main.yaml` to tune risk, strategies, and reporting. For custodial accounts, create configs in `config/accounts/`.

## Paper Trading Launch
```bash
python services/orchestrator/run.py
```

Start the admin UI in a separate terminal:
```bash
python ui/main.py
```

## Switching to Live Trading
> ⚠️ **WARNING**: Live trading involves real money. Ensure paper trading is stable.

Update `.env`:
```
ALPACA_MODE="live"
ALPACA_LIVE_API_KEY="your_live_key"
ALPACA_LIVE_API_SECRET="your_live_secret"
```

## Monitoring
- System logs: `logs/system/`
- Trade logs: `logs/trades/`
- Daily reports: `reports/daily/`
- Monday reports: `reports/monday/`

## Troubleshooting
Check logs and runtime state:
```bash
grep ERROR logs/system/*.log
cat runtime/state.json
```

## Emergency Procedures
### Kill Switch
Edit `config/main.yaml`:
```yaml
emergency:
  kill_switch:
    enabled: true
```

### Cash Release
Via API:
```
POST /api/controls/cash-release
{
  "amount": 750.00
}
```
