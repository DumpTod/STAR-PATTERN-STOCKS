import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fyers_auth import FyersAuth
import time

class MorningStarScanner:
    def __init__(self, db):
        self.db = db
        self.fyers_auth = FyersAuth()
        self.fyers = None
        
    def connect_fyers(self):
        """Establish Fyers connection"""
        self.fyers = self.fyers_auth.get_fyers_client()
        if not self.fyers:
            raise Exception("Failed to connect to Fyers API")
        return True
    
    def get_nifty500_symbols(self):
        """Get list of NSE equity symbols to scan"""
        # For now, using a curated list of liquid stocks
        # In production, fetch from Fyers symbol master or use your uploaded CSV
        symbols = [
            "NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:INFY-EQ",
            "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:BHARTIARTL-EQ",
            "NSE:HINDUNILVR-EQ", "NSE:ITC-EQ", "NSE:LT-EQ", "NSE:KOTAKBANK-EQ",
            "NSE:AXISBANK-EQ", "NSE:ASIANPAINT-EQ", "NSE:MARUTI-EQ",
            "NSE:BAJFINANCE-EQ", "NSE:TITAN-EQ", "NSE:WIPRO-EQ", "NSE:NESTLEIND-EQ",
            "NSE:HCLTECH-EQ", "NSE:ULTRACEMCO-EQ", "NSE:SUNPHARMA-EQ",
            "NSE:ONGC-EQ", "NSE:TATAMOTORS-EQ", "NSE:POWERGRID-EQ", "NSE:NTPC-EQ",
            "NSE:M&M-EQ", "NSE:TATASTEEL-EQ", "NSE:TECHM-EQ", "NSE:BAJAJFINSV-EQ",
            "NSE:ADANIPORTS-EQ", "NSE:COALINDIA-EQ", "NSE:HINDALCO-EQ",
            "NSE:INDUSINDBK-EQ", "NSE:JSWSTEEL-EQ", "NSE:BRITANNIA-EQ",
            "NSE:CIPLA-EQ", "NSE:DRREDDY-EQ", "NSE:EICHERMOT-EQ", "NSE:GRASIM-EQ",
            "NSE:HEROMOTOCO-EQ", "NSE:DIVISLAB-EQ", "NSE:TATACONSUM-EQ",
            "NSE:APOLLOHOSP-EQ", "NSE:ADANIENT-EQ", "NSE:SHREECEM-EQ",
            "NSE:PIDILITIND-EQ", "NSE:HAVELLS-EQ", "NSE:DABUR-EQ", "NSE:GODREJCP-EQ"
        ]
        return symbols
    
    def fetch_historical_data(self, symbol, days=10):
        """Fetch historical OHLC data from Fyers"""
        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            # Format dates for Fyers API (YYYY-MM-DD)
            data = {
                "symbol": symbol,
                "resolution": "D",  # Daily candles
                "date_format": "1",  # Standard date format
                "range_from": from_date.strftime("%Y-%m-%d"),
                "range_to": to_date.strftime("%Y-%m-%d"),
                "cont_flag": "1"
            }
            
            response = self.fyers.history(data=data)
            
            if response['code'] != 200 or 'candles' not in response:
                return None
            
            # Convert to DataFrame
            candles = response['candles']
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.drop('timestamp', axis=1)
            
            return df
            
        except Exception as e:
            print(f"Error fetching {symbol}: {str(e)}")
            return None
    
    def is_doji(self, row):
        """Check if candle is a doji (small body)"""
        body = abs(row['close'] - row['open'])
        candle_range = row['high'] - row['low']
        
        if candle_range == 0:
            return False
        
        # Doji: body is less than 10% of the total range
        return (body / candle_range) < 0.10
    
    def detect_morning_star(self, df):
        """
        Detect Morning Star pattern in the last 3 candles
        
        Pattern:
        - Day 1 (n-2): Red candle (bearish)
        - Day 2 (n-1): Doji/Small body (indecision)
        - Day 3 (n): Green candle closing above Day 1's close
        """
        if len(df) < 3:
            return False, None
        
        # Get last 3 candles
        candle_1 = df.iloc[-3]  # Two days ago
        candle_2 = df.iloc[-2]  # Yesterday
        candle_3 = df.iloc[-1]  # Today
        
        # Day 1: Bearish (red) candle
        is_day1_bearish = candle_1['close'] < candle_1['open']
        
        # Day 2: Doji or small body
        is_day2_doji = self.is_doji(candle_2)
        
        # Day 3: Bullish (green) candle
        is_day3_bullish = candle_3['close'] > candle_3['open']
        
        # Day 3 closes above Day 1's close (confirmation)
        day3_closes_above = candle_3['close'] > candle_1['close']
        
        # Morning Star detected
        if is_day1_bearish and is_day2_doji and is_day3_bullish and day3_closes_above:
            signal_data = {
                'entry_price': candle_3['close'],
                'sl_price': candle_2['low'] * 0.97,  # 3% below Day 2 low
                'signal_date': candle_3['date'].date()
            }
            return True, signal_data
        
        return False, None
    
    def scan_all_stocks(self):
        """Main scanner function - scans all stocks for Morning Star"""
        start_time = time.time()
        
        try:
            # Connect to Fyers
            self.connect_fyers()
            
            symbols = self.get_nifty500_symbols()
            total_stocks = len(symbols)
            signals_found = 0
            stocks_scanned = 0
            
            results = []
            
            for symbol in symbols:
                try:
                    # Fetch data
                    df = self.fetch_historical_data(symbol)
                    
                    if df is None or len(df) < 3:
                        continue
                    
                    stocks_scanned += 1
                    
                    # Detect pattern
                    is_signal, signal_data = self.detect_morning_star(df)
                    
                    if is_signal:
                        # Extract stock name from symbol (NSE:SBIN-EQ -> SBIN)
                        stock_name = symbol.split(':')[1].replace('-EQ', '')
                        
                        # Save to database
                        signal_id = self.db.add_signal(
                            stock_symbol=stock_name,
                            signal_date=signal_data['signal_date'],
                            signal_type='morning_star',
                            entry_price=signal_data['entry_price'],
                            sl_price=signal_data['sl_price']
                        )
                        
                        if signal_id:
                            signals_found += 1
                            results.append({
                                'symbol': stock_name,
                                'entry_price': signal_data['entry_price'],
                                'sl_price': signal_data['sl_price'],
                                'date': signal_data['signal_date']
                            })
                    
                    # Rate limiting - don't hammer API
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"Error scanning {symbol}: {str(e)}")
                    continue
            
            # Calculate scan duration
            scan_duration = time.time() - start_time
            
            # Log scan results
            self.db.add_scanner_log(
                scan_date=datetime.now().date(),
                stocks_scanned=stocks_scanned,
                signals_found=signals_found,
                scan_duration=scan_duration,
                status='success'
            )
            
            return {
                'success': True,
                'stocks_scanned': stocks_scanned,
                'signals_found': signals_found,
                'scan_duration': scan_duration,
                'results': results
            }
            
        except Exception as e:
            # Log error
            self.db.add_scanner_log(
                scan_date=datetime.now().date(),
                stocks_scanned=0,
                signals_found=0,
                scan_duration=time.time() - start_time,
                status='error',
                error_message=str(e)
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_active_trades_exit(self):
        """
        Check if active trades should be exited
        - 3% trailing stop loss hit
        - Evening Star pattern detected (opposite of Morning Star)
        """
        try:
            self.connect_fyers()
            
            active_trades = self.db.get_active_trades()
            
            for trade in active_trades:
                symbol = f"NSE:{trade['stock_symbol']}-EQ"
                
                # Fetch latest data
                df = self.fetch_historical_data(symbol, days=5)
                
                if df is None or len(df) < 1:
                    continue
                
                latest_candle = df.iloc[-1]
                current_price = latest_candle['close']
                
                # Check 3% trailing stop loss
                # SL trails from entry, not from highest point (simplified version)
                if current_price <= trade['sl_price']:
                    # Stop loss hit
                    pnl = self.db.close_trade(
                        trade_id=trade['id'],
                        exit_date=latest_candle['date'].date(),
                        exit_price=current_price,
                        exit_reason='stop_loss'
                    )
                    print(f"Closed {trade['stock_symbol']} at SL. P&L: ₹{pnl:.2f}")
                
                # TODO: Add Evening Star detection for exit
                # For now, keeping it simple with just SL
        
        except Exception as e:
            print(f"Error checking exits: {str(e)}")
