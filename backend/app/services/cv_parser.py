#cv parser service
from io import BytesIO

from docx import Document
from pypdf import PdfReader

# extract text from PDF file
def extract_pdf_text(file_bytes: bytes) -> str:
    pdf_file = BytesIO(file_bytes)

    reader = PdfReader(pdf_file)

    text_parts = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()


# extract text from DOCX file
def extract_docx_text(file_bytes: bytes) -> str:
    docx_file = BytesIO(file_bytes)

    document = Document(docx_file)

    text_parts = []

    # Extract normal paragraphs
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    # Extract text from tables as well
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text_parts.append(cell.text)

    return "\n".join(text_parts).strip()

# Extract text from CV file based on its type (PDF or DOCX)
def extract_cv_text(file_bytes: bytes, file_type: str) -> str:
    if file_type == "pdf":
        return extract_pdf_text(file_bytes)
    elif file_type == "docx":
        return extract_docx_text(file_bytes)
    else:
        raise ValueError("Unsupported file type. Only 'pdf' and 'docx' are supported.")