# Smart Document Analyzer

A Streamlit application that uses AI vision technology to extract information from documents and validate addresses with geolocation services.

## 🌟 Features

- **Document Analysis**: Extract names, addresses, and dates from various document types using OpenAI's GPT-4 Vision API
- **Bank Statement Detection**: Automatically identify if a document is a bank statement
- **Address Validation**: Verify and standardize addresses using Geoapify's geocoding service
- **PDF Support**: Process both image files and PDF documents
- **Confidence Scoring**: Visual representation of address validation confidence
- **Dark Mode UI**: Sleek, intuitive interface with responsive design

## 📋 Requirements

### API Keys
- [OpenAI API Key](https://platform.openai.com/) for document analysis
- [Geoapify API Key](https://www.geoapify.com/) for address validation

### Python Dependencies
```
streamlit
pillow (PIL)
openai
requests
base64
```

## 🚀 Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/smart-document-analyzer.git
cd smart-document-analyzer
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Make sure pdf_handler.py is in the project directory

## 💻 Usage

1. Start the application
```bash
streamlit run app.py
```

2. Open your browser and navigate to the URL provided by Streamlit (typically http://localhost:8501)

3. Enter your API keys in the sidebar
   - OpenAI API Key
   - Geoapify API Key

4. Select your preferred AI model (GPT-4 Vision or GPT-4o)

5. Upload a document (JPG, JPEG, PNG, or PDF)

6. View the extracted information and address validation results

## 🔄 Application Workflow

1. **Upload Document**: Submit an image or PDF containing personal information
2. **AI Analysis**: The document is processed using OpenAI's Vision API
3. **Information Extraction**: Name, address, and document date are identified
4. **Address Validation**: The extracted address is verified using geocoding
5. **Results Display**: View extracted information and validation metrics

## 🧩 Project Structure

```
smart-document-analyzer/
├── app.py                  # Main Streamlit application
├── pdf_handler.py          # PDF processing utilities
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## 🛠️ Key Functions

### Document Processing
```python
def process_document(document_file, api_key, model_name="gpt-4-vision-preview"):
    """
    Process the uploaded document using OpenAI's GPT-4 Vision API
    """
```

### Address Validation
```python
def validate_address(address, api_key):
    """
    Validate an address using Geoapify API
    Returns a dict with validation results including confidence metrics
    """
```

## 📊 Example Response

```json
{
    "is_bank_statement": true,
    "name": "John Doe",
    "address": "123 Main St, Anytown, CA 12345",
    "document_date": "January 2023"
}
```

## 🔒 Privacy Considerations

- No document data is stored or retained after processing
- API communication is secured via HTTPS
- API keys are kept in memory only and not stored

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [Streamlit](https://streamlit.io/) for the app framework
- [OpenAI](https://openai.com/) for the GPT-4 Vision API
- [Geoapify](https://www.geoapify.com/) for the geocoding services
- [Icons8](https://icons8.com/) for the document icon
