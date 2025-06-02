from pathlib import Path
from typing import Optional

from ..config.config_service import ConfigService
from .storage_adapter import StorageAdapter
from .sqlite_adapter import SQLiteAdapter
from .json_adapter import JSONAdapter


class StorageFactory:
    """Factory for creating storage adapters based on configuration."""
    
    @staticmethod
    def create_storage_adapter(config: ConfigService) -> StorageAdapter:
        """Create a storage adapter based on configuration.
        
        Args:
            config: Configuration service
            
        Returns:
            Appropriate storage adapter instance
            
        Raises:
            ValueError: If storage type is not supported
        """
        storage_type = config.get_storage_type().lower()
        storage_path = config.get_storage_path()
        
        if storage_type == "sqlite":
            db_path = Path(storage_path) / "youtube_comments.db"
            return SQLiteAdapter(str(db_path))
        elif storage_type == "json":
            return JSONAdapter(storage_path, use_jsonl=False)
        elif storage_type == "jsonl":
            return JSONAdapter(storage_path, use_jsonl=True)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}. "
                             f"Supported types are: sqlite, json, jsonl.") 