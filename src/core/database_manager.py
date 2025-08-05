"""
Database Manager
Veritabanı işlemlerini yönetir (SQLite, PostgreSQL, MongoDB desteği)
"""

import sqlite3
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
import pandas as pd
from loguru import logger
import concurrent.futures


class DatabaseManager:
    """Veritabanı yöneticisi"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Args:
            db_config: Veritabanı konfigürasyonu
        """
        self.config = db_config
        self.db_type = db_config.get('type', 'sqlite')
        self.db_path = db_config.get('path', 'data/trading_bot.db')
        self.connection = None
        
        # SQLite için path'i oluştur
        if self.db_type == 'sqlite':
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """Veritabanını başlat ve tabloları oluştur"""
        try:
            if self.db_type == 'sqlite':
                await self._initialize_sqlite()
            elif self.db_type == 'postgresql':
                await self._initialize_postgresql()
            elif self.db_type == 'mongodb':
                await self._initialize_mongodb()
            else:
                raise ValueError(f"Desteklenmeyen veritabanı türü: {self.db_type}")
            
            await self._create_tables()
            logger.info(f"✅ Veritabanı başlatıldı: {self.db_type}")
            
        except Exception as e:
            logger.error(f"❌ Veritabanı başlatma hatası: {e}")
            raise
    
    async def _initialize_sqlite(self) -> None:
        """SQLite veritabanını başlat"""
        self.connection = await aiosqlite.connect(self.db_path)
        # Enable WAL mode for better concurrency
        await self.connection.execute("PRAGMA journal_mode=WAL")
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.commit()
    
    async def _initialize_postgresql(self) -> None:
        """PostgreSQL veritabanını başlat"""
        # TODO: PostgreSQL desteği eklenecek
        raise NotImplementedError("PostgreSQL desteği henüz eklenmedi")
    
    async def _initialize_mongodb(self) -> None:
        """MongoDB veritabanını başlat"""
        # TODO: MongoDB desteği eklenecek
        raise NotImplementedError("MongoDB desteği henüz eklenmedi")
    
    async def _create_tables(self) -> None:
        """Gerekli tabloları oluştur"""
        tables = {
            'market_data': '''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    timeframe TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, exchange, timestamp, timeframe)
                )
            ''',
            
            'positions': '''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    side TEXT NOT NULL,  -- BUY, SELL
                    size REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL,
                    pnl REAL DEFAULT 0,
                    pnl_percentage REAL DEFAULT 0,
                    strategy TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT DEFAULT 'OPEN',  -- OPEN, CLOSED, CANCELLED
                    opened_at DATETIME NOT NULL,
                    closed_at DATETIME,
                    close_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'trades': '''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id INTEGER,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    price REAL NOT NULL,
                    fee REAL DEFAULT 0,
                    trade_type TEXT NOT NULL,  -- ENTRY, EXIT, PARTIAL_EXIT
                    order_id TEXT,
                    executed_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (position_id) REFERENCES positions (id)
                )
            ''',
            
            'signals': '''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    signal_type TEXT NOT NULL,  -- BUY, SELL, HOLD
                    strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    price REAL NOT NULL,
                    indicators TEXT,  -- JSON string
                    ai_analysis TEXT,  -- JSON string
                    market_condition TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'performance': '''
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_pnl REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_win REAL DEFAULT 0,
                    avg_loss REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    portfolio_value REAL DEFAULT 0,
                    roi REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''',
            
            'ai_models': '''
                CREATE TABLE IF NOT EXISTS ai_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    version TEXT NOT NULL,
                    accuracy REAL,
                    training_data_size INTEGER,
                    parameters TEXT,  -- JSON string
                    model_path TEXT,
                    trained_at DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'system_logs': '''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module TEXT,
                    function_name TEXT,
                    line_number INTEGER,
                    traceback TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''
        }
        
        for table_name, create_sql in tables.items():
            await self.connection.execute(create_sql)
            logger.debug(f"📋 Tablo oluşturuldu/kontrol edildi: {table_name}")
        
        await self.connection.commit()
        logger.info("✅ Tüm tablolar oluşturuldu")
    
    async def save_market_data(self, symbol: str, exchange: str, timeframe: str, 
                              data: Dict[str, Any]) -> None:
        """Market verilerini kaydet"""
        try:
            sql = '''
                INSERT OR REPLACE INTO market_data 
                (symbol, exchange, timestamp, open_price, high_price, low_price, 
                 close_price, volume, timeframe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            await self.connection.execute(sql, (
                symbol, exchange, data['timestamp'], data['open'], 
                data['high'], data['low'], data['close'], 
                data['volume'], timeframe
            ))
            await self.connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Market data kaydetme hatası: {e}")
            raise
    
    async def save_position(self, position_data: Dict[str, Any]) -> int:
        """Pozisyon kaydet"""
        try:
            sql = '''
                INSERT INTO positions 
                (symbol, exchange, side, size, entry_price, strategy, confidence, 
                 stop_loss, take_profit, opened_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            cursor = await self.connection.execute(sql, (
                position_data['symbol'], position_data['exchange'],
                position_data['side'], position_data['size'],
                position_data['entry_price'], position_data['strategy'],
                position_data['confidence'], position_data.get('stop_loss'),
                position_data.get('take_profit'), position_data['opened_at']
            ))
            await self.connection.commit()
            
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"❌ Pozisyon kaydetme hatası: {e}")
            raise
    
    async def update_position(self, position_id: int, updates: Dict[str, Any]) -> None:
        """Pozisyon güncelle"""
        try:
            # Dinamik SQL oluştur
            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            sql = f"UPDATE positions SET {set_clause} WHERE id = ?"
            
            values = list(updates.values()) + [position_id]
            await self.connection.execute(sql, values)
            await self.connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Pozisyon güncelleme hatası: {e}")
            raise
    
    async def save_trade(self, trade_data: Dict[str, Any]) -> int:
        """Trade kaydet"""
        try:
            sql = '''
                INSERT INTO trades 
                (position_id, symbol, exchange, side, size, price, fee, 
                 trade_type, order_id, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            cursor = await self.connection.execute(sql, (
                trade_data.get('position_id'), trade_data['symbol'],
                trade_data['exchange'], trade_data['side'],
                trade_data['size'], trade_data['price'],
                trade_data.get('fee', 0), trade_data['trade_type'],
                trade_data.get('order_id'), trade_data['executed_at']
            ))
            await self.connection.commit()
            
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"❌ Trade kaydetme hatası: {e}")
            raise
    
    async def save_signal(self, signal_data: Dict[str, Any]) -> None:
        """Sinyal kaydet"""
        try:
            sql = '''
                INSERT INTO signals 
                (symbol, exchange, signal_type, strength, confidence, strategy, 
                 timeframe, price, indicators, ai_analysis, market_condition)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            await self.connection.execute(sql, (
                signal_data['symbol'], signal_data['exchange'],
                signal_data['signal_type'], signal_data['strength'],
                signal_data['confidence'], signal_data['strategy'],
                signal_data['timeframe'], signal_data['price'],
                json.dumps(signal_data.get('indicators')),
                json.dumps(signal_data.get('ai_analysis')),
                signal_data.get('market_condition')
            ))
            await self.connection.commit()
            
        except Exception as e:
            logger.error(f"❌ Sinyal kaydetme hatası: {e}")
            raise
    
    async def get_positions(self, symbol: str = None, status: str = 'OPEN') -> List[Dict]:
        """Pozisyonları getir"""
        try:
            if symbol:
                sql = "SELECT * FROM positions WHERE symbol = ? AND status = ?"
                cursor = await self.connection.execute(sql, (symbol, status))
            else:
                sql = "SELECT * FROM positions WHERE status = ?"
                cursor = await self.connection.execute(sql, (status,))
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"❌ Pozisyon getirme hatası: {e}")
            return []
    
    async def get_market_data(self, symbol: str, exchange: str, timeframe: str, 
                             limit: int = 100) -> pd.DataFrame:
        """Market verilerini getir"""
        try:
            sql = '''
                SELECT * FROM market_data 
                WHERE symbol = ? AND exchange = ? AND timeframe = ?
                ORDER BY timestamp DESC LIMIT ?
            '''
            
            # Use sync connection for pandas compatibility
            def _read_sql_sync():
                conn = sqlite3.connect(self.db_path)
                try:
                    return pd.read_sql_query(sql, conn, params=(symbol, exchange, timeframe, limit))
                finally:
                    conn.close()
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                df = await loop.run_in_executor(executor, _read_sql_sync)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Market data getirme hatası: {e}")
            return pd.DataFrame()
    
    async def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Performans istatistiklerini getir"""
        try:
            # Son N günlük performans
            start_date = datetime.now() - timedelta(days=days)
            
            sql = '''
                SELECT * FROM performance 
                WHERE date >= ? 
                ORDER BY date ASC
            '''
            
            cursor = await self.connection.execute(sql, (start_date.date(),))
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            performance_data = [dict(zip(columns, row)) for row in rows]
            
            if not performance_data:
                return {}
            
            # Temel istatistikleri hesapla
            total_pnl = sum(p['total_pnl'] for p in performance_data)
            total_trades = sum(p['total_trades'] for p in performance_data)
            winning_trades = sum(p['winning_trades'] for p in performance_data)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'days_analyzed': len(performance_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Performans istatistikleri hatası: {e}")
            return {}
    
    async def cleanup_old_data(self) -> None:
        """Eski verileri temizle"""
        try:
            retention_days = self.config.get('data_retention_days', 90)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            tables_to_clean = ['market_data', 'signals', 'system_logs']
            
            for table in tables_to_clean:
                sql = f"DELETE FROM {table} WHERE created_at < ?"
                cursor = await self.connection.execute(sql, (cutoff_date,))
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    logger.info(f"🧹 {table} tablosundan {deleted_count} eski kayıt silindi")
            
            await self.connection.commit()
            
            # VACUUM işlemi
            await self.connection.execute("VACUUM")
            logger.info("✅ Veritabanı temizlik işlemi tamamlandı")
            
        except Exception as e:
            logger.error(f"❌ Veritabanı temizlik hatası: {e}")
    
    async def close(self) -> None:
        """Veritabanı bağlantısını kapat"""
        if self.connection:
            await self.connection.close()
            logger.info("✅ Veritabanı bağlantısı kapatıldı")