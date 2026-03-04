from typing import Dict, Any
from pathlib import Path
import json
from datetime import datetime

class TherapistInitializer:
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        config_path = Path(__file__).parent / "api_config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def _load_client_record(self, patient_id: str = None) -> Dict:
        record_path = Path(__file__).parent / "client_records_translate.json"
        with open(record_path, 'r', encoding='utf-8') as f:
            all_records = json.load(f)
            if patient_id:
                return all_records.get(patient_id, {})
            return all_records

    def _get_initial_record(self, patient_id: str = None) -> Dict:
        client_record = self._load_client_record(patient_id) if patient_id else self._load_client_record()
    
        if not client_record:
            return {}
        medical_info = client_record.get("medical information", {}) if isinstance(client_record, dict) else client_record
        return {
            "patient pseudonym": medical_info.get("patient pseudonym", ""),
            "patient age": medical_info.get("patient age", ""),
            "mental health history": medical_info.get("mental health history", ""),
            "physical health history": medical_info.get("physical health history", ""),
            "current problems and symptoms": medical_info.get("current problems and symptoms", "")
        }