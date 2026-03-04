import os
from openai import OpenAI
import json
from typing import Dict, Any, Optional
from memory import StrictMemoryManager
from initialization import TherapistInitializer
from evaluation import TherapistEvaluator
import time
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any, Optional
import random
import re

config = StrictMemoryManager().get_config()
client = OpenAI(
    base_url=config["api_config"]["openai"]["base_url"],
    api_key=config["api_config"]["openai"]["api_key"],
)


class PatientAgent:
    def __init__(self, medical_record: Dict, patient_id: str):
        self.medical_record = medical_record
        self.patient_id = patient_id
        self.session_guides = self._load_session_guides()
        self.current_session_num = 1
        self.dialogue_count = 0  
        self.memory_manager = StrictMemoryManager()
        self.last_attitude = None  

    def _get_all_historical_dialogs(self) -> List[str]:
        all_dialogs = []
        memory_manager = StrictMemoryManager()
        full_record = memory_manager.get_full_record(self.patient_id)
        
        sessions_data = {}
        for session_key, session_data in full_record.get("sessions", {}).items():
            sessions_data[session_key] = {
                "dialogs": session_data.get("dialogs", [])
            }
        
        return sessions_data if sessions_data else {"session_1": {"dialogs": []}}
    
    def _load_session_guides(self) -> Dict[int, str]:
        with open("new_data_translate.json", "r", encoding="utf-8") as f:
            all_data = json.load(f)
            patient_data = all_data.get(self.patient_id, {})
            if not patient_data:
                return {}
                
            session_guides = patient_data.get("Conversation guidance", {})
            processed_guides = {}
                
            for k, v in session_guides.items():
                if k.startswith("session_"):
                    session_num = int(k.split("_")[1])
                    guide_content = v.split(":", 1)[1].strip() if ":" in v else v.strip()
                    processed_guides[session_num] = guide_content                
            return processed_guides
                
    
    def update_session(self, session_num: int):
        self.current_session_num = session_num
        self.dialogue_count = 0 

    def generate_response(self, therapist_message):
        self.dialogue_count += 1
        session_guide = self.session_guides.get(self.current_session_num, "")
        historical_dialogs = self._get_all_historical_dialogs()
        client_information = self.medical_record
        session_number = self.current_session_num
        attitude = random.choices(["positive", "negative"], weights=[70, 30])[0]
        self.last_attitude = attitude  
        dialogue_count = self.dialogue_count

        prompt = f"""
You are a patient participating in psychological counseling. Please give a response.
  - This is your personal information: {client_information}
  - This is round_{dialogue_count} in your session_{session_number} with the counselor.
  - The conselor just said: {therapist_message}
  - Previous consultation conversation history record: {historical_dialogs}
##Requirements:
1.Your speech should revolve around the guidance for this session: {session_guide}.
2.You must finish this session within 4 to 5 rounds strictly. Now is round_{dialogue_count} in this session. 
  - Please pay attention to the round number and reasonably adjust dialogue rhythm and content each time. 
  - In your last round of speaking, you must proactively, naturally, and very clearly convey the meaning of ending the conversation.
3.Your response should clearly reflect your attitude: {attitude}. You can refer to the following ways to explicitly convey your current attitude.
  - Positive reactions: such as expressing emotions, introspection, exploration, insight, self acceptance, positive action, etc
  - Negative reactions: such as denial, external blame, withdrawal, confused expression, resistance etc
4.On the basis of responding to doctors, you should also pay attention to your own consultation needs. Try to make a balance between them.
5.Your expression should be in line with the patient's speaking style, as colloquial and natural as possible. Limit your speech to 1 to 2 sentences each time, and be faithful to your personal information when speaking.
##Constraints:
Generate your response in English. Your response should be no more than 60 words. 
Do not include any additional text, explanations, word count or formatting outside the JSON object. 
Strictly return a JSON object, like this:
{{
    "patient_response": "your response here"
}}
"""
        import time
        
        completion = client.chat.completions.create(
            model="Pro/deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "system", "content": "You are a patient receiving psychological counseling."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=300
        )

        raw_response = completion.choices[0].message.content
        cleaned_response = re.sub(r'^\s*```(json)?|```\s*$', '', raw_response, flags=re.IGNORECASE).strip()
        response = json.loads(cleaned_response)
        response["attitude"] = attitude  

        self._save_label_data(
            session_num=self.current_session_num,
            speak_num=self.dialogue_count,
            attitude=attitude
        )
            
        return {
            "text": response["patient_response"],  
            "attitude": attitude  
        }  
            
    def _save_label_data(self, session_num: int, speak_num: int, attitude: str):
        label_dir = "label_data"
        os.makedirs(label_dir, exist_ok=True)
        filename = f"label_{self.patient_id}.json"
        filepath = os.path.join(label_dir, filename)
        

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
              
        session_key = f"session_{session_num}"
        speak_key = f"speak_{speak_num}"
            
        if session_key not in data:
            data[session_key] = {}
        data[session_key][speak_key] = {"attitude": attitude}
            
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
                


