from langchain.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io
import logging
from langchain.schema import Document


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
    
    def extract_azure_intelligence(self):
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
        return text,"azure"
        
    def extract_with_ocr(self):
        images = convert_from_path(self.pdf_path,poppler_path=self.poppler_path)
        text = ""
        documents = []
        for i,image in enumerate(images):
            text += pytesseract.image_to_string(image)
            doc = Document(page_content=text, metadata={"page": i + 1, "source": self.pdf_path})
            documents.append(doc)
        return documents,"OCR"
    def extract_text(self):
        text,source = self.extract_with_langchain()
        if source=="pymupdf failed" or len(text.strip())<100:
            logging.info("Falling back to OCR")
            text,source = self.extract_with_ocr()
        return text,source

file_path = "sample_lease/FE LA - 250 Vista Blvd, Suite 101 Sparks, NV 89434 11.02.21.pdf"

loader = HybridPDFLoader(file_path)
text,source = loader.extract_text()
print(f"Langchain Extracted Text: {text}")
print(f"Source: {source}")

print("--------------------------------------------------------------------------------------------------")

file_path = "sample_lease/FE LA - 2720 Pellissier Pl, City of Industry, CA 91745 - 03.04.22 (1).pdf"
loader = HybridPDFLoader(file_path)
text,source = loader.extract_text()
print(1)
print(f"OCR Extracted Text: {text}")
print(f"Source: {source}")
print("--------------------------------------------------------------------------------------------------")


