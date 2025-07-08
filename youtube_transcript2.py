from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator

import argparse
from urllib.parse import urlparse, parse_qs

def fetch_transcript(video_id):
    """Fetch YouTube video transcript"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def translate_text(text, src_lang):
    """Translate text to English"""
    try:
        translator = GoogleTranslator(source=src_lang, target='en')
        translated_text = translator.translate(text)
        return translated_text
    except Exception as e:
        print(f"Error translating text: {e}")
        return text

def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube transcript')
    parser.add_argument('url', help='YouTube video URL')
    args = parser.parse_args()

    parsed_url = urlparse(args.url)
    video_id = parse_qs(parsed_url.query)['v'][0]
    transcript = fetch_transcript(video_id)

    if transcript:
        output_text = ""
        for snippet in transcript:
            text = snippet['text']
            # Detect language (simple implementation, may not work for all cases)
            if not text.isascii():
                src_lang = 'auto'
                translated_text = translate_text(text, src_lang)
                output_text += translated_text + "\n"
            else:
                output_text += text + "\n"

        with open("output.txt", "w") as f:
            f.write(output_text)
        print("Transcript saved to output.txt")

if __name__ == "__main__":
    main()