class TherapistAgent:
    def __init__(self):
        self.memory_manager = StrictMemoryManager()  
        self.initializer = TherapistInitializer(self.memory_manager)
        self.evaluator = TherapistEvaluator(self.memory_manager)
        self.current_session_id = None
        self.current_patient_id = None
        self.dialog_count = 0  
        self.session_counter = 0
        self.current_therapy = "unspecified therapy"  

    def auto_conversation(self, patient_id: str, medical_record: Dict, patient_agent: PatientAgent, max_rounds: int = 20):
        session = self.start_new_session(patient_id)
        print(f"DOCTOR: {session['therapist_response']}")
        
        while True:  
            patient_response = patient_agent.generate_response(session['therapist_response'])
            print(f"PATIENT: {patient_response['text']}")
        
            session = self.process_patient_input(patient_response)
            print(f"DOCTOR: {session['therapist_response']}")
        
            if session['session_ended']:
                print("[SYSTEM] This conversation ended normally.")
                break
            
            if self.dialog_count >= max_rounds:  
                print("[SYSTEM] The maximum number of dialogue rounds is reached, the conversation will be forcibly ended.")
                self._end_current_session()
                break
            
            time.sleep(1)
        

    def _end_current_session(self):
        if not hasattr(self, 'current_session_id') or not self.current_session_id:
            return
            
        self.current_session_id = None
        self.dialog_count = 0

    def start_new_session(self, patient_id: str) -> Dict[str, Any]:
        self.current_patient_id = patient_id
        self.dialog_count = 0
        
        full_record = self.memory_manager.get_full_record(patient_id)
        if not full_record or not full_record.get("patient_record"):
            initializer = TherapistInitializer(self.memory_manager)
            medical_info = initializer._get_initial_record(patient_id)
            
            self.memory_manager.create_patient_record(patient_id, medical_info)
            full_record = self.memory_manager.get_full_record(patient_id)  
        
        evaluation_result = self.evaluator.cross_session_evaluate(patient_id)
        self.current_therapy = self._determine_therapy_for_new_session(patient_id)
        
        session_num = self.memory_manager.add_session(patient_id, self.current_therapy)
        self.current_session_id = f"{patient_id}_{session_num}"

        if session_num == 1:
            greeting = "Hello, I'm your psychological counselor. Nice to meet you. Today we can talk about your recent situation."
        else:
            last_session = self.memory_manager.get_session(patient_id, session_num-1)
            last_therapy = "unspecified therapy"
            if last_session is not None:
                last_therapy = last_session.get("therapy", "unspecified therapy")
            greeting = f"Hello! Nice to see you again. How are you feeling today?"
        
        self.evaluator._save_therapy_reason(
            patient_id=patient_id,
            session_num=session_num,
            reason=evaluation_result.get("reason", "")
        )

        return {
            'patient_id': patient_id,
            'session_id': self.current_session_id,
            'therapist_response': greeting,
            'current_therapy': self.current_therapy
        }
    
    def _determine_therapy_for_new_session(self, patient_id: str) -> str:
        full_record = self.memory_manager.get_full_record(patient_id)
        if not full_record.get("sessions"):
            return self.evaluator.select_initial_therapy(full_record["patient_record"])
        evaluation = self.evaluator.cross_session_evaluate(patient_id)
    
        return evaluation.get("new_therapy", "")
    
    def process_patient_input(self, patient_response: Dict) -> Dict[str, Any]:
        patient_text = patient_response["text"]
        patient_attitude = patient_response["attitude"]

        if not hasattr(self, 'current_session_id') or not self.current_session_id:
            return {
                "therapist_response": "There is no active session.",
                "session_ended": False,
                "current_therapy": "unspecified therapy",
                "strategy": {"strategy": "", "strategy_text": ""}
            }
            
        session_num = int(self.current_session_id.split("_")[-1])
        self.evaluator._current_session_num = session_num 
        self.dialog_count += 1

        self.memory_manager.add_dialog(
            self.current_patient_id,
            session_num,
            "patient",
            patient_text
        )

        should_end = self.evaluator.should_end_session(patient_text, self.dialog_count)
        is_rejecting = self.evaluator.evaluate_client_reaction(patient_text)
        emotion_result = self.evaluator.assess_emotion(patient_text)
        if not isinstance(emotion_result, dict):
            emotion_result = {}
        emotion_data = {
            "primary_emotion": emotion_result.get("primary_emotion", ""),
            "emotional_intensity": float(emotion_result.get("emotional_intensity", 0.0))
        }       
        
        full_record = self.memory_manager.get_full_record(self.current_patient_id)
        memory_result = self.evaluator.should_use_memory(
            all_sessions_memory=full_record.get("sessions", {}),
            patient_input=patient_text
        )
        
        current_stage = self.memory_manager.get_current_stage(self.current_patient_id)
    
        strategy_result = self.evaluator.update_response_strategy(
            emotion_data = emotion_data, 
            is_rejecting = is_rejecting,
            patient_input=patient_text,
            patient_id=self.current_patient_id
        )
        strategy = {
            "strategy": strategy_result.get("strategy", ""),
            "strategy_text": strategy_result.get("strategy_text", "")
        }

        response = self._generate_response(
            patient_input=patient_text,
            emotion_data=emotion_data,
            current_therapy=self.current_therapy
        )
        
        self.memory_manager.add_dialog(
            self.current_patient_id,
            session_num,
            "doctor",
            response
        )
        
        decision_data = {
            "Memory Invoke": memory_result,
            "Whether to Reject or Deviate": is_rejecting,
            "Current Therapy": self.current_therapy,
            "Current Stage": current_stage,
            "Primary Emotion": emotion_result.get("primary_emotion", ""),
            "Emotional Intensity": emotion_result.get("emotional_intensity", 0.0),
            "Response Strategy": strategy_result.get("strategy", ""),
            "Strategy Description": strategy_result.get("strategy_text", ""),
            "Attitude": patient_attitude
        }  
        self.memory_manager.save_decision_data(
            patient_id=self.current_patient_id,
            session_num=session_num,
            response_num=self.dialog_count,
            decision_data=decision_data
        )

        session_ended = should_end 
        if session_ended:
            self._end_current_session()
        
        return {
            "therapist_response": response,
            "session_ended": session_ended,
            "current_therapy": self.current_therapy,
            "strategy": strategy
        }
    
    def _get_current_therapy(self) -> str:
        if not hasattr(self, 'current_session_id') or not self.current_session_id:
            return "unspecified therapy"
        
        session_num = int(self.current_session_id.split("_")[-1])
        session = self.memory_manager.get_session(self.current_patient_id, session_num)
        return session.get("therapy", "unspecified therapy")
    

    def _generate_response(self, 
                     patient_input: str,   
                     emotion_data: Dict[str, Any],
                     current_therapy: str) -> str:
        config = self.memory_manager.get_config()
                
        session_memory = {}
        if self.current_session_id:
            try:
                session_num = int(self.current_session_id.split("_")[-1])
                full_record = self.memory_manager.get_full_record(self.current_patient_id)
                session_key = f"session_{session_num}"
                if session_key in full_record.get("sessions", {}):
                    session_memory = {
                        "dialogs": full_record["sessions"][session_key].get("dialogs", [])
                    }
            except Exception as e:
                session_memory = {"dialogs": []}

        current_stage = self.memory_manager.get_current_stage(self.current_patient_id)
        full_record = self.memory_manager.get_full_record(self.current_patient_id)
        memory_result = self.evaluator.should_use_memory(
            all_sessions_memory=full_record.get("sessions", {}),
            patient_input=patient_input
        )
        
        primary_emotion = emotion_data.get("primary_emotion", "unknown")
        emotional_intensity = emotion_data.get("emotional_intensity", 0.0)
        
        is_rejecting = self.evaluator.evaluate_client_reaction(patient_input)
        strategy_result = self.evaluator.update_response_strategy(
            emotion_data = emotion_data, 
            is_rejecting = is_rejecting,
            patient_input=patient_input,
            patient_id=self.current_patient_id
        )
        
        current_strategy = strategy_result.get('strategy', '')
        current_strategy_text = strategy_result.get('strategy_text', '')

        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
