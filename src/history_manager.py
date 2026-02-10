"""
history_manager.py - Gestor de historial, favoritos y exportacion de links resueltos.

Maneja:
- Guardado de links resueltos en BD SQLite
- Sistema de favoritos (marcar/desmarcar)
- Exportacion a JSON y CSV
"""

import sqlite3
import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ResolutionRecord:
    """Registro de una resolucion de link"""
    id: Optional[int] = None
    original_url: str = ""
    resolved_url: str = ""
    quality: str = ""
    format_type: str = ""
    provider: str = ""
    score: float = 0.0
    is_favorite: bool = False
    timestamp: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        data = asdict(self)
        # Remover el ID para exportacion
        if data.get('id'):
            del data['id']
        return data


class HistoryManager:
    """
    Gestor de historial, favoritos y exportacion.
    Usa SQLite para persistencia.
    """
    
    DB_FILENAME = "neo_link_resolver.db"
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa el gestor de historial.
        
        Args:
            db_path: Ruta personalizada para la BD (default: directorio data/)
        """
        if db_path is None:
            # Usar directorio data/ del proyecto
            base_dir = Path(__file__).parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / self.DB_FILENAME
        else:
            db_path = Path(db_path) / self.DB_FILENAME
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializa la BD y crea tablas si no existen"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Crear tabla de historial
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS resolution_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_url TEXT NOT NULL,
                        resolved_url TEXT,
                        quality TEXT,
                        format_type TEXT,
                        provider TEXT,
                        score REAL,
                        is_favorite BOOLEAN DEFAULT 0,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT,
                        UNIQUE(original_url, timestamp)
                    )
                """)
                
                conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def add_record(
        self,
        original_url: str,
        resolved_url: str,
        quality: str = "",
        format_type: str = "",
        provider: str = "",
        score: float = 0.0,
        notes: str = ""
    ) -> Optional[int]:
        """
        Agrega un registro al historial.
        
        Returns:
            ID del registro insertado, o None si hubo error
        """
        try:
            timestamp = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO resolution_history 
                    (original_url, resolved_url, quality, format_type, provider, score, timestamp, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (original_url, resolved_url, quality, format_type, provider, score, timestamp, notes))
                
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error adding record: {e}")
            return None
    
    def get_all_records(self) -> List[ResolutionRecord]:
        """Obtiene todos los registros del historial"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM resolution_history ORDER BY timestamp DESC
                """)
                
                records = []
                for row in cursor.fetchall():
                    record = ResolutionRecord(
                        id=row['id'],
                        original_url=row['original_url'],
                        resolved_url=row['resolved_url'],
                        quality=row['quality'],
                        format_type=row['format_type'],
                        provider=row['provider'],
                        score=row['score'],
                        is_favorite=bool(row['is_favorite']),
                        timestamp=row['timestamp'],
                        notes=row['notes']
                    )
                    records.append(record)
                
                return records
        except Exception as e:
            print(f"Error getting records: {e}")
            return []
    
    def get_favorites(self) -> List[ResolutionRecord]:
        """Obtiene solo los registros marcados como favoritos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM resolution_history 
                    WHERE is_favorite = 1 
                    ORDER BY timestamp DESC
                """)
                
                records = []
                for row in cursor.fetchall():
                    record = ResolutionRecord(
                        id=row['id'],
                        original_url=row['original_url'],
                        resolved_url=row['resolved_url'],
                        quality=row['quality'],
                        format_type=row['format_type'],
                        provider=row['provider'],
                        score=row['score'],
                        is_favorite=bool(row['is_favorite']),
                        timestamp=row['timestamp'],
                        notes=row['notes']
                    )
                    records.append(record)
                
                return records
        except Exception as e:
            print(f"Error getting favorites: {e}")
            return []
    
    def toggle_favorite(self, record_id: int) -> bool:
        """
        Marca/desmarca un registro como favorito.
        
        Returns:
            True si se actualizo correctamente, False si hubo error
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener estado actual
                cursor.execute("SELECT is_favorite FROM resolution_history WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                current_state = row[0]
                new_state = 1 - current_state  # Toggle
                
                cursor.execute(
                    "UPDATE resolution_history SET is_favorite = ? WHERE id = ?",
                    (new_state, record_id)
                )
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error toggling favorite: {e}")
            return False
    
    def delete_record(self, record_id: int) -> bool:
        """
        Elimina un registro del historial.
        
        Returns:
            True si se elimino correctamente, False si hubo error
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM resolution_history WHERE id = ?", (record_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting record: {e}")
            return False
    
    def update_notes(self, record_id: int, notes: str) -> bool:
        """
        Actualiza las notas de un registro.
        
        Returns:
            True si se actualizo correctamente, False si hubo error
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE resolution_history SET notes = ? WHERE id = ?",
                    (notes, record_id)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating notes: {e}")
            return False
    
    def search_records(self, query: str) -> List[ResolutionRecord]:
        """
        Busca registros por URL o notas.
        
        Args:
            query: Termino a buscar
            
        Returns:
            Lista de registros que coinciden
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                search_pattern = f"%{query}%"
                cursor.execute("""
                    SELECT * FROM resolution_history 
                    WHERE original_url LIKE ? OR resolved_url LIKE ? OR notes LIKE ?
                    ORDER BY timestamp DESC
                """, (search_pattern, search_pattern, search_pattern))
                
                records = []
                for row in cursor.fetchall():
                    record = ResolutionRecord(
                        id=row['id'],
                        original_url=row['original_url'],
                        resolved_url=row['resolved_url'],
                        quality=row['quality'],
                        format_type=row['format_type'],
                        provider=row['provider'],
                        score=row['score'],
                        is_favorite=bool(row['is_favorite']),
                        timestamp=row['timestamp'],
                        notes=row['notes']
                    )
                    records.append(record)
                
                return records
        except Exception as e:
            print(f"Error searching records: {e}")
            return []
    
    def export_to_json(self, records: Optional[List[ResolutionRecord]] = None, filepath: Optional[str] = None) -> Tuple[bool, str]:
        """
        Exporta registros a JSON.
        
        Args:
            records: Lista de registros a exportar (default: todos)
            filepath: Ruta donde guardar el archivo (default: directorio actual)
            
        Returns:
            Tupla (exito, ruta_archivo)
        """
        try:
            if records is None:
                records = self.get_all_records()
            
            if filepath is None:
                filename = f"neo_link_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                data_dir = Path(__file__).parent.parent / "data"
                data_dir.mkdir(exist_ok=True)
                filepath = data_dir / filename
            else:
                filepath = Path(filepath)
            
            # Convertir registros a dicts
            data = {
                "export_date": datetime.now().isoformat(),
                "total_records": len(records),
                "records": [record.to_dict() for record in records]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True, str(filepath)
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False, str(e)
    
    def export_to_csv(self, records: Optional[List[ResolutionRecord]] = None, filepath: Optional[str] = None) -> Tuple[bool, str]:
        """
        Exporta registros a CSV.
        
        Args:
            records: Lista de registros a exportar (default: todos)
            filepath: Ruta donde guardar el archivo (default: directorio actual)
            
        Returns:
            Tupla (exito, ruta_archivo)
        """
        try:
            if records is None:
                records = self.get_all_records()
            
            if filepath is None:
                filename = f"neo_link_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                data_dir = Path(__file__).parent.parent / "data"
                data_dir.mkdir(exist_ok=True)
                filepath = data_dir / filename
            else:
                filepath = Path(filepath)
            
            if not records:
                return False, "No records to export"
            
            # Obtener headers del primer registro
            fieldnames = ['original_url', 'resolved_url', 'quality', 'format_type', 'provider', 'score', 'is_favorite', 'timestamp', 'notes']
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in records:
                    row = record.to_dict()
                    row['is_favorite'] = 'Yes' if row.get('is_favorite') else 'No'
                    writer.writerow(row)
            
            return True, str(filepath)
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False, str(e)
    
    def get_statistics(self) -> Dict:
        """
        Obtiene estadisticas del historial.
        
        Returns:
            Diccionario con estadisticas
        """
        try:
            records = self.get_all_records()
            
            if not records:
                return {
                    "total_records": 0,
                    "total_favorites": 0,
                    "success_rate": 0.0,
                    "most_used_provider": None,
                    "most_used_quality": None
                }
            
            # Contar
            total = len(records)
            favorites = len(self.get_favorites())
            successful = len([r for r in records if r.resolved_url and r.resolved_url != "LINK_NOT_RESOLVED"])
            
            # Estadisticas
            providers = {}
            qualities = {}
            
            for record in records:
                if record.provider:
                    providers[record.provider] = providers.get(record.provider, 0) + 1
                if record.quality:
                    qualities[record.quality] = qualities.get(record.quality, 0) + 1
            
            most_used_provider = max(providers.items(), key=lambda x: x[1])[0] if providers else None
            most_used_quality = max(qualities.items(), key=lambda x: x[1])[0] if qualities else None
            
            return {
                "total_records": total,
                "total_favorites": favorites,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "most_used_provider": most_used_provider,
                "most_used_quality": most_used_quality,
                "average_score": sum(r.score for r in records) / total if total > 0 else 0
            }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    def clear_history(self) -> bool:
        """
        Borra todo el historial (sin confirmar - usar con cuidado).
        
        Returns:
            True si se borro correctamente, False si hubo error
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM resolution_history")
                conn.commit()
                return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
