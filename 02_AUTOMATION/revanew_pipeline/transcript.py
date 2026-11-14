"""YouTube URL -> transcript text."""
import re


def extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([0-9A-Za-z_-]{11})", url)
    if not m:
        raise ValueError(f"Not a recognisable YouTube URL: {url}")
    return m.group(1)


def fetch_transcript(url: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    vid = extract_video_id(url)
    fetched = YouTubeTranscriptApi().fetch(vid)
    return " ".join(s.text.replace("\n", " ") for s in fetched.snippets)
