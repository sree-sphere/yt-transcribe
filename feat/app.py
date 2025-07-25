import whisper
from pytubefix import YouTube
import requests, io
from urllib.request import urlopen
from PIL import Image
import time
import streamlit as st
from streamlit_lottie import st_lottie
import numpy as np
import os
from typing import Iterator
from io import StringIO
from formatting_utils import write_vtt, write_srt

st.set_page_config(page_title="YouTube Transcriber", page_icon="🗣", layout="wide")

from pytube.innertube import _default_clients
from pytube import cipher
import re

# Sync these versions with latest client behavior
_default_clients["ANDROID"]["context"]["client"]["clientVersion"] = "19.08.35"
_default_clients["ANDROID_EMBED"]["context"]["client"]["clientVersion"] = "19.08.35"

# Patch throttling extractor to prevent RegexMatch errors
def get_throttling_function_name(js: str) -> str:
    function_patterns = [
        r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&\s*\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])\([a-z]\)',
    ]
    for pattern in function_patterns:
        m = re.search(pattern, js)
        if m:
            if len(m.groups()) == 1:
                return m.group(1)
            idx = m.group(2)
            if idx:
                arr = re.search(
                    rf'var {re.escape(m.group(1))}\s*=\s*(\[.+?\]);', js
                )
                if arr:
                    arr = arr.group(1).strip("[]").split(",")
                    arr = [x.strip() for x in arr]
                    return arr[int(idx)]
    raise Exception("get_throttling_function_name: regex no match")

cipher.get_throttling_function_name = get_throttling_function_name


# Define a function that we can use to load lottie files from a link.
@st.cache(allow_output_mutation=True)
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

col1, col2 = st.columns([1, 3])
with col1:
    lottie = load_lottieurl("https://assets9.lottiefiles.com/private_files/lf30_bntlaz7t.json")
    st_lottie(lottie, speed=1, height=200, width=200)

with col2:
    st.write("""
    ## Youtube Transcriber 
    ##### This is an app that transcribes YouTube videos into text.""")


#def load_model(size):
    #default_size = size
    #if size == default_size:
        #return None
    #else:
        #loaded_model = whisper.load_model(size)
        #return loaded_model 
    
@st.cache(allow_output_mutation=True)
def populate_metadata(link):
    yt = YouTube(link)
    author = yt.author
    title = yt.title
    description = yt.description
    thumbnail = yt.thumbnail_url
    length = yt.length
    views = yt.views
    return author, title, description, thumbnail, length, views

# Uncomment if you want to fetch the thumbnails as well.
#def fetch_thumbnail(thumbnail):
    #tnail = urlopen(thumbnail)
    #raw_data = tnail.read()
    #image = Image.open(io.BytesIO(raw_data))
    #st.image(image, use_column_width=True)


def convert(seconds):
    return time.strftime("%H:%M:%S", time.gmtime(seconds))


loaded_model = whisper.load_model("base")
current_size = "None"
size = st.selectbox("Model Size", ["tiny", "base", "small", "medium", "large"], index=1)


def change_model(current_size, size):
    if current_size != size:
        loaded_model = whisper.load_model(size)
        st.write(f"Model is {'multilingual' if loaded_model.is_multilingual else 'English-only'} "
        f"and has {sum(np.prod(p.shape) for p in loaded_model.parameters()):,} parameters.")
        return loaded_model
    else:
        return None


@st.cache(allow_output_mutation=True)
def inference(link):
    yt = YouTube(link)
    path = yt.streams.filter(only_audio=True)[0].download(filename="audio.mp4")
    results = loaded_model.transcribe(path)
    vtt = getSubs(results["segments"], "vtt", 80)
    srt = getSubs(results["segments"], "srt", 80)
    return results["text"], vtt, srt

def getSubs(segments: Iterator[dict], format: str, maxLineWidth: int) -> str:
    segmentStream = StringIO()

    if format == 'vtt':
        write_vtt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    elif format == 'srt':
        write_srt(segments, file=segmentStream, maxLineWidth=maxLineWidth)
    else:
        raise Exception("Unknown format " + format)

    segmentStream.seek(0)
    return segmentStream.read()


def main():
    change_model(current_size, size)
    link = st.text_input("YouTube Link")
    if st.button("Transcribe"):
        author, title, description, thumbnail, length, views = populate_metadata(link)
        results = inference(link)
            
        col3, col4 = st.columns(2)
        with col3:
            #fetch_thumbnail(thumbnail)
            st.video(link)
            st.markdown(f"**Channel**: {author}")
            st.markdown(f"**Title**: {title}")
            st.markdown(f"**Length**: {convert(length)}")
            st.markdown(f"**Views**: {views:,}")

        with col4:
            with st.expander("Video Description"):
                st.write(description)
            #st.markdown(f"**Video Description**: {description}")
            with st.expander("Video Transcript"):
                st.write(results[0])
            # Write the results to a .txt file and download it.
            with open("transcript.txt", "w+") as f:
                f.writelines(results[0])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.txt"), "rb") as f:
                datatxt = f.read()
            

            with open("transcript.vtt", "w+") as f:
                f.writelines(results[1])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.vtt"), "rb") as f:
                datavtt = f.read()
            
            with open("transcript.srt", "w+") as f:
                f.writelines(results[2])
                f.close()
            with open(os.path.join(os.getcwd(), "transcript.srt"), "rb") as f:
                datasrt = f.read()
            
            if st.download_button(label="Download Transcript (.txt) ",
                                data=datatxt,
                                file_name=f"{title}.txt"):
                st.success("Downloaded Successfully!")
            
            elif st.download_button(label="Download Transcript (.vtt)",
                                data=datavtt,
                                file_name=f"{title}.vtt"):
                st.success("Downloaded Successfully!")

            elif st.download_button(label="Download Transcript (.srt)",
                                data=datasrt,
                                file_name=f"{title}.srt"):
                st.success("Downloaded Successfully! ")
            else:
                st.success("You can download the transcript in .srt format and upload it to YouTube to create subtitles for your video.")
                st.info("Streamlit refreshes after the download button is clicked. The data is cached so you can download the transcript again without having to transcribe the video again.")
        

if __name__ == "__main__":
    main()