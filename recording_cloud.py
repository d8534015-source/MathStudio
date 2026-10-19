"""Private R2 transport. Bounded multipart buffers; no public URLs or local credentials."""
import hashlib
import hmac
import urllib.request
import urllib.error
from urllib.parse import quote
from datetime import datetime, timezone
import xml.etree.ElementTree as ET


class R2:
    def __init__(self,config):self.config=config

    def ready(self):return self.config().get('backend')=='r2'

    def request(self,method,key,body=b'',query=None,headers=None,stream=False):
        cfg=self.config()
        if cfg.get('backend')!='r2':raise RuntimeError('Private R2 storage is not configured.')
        host=cfg['account']+'.r2.cloudflarestorage.com'
        uri='/'+quote(cfg['bucket'],safe='')+'/'+quote(key,safe='/~')
        query='&'.join(quote(str(k),safe='~')+'='+quote(str(v),safe='~') for k,v in sorted((query or {}).items()))
        now=datetime.now(timezone.utc);stamp=now.strftime('%Y%m%d');date=now.strftime('%Y%m%dT%H%M%SZ')
        digest=hashlib.sha256(body).hexdigest();signed='host;x-amz-content-sha256;x-amz-date'
        canonical='\n'.join((method,uri,query,f'host:{host}\nx-amz-content-sha256:{digest}\nx-amz-date:{date}\n',signed,digest))
        scope=stamp+'/auto/s3/aws4_request'
        message='\n'.join(('AWS4-HMAC-SHA256',date,scope,hashlib.sha256(canonical.encode()).hexdigest()))
        secret=('AWS4'+cfg['secret']).encode()
        for part in (stamp,'auto','s3','aws4_request'):secret=hmac.new(secret,part.encode(),hashlib.sha256).digest()
        signature=hmac.new(secret,message.encode(),hashlib.sha256).hexdigest()
        hdr={'x-amz-date':date,'x-amz-content-sha256':digest,
             'Authorization':f"AWS4-HMAC-SHA256 Credential={cfg['access']}/{scope}, SignedHeaders={signed}, Signature={signature}"}
        hdr.update(headers or {})
        req=urllib.request.Request('https://'+host+uri+('?' +query if query else ''),data=body if method in ('POST','PUT') else None,headers=hdr,method=method)
        # Never forward signed authorization to redirects or another endpoint.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args):return None
        try:
            response=urllib.request.build_opener(NoRedirect()).open(req,timeout=45)
            if stream:return response
            with response:return response.read(1024*1024),dict(response.headers)
        except urllib.error.HTTPError as error:
            if method=='DELETE' and error.code==404:return b'',{}
            raise RuntimeError('Private cloud transfer failed; it will be retried.') from None
        except OSError:raise RuntimeError('Private cloud transfer failed; it will be retried.') from None

    @staticmethod
    def key(record_id):return 'private-recordings/'+record_id

    def upload(self,row,path,checkpoint):
        """Resume using DB upload ID and ETags; at most one 8MiB part in memory."""
        import json
        key=self.key(row['id']);upload=row['upload_id'];parts=json.loads(row['parts'])
        if not upload:
            data,_=self.request('POST',key,query={'uploads':''},headers={'Content-Type':row['mime']})
            root=ET.fromstring(data);upload=next((x.text for x in root.iter() if x.tag.split('}')[-1]=='UploadId'),None)
            if not upload:raise RuntimeError('Cloud multipart response was invalid.')
            checkpoint(upload,parts)
        # A lost completion response can leave the object committed in R2 while
        # the durable metadata still says uploading. Verify it without replaying
        # an already-consumed multipart upload ID.
        size=path.stat().st_size
        if parts and len(parts)==(size+8*1024**2-1)//(8*1024**2):
            try:
                _,headers=self.request('HEAD',key)
                length=next((v for k,v in headers.items() if k.lower()=='content-length'),None)
                if length is not None and int(length)==size:return
            except RuntimeError:pass
        with path.open('rb') as source:
            source.seek(len(parts)*8*1024**2)
            while True:
                chunk=source.read(8*1024**2)
                if not chunk:break
                _,headers=self.request('PUT',key,chunk,{'partNumber':len(parts)+1,'uploadId':upload})
                etag=next((v for k,v in headers.items() if k.lower()=='etag'),None)
                if not etag:raise RuntimeError('Cloud part acknowledgment was invalid.')
                parts.append(etag);checkpoint(upload,parts)
        root=ET.Element('CompleteMultipartUpload')
        for number,etag in enumerate(parts,1):
            part=ET.SubElement(root,'Part');ET.SubElement(part,'PartNumber').text=str(number);ET.SubElement(part,'ETag').text=etag
        data,_=self.request('POST',key,ET.tostring(root),{'uploadId':upload},headers={'Content-Type':'application/xml'})
        if ET.fromstring(data).tag.split('}')[-1]!='CompleteMultipartUploadResult':raise RuntimeError('Cloud finalization was not acknowledged.')

    def remove(self,row):
        if row['upload_id'] and row['state']!='ready':self.request('DELETE',self.key(row['id']),query={'uploadId':row['upload_id']})
        self.request('DELETE',self.key(row['id']))

    def open(self,row,range_header=None):
        headers={}
        if range_header:
            import re
            if not re.fullmatch(r'bytes=\d*-\d*',range_header) or range_header=='bytes=-':raise ValueError('Invalid byte range.')
            headers['Range']=range_header
        return self.request('GET',self.key(row['id']),headers=headers,stream=True)
