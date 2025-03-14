import streamlit as st
import os
import io
import json
import tempfile
import base64
from PIL import Image
import openai
import requests
from urllib.parse import quote
import time
from pdf_handler import prepare_document_image, is_pdf

# Set page configuration
st.set_page_config(
    page_title="Smart Document Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set dark mode theme
st.markdown("""
<style>
    .reportview-container {
        background-color: #1E1E1E;
        color: #ffffff;
    }
    .sidebar .sidebar-content {
        background-color: #252526;
        color: #ffffff;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff;
    }
    .stButton>button {
        background-color: #0078D7;
        color: white;
    }
    .stTextInput>div>div>input {
        color: #d6dadf;
    }
    .stSelectbox>div>div>div {
        color: #d6dadf;
    }
</style>
""", unsafe_allow_html=True)

# st.set_page_config(page_title="Document OCR with Address Validation", layout="wide")

def encode_image(image_data):
    """
    Encode the image file to base64 for OpenAI API
    """
    try:
        # Open the image using PIL
        if isinstance(image_data, (io.BytesIO, io.BufferedReader)):
            img = Image.open(image_data)
        else:
            img = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Save as JPEG
        img_byte_array = io.BytesIO()
        img.save(img_byte_array, format='JPEG', quality=95)
        binary_data = img_byte_array.getvalue()
        
        # Encode as base64
        base64_string = base64.b64encode(binary_data).decode('utf-8')
        
        return base64_string
    except Exception as e:
        st.error(f"Error encoding image: {str(e)}")
        raise

def process_document(document_file, api_key, model_name="gpt-4-vision-preview"):
    """
    Process the uploaded document using OpenAI's GPT-4 Vision API
    """
    try:
        # Configure OpenAI API key
        openai.api_key = api_key

        # Read the image data
        image_data = document_file.read()
        document_file.seek(0)  # Reset file pointer
        
        # Encode the image
        base64_image = encode_image(image_data)
        
        prompt = """Analyze this document and provide information in JSON format.
1. First determine if this is a bank statement (look for elements like transactions, balances, bank name)
2. Extract the following whether it's a bank statement or other document:
   - Person's full name
   - Complete address
   - Document date or period
3. Return the data in this exact JSON format:
{
    "is_bank_statement": true/false,
    "name": "[full name]",
    "address": "[complete address]",
    "document_date": "[statement date/period]"
}

If you cannot extract certain information, use empty strings for those fields.
Respond ONLY with the JSON, no other text."""
        
        # Prepare the API request
        with st.spinner("Analyzing document with GPT-4 Vision..."):
            response = openai.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024,
                temperature=0
            )
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            # Strip any markdown formatting that might be present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text.replace("```json", "", 1)
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            extracted_info = json.loads(cleaned_text)
        except json.JSONDecodeError:
            st.error("Could not parse GPT's response as JSON")
            st.code(response_text, language="json")
            extracted_info = {
                'is_bank_statement': False,
                'name': '',
                'address': '',
                'document_date': '',
                'error': 'Failed to parse response'
            }
        
        # Ensure all required fields are present
        required_fields = ['is_bank_statement', 'name', 'address', 'document_date']
        for field in required_fields:
            if field not in extracted_info:
                extracted_info[field] = ''
                
        return extracted_info
        
    except Exception as e:
        st.error(f"Error in process_document: {str(e)}")
        return {
            'is_bank_statement': False,
            'name': '',
            'address': '',
            'document_date': '',
            'error': str(e)
        }

def geocode_address(address, api_key):
    """
    Geocode an address using Geoapify API
    Returns the API response or None if error
    """
    try:
        # URL encode the address
        encoded_address = quote(address)
        
        # Make request to Geoapify
        geoapify_api_url = "https://api.geoapify.com/v1/geocode/search"
        response = requests.get(
            f"{geoapify_api_url}?text={encoded_address}&apiKey={api_key}"
        )
        
        # Check response status
        if response.status_code != 200:
            st.error(f"Geoapify API error: {response.text}")
            return None
            
        # Return the full API response
        return response.json()
        
    except Exception as e:
        st.error(f"Error geocoding address: {str(e)}")
        return None

