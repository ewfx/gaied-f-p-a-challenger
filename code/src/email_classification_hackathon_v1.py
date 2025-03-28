# -*- coding: utf-8 -*-
"""Email_Classification_Hackathon_V1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1GxsvIH0nohrcFvo1Y24LLIIsm5OhhXap

# Install Dependencies
"""

pip install PyMuPDF

pip install python-multipart

pip install fastapi uvicorn

pip install bs4 PyMuPDF pytesseract pdf2image

"""# Extract Email Content"""

file_path = "/content/SampleEmail2.eml"  # Provide your .eml file path

"""Combine Email & Attachment(".pdf",".txt",".png", ".jpg", ".jpeg ) Text  for Classification

Extracts Email Body (Plain & HTML)
Extracts Attachments & Reads Content
Extract Images (OCR via Tesseract), Text Files
"""

import os
import email
import base64
import fitz  # PyMuPDF
import pytesseract
from bs4 import BeautifulSoup
from pdf2image import convert_from_bytes
from email import policy
from email.parser import BytesParser

def extract_text_from_pdf(pdf_bytes):
    """Extract text from a PDF file."""
    pdf_text = ""
    pdf_document = fitz.open("pdf", pdf_bytes)
    for page in pdf_document:
        pdf_text += page.get_text("text")
    return pdf_text.strip()

def extract_text_from_image(image_bytes):
    """Extract text from an image using OCR."""
    images = convert_from_bytes(image_bytes)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text.strip()

def read_eml(file_path):
    with open(file_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    # Extract headers
    subject = msg["subject"]
    sender = msg["from"]
    recipient = msg["to"]

    # Extract body (text or HTML)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html":
                html = part.get_payload(decode=True).decode(errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                body = soup.get_text()
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    # Extract attachments and process them
    attachments = {}
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename()
            attachment_data = part.get_payload(decode=True)

            # Process attachment based on file type
            if filename.endswith(".pdf"):
                extracted_text = extract_text_from_pdf(attachment_data)
            elif filename.endswith((".png", ".jpg", ".jpeg")):
                extracted_text = extract_text_from_image(attachment_data)
            elif filename.endswith(".txt"):
                extracted_text = attachment_data.decode(errors="ignore")
            else:
                extracted_text = "[Unsupported File Type]"

            attachments[filename] = extracted_text

    return {
        "subject": subject,
        "sender": sender,
        "recipient": recipient,
        "body": body,
        "attachments": attachments
    }

# Example Usage
email_data = read_eml(file_path)

email_content = email_data["body"] + "\n".join(email_data["attachments"].values())
print("\nEmail Content:")
print(email_content)

"""Clean Email Content (Remove Greetings, Signatures, Footers)"""

import re

def clean_email_text(text):
    # Convert to lowercase
    text = text.lower()
    # Remove greetings
    text = re.sub(r"^(hi|hello|dear|hey)[, ]*", "", text, flags=re.MULTILINE)
    # Remove email signatures (common closing phrases)
    text = re.sub(r"(best regards|thanks|sincerely|kind regards|cheers)[,\n]?.*", "", text, flags=re.MULTILINE)
    # Remove confidentiality notices (common footer text)
    text = re.sub(r"this email is confidential.*", "", text, flags=re.MULTILINE)
    # Remove extra whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

final_email_content = clean_email_text(email_content)
print(email_content)

pip install transformers datasets torch pdfplumber pytesseract openai-whisper

def extract_details(text):
    details = {}

    # Extract bank name
    bank_match = re.search(r'current bank name:\s*(.*)', text, re.IGNORECASE)
    if bank_match:
        details['Bank Name'] = bank_match.group(1)

    # Extract account number
    account_match = re.search(r'account number:\s*(\d+)', text, re.IGNORECASE)
    if account_match:
        details['Account Number'] = account_match.group(1)

    # Extract account name
    account_name_match = re.search(r'account name:\s*(.*)', text, re.IGNORECASE)
    if account_name_match:
        details['Account Name'] = account_name_match.group(1)

    # Extract deal name
    deal_match = re.search(r'deal name:\s*(.*)', text, re.IGNORECASE)
    if deal_match:
        details['Deal Name'] = deal_match.group(1)

    # Extract the amount if the pattern is found
    amount = re.search(r'Amount:\s*₹([\d,]+\.\d{2})', text, re.IGNORECASE)
    if amount:
          details['amount'] = amount.group(1)

    return json.dumps(details, indent=4)

# Extract and print details
details = extract_details(email_content)
print(details)

"""# Classify Emails Using Hugging Face Model"""

from transformers import pipeline
import re

# Load Zero-Shot Classification Model
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Define Categories
request_types = ["Adjustment","Money Movement Inbound", "AU Transfer", "Closing Notice", "Commitment Change", "Fee Payment","loan transfer","money movement"]
request_sub_types = {
    "Adjustment": ["Adjustment"],
    "Money Movement Inbound": ["Money Movement Inbound"],
    "AU Transfer": ["AU Transfer"],
    "Closing Notice": ["Reallocation Fees", "Amendment Fees", "Reallocation Principal"],
    "Commitment Change": ["Cashless Roll", "Decrease", "Increase"],
    "Fee Payment": ["Ongoing Fee", "Letter of Credit Fee"],
    "loan transfer": ["loan transfer"],
    "money movement":["money movement"]
}

# Define Priority Rules
priority_map = {
    "Closing Notice": "High",
    "Commitment Change": "Medium",
    "Fee Payment": "Low"
}


# Email Classification Function
def classify_email(final_email):
    text = clean_email_text(final_email)
    # Step 1: Predict Request Type
    type_result = classifier(text, candidate_labels=request_types)
    request_type = type_result["labels"][0]
    request_type_confidence = type_result["scores"][0]

    # Step 2: Predict Request Sub-Type
    sub_type_result = classifier(text, candidate_labels=request_sub_types[request_type])
    request_sub_type = sub_type_result["labels"][0]
    request_sub_type_confidence = sub_type_result["scores"][0]

    # Step 3: Assign Priority
    priority = priority_map.get(request_sub_type, "Low")

    # Step 4: Extract Fields
    extracted_fields = extract_details(final_email)

    return {
        "request_type": request_type,
        "request_type_confidence": round(request_type_confidence * 100, 2),
        "request_sub_type": request_sub_type,
        "request_sub_type_confidence": round(request_sub_type_confidence * 100, 2),
        "priority": priority,
        "extracted_fields": extracted_fields
    }

import json

classification = classify_email(email_content)
#print(classification)
print(json.dumps(classification, indent=4))

