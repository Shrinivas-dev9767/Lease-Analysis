import PyPDF2
import openai
import re
import tiktoken

filepath = "sample_lease/FE LA - 250 Vista Blvd, Suite 101 Sparks, NV 89434 11.02.21.pdf"

document  = PyPDF2.PdfReader(filepath)

page = document.pages[0]
#print(len(document.pages))
#print(page.extract_text())
text = ""
for page in document.pages:
    text += page.extract_text()

print("------------------------------------------------------------------")
def num_token_from_string(text):
    encoding = tiktoken.encoding_for_model("gpt-4")
    num_tokens = len(encoding.encode(text))
    return num_tokens

def split_into_chunks(text):
    chunks = []
    text = text.split()
    current_chunk = ""
    current_chunk_token = 0
    for word in text:
        current_chunk += word + " "
        current_chunk_token +=1
        if current_chunk_token>=4096:
            chunks.append(current_chunk)
            current_chunk = ""
            current_chunk_token = 0
    if current_chunk:
        chunks.append(current_chunk)
    return chunks 

def clean_text(text):
    corpus = []
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(" +", " ", text)
    text = text.strip()
    corpus.append(text)
    return " ".join(corpus)

def response_gpt(previous_response,chunk):
    prompt = f"""You are an expert lease document analyzer. Your task is to extract the following fields from a lease text chunk and return them in JSON format

            fields to extract : {fields}

            and the current lease chunk is : {chunk}
            Rules:
                - If a field is confidently found in the current chunk, update it.
                - If a field is missing in the current chunk, reuse the value from the previous result below.
                - Do NOT overwrite previous values with nulls unless the current chunk explicitly negates the value (e.g., says "no fire sprinklers").
                - Dates given as durations (e.g., 62 months, 5 years) should be converted to an exact date using the Commencement Date as reference.
                - Your output must be a valid JSON object with all fields present, preserving previous values unless confidently updated.
                - If a field is not in previous result and it found in current chunk then add it to the JSON object.
            previous result : {previous_response}
            Return only the final merged JSON dictionary. Do not include any explanation.
            """
    client = openai.OpenAI(api_key="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")
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts information from a lease agreement and return result in JSON format"},
            {"role": "user", "content": prompt}
            ],
    temperature=0.1
    )
    return response.choices[0].message.content
print("--------------------------------------------------------------------------------")
fields = ["Address", "City", "State", "Zip", "County", "Effective Date"
    "Occupancy Date", "Commencement Date", "Lease Expiration Date",
    "Sqft","Lease Owned","Tenant","Sub Tenant","Internal Companies",
    "Lot Size (AC)","Year Built","Zoning","Construction Type","Building Type",
    "Truck Court","Number of Grade Level Docks","Number of Loading Docks",
    "Fire Sprinklers","Fire Alarm System","Clearance Height","Stories",
    "Power","Power Supply","Energy Star","Gas","Sewer","Water","Heating",
    "Lighting / Lights","Rent/SF/YR"]


def semantic_chunks(previous_response,chunk,category_list):
    prompt = f"""
    You are an expert lease document analyzer. Your task is to extract all relevant text from a lease text chunk that pertains to the given category.
    Categories are as follows : {category_list}

    Lease Text Chunk:
    \"\"\"
    {chunk}
    \"\"\"

    Rules:
        - Extract only the paragraphs or sentences that contain or relate to the categories listed above.
        - Do NOT return unrelated text or general clauses.
        - If no relevant information is found in the chunk, return an empty string for that category.
        - The output must be a valid JSON object with the category as the key and extracted text as the value.
        - If the same category has previous text collected, merge both texts (append new content without duplicating).
        - Preserve the original wording and formatting as much as possible.

    Previous result:
    {previous_response}

    Return only the final merged JSON dictionary. Do not include any explanation.
    """

    client = openai.OpenAI(api_key="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")
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts information from a lease agreement and return result in JSON format"},
            {"role": "user", "content": prompt}
            ],
        temperature=0.1
    )
    return response.choices[0].message.content
text = clean_text(text)
print(text)

categories = {
    'Property Information':["address", "zip", "sqft", "zoning", "lot size", "year built", "building type","construction type"],
    "Lease Terms": ["effective date", "lease term", "commencement", "expiration", "rent", "renewal"],
    "Utilities": ["water", "sewer", "gas", "electric", "meter", "submetered"],
    "Contacts": ["property manager", "contact name", "phone", "email", "broker", "tenant", "landlord"],
    "Fire and Security": ["fire alarm", "sprinkler", "security system", "account", "provided by landlord"],
    "Structural": ["clearance height", "truck court", "grade level", "loading docks", "stories", "column spacing"],
    "Services": ["pest control", "landscape", "trash", "hvac", "heating", "lights"]
}
categories_list = list(categories.keys())
chunks = split_into_chunks(text)
print(chunks)
all_responses = []
for idx,chunk in enumerate(chunks):
    if idx == 0:
        response = semantic_chunks(None,chunk,categories_list)
    else:
        response = semantic_chunks(all_responses[-1],chunk,categories_list)
    all_responses.append(response)

print(all_responses[-1])