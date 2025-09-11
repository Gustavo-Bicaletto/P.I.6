import pandas as pd
import re
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import TreebankWordTokenizer
import nltk
from datetime import datetime
from pymongo import MongoClient

# Configura NLTK e stopwords
nltk.data.path.append(r"C:\Users\gusta\AppData\Roaming\nltk_data")
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

tokenizer = TreebankWordTokenizer()

# Limpa o texto de HTML, Markdown, caracteres desnecessários e stopwords
def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r'\*\*|\*|-', '', text)
    text = re.sub(r'[^A-Za-z0-9\s.,]', '', text)
    text = text.lower()
    tokens = tokenizer.tokenize(text)
    tokens = [word for word in tokens if word not in stop_words]
    return " ".join(tokens)

# Extrai emails e telefones do texto
def extract_contacts(text):
    emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
    phones = re.findall(r'\+?\d[\d\s-]{7,}\d', text)
    return emails, phones

# Extrai skills de T.I. presentes no texto
def extract_skills(text, skill_list):
    text_lower = text.lower()
    skills_found = [skill for skill in skill_list if skill.lower() in text_lower]
    return list(set(skills_found))

ti_skills = ["Python", "C++", "Java", "SQL", "Linux", "Windows",
             "AWS", "Docker", "Kubernetes", "HTML", "CSS", "JavaScript"]

# Conexão com MongoDB Atlas
client = MongoClient("mongodb+srv://pi6time5:remanejamento123@resumai.hlueghe.mongodb.net/")
db = client['resumAI']
collection = db['dados_processados']

# Carrega CSV de vagas/currículos
df = pd.read_csv(r"C:\P.I.6\datasets\India_tech_jobs - India_tech_jobs.xls.csv", dtype=str)

# Processa e insere cada documento no MongoDB
for _, row in df.iterrows():
    description_text = row.get('description', '')
    cleaned_description = clean_text(description_text)
    emails, phones = extract_contacts(description_text)
    skills_found = extract_skills(description_text, ti_skills)

    try:
        min_amount = float(row.get("min_amount", 0))
    except:
        min_amount = None
    try:
        max_amount = float(row.get("max_amount", 0))
    except:
        max_amount = None

    date_posted = row.get("date_posted")
    try:
        date_posted = datetime.strptime(date_posted, "%Y-%m-%d")
    except:
        date_posted = None

    doc = {
        "id": row.get("id"),
        "title": row.get("title"),
        "company": row.get("company"),
        "location": row.get("location"),
        "date_posted": date_posted,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "currency": row.get("currency"),
        "is_remote": row.get("is_remote"),
        "description_clean": cleaned_description,
        "skills": skills_found,
        "contact_email": emails,
        "contact_phone": phones
    }

    collection.insert_one(doc)

print("Todos os documentos processados foram inseridos no MongoDB com sucesso!")
