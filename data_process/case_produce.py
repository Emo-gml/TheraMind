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

class ClientRecordsGenerator:
    def __init__(self):
        self.raw_data_path = "raw_data_translate.json"
        self.output_path = "client_records_translate.json"  
    
    def load_raw_data(self) -> Dict[str, Dict[str, Any]]:
        with open(self.raw_data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            if not isinstance(raw_data, list):
                raise ValueError("The original data format error: it should be a list")
            return raw_data

    def generate_single_record(self, patient_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
##Task:
Generate standard patient medical records based on the following raw case information.
[raw case information]:
  - case title: {case_data.get('case title')}
  - case category: {case_data.get('case category')}
  - case summary: {case_data.get('case summary')}
##Requirement:
1、Return a JSON object containing the following keys(the value for each key should be no more than 100 words):
   - "patient pseudonym" (a common English name)
   - "patient age" (make a reasonable guess based on the case information)
   - "mental health history" 
   - "physical health history" 
   - "current problems and symptoms" 
2、You can make reasonable supplements to the missing information, but do not include disease diagnoses that are not in the raw case information.
3、Maintain a professional medical record style.
4、Extract all important case information. The medical record you generate should be detailed and comprehensive.
##Constraint:
You must use English to answer.
Output the JSON object strictly without any explanatory text.
"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional medical record generation system."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
            
        if response.choices and response.choices[0].message.content:
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content[7:-3].strip()
            return json.loads(content)
        return {}

    def generate_all_records(self) -> Dict[str, Dict[str, Any]]:
        raw_cases = self.load_raw_data()
        if not raw_cases:
            return {}
        
        records = {}
        for patient_id, patient_data in raw_cases.items():
            print(f"Generating the medical record of {patient_id}...")
            record = self.generate_single_record(patient_id, patient_data)
            if record:
                records[patient_id] = {"medical information": record}
            else:
                print(f"Warning: the medical record of {patient_id} generation failed, the default information will be used")
                records[patient_id] = {
                    **patient_data,
                    "medical information": {
                        "patient pseudonym": patient_id,
                        "patient age": 40 if "elderly" in patient_data.get("case title","") else 30,
                        "mental health history": "see case content",
                        "physical health history": "see case content",
                        "current problems and symptoms": "see case content"
                    }
                }
        return records

    def save_records(self, records: Dict[str, Dict[str, Any]]):
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved to {self.output_path}")

    def process(self):
        records = self.generate_all_records()
        if records:
            self.save_records(records)
            return records
        return {}

if __name__ == "__main__":
    generator = ClientRecordsGenerator()
    generated_records = generator.process()