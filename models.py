import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_path='star_pattern.db'):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Signals table - stores detected Morning Star patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                signal_date DATE NOT NULL,
                signal_type TEXT NOT NULL,
                entry_price REAL,
                sl_price REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_symbol, signal_date)
            )
        ''')
        
        # Trades table - tracks active and closed trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                stock_symbol TEXT NOT NULL,
                entry_date DATE,
                entry_price REAL,
                quantity INTEGER,
                position_value REAL,
                sl_price REAL,
                exit_date DATE,
                exit_price REAL,
                exit_reason TEXT,
                pnl REAL,
                pnl_percent REAL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES signals(id)
            )
        ''')
        
        # Portfolio table - tracks capital over time
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                starting_capital REAL,
                ending_capital REAL,
                day_pnl REAL,
                active_trades INTEGER,
                total_trades INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Scanner logs - verify scanner is running
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanner_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_date DATE NOT NULL,
                stocks_scanned INTEGER,
                signals_found INTEGER,
                scan_duration REAL,
                status TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize portfolio if empty
        cursor.execute('SELECT COUNT(*) as count FROM portfolio')
        if cursor.fetchone()['count'] == 0:
            cursor.execute('''
                INSERT INTO portfolio (date, starting_capital, ending_capital, day_pnl, active_trades, total_trades)
                VALUES (?, ?, ?, 0, 0, 0)
            ''', (datetime.now().date(), 500000, 500000))
        
        conn.commit()
        conn.close()
    
    # Signal methods
    def add_signal(self, stock_symbol, signal_date, signal_type, entry_price, sl_price):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO signals (stock_symbol, signal_date, signal_type, entry_price, sl_price, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (stock_symbol, signal_date, signal_type, entry_price, sl_price))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_pending_signals(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            WHERE status = 'pending' 
            ORDER BY signal_date DESC
        ''')
        signals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return signals
    
    def update_signal_status(self, signal_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE signals SET status = ? WHERE id = ?', (status, signal_id))
        conn.commit()
        conn.close()
    
    # Trade methods
    def add_trade(self, signal_id, stock_symbol, entry_date, entry_price, quantity, position_value, sl_price):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (signal_id, stock_symbol, entry_date, entry_price, quantity, 
                              position_value, sl_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ''', (signal_id, stock_symbol, entry_date, entry_price, quantity, position_value, sl_price))
        conn.commit()
        trade_id = cursor.lastrowid
        conn.close()
        return trade_id
    
    def get_active_trades(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM trades 
            WHERE status = 'active' 
            ORDER BY entry_date DESC
        ''')
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    def close_trade(self, trade_id, exit_date, exit_price, exit_reason):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get trade details
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        trade = dict(cursor.fetchone())
        
        # Calculate P&L
        pnl = (exit_price - trade['entry_price']) * trade['quantity']
        pnl_percent = ((exit_price - trade['entry_price']) / trade['entry_price']) * 100
        
        # Update trade
        cursor.execute('''
            UPDATE trades 
            SET exit_date = ?, exit_price = ?, exit_reason = ?, 
                pnl = ?, pnl_percent = ?, status = 'closed'
            WHERE id = ?
        ''', (exit_date, exit_price, exit_reason, pnl, pnl_percent, trade_id))
        
        conn.commit()
        conn.close()
        return pnl
    
    def get_all_trades(self, limit=100):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM trades 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    # Portfolio methods
    def get_latest_portfolio(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM portfolio ORDER BY date DESC LIMIT 1')
        portfolio = dict(cursor.fetchone())
        conn.close()
        return portfolio
    
    def update_portfolio(self, date, ending_capital, day_pnl, active_trades, total_trades):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get previous day's ending capital
        cursor.execute('SELECT ending_capital FROM portfolio ORDER BY date DESC LIMIT 1')
        result = cursor.fetchone()
        starting_capital = result['ending_capital'] if result else 500000
        
        cursor.execute('''
            INSERT OR REPLACE INTO portfolio 
            (date, starting_capital, ending_capital, day_pnl, active_trades, total_trades)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, starting_capital, ending_capital, day_pnl, active_trades, total_trades))
        
        conn.commit()
        conn.close()
    
    # Scanner log methods
    def add_scanner_log(self, scan_date, stocks_scanned, signals_found, scan_duration, status, error_message=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scanner_logs (scan_date, stocks_scanned, signals_found, scan_duration, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (scan_date, stocks_scanned, signals_found, scan_duration, status, error_message))
        conn.commit()
        conn.close()
    
    def get_latest_scan(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scanner_logs ORDER BY created_at DESC LIMIT 1')
        result = cursor.fetchone()
        scan = dict(result) if result else None
        conn.close()
        return scan
    
    # Statistics
    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute('SELECT COUNT(*) FROM trades')
        total_trades = cursor.fetchone()[0]
        
        # Active trades
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = ?', ('active',))
        active_trades = cursor.fetchone()[0]
        
        # Closed trades count
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = ?', ('closed',))
        closed_trades = cursor.fetchone()[0]
        
        # Winners count
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = ? AND pnl > 0', ('closed',))
        winners = cursor.fetchone()[0]
        
        # Losers count
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = ? AND pnl < 0', ('closed',))
        losers = cursor.fetchone()[0]
        
        # Average return
        cursor.execute('SELECT AVG(pnl_percent) FROM trades WHERE status = ?', ('closed',))
        avg_result = cursor.fetchone()[0]
        avg_return = avg_result if avg_result else 0
        
        # Total P&L
        cursor.execute('SELECT SUM(pnl) FROM trades WHERE status = ?', ('closed',))
        pnl_result = cursor.fetchone()[0]
        total_pnl = pnl_result if pnl_result else 0
        
        conn.close()
        
        # Calculate win rate
        win_rate = (winners / closed_trades * 100) if closed_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'active_trades': active_trades,
            'closed_trades': closed_trades,
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_pnl': total_pnl
        }
