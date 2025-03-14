import io
import tempfile
import os
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image

def convert_pdf_to_image(pdf_file):
    """
    Convert the first page of a PDF file to an image
    Returns PIL Image object
    """
    try:
        # Create a temporary file to save the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            # Write the content of the uploaded file to the temp file
            temp_pdf.write(pdf_file.getvalue())
            temp_pdf_path = temp_pdf.name
        
        # Convert PDF to images
        pages = convert_from_path(temp_pdf_path, 300, first_page=1, last_page=1)
        
        # Clean up the temporary file
        os.unlink(temp_pdf_path)
        
        # Return the first page as PIL Image
        if pages:
            return pages[0]
        else:
            raise Exception("No pages found in PDF")
            
    except Exception as e:
        raise Exception(f"Error converting PDF to image: {str(e)}")

def is_pdf(file):
    """
    Check if a file is a PDF by looking at its content type or extension
    """
    if hasattr(file, 'name'):
        return file.name.lower().endswith('.pdf')
    return False

def prepare_document_image(uploaded_file):
    """
    Prepare document image for processing
    If PDF, convert to image
    Returns a BytesIO object containing the image
    """
    if is_pdf(uploaded_file):
        # Convert PDF to image
        image = convert_pdf_to_image(uploaded_file)
        
        # Convert PIL Image to BytesIO
        img_byte_array = io.BytesIO()
        image.save(img_byte_array, format='JPEG', quality=95)
        img_byte_array.seek(0)
        
        return img_byte_array
    else:
        # Return the file as is
        return uploaded_file