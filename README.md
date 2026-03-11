<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=30&pause=1000&color=F7B731&center=true&vCenter=true&width=600&lines=🧠+AI+Quiz+Generator;Test+Your+Knowledge+with+AI;Powered+by+Google+Gemini" alt="Typing SVG" />

<br/>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Stars](https://img.shields.io/github/stars/Himanshu-279/ai-quiz-generator?style=for-the-badge&color=yellow)

<br/>

> **🚀 An intelligent quiz-generation app powered by Google Gemini AI — just enter a topic and get a quiz instantly!**

<br/>

[![Live Demo](https://img.shields.io/badge/🌐%20Live%20Demo-Visit%20App-orange?style=for-the-badge)](https://ai-ayx7.onrender.com/)

</div>

---

## 📌 Table of Contents

- [About](#-about)
- [Features](#-features)
- [Tech Stack](#️-tech-stack)
- [How It Works](#-how-it-works)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [Contact](#-contact)

---

## 🧠 About

**AI Quiz Generator** is a Python-based intelligent application that creates dynamic quizzes on **any topic you choose**, powered by **Google Gemini API**. Whether you're a student revising for exams or a curious learner exploring new subjects, this tool removes the effort of searching for practice questions — the AI does it all for you.

Just type in a topic → choose your settings → and let the AI challenge you! 🎯

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🤖 **AI-Powered Questions** | Generates unique MCQs every time using Google Gemini LLM |
| 🌍 **Any Topic** | Works for any subject — Python, History, Space, Biology, and more |
| 📊 **Instant Feedback** | Displays correct/incorrect status with AI-generated explanations |
| 🎚️ **Difficulty Levels** | Choose between Easy, Medium, or Hard questions |
| 📱 **Clean UI** | Built with Streamlit for a smooth, interactive experience |
| ⚡ **Fast & Free** | No pre-stored question banks — AI generates everything on the fly |

---

## 🛠️ Tech Stack

```
🐍 Language     →  Python 3.10+
🤖 AI Model     →  Google Gemini API (google-generativeai)
🎨 Framework    →  Streamlit
📦 Libraries    →  python-dotenv, google-generativeai
☁️ Deployment   →  Render
```

---

## 🔄 How It Works

```
   ┌─────────────────────────────────────────────────────────┐
   │                                                         │
   │   1. 📝 Enter Topic  →  e.g., "Machine Learning"        │
   │                                                         │
   │   2. ⚙️  Set Options  →  Number of Questions + Diff.    │
   │                                                         │
   │   3. 🤖 Gemini AI    →  Generates MCQs with answers     │
   │                                                         │
   │   4. ✅ Answer Quiz   →  Select your answers            │
   │                                                         │
   │   5. 🏆 Get Score    →  See results + explanations      │
   │                                                         │
   └─────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A [Google Gemini API Key](https://makersuite.google.com/app/apikey)

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Himanshu-279/ai-quiz-generator.git
cd ai-quiz-generator
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Set Up API Key

Create a `.env` file in the root directory:

```bash
GOOGLE_API_KEY="your_api_key_here"
```

> ⚠️ **Never share or commit your `.env` file.** It's already listed in `.gitignore`.

### 4️⃣ Run the App

```bash
# Using Streamlit (recommended)
streamlit run app.py

# OR using basic Python
python main.py
```

Open your browser and navigate to `http://localhost:8501` 🎉

---

## 📁 Project Structure

```
ai-quiz-generator/
│
├── app.py                  # Main Streamlit application
├── main.py                 # CLI version (optional)
├── requirements.txt        # Python dependencies
├── .env                    # API key (not committed)
├── .gitignore
└── README.md
```

---

## 🤝 Contributing

Contributions are always welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a new branch (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -m 'Add some feature'`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open** a Pull Request

Please make sure your code follows clean code practices and includes relevant comments.

---

## 📬 Contact

<div align="center">

**Himanshu Verma**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Himanshu%20Verma-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/himanshu-verma)
[![GitHub](https://img.shields.io/badge/GitHub-Himanshu--279-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Himanshu-279)

</div>

---

<div align="center">

⭐ **If you found this project helpful, consider giving it a star!** ⭐

Made with ❤️ and 🤖 by [Himanshu Verma](https://github.com/Himanshu-279)

</div>
