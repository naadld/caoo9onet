#!/usr/bin/env python3
"""
Step 4: AI Subtitle & Interactive JSON Generator for Abeka Videos.
Scans Google Drive for MP4 video files, checks if .srt or .json subtitles already exist,
and if missing, automatically transcribes audio using Whisper, generates IPA phonetics,
translates to Vietnamese, builds interactive quizzes, creates .srt & .json files,
and uploads them directly back to Google Drive.
"""

import os
import sys
import re
import json
import time
import uuid
import shutil
import argparse
import subprocess
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "vpsg24gb.aleron,root_folder_id=11fQ8VYTmwRX9fMJFXeTrTTeZGDqki6dh:"
RCLONE_BIN = shutil.which("rclone") or "rclone"
RCLONE_CONF = os.getenv("RCLONE_CONFIG") or os.path.expanduser("~/.config/rclone/rclone.conf")
if not os.path.exists(RCLONE_CONF) and os.path.exists("/home/vpsg24gb/.config/rclone/rclone.conf"):
    RCLONE_CONF = "/home/vpsg24gb/.config/rclone/rclone.conf"
FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"

TARGET_PAIRS = [
    ["Grade 4"]
]

def clean_private_key(info):
    if "private_key" in info:
        pk = str(info["private_key"]).strip()
        pk = pk.replace("\\n", "\n").replace("\r", "")
        while "\\n" in pk:
            pk = pk.replace("\\n", "\n")
        info["private_key"] = pk
    return info

def log_to_google_doc(entry_text):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        vn_tz = timezone(timedelta(hours=7))
        now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")

        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.join(BASE_DIR, "credentials.json")
        env_creds = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

        info = None
        if env_creds:
            try:
                info = json.loads(env_creds, strict=False)
            except Exception:
                pass

        if not info and os.path.exists(creds_path):
            with open(creds_path, 'r', encoding='utf-8') as f:
                content = f.read()
                info = json.loads(content, strict=False)

        if not info:
            return

        info = clean_private_key(info)

        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/documents']
        )
        docs_service = build('docs', 'v1', credentials=creds)
        doc_id = '1Ew8UPThE2yN9S7EEzeeToUxZCMNpWbkNqhOfpsqXPBw'

        doc = docs_service.documents().get(documentId=doc_id).execute()
        end_index = doc.get('body').get('content')[-1].get('endIndex') - 1

        formatted_entry = f"{now_str}: {entry_text}\n"

        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': formatted_entry
            }
        }]
        docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        print(f"📝 [Doc Log Success] {formatted_entry.strip()}")
    except Exception as e:
        print(f"⚠️ Doc Logger Error: {e}")

