#!/usr/bin/env python3
"""
Data Manager for A-Stock Analysis
A股数据管理器

Features:
- Unified data interface (统一数据接口)
- Intelligent caching (智能缓存)
- Multi-source aggregation (多源数据整合)
- Cache expiration management (缓存过期管理)
- Data quality validation (数据质量验证)

Author: AI Assistant
Date: 2026-02-19
"""

import os
import json
import pickle
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable
from functools import wraps
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CacheEntry:
    """缓存条目"""
    def __init__(self, data: Any, expire_time: datetime, source: str = "", 
                 metadata: Dict = None):
        self.data = data
        self.created_at = datetime.now()
        self.expire_time = expire_time
        self.source = source
        self.metadata = metadata or {}
        self.access_count = 0
        self.last_accessed = datetime.now()
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.expire_time
    
    def touch(self):
        """更新访问记录"""
        self.access_count += 1
        self.last_accessed = datetime.now()

class DataManager:
    """
    A股数据管理器
    
    功能：
    1. 统一数据接口 - 整合多个数据源
    2. 智能缓存 - 减少API调用，提高性能
    3. 数据验证 - 确保数据质量
    4. 过期管理 - 自动清理过期缓存
    """
    
    # 默认缓存配置
    DEFAULT_CACHE_CONFIG = {
        'realtime_quote': {'ttl': 60, 'unit': 'seconds'},      # 实时行情：1分钟
        'kline_daily': {'ttl': 300, 'unit': 'seconds'},        # 日K线：5分钟
        'kline_weekly': {'ttl': 1800, 'unit': 'seconds'},       # 周K线：30分钟
        'kline_monthly': {'ttl': 3600, 'unit': 'seconds'},       # 月K线：1小时
        'financial_statements': {'ttl': 86400, 'unit': 'seconds'}, # 财务报表：1天
        'valuation_metrics': {'ttl': 3600, 'unit': 'seconds'},   # 估值指标：1小时
        'institutional_holdings': {'ttl': 3600, 'unit': 'seconds'}, # 机构持仓：1小时
        'fund_flow': {'ttl': 300, 'unit': 'seconds'},           # 资金流向：5分钟
        'north_south_bound': {'ttl': 300, 'unit': 'seconds'},   # 北向资金：5分钟
        'analyst_ratings': {'ttl': 3600, 'unit': 'seconds'},    # 分析师评级：1小时
        'sector_performance': {'ttl': 600, 'unit': 'seconds'},   # 板块表现：10分钟
        'search_data': {'ttl': 1800, 'unit': 'seconds'},         # 搜索数据：30分钟
    }
    
    def __init__(self, cache_dir: str = "./cache", config: Dict = None):
        """
        初始化数据管理器
        
        Args:
            cache_dir: 缓存目录路径
            config: 自定义配置（可选）
        """
        self.cache_dir = cache_dir
        self.config = config or {}
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_lock = threading.RLock()
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        
        # 加载磁盘缓存索引
        self.disk_cache_index = self._load_disk_cache_index()
        
        # 启动缓存清理线程
        self._start_cache_cleanup_thread()
        
        logger.info(f"DataManager initialized with cache dir: {cache_dir}")
    
    def _load_disk_cache_index(self) -> Dict:
        """加载磁盘缓存索引"""
        index_path = os.path.join(self.cache_dir, "cache_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}
    
    def _save_disk_cache_index(self):
        """保存磁盘缓存索引"""
        index_path = os.path.join(self.cache_dir, "cache_index.json")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self.disk_cache_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")
    
    def _get_cache_key(self, data_type: str, identifier: str, params: Dict = None) -> str:
        """
        生成缓存键
        
        Args:
            data_type: 数据类型 (e.g., "realtime_quote", "kline_daily")
            identifier: 标识符 (e.g., stock code)
            params: 额外参数
        
        Returns:
            缓存键字符串
        """
        key_parts = [data_type, identifier]
        if params:
            # 将参数字典排序后转换为字符串
            param_str = json.dumps(params, sort_keys=True, separators=(',', ':'))
            key_parts.append(param_str)
        
        raw_key = "|".join(key_parts)
        # 使用哈希缩短键长度
        return hashlib.md5(raw_key.encode()).hexdigest()
    
    def _get_cache_ttl(self, data_type: str) -> int:
        """
        获取缓存过期时间（秒）
        
        Args:
            data_type: 数据类型
        
        Returns:
            过期时间（秒）
        """
        config = self.DEFAULT_CACHE_CONFIG.get(data_type, {'ttl': 300, 'unit': 'seconds'})
        ttl = config['ttl']
        unit = config['unit']
        
        if unit == 'seconds':
            return ttl
        elif unit == 'minutes':
            return ttl * 60
        elif unit == 'hours':
            return ttl * 3600
        elif unit == 'days':
            return ttl * 86400
        else:
            return 300  # 默认5分钟
    
    def get(self, data_type: str, identifier: str, params: Dict = None, 
            force_refresh: bool = False) -> Optional[Any]:
        """
        从缓存获取数据
        
        Args:
            data_type: 数据类型
            identifier: 标识符
            params: 额外参数
            force_refresh: 强制刷新，忽略缓存
        
        Returns:
            缓存数据，如果不存在或已过期则返回None
        """
        if force_refresh:
            return None
        
        cache_key = self._get_cache_key(data_type, identifier, params)
        
        with self.cache_lock:
            # 1. 检查内存缓存
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                if not entry.is_expired():
                    entry.touch()
                    logger.debug(f"Memory cache hit: {cache_key}")
                    return entry.data
                else:
                    # 过期，删除
                    del self.memory_cache[cache_key]
            
            # 2. 检查磁盘缓存
            if cache_key in self.disk_cache_index:
                cache_info = self.disk_cache_index[cache_key]
                expire_time = datetime.fromisoformat(cache_info['expire_time'])
                
                if datetime.now() < expire_time:
                    # 未过期，加载
                    cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
                    try:
                        with open(cache_file, 'rb') as f:
                            data = pickle.load(f)
                        
                        # 同时放入内存缓存
                        entry = CacheEntry(
                            data=data,
                            expire_time=expire_time,
                            source="disk",
                            metadata=cache_info.get('metadata', {})
                        )
                        self.memory_cache[cache_key] = entry
                        
                        logger.debug(f"Disk cache hit: {cache_key}")
                        return data
                    except Exception as e:
                        logger.warning(f"Failed to load disk cache: {e}")
                else:
                    # 过期，删除索引
                    del self.disk_cache_index[cache_key]
                    self._save_disk_cache_index()
        
        return None
    
    def set(self, data_type: str, identifier: str, data: Any, 
            params: Dict = None, metadata: Dict = None) -> bool:
        """
        设置缓存数据
        
        Args:
            data_type: 数据类型
            identifier: 标识符
            data: 要缓存的数据
            params: 额外参数
            metadata: 元数据
        
        Returns:
            是否成功
        """
        try:
            cache_key = self._get_cache_key(data_type, identifier, params)
            ttl = self._get_cache_ttl(data_type)
            expire_time = datetime.now() + timedelta(seconds=ttl)
            
            entry = CacheEntry(
                data=data,
                expire_time=expire_time,
                source="api",
                metadata=metadata or {}
            )
            
            with self.cache_lock:
                # 存入内存缓存
                self.memory_cache[cache_key] = entry
                
                # 同时存入磁盘缓存（如果数据较大或需要持久化）
                if self._should_persist_to_disk(data_type, data):
                    cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
                    with open(cache_file, 'wb') as f:
                        pickle.dump(data, f)
                    
                    # 更新索引
                    self.disk_cache_index[cache_key] = {
                        'expire_time': expire_time.isoformat(),
                        'data_type': data_type,
                        'identifier': identifier,
                        'metadata': metadata or {}
                    }
                    self._save_disk_cache_index()
            
            logger.debug(f"Cache set: {cache_key}, expires at {expire_time}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False
    
    def _should_persist_to_disk(self, data_type: str, data: Any) -> bool:
        """判断是否应该持久化到磁盘"""
        # 财务报表等大数据持久化
        if data_type in ['financial_statements', 'kline_daily', 'kline_weekly']:
            return True
        
        # 检查数据大小（粗略估计）
        try:
            data_size = len(str(data))
            if data_size > 10000:  # 大于10KB
                return True
        except:
            pass
        
        return False
    
    def delete(self, data_type: str, identifier: str, params: Dict = None) -> bool:
        """删除缓存"""
        try:
            cache_key = self._get_cache_key(data_type, identifier, params)
            
            with self.cache_lock:
                # 删除内存缓存
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
                
                # 删除磁盘缓存
                if cache_key in self.disk_cache_index:
                    cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
                    if os.path.exists(cache_file):
                        os.remove(cache_file)
                    
                    del self.disk_cache_index[cache_key]
                    self._save_disk_cache_index()
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete cache: {e}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            with self.cache_lock:
                # 清空内存缓存
                self.memory_cache.clear()
                
                # 清空磁盘缓存
                for cache_key in list(self.disk_cache_index.keys()):
                    cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
                    if os.path.exists(cache_file):
                        os.remove(cache_file)
                
                self.disk_cache_index.clear()
                self._save_disk_cache_index()
            
            logger.info("All cache cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self.cache_lock:
            memory_size = len(self.memory_cache)
            disk_size = len(self.disk_cache_index)
            
            # 计算内存缓存数据大小（粗略估计）
            total_memory_size = 0
            for entry in self.memory_cache.values():
                try:
                    total_memory_size += len(str(entry.data))
                except:
                    pass
            
            # 统计过期缓存
            expired_memory = sum(1 for e in self.memory_cache.values() if e.is_expired())
            
            return {
                'memory_cache_entries': memory_size,
                'disk_cache_entries': disk_size,
                'total_entries': memory_size + disk_size,
                'memory_cache_size_bytes': total_memory_size,
                'memory_cache_size_mb': round(total_memory_size / 1024 / 1024, 2),
                'expired_memory_entries': expired_memory,
                'cache_dir': self.cache_dir,
            }
    
    def _start_cache_cleanup_thread(self):
        """启动缓存清理线程"""
        def cleanup_task():
            while True:
                try:
                    time.sleep(300)  # 每5分钟检查一次
                    self._cleanup_expired_cache()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
        logger.info("Cache cleanup thread started")
    
    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        with self.cache_lock:
            # 清理内存缓存
            expired_keys = [k for k, v in self.memory_cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.memory_cache[key]
            
            # 清理磁盘缓存
            expired_disk_keys = [k for k, v in self.disk_cache_index.items() 
                               if datetime.now() > datetime.fromisoformat(v['expire_time'])]
            for key in expired_disk_keys:
                cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                del self.disk_cache_index[key]
            
            if expired_disk_keys:
                self._save_disk_cache_index()
            
            total_cleaned = len(expired_keys) + len(expired_disk_keys)
            if total_cleaned > 0:
                logger.info(f"Cleaned {total_cleaned} expired cache entries")

# 全局数据管理器实例
_data_manager = None

def get_data_manager(cache_dir: str = "./cache", config: Dict = None) -> DataManager:
    """
    获取数据管理器实例（单例模式）
    
    Args:
        cache_dir: 缓存目录
        config: 配置字典
    
    Returns:
        DataManager实例
    """
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(cache_dir=cache_dir, config=config)
    return _data_manager

def reset_data_manager():
    """重置数据管理器（主要用于测试）"""
    global _data_manager
    _data_manager = None

# 装饰器：自动缓存
def cached(data_type: str, ttl: int = None, identifier_param: str = "stock_code"):
    """
    缓存装饰器
    
    Args:
        data_type: 数据类型
        ttl: 自定义过期时间（秒）
        identifier_param: 标识符参数名
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取数据管理器
            dm = get_data_manager()
            
            # 获取标识符
            identifier = kwargs.get(identifier_param)
            if not identifier and args:
                # 尝试从位置参数获取
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if identifier_param in params:
                    idx = params.index(identifier_param)
                    if idx < len(args):
                        identifier = args[idx]
            
            if not identifier:
                # 无法获取标识符，直接执行函数
                return func(*args, **kwargs)
            
            # 构建其他参数（包含函数名与位置参数绑定，避免同 data_type 接口缓存键冲突）
            import inspect
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            bound.apply_defaults()
            other_params = {
                k: v for k, v in bound.arguments.items() if k != identifier_param
            }
            other_params["__func__"] = func.__name__
            
            # 尝试从缓存获取
            cached_data = dm.get(data_type, identifier, other_params)
            if cached_data is not None:
                logger.debug(f"Cache hit for {data_type}:{identifier}")
                return cached_data
            
            # 缓存未命中，执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            if result is not None:
                # 使用自定义TTL或默认TTL
                if ttl is not None:
                    # 临时修改该数据类型的TTL
                    original_config = dm.DEFAULT_CACHE_CONFIG.get(data_type, {})
                    original_ttl = original_config.get('ttl')
                    dm.DEFAULT_CACHE_CONFIG[data_type] = {'ttl': ttl, 'unit': 'seconds'}
                
                dm.set(data_type, identifier, result, other_params)
                
                # 恢复原始TTL
                if ttl is not None and original_ttl is not None:
                    dm.DEFAULT_CACHE_CONFIG[data_type]['ttl'] = original_ttl
                
                logger.debug(f"Cached {data_type}:{identifier}")
            
            return result
        
        return wrapper
    return decorator

# 测试代码
if __name__ == "__main__":
    # 测试数据管理器
    dm = get_data_manager(cache_dir="./test_cache")
    
    # 测试数据存储
    test_data = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "price": 1800.50,
        "timestamp": datetime.now().isoformat()
    }
    
    # 存入缓存
    result = dm.set("realtime_quote", "600519", test_data)
    print(f"Cache set result: {result}")
    
    # 从缓存读取
    cached_data = dm.get("realtime_quote", "600519")
    print(f"Cache get result: {cached_data}")
    
    # 获取统计信息
    stats = dm.get_stats()
    print(f"Cache stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    print("✅ DataManager test completed!")
