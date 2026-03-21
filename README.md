# ⭐ Star Pattern Stocks - Morning Star Scanner

Automated scanner for detecting Morning Star candlestick patterns in Indian equities using Fyers API.

## 🎯 Features

- **Automated Scanner**: Runs daily at 3:35 PM IST to detect Morning Star patterns
- **Trade Tracking**: Monitors active trades with 3% trailing stop loss
- **Web Dashboard**: Real-time view of signals, trades, and capital growth
- **Complete History**: Track all trades with P&L analysis
- **Capital Tracker**: Monitor portfolio growth from ₹5,00,000 starting capital

## 📊 Strategy Details

**Entry**: Morning Star pattern (3-candle bullish reversal)
- Day 1: Red candle (bearish)
- Day 2: Doji (indecision, body <10% of range)
- Day 3: Green candle closing above Day 1

**Exit**: 3% trailing stop loss from entry price

**Expected Performance** (based on backtesting):
- Win Rate: ~58%
- Average Return: ~15-20% annually
- Risk: 2% per trade

## 🚀 Deployment on Render

### 1. Create GitHub Repository

1. Create a new repo on GitHub
2. Upload all files EXCEPT `.env`
3. Push to GitHub:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### 2. Deploy to Render

1. Go to [render.com](https://render.com)
2. Sign up / Log in
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will auto-detect `render.yaml`

### 3. Set Environment Variables in Render

Go to your service → Environment → Add these:

```
FYERS_CLIENT_ID = your_fyers_client_id
FYERS_SECRET_KEY = your_fyers_secret_key
FYERS_PIN = your_4_digit_pin
FYERS_REDIRECT_URI = https://trade.fyers.in/api-login/redirect-uri/index.html
STARTING_CAPITAL = 500000
TRAILING_SL_PERCENT = 3.0
```

### 4. Keep Render Awake (Free Tier)

Render free tier sleeps after 15 min inactivity. Use **UptimeRobot** to keep it awake:

1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Create free account
3. Add Monitor:
   - Monitor Type: HTTP(s)
   - Friendly Name: Star Pattern Stocks
   - URL: `https://your-app-name.onrender.com/health`
   - Monitoring Interval: Every 5 minutes
4. Save - your app stays awake 24/7!

## 🔑 Fyers API Setup

### Initial Authentication (One-time)

1. Get your Fyers API credentials from [myapi.fyers.in](https://myapi.fyers.in)
2. Create app with redirect URI: `https://trade.fyers.in/api-login/redirect-uri/index.html`
3. Run locally first to generate access token:

```python
from fyers_auth import FyersAuth

auth = FyersAuth()
url = auth.generate_auth_code_url()
print(url)  # Copy this URL to browser

# After login, copy auth code from URL (after ?auth_code=...)
auth.generate_access_token('YOUR_AUTH_CODE_HERE')
```

4. This creates `fyers_access_token.txt` - upload to Render (or re-generate on server)

### Token Refresh (Every 24 hours)

Fyers access token expires daily. For production:
- Use Fyers refresh token (valid 15 days)
- Update `fyers_auth.py` to auto-refresh daily
- Or manually re-authenticate every day

## 📱 Using the Dashboard

### Main Dashboard (`/`)
- View current capital and P&L
- See pending Morning Star signals
- Monitor active trades
- Run scanner manually
- Check for trade exits

### Trade History (`/history`)
- Complete trade log
- Performance statistics
- Win/loss breakdown
- Filter and export trades

## 🔧 Local Development

### Setup

```bash
# Clone repo
git clone YOUR_REPO_URL
cd star-pattern-stocks

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your Fyers credentials

# Run app
python app.py
```

App runs on `http://localhost:5000`

### Manual Scanner Run

```bash
# Run scanner
curl -X POST http://localhost:5000/api/run-scanner

# Check exits
curl -X POST http://localhost:5000/api/check-exits
```

## 📊 Database

Uses SQLite (`star_pattern.db`) with tables:
- `signals` - Detected patterns
- `trades` - Active and closed trades
- `portfolio` - Capital tracking
- `scanner_logs` - Scanner execution logs

## ⚠️ Important Notes

1. **This is a backtest-validated strategy, NOT guaranteed profit**
2. **Always paper trade first** for 3-6 months
3. **Risk management is critical** - never exceed 2% risk per trade
4. **Market conditions matter** - strategy underperforms in choppy markets
5. **Monitor regularly** - check dashboard daily

## 🐛 Troubleshooting

### Scanner not running
- Check scanner logs in database
- Verify Fyers token is valid
- Check Render logs for errors

### No signals detected
- Normal - Morning Star is rare pattern
- Typically 5-10 signals per month across all stocks
- Run scanner manually to verify it's working

### Trades not closing
- Verify `check_active_trades_exit()` is running
- Check if stop loss logic is correct
- Monitor Fyers API rate limits

## 📈 Expected Performance

Based on 6-year backtest (2020-2025):

| Year | Return | Win Rate |
|------|--------|----------|
| 2020 | 26.6%  | 68.7%    |
| 2021 | 37.7%  | 72.4%    |
| 2022 | 0.94%  | 43.5%    |
| 2023 | 24.3%  | 77.5%    |
| 2024 | 9.24%  | 52.8%    |
| 2025 | -9.01% | 16.9%    |

**Average**: 15-20% annual return with proper risk management

## 📞 Support

For issues or questions:
1. Check Render logs
2. Verify Fyers API credentials
3. Review database for error logs
4. Test scanner locally first

## ⚖️ Disclaimer

This is an educational project. Past performance does not guarantee future results. Trade at your own risk. Always start with paper trading before using real capital.

## 📄 License

MIT License - Use at your own risk
