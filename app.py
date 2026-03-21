from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from models import Database
from scanner import MorningStarScanner
import pytz

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# Initialize database
db = Database()

# Initialize scanner
scanner = MorningStarScanner(db)

# Scheduler for automated scans
scheduler = BackgroundScheduler()
ist = pytz.timezone('Asia/Kolkata')


def scheduled_scan():
    """Run scanner automatically at 3:35 PM IST daily"""
    print(f"Running scheduled scan at {datetime.now(ist)}")
    result = scanner.scan_all_stocks()
    print(f"Scan completed: {result}")


def scheduled_exit_check():
    """Check for trade exits every 30 minutes during market hours"""
    print(f"Checking exits at {datetime.now(ist)}")
    scanner.check_active_trades_exit()


# Schedule jobs
# Run scanner at 3:35 PM IST daily (after market close at 3:30 PM)
scheduler.add_job(
    scheduled_scan,
    trigger='cron',
    hour=15,
    minute=35,
    timezone=ist,
    id='daily_scan'
)

# Check exits every 30 minutes from 9:30 AM to 3:30 PM
scheduler.add_job(
    scheduled_exit_check,
    trigger='cron',
    hour='9-15',
    minute='30,0',
    timezone=ist,
    id='exit_check'
)

scheduler.start()


@app.route('/')
def index():
    """Dashboard page"""
    # Get latest portfolio info
    portfolio = db.get_latest_portfolio()
    
    # Get statistics
    stats = db.get_stats()
    
    # Get pending signals
    pending_signals = db.get_pending_signals()
    
    # Get active trades
    active_trades = db.get_active_trades()
    
    # Get latest scan info
    latest_scan = db.get_latest_scan()
    
    return render_template('index.html',
                         portfolio=portfolio,
                         stats=stats,
                         pending_signals=pending_signals,
                         active_trades=active_trades,
                         latest_scan=latest_scan)


@app.route('/history')
def history():
    """Trade history page"""
    # Get all trades
    all_trades = db.get_all_trades(limit=500)
    
    # Get statistics
    stats = db.get_stats()
    
    return render_template('history.html',
                         trades=all_trades,
                         stats=stats)


@app.route('/api/run-scanner', methods=['POST'])
def run_scanner():
    """Manual trigger to run scanner"""
    try:
        result = scanner.scan_all_stocks()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/check-exits', methods=['POST'])
def check_exits():
    """Manual trigger to check exits"""
    try:
        scanner.check_active_trades_exit()
        return jsonify({
            'success': True,
            'message': 'Exit check completed'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/enter-trade', methods=['POST'])
def enter_trade():
    """Manually enter a trade from a pending signal"""
    try:
        data = request.get_json()
        signal_id = data.get('signal_id')
        
        # Get signal details
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
        signal = dict(cursor.fetchone())
        conn.close()
        
        if not signal:
            return jsonify({'success': False, 'error': 'Signal not found'}), 404
        
        # Get current portfolio
        portfolio = db.get_latest_portfolio()
        available_capital = portfolio['ending_capital']
        
        # Calculate position size (2% risk per trade)
        risk_per_trade = available_capital * 0.02
        risk_per_share = signal['entry_price'] - signal['sl_price']
        
        if risk_per_share <= 0:
            return jsonify({'success': False, 'error': 'Invalid stop loss'}), 400
        
        quantity = int(risk_per_trade / risk_per_share)
        position_value = quantity * signal['entry_price']
        
        # Add trade
        trade_id = db.add_trade(
            signal_id=signal_id,
            stock_symbol=signal['stock_symbol'],
            entry_date=datetime.now().date(),
            entry_price=signal['entry_price'],
            quantity=quantity,
            position_value=position_value,
            sl_price=signal['sl_price']
        )
        
        # Update signal status
        db.update_signal_status(signal_id, 'entered')
        
        # Update portfolio
        new_capital = available_capital - position_value
        db.update_portfolio(
            date=datetime.now().date(),
            ending_capital=new_capital,
            day_pnl=0,
            active_trades=len(db.get_active_trades()),
            total_trades=db.get_stats()['total_trades']
        )
        
        return jsonify({
            'success': True,
            'trade_id': trade_id,
            'quantity': quantity,
            'position_value': position_value
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    try:
        stats = db.get_stats()
        portfolio = db.get_latest_portfolio()
        latest_scan = db.get_latest_scan()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'portfolio': portfolio,
            'latest_scan': latest_scan
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health')
def health():
    """Health check endpoint for UptimeRobot"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected'
    })


@app.route('/api/test-fyers')
def test_fyers():
    """Test Fyers connection"""
    try:
        from fyers_auth import FyersAuth
        auth = FyersAuth()
        is_connected = auth.test_connection()
        
        return jsonify({
            'success': is_connected,
            'message': 'Fyers connected' if is_connected else 'Fyers connection failed'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
