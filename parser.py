import pdfplumber
import docx
import os


def extract_text_from_pdf(file_path: str) -> str:
    """
    Opens a PDF and extracts text from every page.
    pdfplumber reads each page one by one.
    Some pages may be empty so we check before adding.
    """
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:               # skip empty pages
                text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    """
    Opens a DOCX (Word) file and reads each paragraph.
    Joins all paragraphs into one big string.
    """
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():      # skip blank paragraphs
            text += paragraph.text + "\n"
    return text.strip()


def extract_text(file_path: str) -> str:
    """
    Main function — detects file type by extension
    and calls the right extractor automatically.

    Supported: .pdf and .docx
    Raises ValueError for unsupported file types.
    """
    # Get file extension e.g. ".pdf" or ".docx"
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(
            f"Unsupported file type: '{ext}'. Only PDF and DOCX are allowed."
        )