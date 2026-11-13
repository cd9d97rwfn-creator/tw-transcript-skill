"""Cloud ASR with durable per-chunk receipts and evidence-preserving exports."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile
import httpx
from opencc import OpenCC
from .terminology import correct_terms


def save_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def process(folder: Path, progress):
    source = next(folder.glob('input.*'))
    chunks = folder / 'chunks'
    chunks.mkdir(exist_ok=True)
    # Decode rather than trusting the extension. Local file protocol only.
    result = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y',
        '-protocol_whitelist', 'file,pipe', '-i', str(source), '-vn', '-ac', '1',
        '-ar', '16000', '-c:a', 'libmp3lame', '-b:a', '48k', '-f', 'segment',
        '-segment_time', '600', '-reset_timestamps', '1', str(chunks/'%05d.mp3')],
        capture_output=True, timeout=7200)
    if result.returncode:
        raise ValueError('無法讀取音訊，請確認檔案格式與內容。')
    files = sorted(chunks.glob('*.mp3'))
    if not files:
        raise ValueError('檔案沒有可轉錄的音軌。')
    model = os.environ.get('TRANSCRIPTION_MODEL', 'gpt-transcribe')
    responses = []
    with httpx.Client(timeout=900) as client:
        for index, audio in enumerate(files):
            receipt = folder / f'response-{index:05d}.json'
            if receipt.exists():
                data = json.loads(receipt.read_text())
            else:
                progress(f'轉錄中：{index + 1} / {len(files)} 段')
                with audio.open('rb') as stream:
                    response = client.post('https://api.openai.com/v1/audio/transcriptions',
                        headers={'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY']},
                        data={'model': model}, files={'file': (audio.name, stream, 'audio/mpeg')})
                if response.status_code != 200:
                    raise ValueError(f'轉錄 API 回傳 HTTP {response.status_code}；請檢查額度與模型權限。')
                data = response.json()
                if not isinstance(data.get('text'), str):
                    raise ValueError('轉錄 API 未回傳有效文字。')
                save_json(receipt, data)
            responses.append({'chunk': index + 1, 'response': data})
    raw = '\n\n'.join(x['response']['text'] for x in responses)
    before = OpenCC('s2twp').convert(raw)
    corrected, changes = correct_terms(before, 'shared')
    export = folder / 'export'
    export.mkdir(exist_ok=True)
    (export/'raw.txt').write_text(raw, encoding='utf-8')
    save_json(export/'raw_segments.json', responses)
    (export/'before_proofread.txt').write_text(before, encoding='utf-8')
    (export/'專有名詞校稿版.txt').write_text(corrected, encoding='utf-8')
    notice = ('共用規則專有名詞校稿版；尚未逐句聽校，也未完成本堂專有名詞的獨立來源核對。'
              '切段可能影響句子銜接；分段 JSON 是 API 回應紀錄，不是逐句時間戳。'
              '人名、否定詞、年代、引文及多義詞仍待人工核對。\n')
    (export/'專有名詞校稿版.md').write_text('# 專有名詞校稿版\n\n> '+notice+'\n'+corrected, encoding='utf-8')
    (export/'校稿範圍與未決疑點.txt').write_text(notice, encoding='utf-8')
    save_json(export/'term_corrections.json', changes)
    save_json(export/'metadata.json', {'model': model, 'term_profile': 'shared',
        'human_listening_review': False, 'course_specific_review': False,
        'chunks': len(files), 'source_sha256': file_hash(source)})
    save_json(export/'sha256.json', {p.name: file_hash(p) for p in sorted(export.iterdir()) if p.name != 'sha256.json'})
    with zipfile.ZipFile(folder/'result.tmp', 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(export.iterdir()):
            bundle.write(path, path.name)
    (folder/'result.tmp').replace(folder/'result.zip')
    source.unlink()
    for audio in files:
        audio.unlink()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()