def validate_address(address, api_key):
    """
    Validate an address using Geoapify API
    Returns a dict with validation results including confidence metrics
    """
    try:
        # Get geocoding results for the address
        with st.spinner("Validating address..."):
            result = geocode_address(address, api_key)
        
        # Initialize response structure
        validation_result = {
            'is_valid': False,
            'confidence': 0.0,
            'details': result,
            'error': None
        }
        
        # If geocoding failed
        if not result:
            validation_result['error'] = 'Could not geocode address'
            return validation_result
            
        # Get the best match (first result) if available
        match = (result.get('features', []) or [{}])[0]
        
        # Get confidence details from the best match
        confidence_details = match.get('properties', {}).get('rank', {})
        
        # Calculate overall confidence
        if confidence_details:
            # Get the confidence score
            confidence_score = confidence_details.get('confidence', 0)
            validation_result['confidence'] = confidence_score
            
            # Consider valid if the match has high confidence
            validation_result['is_valid'] = confidence_score >= 0.8
            
            # Add the confidence details to the response
            validation_result['confidence_details'] = confidence_details
            
            # Add formatted address
            validation_result['formatted_address'] = match.get('properties', {}).get('formatted')
        
        return validation_result
        
    except Exception as e:
        st.error(f"Error validating address: {str(e)}")
        return {
            'is_valid': False,
            'confidence': 0.0,
            'error': str(e),
            'details': None
        }

