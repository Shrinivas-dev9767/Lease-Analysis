from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain.vectorstores import Qdrant
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyMuPDFLoader
from langchain.schema import Document
from langchain_qdrant import QdrantVectorStore
from uuid import uuid4
import re
import openai

collection_name = "Test1"

def clean_text(text):
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^A-Za-z0-9,.?!\s]', '', text)
    return text

client  = QdrantClient(
    host = "192.168.12.150",
    port = 6333,
)

if not client.collection_exists(collection_name):
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

file_path = "sample_lease/FE MLA - 850 Northlake Dr, Coppell, TX 75019 06.30.17 (4).pdf"
loader = PyMuPDFLoader(file_path)
text = loader.load()
print(text)
splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=100)
chunks = splitter.split_documents(text)
print(chunks[0])
print(type(chunks))
embeddings = OpenAIEmbeddings(openai_api_key="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")
vectorstore = QdrantVectorStore(
    client = client,
    collection_name = collection_name,
    embedding = embeddings,
)
'''texts = [doc.page_content for doc in chunks]
metadatas = [doc.metadata for doc in chunks]'''
ids = [str(uuid4()) for _ in chunks]
vectorstore.add_documents(documents=chunks,ids=ids)
retriever = vectorstore.as_retriever(search_type="mmr",search_kwargs={"k":3})

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
    query = f"Please collect relevant information related to :{','.join(keywords)} include dates in date format if present and address in address format if present"
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
        model="gpt-4.1",
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
for category,json_obj in category_results.items():
    print(f"Category: {category}")
    print(json_obj)
    print("---------------------------------------")