from langchain.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import faiss
import re
import openai
import json
import logging 
import pytesseract
from pdf2image import convert_from_path

class HybridPDFLoader:
    def __init__(self,file_path):
        self.pdf_path = file_path
        self.azure_ocr_endpoint = "https://cubeworkocr1.cognitiveservices.azure.com/"
        self.azure_ocr_key = "3bYVtPVAFr1LqTcFiejmzfnD6eRntnnR4DL1liyhnc24ndEeckBbJQQJ99BEACYeBjFXJ3w3AAALACOGsDJN"
        self.poppler_path = r"C:\Users\spatil\AppData\Local\Programs\poppler-24.08.0\Library\bin"
        pytesseract.pytesseract.tesseract_cmd = r"C:\Users\spatil\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

    def extract_with_langchain(self):
        try:
            loader = PyMuPDFLoader(self.pdf_path)
            documents = loader.load()
            text = "".join([doc.page_content for doc in documents])
            if len(text.strip())<100:
                raise ValueError("Text is too short")
            return text,"pymupdf"
        except Exception as e:
            logging.warning(f"Error extracting with Langchain: {e}")
            return "None","pymupdf failed"
    
    '''def extract_azure_intelligence(self):
        loader = AzureAIDocumentIntelligenceLoader(
            file_path=file_path,
            api_key=self.azure_ocr_key,
            api_endpoint=self.azure_ocr_endpoint,
            api_model = "prebuilt-layout"
        )
        documents = loader.load()
        text = "".join([doc.page_content for doc in documents])
        if len(text.strip())<100:
            raise ValueError("Text is too short")
        return text,"azure"'''
        
    def extract_with_ocr(self):
        images = convert_from_path(self.pdf_path,poppler_path=self.poppler_path)
        text = ""
        documents = []
        for i,image in enumerate(images):
            text += pytesseract.image_to_string(image) + " "
            doc = Document(page_content=text,metadata={"source":f"page_{i+1}"})
            documents.append(doc)
        return documents,"OCR"
    def extract_text(self):
        text,source = self.extract_with_langchain()
        if source=="pymupdf failed" or len(text.strip())<100:
            logging.info("Falling back to OCR")
            text,source = self.extract_with_ocr()
        return text,source


file_path = "sample_lease/FE LA - 2720 Pellissier Pl, City of Industry, CA 91745 - 03.04.22 (1).pdf"
loader = HybridPDFLoader(file_path)
text,source = loader.extract_text()

def clean_text(text):
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^A-Za-z0-9,.?!\s]', '', text)
    return text
print("----------------------------------------")
print(text)
print("----------------------------------------")
#text = "".join(text)
#text = clean_text(text)
#print(clean_text(text))
splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=100)
chunks = splitter.split_documents(text)

embeddings = OpenAIEmbeddings(openai_api_key="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")
'''embeddings_dim = len(embeddings.embed_query(text))
index = faiss.IndexFlatL2(embeddings_dim)
vector_store = FAISS(embedding_function = embeddings, index=index,docstore=InMemoryDocstore(),index_to_docstore_id={})'''
#print(data)
#vector_store = FAISS.from_embeddings(chunks,embeddings)
vector_store = FAISS.from_documents(chunks,embeddings)
retriever = vector_store.as_retriever()

categories = {
    "Property Information": [
        "Address", "City", "State", "Zip", "County", "Sqft", "Lease Owned",
        "Lot Size (AC)", "Year Built", "Zoning", "Construction Type", "Building Type",
        "Building Size", "Warehouse Area", "Office Area", "Width / Depth", "Column Spacing"
    ],

    "Lease Terms": [
        "Effective Date", "Occupancy Date / Early Access", "Closing Commencement Date",
        "Lease Expiration Date", "Rent/SF/YR"
    ],

    "Tenant Information": [
        "Tenant Name", "Sub Tenant Name", "Internal Companies"
    ],

    "Landlord Contacts": [
        "Landlord (Master) Company", "Landlord (Master) Contact Name", "Landlord (Master) Phone",
        "Landlord (Master) Email", "Landlord's (Master) Property Manager Company",
        "Landlord's (Master) Property Manager Contact Name", "Landlord's (Master) Property Manager Phone",
        "Landlord's (Master) Property Manager Email"
    ],

    "Tenant Contacts": [
        "Tenant's (Subtenant's) Property Manager Company", "Tenant's (Subtenant's) Property Manager Name",
        "Tenant's (Subtenant's) Property Manager Phone", "Tenant's (Subtenant's) Property Manager Email"
    ],

    "Broker Information": [
        "Sublandlord's Broker Company", "Sublandlord's Broker Contact Name",
        "Sublandlord's Broker Phone", "Sublandlord's Broker Email"
    ],

   "Fire and Security": ["fire alarm", "sprinkler", "security system", "account", "provided by landlord"],

    "Utilities": ["water", "sewer", "gas", "electric", "meter", "submetered"],
}

category_chunks = {}

for category,keywords in categories.items():
    query = f"Please collect information related to :{','.join(keywords)} include dates in date format if present and address in address format if present"
    docs = retriever.get_relevant_documents(query,k=10)
    text = "\n".join(doc.page_content for doc in docs)
    text = clean_text(text)
    category_chunks[category] = text

for category,text in category_chunks.items():
    print(f"Category: {category}")
    print(text)
    print("----------------------------------------")


def response_gpt(category,chunk,fields):
    prompt = f"""
    You are an expert lease document analyzer. Your task is to extract the following fields from a lease text chunk and return them in JSON format

    fields to extract : {', '.join(fields)}

    and the current lease chunk is : {chunk}
    Rules:
    - Dates given as durations (e.g., 62 months, 5 years) should be converted to an exact date using the Commencement Date as reference.
    - Your output must be a valid JSON object with all fields present, preserving previous values unless confidently updated.
    - Your output must be a valid JSON object with all fields present, preserving previous values unless confidently updated.
    - Only contain important information related to the fields.
    - Avoid using general clauses and only use information related to the fields.
    Return only JSON Dicitonary with above fields and their values. Do not include any explanation.
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

category_results = {}

for category,text in category_chunks.items():
    fields = categories.get(category,[])
    if fields:
        response = response_gpt(category,text,fields)
        category_results[category] = response
print("---------------------------------------")
#print(category_results)

'''for category,json_obj in category_results.items():
    print(f"Category: {category}")
    print(json_obj)
    print("---------------------------------------")'''

def merge_json_objects(json_objects):
    merged_dict = {}
    for obj in json_objects.values():
        try:
            parsed = json.loads(obj)
            for key,value in parsed.items():
                if key not in merged_dict:
                    merged_dict[key] = value
        except Exception as e:
            print(f"Error parsing JSON: {e}")
    return merged_dict

final_merged_dict = merge_json_objects(category_results)
print("---------------------------------------")
print(final_merged_dict)

                        
