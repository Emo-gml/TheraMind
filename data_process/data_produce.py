import json
import os
from openai import OpenAI
from typing import List, Dict, Any
from memory import StrictMemoryManager

config = StrictMemoryManager().get_config()
client = OpenAI(
    base_url=config["api_config"]["openai"]["base_url"],
    api_key=config["api_config"]["openai"]["api_key"],
)

class DataProducer:
    def __init__(self):      
        self.raw_data_path = "raw_data_translate.json"
        self.new_data_path = "new_data_translate.json"
        self.client = client
        
    def load_raw_data(self) -> List[Dict[str, Dict[str, Any]]]:
        with open(self.raw_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("The original data format error: it should be a list")
            return data

    
    def generate_consultation_stages(self, case_data: Dict[str, Any]) -> Dict[str, str]:

        prompt = f"""
##Task:
Generate guidance content for four counseling sessions based on the following case information. 
The guidance content you generated will be used to guide the simulated patient's performance in the corresponding counseling session. 
Must generate from the patient's perspective(assume now you are the patient), so that it can better guide the simulated patient to communicate with the counselor.
【case information】:
-case title:{case_data.get("case title")}
-case category:{case_data.get("case category")}
-case description:{case_data.get("case description")}
-consultation process:{case_data.get("consultation process")}
##Requirement:
1.Allocate consultation content for each session based on the "consultation process". And make your allocation in line with the laws of common consulting development.
2.Session guidance content should be detailed, concise and concentrated, no more than 40 words for each one. You should capture and reserve key information according to 【case information】.
3.You can appropriately exert your reasonable imagination to make a supplement. 
##Constraints:
You must use English to answer.
Your final output should be a JSON object contains four keys: session_1, session_2, session_3, session_4. And for each key, its value is the corresponding session guidance content.
Strictly output a JSON object. Do not provide any explanation.
"""


        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a psychological counseling case generation system based on the patient's perspective."},
                {"role": "user", "content": prompt}
            ],
            timeout=30,  
            temperature=0.7,
            max_tokens=1200,
            response_format={"type": "json_object"}
        )
            
        if response.choices:
            content = response.choices[0].message.content
            if content.strip():
                return json.loads(content)
            raise ValueError("Received empty response")
        raise ValueError("Received invalid response")

    
    def process_all_cases(self) -> Dict[str, Dict[str, Any]]:
        cases = self.load_raw_data()
        if not cases:
            print("Error: the case data loaded is empty or the format is incorrect")
            return {}
    
        results = {}
        for case_dict in cases:
            if not isinstance(case_dict, dict):
                continue
                
            for patient_id, patient_data in case_dict.items():
                print(f"Processing the case of {patient_id}...")
                
                if not isinstance(patient_data, dict):
                    print(f"Warning: the data format of {patient_id} is incorrect")
                    continue
                    
                session_guides = self.generate_consultation_stages(patient_data)
                results[patient_id] = {"Conversation guidance": session_guides}
    
        return results

    def save_results(self, results: Dict[str, Dict[str, Any]]):
        with open(self.new_data_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved to {self.new_data_path}")


    def run(self):
        results = self.process_all_cases()
        if results:
            self.save_results(results)
            return results
        return {}

if __name__ == "__main__":
    producer = DataProducer()
    all_results = producer.run()