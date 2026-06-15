"""CSV Exporter — saves report data to CSV files."""
import csv
import os

class CsvExporter:
    @staticmethod
    def export(data: list[dict], filepath: str) -> bool:
        """Export a list of dictionaries to a CSV file."""
        if not data:
            return False
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Extract headers from first dictionary
            headers = list(data[0].keys())
            
            # Write with utf-8-sig to ensure Excel opens it with proper encoding for accents
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
                
            return True
        except Exception as e:
            print(f"Erreur d'export CSV: {e}")
            return False
