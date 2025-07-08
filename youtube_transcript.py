from supadata import Supadata, SupadataError
from langdetect import detect, LangDetectException
import openai

import argparse
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import os

load_dotenv()
# Configuration
# Supadata API key
SUPADATA_API_KEY = os.environ.get("SUPADATA_API_KEY")

# OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# Initialize clients
supadata = Supadata(api_key=SUPADATA_API_KEY)
openai.api_key = OPENAI_API_KEY

# Helpers
def translate_with_openai(text: str, target_lang: str = "English") -> str:
    prompt = (
        f"Translate the following text into {target_lang}, preserving meaning exactly:\n\n"
        f"{text}"
    )
    print(f">>> Sending to OpenAI for translation: {text!r}")
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=500
        )
        translated = resp.choices[0].message.content.strip()
        print(f"<<< Received translation: {translated!r}")
        return translated
    except Exception as e:
        print(f"[ERROR] OpenAI translation failed: {e}")
        return text  # Return original text if translation fails

def is_english(text: str, api_lang: str = None) -> bool:
    """
    Check if text is English using both API language info and langdetect as fallback
    """
    # First check API-provided language if available
    if api_lang:
        print(f"    API language: {api_lang} for text: {text!r}")
        return api_lang.lower() == "en"
    
    # Fallback to langdetect
    try:
        detected_lang = detect(text)
        print(f"    Detected language: {detected_lang} for text: {text!r}")
        return detected_lang == "en"
    except LangDetectException:
        print("    LangDetectException; defaulting to English")
        return True

def format_timestamp(milliseconds: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm format"""
    seconds = milliseconds / 1000.0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"

# Main
def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube transcript')
    parser.add_argument('url', help='YouTube video URL')
    args = parser.parse_args()

    parsed_url = urlparse(args.url)
    VIDEO_ID = parse_qs(parsed_url.query)['v'][0]
    print(f"Processing YouTube video ID: {VIDEO_ID}")
    OUTPUT_FILE = "transcript_en.txt"

    print("1) Fetching structured transcript from Supadata…")
    try:
        # Get the structured transcript (with timestamps & text)
        transcript_obj = supadata.youtube.transcript(video_id=VIDEO_ID)
    except SupadataError as e:
        print(f"[ERROR] Failed to fetch transcript: {e.message}")
        return

    # Extract segments from the transcript object
    segments = None
    
    # The Supadata Transcript object has a 'content' attribute containing the chunks
    if hasattr(transcript_obj, "content"):
        segments = transcript_obj.content
        print(f"Found segments via .content: {len(segments) if segments else 0}")
    elif hasattr(transcript_obj, "results"):
        segments = transcript_obj.results
        print(f"Found segments via .results: {len(segments) if segments else 0}")
    elif hasattr(transcript_obj, "segments"):
        segments = transcript_obj.segments
        print(f"Found segments via .segments: {len(segments) if segments else 0}")
    elif isinstance(transcript_obj, list):
        segments = transcript_obj
        print(f"Transcript object is a list: {len(segments)}")
    else:
        print("[ERROR] Could not find transcript segments in the response.")
        print("Available attributes:", [attr for attr in dir(transcript_obj) if not attr.startswith('_')])
        return

    print(f"   → Retrieved {len(segments)} segments.")
    if not segments:
        print("   [WARNING] No segments found; exiting.")
        return

    print("   First 3 segments for preview:")
    for i, seg in enumerate(segments[:3]):
        # Handle both object attributes and dictionary access
        if hasattr(seg, 'offset'):
            start = seg.offset
            text = seg.text
            lang = getattr(seg, 'lang', None)
        else:
            start = seg.get("offset", seg.get("start", 0))
            text = seg.get("text", "")
            lang = seg.get("lang", None)
        
        print(f"    [{format_timestamp(start)}] {text!r} (lang: {lang})")

    processed_count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fout:
        fout.write("# Transcript with Timestamps\n\n")
        
        for seg in segments:
            # Handle both object attributes and dictionary access
            if hasattr(seg, 'offset'):
                start = seg.offset
                text = seg.text.strip()
                lang = getattr(seg, 'lang', None)
            else:
                start = seg.get("offset", seg.get("start", 0))
                text = seg.get("text", "").strip()
                lang = seg.get("lang", None)

            if not text:
                print(f"   Skipping empty segment at [{format_timestamp(start)}]")
                continue

            # Skip music/sound effect markers
            if text.lower() in ['[music]', '[applause]', '[laughter]', '[sound]']:
                print(f"   Skipping sound marker: {text}")
                continue

            print(f"2) Processing segment [{format_timestamp(start)}] {text!r}")
            
            # Check if translation is needed
            if not is_english(text, lang):
                translated = translate_with_openai(text, target_lang="English")
            else:
                print("    Already English; no translation needed.")
                translated = text

            # Write to file with proper formatting
            fout.write(f"[{format_timestamp(start)}] {translated}\n")
            # fout.write(f"{translated} ")
            processed_count += 1

    print(f"3) Saved {processed_count} translated segments to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
