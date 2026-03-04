from typing import Dict, Any, List, Optional
import json
import os
from openai import OpenAI
from memory import StrictMemoryManager
from datetime import datetime
import re

config = StrictMemoryManager().get_config()
client = OpenAI(
    base_url=config["api_config"]["openai"]["base_url"],
    api_key=config["api_config"]["openai"]["api_key"],
)


class TherapistEvaluator:
    def __init__(self, memory_manager: StrictMemoryManager):
        self.memory_manager = memory_manager
        self._last_session_memory: Optional[Dict] = None  
        self._all_sessions_memory: Optional[List[Dict]] = None
        self._strategy_counter = {}  

    def _parse_gemini_response(self, response) -> Any:
        if hasattr(response, 'text'):
            text = response.text.strip()
            if text.startswith('{') and text.endswith('}'):
                return json.loads(text)
            return text
        elif hasattr(response, 'candidates') and response.candidates:
            return response.candidates[0].content.parts[0].text.strip()
        return None
 
    def _parse_openai_response(self, response) -> Any:
        if isinstance(response, str):
            if response.startswith('{') and response.endswith('}'):
                return json.loads(response)
            return response
            
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content.strip()
            if content.startswith('{') and content.endswith('}'):
                return json.loads(content)
            return content
        return None


    def _call_openai_api(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> Any:
        completion = client.chat.completions.create(
            model="Pro/deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "system", "content": "You are a professional psychological counselor."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return self._parse_openai_response(completion)
  
    def _get_session_strategy_memory(self, patient_id: str) -> str:
        if not patient_id:
            return "No strategy memory available"
    
        full_record = self.memory_manager.get_full_record(patient_id)
        current_session_num = len(full_record.get("sessions", {}))
    
        decision_file = f"eval_data/decision basis_{patient_id}.json"
        if not os.path.exists(decision_file):
            return "No strategy memory available"
    

        with open(decision_file, 'r', encoding='utf-8') as f:
            decision_data = json.load(f)
        
        session_key = f"session_{current_session_num}"
        if session_key not in decision_data:
            return "No strategy memory available"
            
        strategies = []
        for response_key, response_data in decision_data[session_key].items():
            if "Response Strategy" in response_data:
                strategies.append(response_data["Response Strategy"])
        
        if not strategies:
            return "No strategy memory available"
            
        return f"Strategies used in this session: {', '.join(strategies)}"


    def refresh_memory(self, patient_id: str):
        full_record = self.memory_manager.get_full_record(patient_id)
        sessions = full_record["sessions"]
        self._all_sessions_memory = list(sessions.values())
        self._last_session_memory = sessions[f"session_{len(sessions)}"] if sessions else {}
        
    def _get_last_session_memory(self, patient_id: str) -> Dict:
        full_record = self.memory_manager.get_full_record(patient_id)
        if not full_record["sessions"]:
            return {}
        last_session_num = len(full_record["sessions"])
        return full_record["sessions"][f"session_{last_session_num}"]

    def _get_all_sessions_memory(self, patient_id: str) -> List[Dict]:
        full_record = self.memory_manager.get_full_record(patient_id)
        return list(full_record["sessions"].values())

    def cross_session_evaluate(self, patient_id: str) -> Dict:
        self.refresh_memory(patient_id)  
    
        if not self._last_session_memory:  
            initial_therapy = self.select_initial_therapy(
                self.memory_manager.get_full_record(patient_id)["patient_record"]
            )
            self._save_therapy_reason(
                patient_id=patient_id,
                session_num=1,  
                reason="This is the first conversation, the initial therapy is selected based on the patient's medical record."
            )
            return {
                "new_therapy": initial_therapy,
                "reason": "This is the first conversation, the initial therapy is selected based on the patient's medical record."
            }
    
        evaluation = self.evaluate_therapy_progress(self._last_session_memory)
        next_session_num = len(self._all_sessions_memory) + 1
        self._save_therapy_reason(
            patient_id=patient_id,
            session_num=next_session_num,
            reason=evaluation.get("reason", "")
        )
        return {
            "new_therapy": evaluation.get("new_therapy", "cognitive-behavioral therapy"),
            "reason": evaluation.get("reason", "maintain the original therapy")
        }

    def _save_therapy_reason(self, patient_id: str, session_num: int, reason: str) -> bool:
        filename = f"decision basis_{patient_id}.json"
        filepath = os.path.join(self.memory_manager.eval_dir, filename)
    
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        
        session_key = f"session_{session_num}"
        if session_key not in data:
            data[session_key] = {}
        
        data[session_key]["reason for therapy"] = reason
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return True

    def evaluate_client_reaction(self, patient_input: str) -> bool:
        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
##Task:
Based on the patient input: {patient_input}, to determine whether the patient shows resistance or has significantly deviated from the consultation topic.
##Criteria:
Below are just some main criteria (other reasonable standards can also be referred to).
1.indicators that clearly reject the current topic:
  - directly reject the consultant's advice or questions
  - show obvious impatience
  - express a direct refusal or unwillingness to continue the conversation
2.indicators that significantly deviate from the consultation topic:
  - suddenly introducing a completely unrelated new topic
  - the response content has no logical connection with the current discussion issue
  - using expressions that obviously shift the topic 
##Constraints:
Directly output a Boolean value True or False.
"""
        

        response = self._call_openai_api(prompt, max_tokens=5, temperature=0.0)
        if isinstance(response, str):
            return response.lower() == "true"
        return False

    
    def assess_emotion(self, patient_input: str) -> Dict[str, Any]:
        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
Identify the primary emotion and assess its intensity in the patient's words.
##Criteria:
The patient words: {patient_input}.
1.	primary_emotion:
The primary emotion is the most intense one in the patient words. 
You can only choose one from the list: ["joy", "sadness", "anger", "fear", "disgust", "surprise", "trust","anticipation"].
2.	emotional_intensity:
The intensity of the emotion you identified above(a float number from 0 to 1, where 0 indicates no emotion and 1 indicates very intense emotion). Please retain one decimal place.
##Constraints:
Return your answer strictly in JSON format, like this:
{{
   "primary_emotion": "str",          
   "emotional_intensity": "float"     
}}
"""
    
        response = self._call_openai_api(prompt, max_tokens=50, temperature=0.3)
        cleaned_response = re.sub(r'^\s*```(json)?|```\s*$', '', response, flags=re.IGNORECASE).strip()
        return json.loads(cleaned_response)

    def update_response_strategy(self, 
                                emotion_data: Dict[str, Any], 
                                is_rejecting: bool,
                                patient_input: str,
                                patient_id: str = "") -> Dict[str, Any]:  

        session_strategy_memory = self._get_session_strategy_memory(patient_id)
        
        primary_emotion = emotion_data.get('primary_emotion', '未知')
        emotional_intensity = f"{emotion_data.get('emotional_intensity', 0.0):.1f}"
        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
Choose only one response strategy and provide the psychological counselor a response guidance.
##Requirements:
1. Choose a response strategy as "strategy".
*Reference Information:
  - patient's cuurent words: {patient_input}
  - patient's primary emotion: {primary_emotion}
  - patient's emotional intensity: {emotional_intensity}
  - whether the patient is rejecting or deviate from the topic: {"Yes" if is_rejecting else "No"}
*Rules:
  Determine the patient's current attitude first and then choose a suitable strategy based on the information above. The attitude you judged must be strictly positive or negative.
  * If patient attitude is "positive", then you can only strictly choose one suitable strategy from options A to D. 
  * If patient attitude is "negative", then you can only strictly choose one suitable strategy from options E to I.
  [Below are the options]: 
    A. Interpretation (The counselor conducts in-depth analysis and explanation of the patient's words and actions, helping the patient view problems from different perspectives.)
    B. Confrontation (The counselor directly points out the patient's unreasonable ideas, contradictory behaviors, or potential problems, prompting the patient to face reality.)
    C. Invite to Take New Perspectives (The counselor guides clients to view problems from different perspectives and broaden their thinking.)
    D. Invite to Explore New Actions (The counselor encourages the patient to try new behaviors or methods to solve problems and drive the patient to take positive actions.) 
    E. Restatement (The counselor repeats what the patient says to confirm their understanding and also makes the client feel cared for.)
    F. Reflection of Feelings (The counselor identifies and expresses patient's emotions, helping the patient better understand and accept his own feelings.)
    G. Self-disclosure (The counselor shares own similar experiences or feelings to establish resonance and trust with the patient.)
    H. Inquiring Subjective Information (The counselor asks the patient for subjective information such as thoughts, feelings, and expectations to gain a deeper understanding of the patient's inner world.)
    I. Inquiring Objective Information (The counselor inquires about specific facts, data, and other objective information to gain a more accurate understanding of the patient's situation.)
    G. Affirmation and Reassurance (The counselor provides affirmation and comforts to the patient's thoughts, feelings, or behaviors, enhancing the patient's confidence and sense of security.)
    H. Minimal Encouragement (The counselor encourages the patient to continue expressing thoughts and feelings, through simple language or body movements.)
    I. Answer (The counselor provides direct answers to the patient's questions and offers the information or advice the patient need.)
  [Notice]:
  Only return the strategy name of your selected option. For example, if you choose "A. Interpretation", then just return "Interpretation".
2.Based on your strategy, generate a concise corresponding response strategy text of no more than 30 words to precisely guide the psychological counselor's response as "strategy_text".
3.Make strategies more diverse, don't always stick to a single strategy.
  In this session, you have used the following strategies: {session_strategy_memory}. Please try different strategies as much as possible as long as they are reasonable. 
##Constraints:
Strictly output the substantive content of your choice, excluding any option identifiers (such as 'A.', 'B.', 'C.', etc.) and things in parentheses.
Return your answer strictly in JSON format, like this:
{{
   "strategy": “”,          
   "strategy_text": “” 
}}
""" 

        response = self._call_openai_api(prompt, max_tokens=100, temperature=0.5)
        cleaned_response = re.sub(r'^\s*```(json)?|```\s*$', '', response, flags=re.IGNORECASE).strip()
        
        return json.loads(cleaned_response)

    
    def evaluate_therapy_progress(self, last_session_memory: Dict) -> Dict[str, Any]:
        full_dialogs = last_session_memory.get("dialogs", [])
        last_therapy = last_session_memory.get("therapy", "")
        last_dialogs = '\n'.join(full_dialogs)

        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
Determine new therapy for the new session and provide short reason for your decision.
##Skills:
1. Determine “new_therapy”.
Evaluate whether the last conversation had a therapeutic effect based on the therapy used in the last session and the conversation record of the last session provided below. If there is no therapeutic effect, then change the last therapy. If there is therapeutic effect, then stick to the last therapy. You only need to output a standard therapy name as “new_therapy”.
It can be a single therapy or a reasonable combination therapy. Just use ' + ' to separate different therapy, but no more than two therapies.
Please directly output the professional terminology of the therapy name without explanation or additional text.
  - the therapy used in the last session: {last_therapy}
  - the conversation record of the last session: {last_dialogs}
2. Give some reason about your decision on “new_therapy”.
  - The reason should not exceed 50 words.
##Constraints:
Return your answer strictly in JSON format, like this:
{{
   "new_therapy": “”,         
   "reason": “” 
}}
"""

        response = self._call_openai_api(prompt, max_tokens=150, temperature=0.3)
        cleaned_response = re.sub(r'^\s*```(json)?|```\s*$', '', response, flags=re.IGNORECASE).strip()
        
        return json.loads(cleaned_response)

    def determine_treatment_stage(self, all_sessions_memory: List[Dict], current_therapy: str) -> Dict[str, Any]:
        all_dialogs = []
        for session in all_sessions_memory.values():
            all_dialogs.extend(session.get("dialogs", []))

        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
##Requirements:
Provide an analysis of the current stage of treatment. The content of your analysis includes summarizing the completed treatment content and pointing out how to continue treatment next time.
Your analysis should be comprehensive and concise in no more than 80 words.
You also should refer to the two relevant information below:
  - current therapy: {current_therapy}
  - all history dialogs: {all_dialogs}
##Constraints:
Integrate your analysis into a fluent paragraph, without giving it in segments or sections.
Directly output your analysis content. Do not provide any explanation.
"""

        response = self._call_openai_api(prompt, max_tokens=120, temperature=0.3)
        return response if response else "Cannot determine the current treatment stage"
    

    
    def select_initial_therapy(self, patient_record: Dict) -> str:
        medical_record = json.dumps(patient_record, ensure_ascii=False, indent=2)
        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
##Skills:
Please recommend a suitable psychological treatment therapy based on the patient medical record: {medical_record}.
It can be a single therapy or a reasonable combination therapy. Just use ' + ' to separate different therapy, but no more than two therapies.
##Constraints:
Please directly output the professional terminology of the therapy name without explanation or additional text.
"""

        response = self._call_openai_api(prompt, max_tokens=40, temperature=0.3)
        return response.rstrip('。.') if response else "cognitive-behavioral therapy"

    def should_use_memory(self, all_sessions_memory: Dict[str, Dict], patient_input: str) -> str:
        all_dialogs = []
        for session in all_sessions_memory.values():
            all_dialogs.extend(session.get("dialogs", []))
    
        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
##Requirements:
Please determine if it is necessary to refer to the historical conversations to respond to the patient's current words.
  - historical conversations: {all_dialogs}
  - patient's current words: {patient_input}
Only when you can find places in the historical conversations that are clearly related to the content of the patient's current words, and the places are not too far away from the current conversation, is it necessary to refer to history.
  * If reference is needed:
    Summarize relevant historical content in no more than 50 words. Just directly return a concise and accurate summary.
  * If no reference is needed:
    Directly return the sentence 'No need to consider historical conversation memory'.
##Constraints:
Directly output your answer in English. Do not include any other analysis or explanation.
"""
    
        response = self._call_openai_api(prompt, max_tokens=110, temperature=0.3)
        return response if response else "No need to consider historical conversation memory"
    

    def should_end_session(self, patient_input: str, dialog_count: int) -> bool:
        prompt = f"""
##Role:
You are a professional and empathetic psychological counselor. 
##Requirements:
Your task is to strictly judge whether the current session should be ended based on the patient's current words: {patient_input}.
Only when the patient expresses a clear intention to end (such as saying "goodbye", "that's all for today", "we'll talk next time", etc.), return True. Otherwise return False.
##Constraints:
Strictly output a Boolean value True or False.   
"""

        response = self._call_openai_api(prompt, max_tokens=5, temperature=0.0)
        return response.strip().lower() == "true"
