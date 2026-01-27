"""
Экспорт данных в различные форматы
"""

import json
from pathlib import Path
from typing import Literal
import pandas as pd
from rich.console import Console

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from config.settings import ExportConfig, PROCESSED_DATA_DIR
from src.models.product import Product


console = Console()


class DataExporter:
    """Класс для экспорта данных в различные форматы"""
    
    def __init__(self, output_dir: Path = PROCESSED_DATA_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(
        self,
        products: list[Product],
        filename: str,
        format: Literal["json", "csv", "excel"] = "json"
    ) -> Path:
        """
        Экспортировать продукты в файл
        
        Args:
            products: Список продуктов
            filename: Имя файла (без расширения)
            format: Формат экспорта
            
        Returns:
            Путь к созданному файлу
        """
        if format == "json":
            return self._export_json(products, filename)
        elif format == "csv":
            return self._export_csv(products, filename)
        elif format == "excel":
            return self._export_excel(products, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, products: list[Product], filename: str) -> Path:
        """Экспорт в JSON"""
        output_path = self.output_dir / f"{filename}.json"
        
        data = [p.model_dump(mode="json") for p in products]
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=ExportConfig.JSON_INDENT)
        
        console.log(f"[green]Exported to JSON:[/green] {output_path}")
        return output_path
    
    def _export_csv(self, products: list[Product], filename: str) -> Path:
        """Экспорт в CSV"""
        output_path = self.output_dir / f"{filename}.csv"
        
        # Преобразуем в плоский формат
        data = [p.to_flat_dict() for p in products]
        df = pd.DataFrame(data)
        
        df.to_csv(
            output_path,
            index=False,
            sep=ExportConfig.CSV_DELIMITER,
            encoding="utf-8-sig"  # BOM для корректного отображения в Excel
        )
        
        console.log(f"[green]Exported to CSV:[/green] {output_path}")
        return output_path
    
    def _export_excel(self, products: list[Product], filename: str) -> Path:
        """Экспорт в Excel"""
        output_path = self.output_dir / f"{filename}.xlsx"
        
        # Плоские данные для основного листа
        flat_data = [p.to_flat_dict() for p in products]
        df_main = pd.DataFrame(flat_data)
        
        # Детальные данные форматов
        formats_data = []
        for p in products:
            for fmt in p.formats:
                formats_data.append({
                    "article": p.article,
                    "product_name": p.name,
                    "format_name": fmt.name,
                    "dimensions": fmt.dimensions,
                    "weight_kg": fmt.weight_kg,
                    "pieces_per_m2": fmt.pieces_per_m2,
                    "has_perforation": fmt.has_perforation,
                })
        df_formats = pd.DataFrame(formats_data)
        
        # Записываем в Excel с несколькими листами
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df_main.to_excel(writer, sheet_name="Products", index=False)
            if not df_formats.empty:
                df_formats.to_excel(writer, sheet_name="Formats", index=False)
        
        console.log(f"[green]Exported to Excel:[/green] {output_path}")
        return output_path
    
    def export_raw(self, data: dict, filename: str) -> Path:
        """
        Экспорт сырых данных в JSON
        
        Args:
            data: Данные для сохранения
            filename: Имя файла
            
        Returns:
            Путь к файлу
        """
        from config.settings import RAW_DATA_DIR
        output_path = RAW_DATA_DIR / f"{filename}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return output_path
