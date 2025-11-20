import os
import json
from dotenv import load_dotenv
from groq import Groq
from flask import Flask, render_template, request, jsonify
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ----------------------------
# Load Environment Variables
# ----------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file.")

# ----------------------------
# Load Product Data
# ----------------------------
PRODUCT_JSON_PATH = "product_files/product_catalog.json"
if not os.path.exists(PRODUCT_JSON_PATH):
    raise FileNotFoundError(f"{PRODUCT_JSON_PATH} not found.")

with open(PRODUCT_JSON_PATH, "r", encoding="utf-8") as f:
    try:
        products = json.load(f).get("products", [])
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in {PRODUCT_JSON_PATH}")

if not products:
    raise ValueError("No products found in JSON file.")

# ----------------------------
# Flatten Product Data for Vector Search
# ----------------------------
docs = []
for p in products:
    name = p.get("service", "Unnamed Product")
    description = p.get("description", "No description available.")
    docs.append(f"{name}: {description}")

    # Flatten typesOfCampaigns
    types_of_campaigns = p.get("typesOfCampaigns")
    if isinstance(types_of_campaigns, dict):
        for campaign_type, campaign_info in types_of_campaigns.items():
            docs.append(f"{campaign_type}: {campaign_info.get('description', '')} - Ideal For: {campaign_info.get('idealFor','')}")

    # Flatten benefits
    benefits = p.get("benefits")
    if isinstance(benefits, dict):
        for key, value in benefits.items():
            docs.append(f"{key}: {value}")

    # Flatten whyChooseUs
    why_choose_us = p.get("whyChooseUs")
    if isinstance(why_choose_us, dict):
        for key, value in why_choose_us.items():
            docs.append(f"{key}: {value}")

    # Flatten FAQs
    faqs = p.get("faqs")
    if isinstance(faqs, list):
        for faq in faqs:
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            if question and answer:
                docs.append(f"Q: {question} A: {answer}")

    # Flatten contact info
    contact = p.get("contact")
    if isinstance(contact, dict):
        for key in ["phone", "email", "title", "subtitle", "description", "tagline", "about"]:
            if key in contact:
                docs.append(f"Contact {key.capitalize()}: {contact[key]}")
        offices = contact.get("offices")
        if isinstance(offices, dict):
            for country, addr in offices.items():
                docs.append(f"Office in {country.capitalize()}: {addr}")

# ----------------------------
# Create Embeddings + VectorStore
# ----------------------------
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_texts(docs, embeddings)
retriever = vectorstore.as_retriever()

# ----------------------------
# Initialize Groq Client
# ----------------------------
client = Groq(api_key=GROQ_API_KEY)

# ----------------------------
# Flask App
# ----------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_query = request.json.get("query", "").strip()
    if not user_query:
        return jsonify({"answer": "Please type a question."})

    lower_query = user_query.lower().strip()

    # ----------------------------
    # Casual conversation responses (smart)
    # ----------------------------
    casual_responses = {
        "hi": "Hello! 👋 How can I assist you today?",
        "hello": "Hi there! 😊 What can I help you with?",
        "hey": "Hey! How can I assist you?",
        "how are you": "I'm doing great! Thanks for asking 😊 How can I help you today?",
        "i'm fine": "Great to hear that! ❤️ How can I assist further?",
        "thank you": "You're welcome! 😊",
        "thanks": "Happy to help! 🙌",
        "bye": "Goodbye! 👋 Have a great day!",
        "ok": "Okay! Let me know if you need help.",
        "lead done": "Perfect! Your lead is marked as done. 🟢",
    }

    greetings = ["hi", "hello", "hey"]
    # Detect simple greeting only if short query
    if any(lower_query.startswith(g) and len(lower_query.split()) <= 3 for g in greetings):
        for g in greetings:
            if lower_query.startswith(g):
                return jsonify({"answer": casual_responses[g]})
    # Direct exact match for other casual phrases
    for key, resp in casual_responses.items():
        if lower_query == key:
            return jsonify({"answer": resp})

    # ----------------------------
    # Retrieve relevant context from product docs
    # ----------------------------
    context_docs = vectorstore.similarity_search(user_query, k=5)
    context = "\n".join([doc.page_content for doc in context_docs])

    # ----------------------------
    # Prepare prompt for Groq AI
    # ----------------------------
    prompt = f"""
You are a helpful AI assistant. You must ONLY answer using the provided product data.

Context:
{context}

User Question: {user_query}

Instructions:
- Answer in 4–5 complete sentences.
- Provide examples if relevant.
- Write in a friendly, professional tone.
- If the question is outside this context, reply: "I only provide information about the listed products and services."

Answer:
"""

    # ----------------------------
    # Call Groq API
    # ----------------------------
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Error retrieving response: {e}"

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)
