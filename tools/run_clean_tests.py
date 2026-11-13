#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the maintained checks using only the prepared Ubuntu 24.04 userspace."""
import os,subprocess
from pathlib import Path
from prepare_test_root import ROOT,BASE,sandbox

def main():
 if not (BASE/'usr/bin/python3').exists():raise SystemExit('Run tools/prepare_test_root.py first')
 out=ROOT/'.cache/clean-checks';out.mkdir(exist_ok=True)
 commands=[('tests',['/usr/bin/python3','-m','unittest','discover','-v']),('rebuild',['/usr/bin/python3','tools/verify_rebuild.py']),('integration',['/usr/bin/python3','tools/integration.py']),('conversion',['/usr/bin/python3','tools/integration.py','--mode','force','--subtitles','passthrough','--output','.cache/integration-force.json'])]
 for name,command in commands:
  with (out/(name+'.log')).open('w') as log:
   result=subprocess.run(sandbox(command),env=dict(os.environ,UMS_REQUIRE_INTEGRATION='1'),stdout=log,stderr=subprocess.STDOUT)
  print(name,'exit',result.returncode,flush=True)
  if result.returncode:
   print((out/(name+'.log')).read_text(encoding='utf-8')[-3500:]);raise SystemExit(result.returncode)
 print('All clean userspace checks passed. No real systemd user session was simulated as a physical login.')
if __name__=='__main__':main()
