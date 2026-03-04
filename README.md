
<h1 align="center" style="font-size: 52px; font-weight: 600; font-family: 'Palatino Linotype', 'Book Antiqua', serif;">
💌 TheraMind : A Strategic and Adaptive Agent for Longitudinal Psychological Counseling
</h1>


## 🌸 About
This repository contains the official evaluation code and data for the paper "**TheraMind : A Strategic and Adaptive Agent for Longitudinal Psychological Counseling**". See more details in our [paper](https://arxiv.org/abs/2510.25758). If you find this project helpful, feel free to ⭐ it!

> TheraMind represents a definitive shift in AI mental health, moving beyond static models to a dynamic, longitudinal agent that emulates human cognitive processes. It features a novel dual-loop framework that manages both immediate turn-by-turn interactions and long-term strategic goals across multiple sessions. Unlike traditional single-therapy tools, TheraMind utilizes an adaptive selection mechanism to adjust its clinical approach based on real-time efficacy. By integrating patient state perception with phase-aware dialogue management, it transforms standard response generation into a deliberative clinical intervention.

## 📰 News
- **[2026-01-14]** Our paper [**TheraMind: A Strategic and Adaptive Agent for Longitudinal Psychological Counseling**](https://arxiv.org/abs/2510.25758). has been accepted by WWW2026 Web4Good Track!
- **[2025-11-02]** Paper submitted to arXiv:https://arxiv.org/abs/2510.25758.
## 📦 Dataset
**CPsyCounR** (Zhang et al., 2024a) serves as the experimental foundation for our study. This dataset consists of 3,134 anonymized and professionally rewritten Chinese psychological counseling reports, sourced from the platforms Yidianling (Yidianling, 2015) and Psy525 (Psy525, 2007). By adhering to a standardized structure—comprising case briefs, consultation processes, and therapist reflections—the dataset ensures a high degree of authenticity, privacy, and clinical reliability. Ultimately, it provides a robust basis for evaluating the long-term, nuanced capabilities of counseling agents within realistic contexts.


## 🧠 TheraMind
**TheraMind** is an agent specialized in **longitudinal psychological counseling** and **adaptive mental health dialogue generation**. Addressing the critical limitations of standard LLMs, it unifies **tactical dialogue management** and **long-term strategic planning** through a novel **dual-loop** architecture.

<p align="center">
  <img src="https://github.com/Emo-gml/PsyLLM/blob/main/openR1-psy.jpg" alt="OpenR1-Psy Dataset Overview" width="75%">
  <br>
  <em>Figure: Overview of the OpenR1-Psy dataset construction pipeline.</em>
</p>

## 🔥 Quick Start
#### Preparation
```python
# Prepare your api configure first
{"api_config": {
    "openai": {
      "base_url": "",
      "api_key": "",
      "model": "",
      "enabled": true}}
}

# Data process
python data_produce.py
python case_produce.py
```
#### Automatic Conversation Simulation Between Doctor and Patient
```python
from main import AutoDialogueRunner
runner = AutoDialogueRunner()
runner.run(num_sessions=6, max_rounds_per_session=8)
```
#### TherapistAgent Interface
```python
from main import TherapistAgent
therapist = TherapistAgent()
patient_id = "P001" 
session_info = therapist.start_new_session(patient_id)
patient_response = {"text": ""}
session_state = therapist.process_patient_input(patient_response)
print(session_state["therapist_response"])  
```
#### PatientAgent Interface
```python
from main import PatientAgent
from initialization import TherapistInitializer
from memory import StrictMemoryManager

patient_id = "P001"
memory_manager = StrictMemoryManager()
initializer = TherapistInitializer(memory_manager)
medical_record = initializer._get_initial_record(patient_id)
patient_agent = PatientAgent(
    medical_record=medical_record,
    patient_id=patient_id
)
patient_agent.update_session(session_num=1)
therapist_message = ""
patient_reply = patient_agent.generate_response(therapist_message)
print(patient_reply["text"])    
```

## 📜 Citation
```bibtex
@article{hu2025theramind,
  title={Theramind: A strategic and adaptive agent for longitudinal psychological counseling},
  author={Hu, He and Zhou, Yucheng and Ma, Chiyuan and Wang, Qianning and Zhang, Zheng and Ma, Fei and Cui, Laizhong and Tian, Qi},
  journal={arXiv preprint arXiv:2510.25758},
  year={2025}
}
```

## 🧩 License

For **research and educational use only.**

Please ensure compliance with **ethical and legal standards** in mental health AI research.

🔥Please contact huhe@gml.ac.cn
 if you encounter any issues.
