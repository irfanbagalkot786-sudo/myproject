from django.test import TestCase

# Create your tests here.
import whisper

model = whisper.load_model("base")
result = model.transcribe("C:\Users\Hp\OneDrive\Desktop\dummy proj\audio.mp3")

print(result["text"])
