# Live Speech Translation Service

This is a real-time speech translation service that allows speakers to deliver presentations in one language while audience members can listen in their preferred language. The service uses AWS Transcribe, Translate, and Polly services for speech-to-text, translation, and text-to-speech conversion respectively.

## Features

- Real-time speech capture from the speaker
- Multiple language support for audience members
- Live translation of speech to text
- Text-to-speech conversion in the audience's preferred language
- Web-based interface for both speakers and audience members

## Prerequisites

- Python 3.8 or higher
- AWS account with access to:
  - Amazon Transcribe
  - Amazon Translate
  - Amazon Polly
- AWS credentials configured on your system

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your AWS credentials:
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=your-region
```

## Usage

1. Start the server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:8000
```

3. Choose your role:
   - Click "I am a Speaker" if you're the presenter
   - Click "I am an Audience Member" if you're listening

### For Speakers:
- Click "Start Speaking" to begin recording
- Speak clearly into your microphone
- Click "Stop Speaking" when finished

### For Audience Members:
- Select your preferred language from the dropdown menu
- The translation will appear in real-time
- Audio will play automatically in your selected language

## Architecture

The application uses:
- FastAPI for the web server
- WebSocket for real-time communication
- AWS Transcribe for speech-to-text
- AWS Translate for text translation
- AWS Polly for text-to-speech

## Security Considerations

- Ensure your AWS credentials are properly secured
- Use HTTPS in production
- Implement proper authentication for speakers
- Consider rate limiting for audience members

## License

This project is licensed under the MIT License - see the LICENSE file for details. 