Your job is to respond to the patient compassionately and offer support in psychological counseling based on the following information and requirements.
##Requirements:
  1.Patient current words: {patient_input}.
  2.Historical memories you may need to be referred to: {memory_result}.
  3.The patient current primary emotion is {primary_emotion}, with an intensity of {emotional_intensity}.
  4.The therapy you should adopt is {current_therapy}. And please refer to analysis of the current treatment stage {current_stage}. 
  5.The response strategy you should adopt is {current_strategy} and the detailed guidance is {current_strategy_text}.
  6.Your expression should be in line with the psychological counselor's speaking style, as colloquial and natural as possible.
  7.Don't always directly repeat or quote what the patient has said. Just empathize the patient with as little words as possible. Ensure the smooth of the conversation.
  8.You must use diverse and different sentence patterns to reply each time to avoid a single reply mode. To avoid using the same sentence pattern, please refer to your previous replies from the conversation records for this session:{session_memory}.
  9.When the patient expresses a clear desire to end this conversation, please also provide a response to end the conversation in a declarative tone.
##Constraints:
Directly generate your response in English. Your response should be no more than 60 words. Do not provide any word count, analysis or explanation. 
"""

        try:
            completion = client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "system", "content": "You are a experienced and empathetic psychological counselor. "},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            raw_response = completion.choices[0].message.content
            clean_response = raw_response.replace('\\"', '"')
            clean_response = clean_response.strip('"')
        
            return clean_response
        except Exception as e:
            return "Sorry, I'm temporarily unable to process your request, please try again."
        

class AutoDialogueRunner:
    def __init__(self):
        self.agent = TherapistAgent()
        self.patient_records = self._load_all_patient_records()
    
    def _load_all_patient_records(self) -> Dict[str, Dict]:
        initializer = TherapistInitializer(StrictMemoryManager())
        all_records = initializer._load_client_record()
        return {
            pid: initializer._get_initial_record(pid)
            for pid in all_records.keys()
        }
    
    def run(self, num_sessions=6, max_rounds_per_session=8):
        print("\n" + "="*60)
        print("Psychological counseling conversation simulation system".center(40))
        print("="*60 + "\n")
        
        for patient_id, medical_record in self.patient_records.items():
            print(f"\n[SYSTEM] Start the consultation with {patient_id}.")
            
            patient_agent = PatientAgent(
                medical_record=medical_record,
                patient_id=patient_id
            )
            
            for session_num in range(1, num_sessions+1):
                print(f"\n[SYSTEM] Session {session_num} begins.")
                patient_agent.update_session(session_num)
                
                self.agent.auto_conversation(
                    patient_id=patient_id,
                    medical_record=medical_record,
                    patient_agent=patient_agent,  
                    max_rounds=max_rounds_per_session
                )
                print(f"[SYSTEM] Session {session_num} ends.")
                time.sleep(1)

if __name__ == "__main__":
    simulator = AutoDialogueRunner()
    simulator.run(num_sessions=6, max_rounds_per_session=8)