#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproducible Java overrides. The official input JAR is never modified."""
import argparse,hashlib,json,os,pathlib,re,shutil,subprocess,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
PIN='d4154acba671955a4ccfc793e8c654c0a853eca006dbb4ca8b5825265885ea5c'
WINDOWS_PIN='c84b86cfcfc09852ce979be539775ad4797be983f58ef0e38893638e560190c1'
def build(source,output,javac=None,platform='linux'):
    source=pathlib.Path(source).resolve();output=pathlib.Path(output).resolve()
    if source==output:raise ValueError('Output must not replace the official JAR')
    with source.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=(WINDOWS_PIN if platform=='windows' else PIN):raise ValueError('Input is not the pinned official UMS 15.9.0 JAR')
    java_home=os.environ.get('JAVA_HOME')
    compiler=javac or (str(pathlib.Path(java_home)/'bin/javac') if java_home else shutil.which('javac'))
    if not compiler:raise RuntimeError('JDK 17 is required')
    version=subprocess.run([compiler,'-version'],capture_output=True,text=True,check=True)
    if not re.search(r'javac 17[.]',version.stdout+version.stderr):raise RuntimeError('The reproducible bootstrap build requires JDK 17 (set JAVA_HOME or --javac); --release 17 on JDK 21 does not produce identical bytecode')
    with tempfile.TemporaryDirectory(prefix='ums-patch-build-') as temp:
        classes=pathlib.Path(temp)/'classes';classes.mkdir()
        sources=sorted(str(x) for x in (ROOT/'patches/net').rglob('*.java'))
        subprocess.run([compiler,'--release','17','-encoding','UTF-8','-cp',str(source),'-d',str(classes),*sources],check=True,timeout=180)
        output.parent.mkdir(parents=True,exist_ok=True)
        staged=pathlib.Path(temp)/'update.jar'
        with zipfile.ZipFile(staged,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as jar:
            for path in sorted(classes.rglob('*.class')):
                info=zipfile.ZipInfo(path.relative_to(classes).as_posix(),date_time=(2026,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;info.create_system=3
                jar.writestr(info,path.read_bytes(),compresslevel=9)
        shutil.copyfile(staged,output)
    return dict(output=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),sources=len(sources))
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--platform',choices=['linux','windows'],default='linux');parser.add_argument('--javac',help='Explicit JDK 17 compiler');parser.add_argument('--ums-jar',required=True,type=pathlib.Path);parser.add_argument('--output',type=pathlib.Path,default=ROOT/'server-support/update.jar');args=parser.parse_args()
    print(json.dumps(build(args.ums_jar,args.output,args.javac,args.platform)))
if __name__=='__main__':main()
