import pytesseract
import pdf2image
from pdf2image import convert_from_path
import openai

file_path = "sample_lease/FE LA - 2680-2690 Pellissier Pl, City of Industry, CA 90601 - 02.12.24 (1).pdf"
poppler_path = r"C:\Users\spatil\AppData\Local\Programs\poppler-24.08.0\Library\bin"
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Users\spatil\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
)
images = convert_from_path(file_path,poppler_path=poppler_path)

text = ""

for i,image in enumerate(images):
    text += pytesseract.image_to_string(image) + "\n"

print(text)
fields = ["Address", "City", "State", "Zip", "County", "Effective Date"
    "Occupancy Date", "Commencement Date", "Lease Expiration Date",
    "Sqft","Lease Owned","Tenant","Sub Tenant","Internal Companies",
    "Lot Size (AC)","Year Built","Zoning","Construction Type","Building Type",
    "Truck Court","Number of Grade Level Docks","Number of Loading Docks"]
prompt = f"""You are an expert lease document analyzer. Your task is to extract the following fields from a lease text chunk and return them in JSON format

fields to extract : {fields}
Rules:
    - If a field is confidently found in the current chunk, update it.
    - If a field is missing in the current chunk, reuse the value from the previous result below.
    - Do NOT overwrite previous values with nulls unless the current chunk explicitly negates the value (e.g., says "no fire sprinklers").
    - Dates given as durations (e.g., 62 months, 5 years) should be converted to an exact date using the Commencement Date as reference.
    - Your output must be a valid JSON object with all fields present, preserving previous values unless confidently updated.

and the lease text is : {text} 
Return only the final merged JSON dictionary. Do not include any explanation.
"""
client = openai.OpenAI(api_key="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")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that extracts information from a lease agreement."},
        {"role": "user", "content": prompt}
        ],
    temperature=0.1
)

print(response.choices[0].message.content)
