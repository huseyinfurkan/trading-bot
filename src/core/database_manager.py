"""
Database Manager
SQLite veritabanı işlemleri ve veri yönetimi
"""

import asyncio
import aiosqlite
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import sqlite3


class DatabaseManager:
    """Veritabanı yöneticisi"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Args:
            db_config: Veritabanı konfigürasyonu
        """
        self.config = db_config
        self.db_path = Path(db_config.get('path', 'data/trading_bot.db'))
        self.connection = None
        self.connection_pool = []
        self.max_connections = db_config.get('pool_size', 10)
        
        # Create data directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("💾 Database Manager initialized")
    
    async def initialize(self):
        """Veritabanını başlat ve tabloları oluştur"""
        try:
            logger.info("💾 Initializing database...")
            
            # Initialize connection pool
            await self._initialize_connection_pool()
            
            # Create tables
            await self._create_tables()
            
            # Create indexes for better performance
            await self._create_indexes()
            
            logger.success("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            raise
    
    async def _initialize_connection_pool(self):
        """Connection pool başlat"""
        try:
            # Create main connection
            self.connection = await aiosqlite.connect(str(self.db_path))
            
            # Configure for better performance with dynamic values
            await self.connection.execute("PRAGMA journal_mode=WAL")
            await self.connection.execute("PRAGMA synchronous=NORMAL")
            await self.connection.execute("PRAGMA temp_store=MEMORY")
            
            # Dynamic PRAGMA values based on system memory
            try:
                import psutil
                system_memory = psutil.virtual_memory().total
                # Calculate dynamic values based on available memory
                mmap_size = min(system_memory // 4, 268435456)  # 25% of system memory, max 256MB
                cache_size = min(system_memory // (1024 * 1024 * 100), 10000)  # Dynamic cache size
                
                await self.connection.execute(f"PRAGMA mmap_size={mmap_size}")
                await self.connection.execute(f"PRAGMA cache_size={cache_size}")
                await self.connection.execute("PRAGMA page_size=4096")
                
                logger.info(f"📊 Dynamic PRAGMA values - mmap_size: {mmap_size}, cache_size: {cache_size}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not set dynamic PRAGMA values: {e}")
                # Fallback to static values
                await self.connection.execute("PRAGMA mmap_size=268435456")  # 256MB
                await self.connection.execute("PRAGMA cache_size=10000")
                await self.connection.execute("PRAGMA page_size=4096")
            
            # Create additional connections for pool
            for i in range(self.max_connections - 1):
                conn = await aiosqlite.connect(str(self.db_path))
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA temp_store=MEMORY")
                self.connection_pool.append(conn)
            
            logger.info(f"✅ Connection pool initialized with {self.max_connections} connections")
            
        except Exception as e:
            logger.error(f"❌ Connection pool initialization error: {e}")
            raise
    
    async def _get_connection(self):
        """Connection pool'dan connection al"""
        if self.connection_pool:
            return self.connection_pool.pop()
        else:
            # Create new connection if pool is empty
            conn = await aiosqlite.connect(str(self.db_path))
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            return conn
    
    async def _return_connection(self, conn):
        """Connection'ı pool'a geri ver"""
        if len(self.connection_pool) < self.max_connections:
            self.connection_pool.append(conn)
        else:
            await conn.close()
    
    async def _create_tables(self):
        """Veritabanı tablolarını oluştur"""
        try:
            # Positions table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    pnl REAL DEFAULT 0,
                    status TEXT DEFAULT 'OPEN',
                    strategy TEXT,
                    confidence REAL,
                    exchange TEXT,
                    order_id TEXT,
                    leverage REAL DEFAULT 1.0,
                    margin_required REAL DEFAULT 0.0,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Market data table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, exchange, timeframe, timestamp)
                )
            """)
            
            # Signals table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    strategy TEXT,
                    price REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Trades table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    pnl REAL DEFAULT 0,
                    fees REAL DEFAULT 0,
                    strategy TEXT,
                    confidence REAL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_time TIMESTAMP,
                    duration_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)
            
            # System logs table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            await self.connection.commit()
            logger.success("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Table creation error: {e}")
            raise
    
    async def _create_indexes(self):
        """Performans için indexler oluştur"""
        try:
            # Positions indexes
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_positions_opened_at ON positions(opened_at)")
            
            # Market data indexes
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timeframe ON market_data(timeframe)")
            
            # Signals indexes
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type)")
            
            # Trades indexes
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)")
            
            # Performance metrics indexes
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_metrics(date)")
            
            await self.connection.commit()
            logger.success("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Index creation error: {e}")
            raise
    
    async def save_position(self, position_data: Dict[str, Any]) -> int:
        """Pozisyon kaydet"""
        try:
            cursor = await self.connection.execute("""
                INSERT INTO positions (symbol, side, size, entry_price, stop_loss, take_profit, 
                                     strategy, confidence, exchange, order_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data['symbol'],
                position_data['side'],
                position_data['size'],
                position_data['entry_price'],
                position_data.get('stop_loss'),
                position_data.get('take_profit'),
                position_data.get('strategy'),
                position_data.get('confidence'),
                position_data.get('exchange'),
                position_data.get('order_id')
            ))
            
            await self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"❌ Position save error: {e}")
            return None
    
    async def get_positions(self, status: str = None, symbol: str = None) -> List[Dict[str, Any]]:
        """Pozisyonları getir"""
        try:
            query = "SELECT * FROM positions WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY created_at DESC"
            
            cursor = await self.connection.execute(query, params)
            rows = await cursor.fetchall()
            
            # Convert to list of dictionaries
            columns = [description[0] for description in cursor.description]
            positions = []
            for row in rows:
                position = dict(zip(columns, row))
                positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"❌ Get positions error: {e}")
            return []
    
    async def update_position(self, position_id: int, updates: Dict[str, Any]) -> bool:
        """Pozisyon güncelle"""
        try:
            # Validate allowed columns to prevent SQL injection
            allowed_columns = {
                'current_price', 'stop_loss', 'take_profit', 'pnl', 
                'status', 'closed_at', 'side', 'size'
            }
            
            # Build dynamic update query with validation
            set_clauses = []
            params = []
            
            for key, value in updates.items():
                if key not in allowed_columns:
                    logger.warning(f"⚠️ Ignoring invalid column: {key}")
                    continue
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
            if not set_clauses:
                logger.warning("⚠️ No valid columns to update")
                return False
            
            params.append(position_id)
            
            query = f"UPDATE positions SET {', '.join(set_clauses)} WHERE id = ?"
            
            await self.connection.execute(query, params)
            await self.connection.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Position update error: {e}")
            return False
    
    async def save_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Market data kaydet"""
        try:
            await self.connection.execute("""
                INSERT OR REPLACE INTO market_data 
                (symbol, exchange, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data['symbol'],
                market_data['exchange'],
                market_data['timeframe'],
                market_data['timestamp'],
                market_data['open'],
                market_data['high'],
                market_data['low'],
                market_data['close'],
                market_data['volume']
            ))
            
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Market data save error: {e}")
            return False
    
    async def get_market_data(self, symbol: str, exchange: str, timeframe: str, 
                            limit: int = 100) -> pd.DataFrame:
        """Market data getir"""
        try:
            cursor = await self.connection.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM market_data
                WHERE symbol = ? AND exchange = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, exchange, timeframe, limit))
            
            rows = await cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Get market data error: {e}")
            return pd.DataFrame()
    
    async def save_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Sinyal kaydet"""
        try:
            await self.connection.execute("""
                INSERT INTO signals (symbol, signal_type, confidence, strategy, price, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_data['symbol'],
                signal_data['signal_type'],
                signal_data['confidence'],
                signal_data.get('strategy', ''),
                signal_data.get('price', 0),
                signal_data.get('timestamp', datetime.now()),
                signal_data.get('metadata', '')
            ))
            
            await self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Signal save error: {e}")
            return False
    
    async def get_daily_pnl(self, date: datetime.date) -> Optional[float]:
        """Günlük P&L getir"""
        try:
            cursor = await self.connection.execute("""
                SELECT SUM(pnl) as daily_pnl
                FROM positions
                WHERE DATE(created_at) = ? AND status = 'CLOSED'
            """, (date,))
            
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0.0
            
        except Exception as e:
            logger.error(f"❌ Daily PnL error: {e}")
            return 0.0
    
    async def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Performans istatistikleri getir"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            cursor = await self.connection.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_win,
                    MIN(pnl) as max_loss
                FROM positions
                WHERE DATE(closed_at) BETWEEN ? AND ?
                  AND status = 'CLOSED'
            """, (start_date, end_date))
            
            row = await cursor.fetchone()
            
            if not row or row[0] == 0:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'profit_factor': 0
                }
            
            total_trades, winning_trades, losing_trades, total_pnl, avg_pnl, max_win, max_loss = row
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate profit factor
            total_wins = await self._get_total_wins(start_date, end_date)
            total_losses = abs(await self._get_total_losses(start_date, end_date))
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl or 0,
                'avg_pnl': avg_pnl or 0,
                'profit_factor': profit_factor,
                'max_win': max_win or 0,
                'max_loss': max_loss or 0
            }
            
        except Exception as e:
            logger.error(f"❌ Performance stats error: {e}")
            return {}
    
    async def _get_total_wins(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """Toplam kazanç getir"""
        try:
            cursor = await self.connection.execute("""
                SELECT SUM(pnl) FROM positions
                WHERE DATE(closed_at) BETWEEN ? AND ?
                  AND status = 'CLOSED' AND pnl > 0
            """, (start_date, end_date))
            
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0.0
            
        except Exception as e:
            logger.error(f"❌ Total wins error: {e}")
            return 0.0
    
    async def _get_total_losses(self, start_date: datetime.date, end_date: datetime.date) -> float:
        """Toplam zarar getir"""
        try:
            cursor = await self.connection.execute("""
                SELECT SUM(pnl) FROM positions
                WHERE DATE(closed_at) BETWEEN ? AND ?
                  AND status = 'CLOSED' AND pnl < 0
            """, (start_date, end_date))
            
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0.0
            
        except Exception as e:
            logger.error(f"❌ Total losses error: {e}")
            return 0.0
    
    async def save_trade(self, trade_data: Dict[str, Any]) -> Optional[int]:
        """Trade bilgisini veritabanına kaydet - with validation and retry"""
        # DATA TYPE VALIDATION
        if not self._validate_trade_data(trade_data):
            logger.error("❌ Trade data validation failed")
            return None
        
        # RETRY MECHANISM
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Ensure connection is healthy
                if not await self._ensure_connection():
                    if attempt == max_retries - 1:
                        logger.error("❌ Database connection failed after retries")
                        return None
                    await asyncio.sleep(0.5)
                    continue
                
                cursor = await self.connection.execute("""
                    INSERT INTO trades (
                        symbol, side, size, entry_price, exit_price, pnl, fees, strategy, 
                        confidence, entry_time, exit_time, duration_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get('symbol'),
                    trade_data.get('side'),
                    float(trade_data.get('size', 0.0)),
                    float(trade_data.get('entry_price', 0.0)),
                    float(trade_data.get('exit_price', 0.0)),
                    float(trade_data.get('pnl', 0.0)),
                    float(trade_data.get('fees', 0.0)),
                    trade_data.get('strategy'),
                    float(trade_data.get('confidence', 0.0)),
                    trade_data.get('entry_time', datetime.now()),
                    trade_data.get('exit_time'),
                    trade_data.get('duration_seconds', 0)
                ))
                
                await self.connection.commit()
                trade_id = cursor.lastrowid
                
                logger.debug(f"✅ Trade saved: {trade_data.get('symbol')} {trade_data.get('side')} - ID: {trade_id}")
                return trade_id
                
            except Exception as e:
                logger.warning(f"⚠️ Save trade attempt {attempt + 1} failed: {e}")
                await self.connection.rollback()
                
                if attempt == max_retries - 1:
                    logger.error(f"❌ Error saving trade after {max_retries} attempts: {e}")
                    return None
                
                # Wait before retry
                await asyncio.sleep(0.5 * (attempt + 1))
        
        return None
    
    def _validate_trade_data(self, trade_data: Dict[str, Any]) -> bool:
        """Trade data type validation"""
        try:
            required_fields = ['symbol', 'side', 'size', 'price']
            
            # Check required fields
            for field in required_fields:
                if field not in trade_data:
                    logger.error(f"❌ Missing required field: {field}")
                    return False
            
            # Validate types
            if not isinstance(trade_data.get('symbol'), str):
                logger.error("❌ Symbol must be string")
                return False
                
            if trade_data.get('side') not in ['BUY', 'SELL', 'LONG', 'SHORT']:
                logger.error(f"❌ Invalid side: {trade_data.get('side')}")
                return False
            
            # Validate numeric fields
            try:
                float(trade_data.get('size', 0))
                float(trade_data.get('price', 0))
                if 'pnl' in trade_data:
                    float(trade_data.get('pnl'))
                if 'confidence' in trade_data:
                    confidence = float(trade_data.get('confidence'))
                    if not 0 <= confidence <= 1:
                        logger.error(f"❌ Confidence must be 0-1, got: {confidence}")
                        return False
            except (ValueError, TypeError) as e:
                logger.error(f"❌ Numeric validation failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Trade data validation error: {e}")
            return False
    
    async def update_trade_pnl(self, trade_id: int, pnl: float) -> bool:
        """Trade PnL'ini güncelle"""
        try:
            await self.connection.execute("""
                UPDATE trades SET pnl = ? WHERE id = ?
            """, (pnl, trade_id))
            
            await self.connection.commit()
            logger.debug(f"✅ Trade PnL updated: ID {trade_id} = {pnl}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating trade PnL: {e}")
            await self.connection.rollback()
            return False

    async def get_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Trade geçmişini getir"""
        try:
            # Get connection from pool
            conn = await self._get_connection()
            
            if symbol:
                cursor = await conn.execute("""
                    SELECT * FROM trades WHERE symbol = ? 
                    ORDER BY entry_time DESC LIMIT ?
                """, (symbol, limit))
            else:
                cursor = await conn.execute("""
                    SELECT * FROM trades 
                    ORDER BY entry_time DESC LIMIT ?
                """, (limit,))
            
            rows = await cursor.fetchall()
            
            trades = []
            for row in rows:
                trades.append({
                    'id': row[0],
                    'symbol': row[1],
                    'side': row[2],
                    'size': row[3],
                    'entry_price': row[4],
                    'exit_price': row[5],
                    'pnl': row[6],
                    'fees': row[7],
                    'strategy': row[8],
                    'confidence': row[9],
                    'entry_time': row[10],
                    'exit_time': row[11],
                    'duration_seconds': row[12]
                })
            
            # Return connection to pool
            await self._return_connection(conn)
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Get trades error: {e}")
            # Return connection to pool on error
            if 'conn' in locals():
                await self._return_connection(conn)
            return []
    
    async def cleanup_old_data(self, days: int = 90):
        """Eski verileri temizle"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clean old market data
            await self.connection.execute("""
                DELETE FROM market_data WHERE created_at < ?
            """, (cutoff_date,))
            
            # Clean old signals
            await self.connection.execute("""
                DELETE FROM signals WHERE created_at < ?
            """, (cutoff_date,))
            
            await self.connection.commit()
            logger.info(f"🗑️ Old data cleaned (older than {days} days)")
            
        except Exception as e:
            logger.error(f"❌ Data cleanup error: {e}")
    
    async def check_connection_health(self) -> bool:
        """Veritabanı bağlantı sağlığını kontrol et"""
        try:
            if not self.connection:
                return False
            
            cursor = await self.connection.execute("SELECT 1")
            await cursor.fetchone()
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection health check failed: {e}")
            return False
    
    async def _ensure_connection(self) -> bool:
        """Veritabanı bağlantısının aktif olduğundan emin ol"""
        try:
            if await self.check_connection_health():
                return True
            
            logger.warning("⚠️ Database connection lost, reconnecting...")
            
            # Close existing connection if any
            if self.connection:
                await self.connection.close()
            
            # Reinitialize connection
            await self.initialize()
            return await self.check_connection_health()
            
        except Exception as e:
            logger.error(f"❌ Database reconnection failed: {e}")
            return False
    
    async def execute_with_retry(self, query: str, params=None, max_retries: int = 3):
        """Execute SQL with automatic retry on connection failure"""
        for attempt in range(max_retries):
            try:
                if not await self._ensure_connection():
                    if attempt == max_retries - 1:
                        raise Exception("Database connection could not be established")
                    continue
                
                if params:
                    cursor = await self.connection.execute(query, params)
                else:
                    cursor = await self.connection.execute(query)
                
                return cursor
                
            except Exception as e:
                logger.warning(f"⚠️ Database query attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                
                # Wait before retry
                await asyncio.sleep(0.5 * (attempt + 1))
        
        raise Exception("All database retry attempts failed")
    
    async def close(self):
        """Veritabanı bağlantısını kapat"""
        try:
            if self.connection:
                await self.connection.close()
                logger.info("💾 Database connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing database: {e}")
    
    async def get_connection(self):
        """Veritabanı bağlantısını döndür"""
        return self.connection