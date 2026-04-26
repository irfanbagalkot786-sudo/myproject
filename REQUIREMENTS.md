# Project Requirements & Technologies

This file lists the technologies, libraries, and software used in the **Smart Placement Portal** project.

## 🛠️ Software & Core Frameworks
- **Python**: The primary programming language used for the backend.
- **Django (v6.0.3)**: The web framework used to build the portal.
- **SQLite**: Default database used for development and data storage.

## 🤖 Artificial Intelligence (AI) & Proctoring
- **OpenAI GPT-4o-mini**: Used for resume analysis, intelligent recommendations, interview coaching, and question generation.
- **OpenAI Whisper**: Used for speech-to-text conversion in the virtual interview and communication skills modules.
- **TensorFlow.js (COCO-SSD)**: Used in the frontend for real-time object detection (e.g., detecting mobile phones, laptops) and multi-person detection during interviews.
- **Face-API.js**: Used for real-time face tracking, eye contact analysis, and confidence scoring.
- **Web Speech API**: Used for the "Vexa" AI Interviewer's text-to-speech functionality.

## 🔧 System Tools
- **FFmpeg**: Required as a dependency for **OpenAI Whisper** to process and convert audio/video files.

## 📚 Python Libraries
- **openai**: To interact with OpenAI's API.
- **openai-whisper**: For local speech-to-text processing.
- **PyMuPDF (fitz)**: Used to convert PDF resume pages into images for AI vision analysis.
- **PyPDF2**: Used for extracting text content from PDF files.
- **requests**: For making HTTP requests to external APIs.
- **django-simple-captcha**: Used for security and bot protection.
- **pathlib, json, os, re, subprocess**: Standard Python libraries for file handling and processing.

## 🎨 Frontend Technologies
- **HTML5 & CSS3**: Core structure and styling.
- **Vanilla JavaScript**: Used for AJAX requests, dynamic UI updates, and handling AI responses.
- **TensorFlow.js & Face-API.js**: Powering the browser-based AI proctoring and tracking.
- **Font Awesome**: Used for icons across the portal.
- **Google Fonts**: Used for modern typography (Inter, Roboto, etc.).

## 🔑 Environment & Configuration
- **env.html**: A custom file used to securely store the `OPENAI_API_KEY` (managed via the project root).
