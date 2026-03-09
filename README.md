
<h1 align="center" style="font-size: 52px; font-weight: 600; font-family: 'Palatino Linotype', 'Book Antiqua', serif;">
💌 TheraMind : A Strategic and Adaptive Agent for Longitudinal Psychological Counseling (WWW 2026)
</h1>


## 🌸 About
This repository contains the official evaluation code and data for the paper "**TheraMind : A Strategic and Adaptive Agent for Longitudinal Psychological Counseling**". See more details in our [paper](https://arxiv.org/abs/2510.25758). If you find this project helpful, feel free to ⭐ it!

> TheraMind represents a definitive shift in AI mental health, moving beyond static models to a dynamic, longitudinal agent that emulates human cognitive processes. It features a novel dual-loop framework that manages both immediate turn-by-turn interactions and long-term strategic goals across multiple sessions. Unlike traditional single-therapy tools, TheraMind utilizes an adaptive selection mechanism to adjust its clinical approach based on real-time efficacy. By integrating patient state perception with phase-aware dialogue management, it transforms standard response generation into a deliberative clinical intervention.

## 📰 News
- **[2026-01-14]** Our paper [**TheraMind**](https://arxiv.org/abs/2510.25758) has been accepted by WWW2026 !
- **[2025-11-02]** Paper submitted to arXiv:https://arxiv.org/abs/2510.25758.
## 📦 Dataset
Patient-Medical-Record dataset provides a comprehensive medical profile for Patient Agent to create a more realistic patient. It contains key information including patient pseudonym, age, mental health history, physical health history, current problems and symptoms, and its corresponding types of mental illness. We apply large language models to automatically extract and integrate key information from the original dataset to get the Patient-Medical-Record dataset. [TheraMind-Patient-Guidance](https://huggingface.co/datasets/GMLHUHE/TheraMind_Patient_Guidance) dataset provides a session-level guidance for Patient Agent to achieve better performance during the multi-session conversation. We use large language models to automatically summarize the treatment process from the origianl dataset and allocate reasonably to get sessinon-level abstracts. By adhering to a standardized structure, our synthesized datasets ensure a high degree of authenticity, privacy, and clinical reliability. Ultimately, it provides a robust basis for evaluating the long-term, nuanced capabilities of counseling agents within realistic contexts.

The original psychological dataset used in our synthesized datasets are derived from a publicly available research dataset [CPsyCounR](https://huggingface.co/datasets/CAS-SIAT-XinHai/CPsyCounR) which consists of 3,134 anonymized and professionally rewritten Chinese psychological counseling reports. All datasets are used strictly for research purposes in accordance with their original licenses and usage guidelines.

## 🧠 What is TheraMind ？
**TheraMind** is an agent specialized in **longitudinal psychological counseling** and **adaptive mental health dialogue generation**. Addressing the critical limitations of standard LLMs, it unifies **tactical dialogue management** and **long-term strategic planning** through a novel **dual-loop** architecture.

<p align="center">
  <img src="https://github.com/Emo-gml/TheraMind/blob/main/figues/pipeline-agent.jpg" alt="Agent Pipline Overview" width="75%">
  <br>
  <em></em>
</p>

### 📈 Superior Performance
Our TheraMind achieves better performance across all ten distinct categories of psychological issues in both single-session (left) and multi-
session (right) contexts.
<p align="center">
  <img src="https://github.com/Emo-gml/TheraMind/blob/main/figues/combined_radar_chart.jpg" alt="radar overview" width="60%">
  <br>
  <em></em>
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

# Produce patient medical records
python case_produce.py

# Generate session guidance
python data_produce.py
```
#### Automatic Conversation Simulation Between Doctor and Patient
```python
from main import AutoDialogueRunner
runner = AutoDialogueRunner()
runner.run(num_sessions=6, max_rounds_per_session=8)

# or you can directly run
python agent/main.py
```
#### TherapistAgent Create
```python
from main import TherapistAgent
therapist = TherapistAgent()
```
#### PatientAgent Create
```python
from main import PatientAgent
patient_agent = PatientAgent() 
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

🔥Please contact huhe@gml.ac.cn or chiyuanma@link.cuhk.edu.cn
 if you encounter any issues.
