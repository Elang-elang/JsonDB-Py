import json
import os
from typing import Dict, Any
from .exceptions import StorageError

class StorageHandler:
    """Handles reading from and writing to the JSON file."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensures the directory and an empty JSON file exist."""
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)  # exist_ok=True untuk menghindari race condition
            except OSError as e:
                raise StorageError(f"Failed to create directory: {directory}") from e

        # Gunakan try-except untuk menghindari race condition
        try:
            with open(self.file_path, 'x', encoding='utf-8') as file:
                json.dump({}, file, ensure_ascii=False, indent=2)
        except FileExistsError:
            # File sudah ada, tidak perlu dibuat
            pass
        except IOError as e:
            raise StorageError(f"Failed to create file: {self.file_path}") from e

    def read_data(self) -> Dict[str, Any]:
        """Reads and parses the entire JSON file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except FileNotFoundError:
            # Jika file tidak ada, buat file baru dan return empty dict
            self._ensure_file_exists()
            return {}
        except json.JSONDecodeError as e:
            raise StorageError(
                f"Failed to decode JSON from {self.file_path}. "
                f"The file might be corrupted: {str(e)}"
            ) from e
        except IOError as e:
            raise StorageError(f"Failed to read file: {self.file_path}") from e

    def write_data(self, data: Dict[str, Any]) -> None:
        """Writes data to the JSON file with indentation and atomic operation."""
        temp_file = self.file_path + '.tmp'
        
        try:
            # Tulis ke file temporary dulu untuk atomic operation
            with open(temp_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            
            # Kemudian rename file temporary ke file asli
            if os.name == 'nt':  # Windows
                # Di Windows, perlu hapus file lama dulu
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
            os.rename(temp_file, self.file_path)
            
        except IOError as e:
            # Cleanup temporary file jika ada error
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass  # Ignore cleanup errors
            raise StorageError(f"Failed to write to file: {self.file_path}") from e