def format_timestamp_srt(seconds):
    """Converts floating seconds into SRT timestamp format: HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int((seconds - total_seconds) * 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def is_sentence_end(word_text):
    return any(punct in word_text for punct in ['.', '?', '!', ';'])

def transcribe_and_generate(audio_path, output_json, output_srt, model_size="tiny.en"):
    """Transcribes audio, generates IPA phonetics, translates to VI, builds quizzes, and saves JSON + SRT."""
    try:
        from faster_whisper import WhisperModel
        import eng_to_ipa as ipa
        from deep_translator import GoogleTranslator
    except ImportError as e:
        print(f"❌ Missing required libraries: {e}")
        print("Please install via: pip install faster-whisper eng-to-ipa deep-translator")
        return False

    print(f"🎙️ Loading Whisper model '{model_size}'...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"🔊 Transcribing {audio_path}...")
    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        condition_on_previous_text=False,
        vad_filter=True
    )

    custom_segments = []
    current_words = []
    MAX_WORDS = 12
    PAUSE_THRESHOLD = 0.8

    for segment in segments:
        for word in segment.words:
            if len(current_words) > 0:
                prev_word = current_words[-1]
                if word.start - prev_word["end"] > PAUSE_THRESHOLD:
                    if current_words:
                        custom_segments.append(current_words)
                        current_words = []

            clean_word = word.word.strip()
            if not clean_word:
                continue

            ipa_text = ""
            try:
                raw = "".join(c for c in clean_word if c.isalnum() or c == "'")
                if raw:
                    converted = ipa.convert(raw)
                    ipa_text = "/" + converted.replace('*', '') + "/" if converted else ""
            except Exception:
                pass

            word_obj = {
                "word": word.word,
                "pinyin": ipa_text,
                "start": round(word.start, 2),
                "end": round(word.end, 2)
            }
            current_words.append(word_obj)

            if len(current_words) >= MAX_WORDS or is_sentence_end(word.word):
                custom_segments.append(current_words)
                current_words = []

    if current_words:
        custom_segments.append(current_words)

    print(f"✨ Generated {len(custom_segments)} short sentences.")

    english_texts = []
    for words in custom_segments:
        text = "".join(w["word"] for w in words).strip()
        english_texts.append(text)

    print("🌐 Translating segments to Vietnamese...")
    translator = GoogleTranslator(source='en', target='vi')
    translations = []
    for i in range(0, len(english_texts), 50):
        batch = english_texts[i:i+50]
        try:
            translated_batch = translator.translate_batch(batch)
            translations.extend(translated_batch)
        except Exception:
            for text in batch:
                try:
                    translations.append(translator.translate(text))
                except Exception:
                    translations.append("")
        time.sleep(0.5)

    # Assemble JSON structure
    transcript_data = {
        "audio_path": os.path.basename(audio_path),
        "segments": [],
        "quizzes": []
    }

    srt_lines = []

    for idx, (words, text, vi_text) in enumerate(zip(custom_segments, english_texts, translations), 1):
        if not words:
            continue
        start_sec = words[0]["start"]
        end_sec = words[-1]["end"]

        transcript_data["segments"].append({
            "id": idx - 1,
            "start": start_sec,
            "end": end_sec,
            "text": text,
            "vietnamese": vi_text,
            "highlight": "",
            "words": words
        })

        # SRT format entry
        start_srt = format_timestamp_srt(start_sec)
        end_srt = format_timestamp_srt(end_sec)
        srt_lines.append(f"{idx}\n{start_srt} --> {end_srt}\n{text}\n{vi_text}\n")

    # Generate interactive quizzes
    segs = transcript_data["segments"]
    for i in range(len(segs) - 1):
        text = segs[i]["text"].strip()
        if text.endswith("?"):
            gap = segs[i+1]["start"] - segs[i]["end"]
            if gap >= 1.0:
                transcript_data["quizzes"].append({
                    "id": len(transcript_data["quizzes"]) + 1,
                    "segmentId": segs[i]["id"],
                    "qStart": segs[i]["start"],
                    "qEnd": segs[i]["end"],
                    "aStart": segs[i+1]["start"],
                    "aEnd": segs[i+1]["end"],
                    "questionText": text,
                    "answerText": segs[i+1]["text"],
                    "gap": round(gap, 2)
                })

    # Save JSON file
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

    # Save SRT file
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_lines))

    print(f"✅ Created JSON: {output_json}")
    print(f"✅ Created SRT: {output_srt}")
    return True

def run_subtitle_generator(target_folder="Grade 4"):
    print("=" * 60)
    print(f"🚀 STEP 4: ABEKA SUBTITLE & JSON GENERATOR (Target: {target_folder})")
    print("=" * 60)

    # 1. Fetch file list from Google Drive
    target_remote = f"{REMOTE_BASE}{target_folder.rstrip('/')}/"
    print(f"🔍 Scanning files on Google Drive: {target_remote}...")
    
    cmd = [RCLONE_BIN, "--config", RCLONE_CONF, "lsf", "-R", "--files-only", target_remote]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Failed to list files on GDrive: {res.stderr}")
        return

    all_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    
    # Existing files index
    mp4_files = [f for f in all_files if f.lower().endswith('.mp4')]
    existing_subs = set(f.lower() for f in all_files if f.lower().endswith('.srt') or f.lower().endswith('.json'))

    print(f"📊 Found {len(mp4_files)} total MP4 videos on Google Drive.")

    processed_count = 0
    skipped_count = 0

    for idx, rel_mp4_path in enumerate(mp4_files, 1):
        full_rel_path = f"{target_folder.rstrip('/')}/{rel_mp4_path}"
        base_no_ext = os.path.splitext(rel_mp4_path)[0]
        
        srt_rel_path = base_no_ext + ".srt"
        json_rel_path = base_no_ext + ".json"

        # Check if SRT or JSON already exists
        if srt_rel_path.lower() in existing_subs or json_rel_path.lower() in existing_subs:
            print(f"[{idx}/{len(mp4_files)}] ⏭️ Subtitle already exists for: {rel_mp4_path}. Skipping.")
            skipped_count += 1
            continue

        print(f"\n[{idx}/{len(mp4_files)}] 🎬 Subtitle missing! Processing video: {rel_mp4_path}")

        task_tmp_dir = os.path.join(BASE_DIR, ".tmp_subtitles", uuid.uuid4().hex)
        os.makedirs(task_tmp_dir, exist_ok=True)

        local_mp4 = os.path.join(task_tmp_dir, "input.mp4")
        local_wav = os.path.join(task_tmp_dir, "audio.wav")
        local_json = os.path.join(task_tmp_dir, "output.json")
        local_srt = os.path.join(task_tmp_dir, "output.srt")

        # Step A: Download MP4 from GDrive
        print("  1/4 Downloading video file from Google Drive...")
        dl_cmd = [
            RCLONE_BIN, "--config", RCLONE_CONF, "copyto",
            f"{REMOTE_BASE}{full_rel_path}", local_mp4
        ]
        p_dl = subprocess.run(dl_cmd, capture_output=True, text=True)
        if p_dl.returncode != 0 or not os.path.exists(local_mp4):
            print(f"    ❌ Download failed: {p_dl.stderr.strip()}")
            shutil.rmtree(task_tmp_dir, ignore_errors=True)
            continue

        # Step B: Extract audio via FFmpeg
        print("  2/4 Extracting audio stream...")
        audio_cmd = [
            FFMPEG_BIN, "-y", "-loglevel", "error",
            "-i", local_mp4,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            local_wav
        ]
        p_aud = subprocess.run(audio_cmd, capture_output=True, text=True)
        if p_aud.returncode != 0 or not os.path.exists(local_wav):
            print(f"    ❌ Audio extraction failed: {p_aud.stderr.strip()}")
            shutil.rmtree(task_tmp_dir, ignore_errors=True)
            continue

        # Step C: Transcribe & Generate SRT + JSON
        print("  3/4 Transcribing & generating SRT + JSON...")
        ok = transcribe_and_generate(local_wav, local_json, local_srt)
        if not ok or not os.path.exists(local_json) or not os.path.exists(local_srt):
            print("    ❌ Subtitle generation failed.")
            shutil.rmtree(task_tmp_dir, ignore_errors=True)
            continue

        # Step D: Upload SRT & JSON to Google Drive folder
        print("  4/4 Uploading SRT & JSON to Google Drive...")
        gdrive_srt_path = f"{REMOTE_BASE}{target_folder.rstrip('/')}/{srt_rel_path}"
        gdrive_json_path = f"{REMOTE_BASE}{target_folder.rstrip('/')}/{json_rel_path}"

        up_srt = subprocess.run([RCLONE_BIN, "--config", RCLONE_CONF, "copyto", local_srt, gdrive_srt_path], capture_output=True)
        up_json = subprocess.run([RCLONE_BIN, "--config", RCLONE_CONF, "copyto", local_json, gdrive_json_path], capture_output=True)

        if up_srt.returncode == 0 and up_json.returncode == 0:
            print(f"    🎉 Successfully uploaded subtitles for: {rel_mp4_path}")
            vn_tz = timezone(timedelta(hours=7))
            now_str = datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
            log_to_google_doc(f"{now_str}: Hoàn thành tạo Phụ đề SRT & JSON cho {full_rel_path}")
            processed_count += 1
        else:
            print(f"    ❌ Upload failed. SRT code: {up_srt.returncode}, JSON code: {up_json.returncode}")

        shutil.rmtree(task_tmp_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print(f"🎉 STEP 4 SUMMARY: Processed {processed_count} new subtitles, Skipped {skipped_count} existing.")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Step 4: AI Subtitle & Interactive JSON Generator for Abeka Videos.")
    parser.add_argument("--folder", default="Grade 4", help="Folder to target on Google Drive (e.g. 'Grade 4')")
    args = parser.parse_args()

    run_subtitle_generator(target_folder=args.folder)

if __name__ == "__main__":
    main()
