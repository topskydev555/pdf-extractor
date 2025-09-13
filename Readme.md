# PDF Extractor Web App

A simple Flask web application that extracts text, tables, and figures from PDFs using Adobe PDF Services API, with Dropbox integration for file management and web-based viewing/editing capabilities.

## Features

- **PDF Extraction**: Extract text, tables, and figures from PDF documents
- **Dropbox Integration**: Upload extracted data to Dropbox for cloud storage
- **Web Interface**: View and edit extracted data through a clean web interface
- **Scalable Architecture**: Built for easy scaling and improvement

## Workflow

1. **Upload PDF** → User uploads a PDF file through the web interface
2. **Extract Data** → Adobe PDF Services API processes the PDF
3. **Upload to Dropbox** → Extracted data is automatically uploaded to Dropbox
4. **View & Edit** → Users can view and edit the extracted content via web interface

## Tech Stack

- **Backend**: Python Flask
- **PDF Processing**: Adobe PDF Services API
- **Cloud Storage**: Dropbox API
- **Frontend**: HTML/CSS/JavaScript
- **Environment**: Python virtual environment

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd pdf-extraction
```

2. Create virtual environment:

```bash
python -m venv env
env\Scripts\activate  # Windows
# or
source env/bin/activate  # Linux/Mac
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   Create a `.env` file with your credentials:

```
CLIENT_ID=your_adobe_client_id
CLIENT_SECRET=your_adobe_client_secret
DROPBOX_TOKEN=your_dropbox_token
```

5. Run the application:

```bash
python app.py
```

## Usage

1. Place your PDF file as `input.pdf` in the project root
2. Run the extraction script:

```bash
python index.py
```

3. Check the `out_demo/` folder for extracted content:
   - `text.txt` - Extracted text
   - `structuredData.json` - Full structured data
   - `figures/` - PNG images of figures
   - `tables/` - PNG images and CSV files of tables

## Project Structure

```
pdf-extraction/
├── app.py                 # Flask web application
├── index.py               # PDF extraction script
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (gitignored)
├── .gitignore            # Git ignore rules
└── env/                  # Virtual environment (gitignored)
```

## API Integration

### Adobe PDF Services API

- Extracts text, tables, and figures from PDFs
- Returns structured JSON data with renditions
- Handles various PDF formats and layouts

### Dropbox API

- Uploads extracted files to cloud storage
- Organizes files in structured folders
- Provides sharing and collaboration features

## Scaling & Improvements

### Current Capabilities

- Single PDF processing
- Basic web interface
- Local file storage

### Future Enhancements

- **Batch Processing**: Handle multiple PDFs simultaneously
- **User Authentication**: Multi-user support with login system
- **Database Integration**: Store extraction history and metadata
- **Real-time Processing**: WebSocket support for live updates
- **Advanced Editing**: Rich text editor for extracted content
- **API Endpoints**: RESTful API for third-party integrations
- **Caching**: Redis integration for improved performance
- **Monitoring**: Logging and analytics dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, please open an issue in the repository or contact the development team.
