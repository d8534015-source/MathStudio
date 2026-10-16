"""Validate or assemble deterministic SOURCE candidates from an explicit manifest.

This does not produce a signed Windows installer. Unlisted files are never read.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def candidate_files(root,manifest,kind):
    root=Path(root).resolve();result={}
    for name,item in manifest['files'].items():
        if kind not in item['packages']:continue
        relative=PurePosixPath(name)
        blocked={'.git','.venv','bulletin_data','file_store','private_config.json','media_config.bat','cloud_storage.bat','.env'}
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or any(part.lower() in blocked for part in relative.parts):
            raise ValueError('Private or unsafe package path: '+name)
        if relative.suffix.lower() in ('.db','.sqlite','.sqlite3','.log','.exe','.dll','.pfx','.p12','.pem','.key'):
            raise ValueError('Runtime data, secrets and unverified binaries are excluded: '+name)
        path=root/name
        if path.resolve()!=path or not path.is_file():raise ValueError('Missing or linked release file: '+name)
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Release hash mismatch: '+name)
        archive_name=item.get('archive_names',{}).get(kind,name)
        archive_path=PurePosixPath(archive_name)
        if archive_path.is_absolute() or '..' in archive_path.parts or '\\' in archive_name or archive_name in result:
            raise ValueError('Invalid or duplicate archive name: '+archive_name)
        result[archive_name]=data
    if not result:raise ValueError('Empty release selection.')
    return result


def create_archive(root,manifest,kind,destination):
    files=candidate_files(root,manifest,kind)
    prefix=manifest['folders'][kind]
    if '/' in prefix or '\\' in prefix or prefix in ('.','..'):raise ValueError('Invalid package folder.')
    files['release_manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    destination=Path(destination)
    if destination.exists():raise FileExistsError('Refusing to overwrite an existing artifact.')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            entry=zipfile.ZipInfo(prefix+'/'+name,date_time=(1980,1,1,0,0,0))
            entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,data)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=('owner','teacher'),required=True)
    parser.add_argument('--output',type=Path,help='Create an unsigned source candidate ZIP at this NEW path; omit to validate only.')
    args=parser.parse_args();root=Path(__file__).resolve().parent
    manifest=json.loads((root/'release_manifest.json').read_text())
    if args.output:print('Unsigned source candidate SHA-256: '+create_archive(root,manifest,args.kind,args.output))
    else:print('Validated '+str(len(candidate_files(root,manifest,args.kind)))+' allowlisted source files. Windows signing/installation validation is still required.')


if __name__=='__main__':main()
