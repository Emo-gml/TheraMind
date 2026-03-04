import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests


class StrictMemoryManager:
    def __init__(self):
        self.data_dir = "save_data"
        self.eval_dir = "eval_data"
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.eval_dir, exist_ok=True)
        self._config = self._load_config()
        self._evaluator = None  

    def get_evaluator(self):
        if self._evaluator is None:
            from evaluation import TherapistEvaluator
            self._evaluator = TherapistEvaluator(self)
        return self._evaluator
   
    def _load_config(self) -> Dict:
        config_path = Path(__file__).parent / "api_config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
           
            
    def get_config(self) -> Dict:
        if not hasattr(self, '_config') or self._config is None:
            self._config = self._load_config()
        return self._config or {}
    
    def get_current_stage(self, patient_id: str) -> str:
        record = self.get_full_record(patient_id)
        sessions = record.get("sessions", {})

        if not sessions:
            return "initial assessment phase: first session started"

        current_therapy = self.get_current_therapy(patient_id)

        evaluator = self.get_evaluator()
        stage_assessment = evaluator.determine_treatment_stage(
            all_sessions_memory=sessions,
            current_therapy=current_therapy
        )

        return stage_assessment 
        
    def get_current_therapy(self, patient_id: str) -> str:
        record = self.get_full_record(patient_id)
        sessions = record.get("sessions", {})
        if not sessions:
            return "unspecified therapy"  
    
        current_session_num = len(sessions)
        current_session = sessions.get(f"session_{current_session_num}", {})
        return current_session.get("therapy", "")  

    def create_patient_record(self, patient_id: str , medical_info: Dict) -> Dict:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")
        data = {
            "patient_record": {
            "patient pseudonym": medical_info.get("patient pseudonym", ""),
            "patient age": medical_info.get("patient age", ""),
            "mental health history": medical_info.get("mental health history", ""),
            "physical health history": medical_info.get("physical health history", ""),
            "current problems and symptoms": medical_info.get("current problems and symptoms", "")
            },  
            "sessions": {}  
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def add_session(self, patient_id: str, therapy: str) -> int:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")
        with open(filepath, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            session_num = len(data.get("sessions", {})) + 1
            session_key = f"session_{session_num}"
            
            if session_key not in data["sessions"]:
                data["sessions"][session_key] = {
                    "therapy": therapy,
                    "dialogs": []
                }
                
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
                return session_num
            raise ValueError(f"会话{session_num}已存在")
            
    def add_dialog(self, patient_id: str, session_num: int, role: str, content: str) -> bool:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")
        with open(filepath, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            session_key = f"session_{session_num}"
            
            if session_key in data["sessions"]:
                formatted_content = f"{'PATIENT' if role == 'patient' else 'DOCTOR'}: {content}"
                data["sessions"][session_key]["dialogs"].append(formatted_content)
            
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            return False

    def get_session(self, patient_id: str, session_num: int) -> Optional[Dict]:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                session_data = data.get(f"session_{session_num}", {})
                return {
                    'therapy': session_data.get('therapy', ''),
                    'dialogs': session_data.get('dialogs', [])
                }
        except FileNotFoundError:
            return None
    
    def load_session(self, session_id: str) -> Dict:
        patient_id = session_id.split("_")[0]
        session_num = int(session_id.split("_")[1])
        full_record = self.get_full_record(patient_id)
        return full_record.get(f"session_{session_num}", {})

    def get_full_record(self, patient_id: str) -> Dict:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "sessions" not in data:
                data["sessions"] = {}
            if "patient_record" not in data:
                data["patient_record"] = {}
            return data


    def update_session_info(self, patient_id: str, session_num: int, info: Dict) -> bool:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")

        with open(filepath, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            session_key = f"session_{session_num}"
            if session_key in data:
                data[session_key]["session_info"].update(info)
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
                return True
            return False


    def add_dialog_to_session(self, patient_id: str, session_num: int, speaker: str, content: str) -> bool:
        filepath = os.path.join(self.data_dir, f"{patient_id}.json")

        with open(filepath, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            session_key = f"session_{session_num}"
            if session_key in data:
                data[session_key]["dialog_records"].append({
                    speaker: content
                })
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
                return True
            return False

    
    def save_decision_data(self, patient_id: str, session_num: int, 
                         response_num: int, decision_data: Dict) -> bool:
        filename = f"decision basis_{patient_id}.json"
        filepath = os.path.join(self.eval_dir, filename)
        

        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}
            
        session_key = f"session_{session_num}"
        response_key = f"response_{response_num}"
            
        if session_key not in existing_data:
            existing_data[session_key] = {}
          
        existing_data[session_key][response_key] = decision_data
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
        return True
