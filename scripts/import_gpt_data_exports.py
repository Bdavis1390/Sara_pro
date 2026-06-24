#!/usr/bin/env python3
"""Import local ChatGPT/OpenAI data-export ZIPs and project folders into Sara_pro/world_documents.

This does not contact OpenAI. It only reads files already present on the local machine.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, sys, time, zipfile
from pathlib import Path
from html import unescape

TEXT_EXTS={'.txt','.md','.markdown','.json','.html','.htm','.csv','.tsv','.pdf','.docx','.odt','.rtf','.yaml','.yml'}
ZIP_NAME_RE=re.compile(r'(chatgpt|openai|gpt|conversation|data[_ -]?export|project)', re.I)
MAX_FILE_BYTES=int(os.environ.get('WORLD_IMPORT_MAX_FILE_BYTES','52428800')) # 50 MB/file default

def sha256_file(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def safe_name(s: str, limit: int=110)->str:
    s=unescape(s or 'untitled')
    s=re.sub(r'[^A-Za-z0-9._ -]+','_',s).strip().replace(' ','_')
    s=re.sub(r'_+','_',s)
    return (s[:limit] or 'untitled')

def iter_message_parts(node):
    # ChatGPT export conversations.json shape: mapping -> message -> content -> parts
    if not isinstance(node, dict):
        return
    msg=node.get('message') or {}
    if not isinstance(msg, dict):
        return
    author=(msg.get('author') or {}).get('role','unknown')
    content=msg.get('content') or {}
    parts=content.get('parts') or []
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, str) and part.strip():
                yield author, part.strip()
            elif isinstance(part, dict):
                txt=json.dumps(part, ensure_ascii=False, indent=2)
                yield author, txt

def convert_conversations_json(src: Path, out_dir: Path, source_label: str):
    made=[]
    try:
        data=json.loads(src.read_text(encoding='utf-8', errors='replace'))
    except Exception as e:
        return made, f'could not parse conversations.json: {e}'
    if not isinstance(data, list):
        return made, 'conversations.json was not a list'
    conv_dir=out_dir/'converted_conversations'
    conv_dir.mkdir(parents=True, exist_ok=True)
    index=[]
    for i, conv in enumerate(data):
        if not isinstance(conv, dict):
            continue
        title=conv.get('title') or f'conversation_{i+1}'
        create_time=conv.get('create_time')
        update_time=conv.get('update_time')
        fname=f'{i+1:05d}_{safe_name(title)}.md'
        mapping=conv.get('mapping') or {}
        lines=[f'# {title}', '', f'- Source: {source_label}', f'- Conversation index: {i+1}', f'- Create time: {create_time}', f'- Update time: {update_time}', '', '---', '']
        count=0
        if isinstance(mapping, dict):
            # preserve insertion order from JSON export
            for node_id, node in mapping.items():
                for role, text in iter_message_parts(node):
                    count += 1
                    lines.append(f'## {count}. {role}')
                    lines.append('')
                    lines.append(text)
                    lines.append('')
        out=conv_dir/fname
        out.write_text('\n'.join(lines), encoding='utf-8')
        made.append(out)
        index.append({'title':title,'file':str(out),'messages':count,'create_time':create_time,'update_time':update_time})
    (conv_dir/'CONVERSATION_INDEX.json').write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
    return made, None

def copy_if_allowed(src: Path, dest: Path, records: list, source_type: str):
    try:
        if not src.is_file():
            return
        if src.stat().st_size > MAX_FILE_BYTES:
            records.append({'source':str(src),'status':'skipped_large','bytes':src.stat().st_size})
            return
        if src.suffix.lower() not in TEXT_EXTS:
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            stem, suffix=dest.stem, dest.suffix
            dest=dest.with_name(stem+'_'+sha256_file(src)[:8]+suffix)
        shutil.copy2(src, dest)
        records.append({'source':str(src),'dest':str(dest),'bytes':dest.stat().st_size,'sha256':sha256_file(dest),'source_type':source_type,'status':'copied'})
    except Exception as e:
        records.append({'source':str(src),'status':'error','error':str(e)})

def import_zip(zip_path: Path, repo: Path, records: list):
    tag=safe_name(zip_path.stem)
    base=repo/'world_documents'/'gpt_exports'/tag
    raw=base/'raw'
    raw.mkdir(parents=True, exist_ok=True)
    records.append({'source':str(zip_path),'dest':str(base),'source_type':'zip','status':'opening'})
    try:
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                name=info.filename
                if info.is_dir():
                    continue
                suffix=Path(name).suffix.lower()
                if suffix not in TEXT_EXTS:
                    continue
                if info.file_size > MAX_FILE_BYTES:
                    records.append({'source':str(zip_path),'member':name,'status':'skipped_large','bytes':info.file_size})
                    continue
                # avoid zip slip
                target=(raw/Path(name).name).resolve()
                if not str(target).startswith(str(raw.resolve())):
                    continue
                with z.open(info) as f, target.open('wb') as out:
                    shutil.copyfileobj(f, out)
                records.append({'source':str(zip_path),'member':name,'dest':str(target),'bytes':target.stat().st_size,'sha256':sha256_file(target),'status':'extracted'})
        conv=raw/'conversations.json'
        if conv.exists():
            made, err=convert_conversations_json(conv, base, str(zip_path))
            for m in made:
                records.append({'source':str(conv),'dest':str(m),'bytes':m.stat().st_size,'sha256':sha256_file(m),'source_type':'converted_conversation','status':'converted'})
            if err:
                records.append({'source':str(conv),'status':'conversion_warning','error':err})
    except Exception as e:
        records.append({'source':str(zip_path),'source_type':'zip','status':'error','error':str(e)})

def discover_zips(paths):
    seen=set()
    for root in paths:
        root=Path(os.path.expanduser(root))
        if not root.exists():
            continue
        for p in root.rglob('*.zip'):
            if p in seen:
                continue
            seen.add(p)
            if ZIP_NAME_RE.search(p.name) or ZIP_NAME_RE.search(str(p.parent)):
                yield p

def import_loose_projects(paths, repo: Path, records: list):
    dest_root=repo/'world_documents'/'account_projects_loose'
    for root in paths:
        root=Path(os.path.expanduser(root))
        if not root.exists():
            continue
        # avoid recursively copying Sara_pro into itself except target docs are already scanned
        for p in root.rglob('*'):
            if '/.git/' in str(p):
                continue
            if 'node_modules' in p.parts or '.venv' in p.parts or '__pycache__' in p.parts:
                continue
            if p.is_file() and p.suffix.lower() in TEXT_EXTS and p.stat().st_size <= MAX_FILE_BYTES:
                rel=str(p.relative_to(root)) if p.is_relative_to(root) else p.name
                dest=dest_root/safe_name(root.name)/rel
                copy_if_allowed(p, dest, records, 'loose_project_file')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(Path.home()/'Sara_pro'))
    ap.add_argument('--sources', nargs='*', default=[str(Path.home()/'Downloads'), str(Path.home()/'Documents'), str(Path.home()/'ChatGPT_Exports'), str(Path.home()/'GPT_Exports'), str(Path.home()/'Worldshepherd'), str(Path.home()/'worldshepherd')])
    ap.add_argument('--loose-projects', action='store_true', help='also copy loose project documents from sources into world_documents/account_projects_loose')
    args=ap.parse_args()
    repo=Path(os.path.expanduser(args.repo)).resolve()
    (repo/'world_documents').mkdir(parents=True, exist_ok=True)
    records=[]
    for z in discover_zips(args.sources):
        import_zip(z, repo, records)
    if args.loose_projects:
        import_loose_projects(args.sources, repo, records)
    manifest=repo/'world_documents'/'GPT_ACCOUNT_IMPORT_MANIFEST.json'
    manifest.write_text(json.dumps({'generated_at':time.time(),'repo':str(repo),'sources':args.sources,'records':records}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[GPT-IMPORT] records: {len(records)}')
    print(f'[GPT-IMPORT] manifest: {manifest}')
    copied=sum(1 for r in records if r.get('status') in ('copied','extracted','converted'))
    print(f'[GPT-IMPORT] imported/extracted/converted: {copied}')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
