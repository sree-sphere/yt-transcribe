Method 1: Using supadata API, langdetect and Large Language Models (LLM)

`pip install supadata openai langdetect`

`python youtube_transcript.py 'url'`

Method 2: Using youtube-transcript-api and Google Translate

`pip install youtube-transcript-api deep-translator`

`python youtube_transcript2.py 'url'`

Method 3: Using pytube and whisper (forked and modified from [HuggingFace](https://huggingface.co/spaces/BatuhanYilmaz/Youtube-Transcriber/tree/main)):

`streamlit run feat/app.py`