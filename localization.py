# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 N3ruk
"""Offline UI translations. User data and upstream logs are never translated."""
import json,re
from pathlib import Path
CATALOG=json.loads(Path(__file__).with_name('translations.json').read_text(encoding='utf-8'))
_language='es'

def set_language(language):
 global _language
 if language not in {'es','en','fr','de','it','zh','ja'}:raise ValueError('Unknown UI language')
 _language=language

def platform_text(text):
 import os
 return text.replace('Ubuntu','Windows' if os.name=='nt' else 'Linux')

def translate_between(text,source,target):
 text=platform_text(text)
 if not text or source==target:return text
 # Exact texts first; keep all technical values and user-provided data untouched.
 for original,values in CATALOG.items():
  old=platform_text(original if source=='es' else values[source])
  new=platform_text(original if target=='es' else values[target])
  if text==old:return new
 # Dynamic messages explicitly expose only named placeholders, not arbitrary substitutions.
 for original,values in CATALOG.items():
  old=platform_text(original if source=='es' else values[source])
  if '{value}' not in old:continue
  before,after=old.split('{value}');match=re.fullmatch(re.escape(before)+'(.+?)'+re.escape(after),text,re.S)
  if match:return platform_text(original if target=='es' else values[target]).replace('{value}',match[1])
 # UI-generated compound summaries consist exclusively of registered fragments.
 # Never called on text edits, device names, paths, media titles or server logs.
 candidates=[]
 for original,values in CATALOG.items():
  old=platform_text(original if source=='es' else values[source])
  if len(old.strip())<3 or '{value}' in old:continue
  new=platform_text(original if target=='es' else values[target])
  candidates.append((old,new))
 lookup=dict(candidates)
 if lookup:
  pattern='|'.join(re.escape(s) for s in sorted(lookup,key=len,reverse=True))
  return re.sub(pattern,lambda m:lookup[m[0]],text)
 return text

def tr(text):
    return translate_between(str(text),'es',_language)
