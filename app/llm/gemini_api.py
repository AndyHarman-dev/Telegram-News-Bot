import textwrap
import google.generativeai as genai
#from IPython.display import Markdown


def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


GOOGLE_API_KEY = 'AIzaSyC_sSxPRaAfcy2fVrihZLYsOxqhdeivNo0'
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content("What is the meaning of life?")
to_markdown(response.text)