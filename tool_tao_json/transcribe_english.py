import argparse
import json
import os
import time
from faster_whisper import WhisperModel
import eng_to_ipa as ipa
from deep_translator import GoogleTranslator

def is_sentence_end(word_text):
    # simple heuristic for sentence boundary
    return any(punct in word_text for punct in ['.', '?', '!', ';'])

def transcribe(video_path, output_json, model_size="small.en"):
    print(f"Loading Whisper model '{model_size}'...")
    # device="auto" uses GPU if available, else CPU
    model = WhisperModel(model_size, device="auto", compute_type="default")
    
    print(f"Transcribing {video_path}...")
    segments, info = model.transcribe(video_path, word_timestamps=True, condition_on_previous_text=False, vad_filter=True)
    
    print(f"Detected language '{info.language}' with probability {info.language_probability}")
    
    # Process into shorter sentences
    custom_segments = []
    current_segment = []
    current_words = []
    
    MAX_WORDS = 12
    PAUSE_THRESHOLD = 0.8
    
    print("Processing segments...")
    for segment in segments:
        for word in segment.words:
            # Check pause
            if len(current_words) > 0:
                prev_word = current_words[-1]
                if word.start - prev_word["end"] > PAUSE_THRESHOLD:
                    # Flush current segment
                    if current_words:
                        custom_segments.append(current_words)
                        current_words = []
            
            clean_word = word.word.strip()
            if not clean_word:
                continue
                
            ipa_text = ""
            try:
                # remove punctuation for IPA lookup
                raw = "".join(c for c in clean_word if c.isalnum() or c == "'")
                if raw:
                    converted = ipa.convert(raw)
                    ipa_text = "/" + converted.replace('*', '') + "/" if converted else ""
            except:
                pass

            word_obj = {
                "word": word.word, # keep original spacing/punctuation
                "pinyin": ipa_text,
                "start": word.start,
                "end": word.end
            }
            
            current_words.append(word_obj)
            
            # Check split conditions
            if len(current_words) >= MAX_WORDS or is_sentence_end(word.word):
                custom_segments.append(current_words)
                current_words = []
                
    if current_words:
        custom_segments.append(current_words)
        
    print(f"Generated {len(custom_segments)} short sentences.")
    
    # Prepare JSON structure
    transcript_data = {
        "video_path": os.path.abspath(video_path),
        "segments": []
    }
    
    translator = GoogleTranslator(source='en', target='vi')
    
    # Batch translation to save time
    english_texts = []
    for words in custom_segments:
        text = "".join(w["word"] for w in words).strip()
        english_texts.append(text)
        
    print("Translating to Vietnamese...")
    translations = []
    for i in range(0, len(english_texts), 50):
        batch = english_texts[i:i+50]
        try:
            translated_batch = translator.translate_batch(batch)
            translations.extend(translated_batch)
        except Exception as e:
            print(f"Batch translation error: {e}, falling back to individual")
            for text in batch:
                try:
                    translations.append(translator.translate(text))
                except:
                    translations.append("")
        time.sleep(1)
        
    # Assemble final segments
    for idx, (words, text, vi_text) in enumerate(zip(custom_segments, english_texts, translations)):
        if not words:
            continue
        transcript_data["segments"].append({
            "id": idx,
            "start": words[0]["start"],
            "end": words[-1]["end"],
            "text": text,
            "vietnamese": vi_text,
            "highlight": "",
            "words": words
        })
        
    # Generate Interactive Quizzes
    transcript_data["quizzes"] = []
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
                
    # Save JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe English video to custom JSON")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("output", nargs="?", help="Path to output JSON file (optional). If not provided, saves next to the video.")
    args = parser.parse_args()
    
    if args.output:
        output_path = args.output
    else:
        # Save JSON next to the MP4 file
        output_path = os.path.splitext(args.video)[0] + ".json"
        
    transcribe(args.video, output_path)
