# SPDX-License-Identifier: GPL-3.0-or-later
"""Installation language is only a default; saved user preferences always win."""
import json
from pathlib import Path
LANGUAGES={'en':'English','es':'Español','fr':'Français','de':'Deutsch','it':'Italiano','zh':'中文','ja':'日本語'}
PROMPT='Select the language for the first launch of UMS Control.'
NOTICE='The language can also be changed later from the Language menu in the program.'

def initial_language():
    import platform_support as p
    for file in [p.ROOT/'first-language.json',Path('/etc/ums-control/first-language')]:
        try:
            value=file.read_text(encoding='utf-8').strip()
            if file.suffix=='.json':value=json.loads(value)['language']
            if value in LANGUAGES:return value
        except (OSError,ValueError,KeyError,TypeError):pass
    return 'en'

def choose(explicit=None):
    if explicit:
        if explicit not in LANGUAGES:raise ValueError('Unsupported language code')
        return explicit
    print(PROMPT);print(NOTICE)
    codes=list(LANGUAGES)
    for n,code in enumerate(codes,1):print(str(n)+'. '+LANGUAGES[code]+' ['+code+']')
    if not __import__('sys').stdin.isatty():raise RuntimeError('Interactive language selection requires a terminal. Use --language en (or es, fr, de, it, zh, ja) for unattended installation.')
    while True:
        answer=input('Language [1 / en]: ').strip() or 'en'
        if answer in LANGUAGES:return answer
        if answer.isdigit() and 1<=int(answer)<=len(codes):return codes[int(answer)-1]
        print('Please select a listed number or language code.')