def main():
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #d6dadf;
        font-weight: 600;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        color: #333333;
    }
    .info-card {
        background-color: #f1f8ff;
        border-left: 5px solid #1E88E5;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #333333;
    }
    .success-card {
        background-color: #edfaef;
        border-left: 5px solid #4CAF50;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #333333;
    }
    .warning-card {
        background-color: #fff8e1;
        border-left: 5px solid #FFC107;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #333333;
    }
    .error-card {
        background-color: #ffebee;
        border-left: 5px solid #F44336;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #333333;
    }
    .highlight {
        font-weight: 600;
        color: #1E88E5;
    }
    .confidence-bar-bg {
        width: 100%;
        height: 20px;
        background-color: #f0f0f0;
        border-radius: 10px;
        margin-top: 10px;
    }
    .confidence-bar {
        height: 20px;
        background-color: #4CAF50;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
    }
    .field-label {
        font-weight: 600;
        color: #333333;
        margin-bottom: 5px;
    }
    .field-value {
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 5px;
        margin-bottom: 15px;
        color: #333333;
    }
    .sidebar-content {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin-top: 20px;
        color: #333333;
    }
    .footer {
        text-align: center;
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #eee;
        color: #888;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("<h1 class='main-header'>📄 Smart Document Analyzer</h1>", unsafe_allow_html=True)
    
    # Description
    st.markdown("""
    <div class="info-card" style="color:#333333;">
    This intelligent application extracts key information from documents using AI vision technology
    and validates addresses with geolocation services. Perfect for streamlining data entry and verifying document details.
    </div>
    """, unsafe_allow_html=True)

    # Sidebar configuration with better styling
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/document.png", width=80)
        st.markdown("<h2 style='text-align: center; color: white;'>Configuration</h2>", unsafe_allow_html=True)
        
        # API Configuration section
        # st.markdown("<div class='sidebar-content' style='color:#333333;'>", unsafe_allow_html=True)
        st.subheader("🔑 API Keys")
        openai_api_key = st.text_input("OpenAI API Key", type="password", help="Required for document analysis")
        geoapify_api_key = st.text_input("Geoapify API Key", type="password", help="Required for address validation")
        
        # Model selection with visuals
        st.subheader("🤖 AI Model")
        model_options = {
            "GPT-4 Vision": "gpt-4-vision-preview",
            "GPT-4o": "gpt-4o"
        }
        selected_model = st.selectbox("Select OpenAI Model", list(model_options.keys()))
        model_name = model_options[selected_model]
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Documentation section
        with st.expander("ℹ️ How it works"):
            st.write("""
            1. Upload a document image or PDF
            2. AI extracts key information
            3. Address is validated through geocoding
            4. Results display with confidence ratings
            """)
        
        # Credits
        st.markdown("<div class='footer'>Created by Peter Mamdouh</div>", unsafe_allow_html=True)

    # Main content area
    # st.markdown("<div class='card' style='color:#333333;'>", unsafe_allow_html=True)
    # File uploader with clear instructions
    st.markdown("<h3 class='sub-header' style='color:#d6dadf;'>📎 Upload Document</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#d6dadf;'>Upload a document containing personal information such as name, address, and date. Supported formats: JPG, PNG, PDF</p>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "pdf"])
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Process the document if we have all we need
    if uploaded_file and openai_api_key and geoapify_api_key:
        # Create a three-column layout for better organization
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # st.markdown("<div class='card' style='color:#333333;'>", unsafe_allow_html=True)
            st.markdown("<h3 class='sub-header' style='color:#d6dadf;'>📄 Document Preview</h3>", unsafe_allow_html=True)
            
            # Handle PDF display differently
            if is_pdf(uploaded_file):
                st.markdown(f"<div class='info-card' style='color:#d6dadf;'><b>PDF File:</b> {uploaded_file.name}</div>", unsafe_allow_html=True)
                st.info("The first page of this PDF will be processed")
            else:
                st.image(uploaded_file, use_column_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Show a spinner during processing
        with st.spinner("Processing document..."):
            # Prepare document for processing (convert PDF to image if needed)
            processed_file = prepare_document_image(uploaded_file)
            
            # Add artificial delay for better UX
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            
            # Process document with OpenAI
            extracted_info = process_document(processed_file, openai_api_key, model_name)
        
        # Clear the progress bar after processing
        progress_bar.empty()
        
        with col2:
            st.markdown("<div class='card' style='color:#d6dadf;'>", unsafe_allow_html=True)
            st.markdown("<h3 class='sub-header' style='color:#d6dadf;'>🔍 Extracted Information</h3>", unsafe_allow_html=True)
            
            # Show document type icon based on detection
            doc_type = "Bank Statement" if extracted_info.get('is_bank_statement') else "Document"
            doc_icon = "💳" if extracted_info.get('is_bank_statement') else "📃"
            st.markdown(f"<div class='info-card' style='color:#333333;'><b>{doc_icon} Document Type:</b> {doc_type}</div>", unsafe_allow_html=True)
            
            # Display extracted information in a clear, styled format
            if extracted_info.get('name'):
                st.markdown("<div class='field-label' style='color:#d6dadf;'>👤 Full Name</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='field-value' style='color:#333333;'>{extracted_info['name']}</div>", unsafe_allow_html=True)
            
            if extracted_info.get('document_date'):
                st.markdown("<div class='field-label' style='color:#d6dadf;'>📅 Document Date</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='field-value' style='color:#333333;'>{extracted_info['document_date']}</div>", unsafe_allow_html=True)
            
            if extracted_info.get('address'):
                st.markdown("<div class='field-label' style='color:#d6dadf;'>🏠 Address</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='field-value' style='color:#333333;'>{extracted_info['address']}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Address validation section with improved visualization
        if extracted_info.get('address'):
            # st.markdown("<div class='card' style='color:#d6dadf;'>", unsafe_allow_html=True)
            st.markdown("<h3 class='sub-header' style='color:#d6dadf;'>🌎 Address Validation</h3>", unsafe_allow_html=True)
            
            # Perform address validation
            validation_result = validate_address(extracted_info['address'], geoapify_api_key)
            
            if validation_result['is_valid']:
                st.markdown("<div class='success-card' style='color:#d6dadf;'>✅ Address validated successfully!</div>", unsafe_allow_html=True)
            elif 'error' in validation_result and validation_result['error']:
                st.markdown(f"<div class='error-card' style='color:#d6dadf;'>❌ Validation error: {validation_result['error']}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='warning-card' style='color:#d6dadf;'>⚠️ Address may not be valid or complete</div>", unsafe_allow_html=True)
            
            # Confidence score visualization
            confidence = validation_result.get('confidence', 0) * 100
            st.markdown("<div class='field-label' style='color:#d6dadf;'>Confidence Score</div>", unsafe_allow_html=True)
            
            # Determine color based on confidence
            if confidence >= 80:
                bar_color = "#4CAF50"  # Green
            elif confidence >= 50:
                bar_color = "#FFC107"  # Yellow/Orange
            else:
                bar_color = "#F44336"  # Red
                
            # Create visualization
            st.markdown(f"""
            <div class='confidence-bar-bg'>
                <div class='confidence-bar' style='width:{confidence}%; background-color:{bar_color};'>{confidence:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Formatted address
            if 'formatted_address' in validation_result and validation_result['formatted_address']:
                st.markdown("<div class='field-label' style='margin-top:15px; color:#d6dadf;'>📬 Standardized Address</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='field-value' style='color:#333333;'>{validation_result['formatted_address']}</div>", unsafe_allow_html=True)
            
            # Display simplified validation details
            if validation_result['details'] and validation_result['details'].get('features'):
                with st.expander("View Geolocation Details"):
                    feature = validation_result['details']['features'][0]
                    
                    # Extract the most relevant information
                    properties = feature.get('properties', {})
                    
                    # Create three columns for better organization
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.markdown("<div class='field-label' style='color:#d6dadf;'>Country</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='field-value' style='color:#333333;'>{properties.get('country', 'N/A')}</div>", unsafe_allow_html=True)
                        
                        st.markdown("<div class='field-label' style='color:#d6dadf;'>City</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='field-value' style='color:#333333;'>{properties.get('city', 'N/A')}</div>", unsafe_allow_html=True)
                    
                    with col_b:
                        st.markdown("<div class='field-label' style='color:#d6dadf;'>State</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='field-value' style='color:#333333;'>{properties.get('state', 'N/A')}</div>", unsafe_allow_html=True)
                        
                        st.markdown("<div class='field-label' style='color:#d6dadf;'>Postal Code</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='field-value' style='color:#333333;'>{properties.get('postcode', 'N/A')}</div>", unsafe_allow_html=True)
                    
                    with col_c:
                        st.markdown("<div class='field-label' style='color:#d6dadf;'>Street</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='field-value' style='color:#333333;'>{properties.get('street', 'N/A')}</div>", unsafe_allow_html=True)
                        
                        if 'lat' in properties and 'lon' in properties:
                            st.markdown("<div class='field-label' style='color:#d6dadf;'>Coordinates</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='field-value' style='color:#333333;'>Lat: {properties.get('lat')}<br>Lon: {properties.get('lon')}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    elif not openai_api_key:
        st.markdown("""
        <div class='warning-card' style='color:#d6dadf;'>
            <b>⚠️ OpenAI API Key Required</b><br>
            Please enter your OpenAI API Key in the sidebar to enable document analysis.
        </div>
        """, unsafe_allow_html=True)
    elif not geoapify_api_key:
        st.markdown("""
        <div class='warning-card' style='color:#d6dadf;'>
            <b>⚠️ Geoapify API Key Required</b><br>
            Please enter your Geoapify API Key in the sidebar to enable address validation.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='info-card' style='color:#d6dadf;'>
            <b>📤 Ready to Process</b><br>
            Please upload a document image to begin the analysis.
        </div>
        """, unsafe_allow_html=True)
        
        # Example images for demonstration
        with st.expander("See Example Documents"):
            st.write("The application can process various types of documents including:")
            cols = st.columns(3)
            with cols[0]:
                st.write("• Bank statements")
            with cols[1]:
                st.write("• Utility bills")
            with cols[2]:
                st.write("• ID cards")

if __name__ == "__main__":
    main()