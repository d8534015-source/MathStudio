"""Explicit real-model acceptance. Never downloads or installs anything.

Uses synthetic public sources in a temporary OWNER database and the selected
external Argos runtime. Missing models are reported as blocked, never passed.
"""
import argparse
import http.client
import json
import os
from pathlib import Path
import time
from unittest import mock
import argos_runtime
from test_security_stability import BackendCase


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    if not argos_runtime.ready():
        report={'status':'blocked_missing_models','examples':[],
                'reason':'Install and verify both real Argos models with OWNER setup first. No real translations were executed.'}
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report));return 1
    fixture=BackendCase();fixture.setUp()
    try:
        teacher=fixture.client('teacher')
        def request(path,data=None):
            connection=http.client.HTTPConnection('127.0.0.1',fixture.http.server_port,timeout=45)
            headers={'Cookie':teacher['cookie'],'Content-Type':'application/json','X-CSRF-Token':teacher['csrf']}
            try:
                connection.request('GET' if data is None else 'POST',path,None if data is None else json.dumps(data),headers)
                response=connection.getresponse();value=json.loads(response.read());assert response.status==200,(response.status,value)
                return value
            finally:connection.close()
        examples=[]
        with mock.patch.dict(os.environ,{'MATH_PUBLIC_TRANSLATION_PROVIDER':'argos'}):
            request('/api/admin/content-translations',{'action':'config','enabled':True,'terms':['Alice Chen','王老师','MathStudio']})
            for target,original in [('zh',r'We learn fractions and solve 2x + 3 = 7 with Alice Chen. Read https://example.org. Use $x^2+1$ and \frac{x}{y}.'),
                                    ('en',r'我们跟王老师一起学习分数。请解方程 2x + 3 = 7，并阅读 https://example.org。保留 $x^2+1$。')]:
                with fixture.app.db() as c:c.execute("UPDATE settings SET value=? WHERE key='intro'",(original,))
                info=request('/api/admin/content-translations');source=next(x for x in info['sources'] if x['key']=='settings:0:intro')
                payload={'action':'generate','key':source['key'],'target':target,'source_hash':source['source_hash']}
                start=time.monotonic();generated=request('/api/admin/content-translations',payload);elapsed=time.monotonic()-start
                draft=generated['draft'];assert draft.strip()!=original.strip()
                for value in ['2x + 3 = 7','$x^2+1$','https://example.org']:assert value in draft,value
                assert ('Alice Chen' if target=='zh' else '王老师') in draft
                with mock.patch.object(argos_runtime,'translate',side_effect=AssertionError('Cache must not invoke model')):
                    assert request('/api/admin/content-translations',payload)['cached']
                rows=request('/api/admin/content-translations')['translations'];row=next(x for x in rows if x['target']==target and x['source_hash']==source['source_hash'])
                request('/api/admin/content-translations',dict(payload,action='approve',text=draft,revision=row['revision']))
                assert request('/api/content-translations?lang='+target)['translations'][source['key']]['text']==draft
                with fixture.app.db() as c:
                    assert c.execute("SELECT value FROM settings WHERE key='intro'").fetchone()[0]==original
                    c.execute("UPDATE settings SET value='Changed public source' WHERE key='intro'")
                assert source['key'] not in request('/api/content-translations?lang='+target)['translations']
                examples.append({'target':target,'source':original,'translation':draft,'seconds':round(elapsed,3),
                                 'protection_cache_approval_invalidation':'passed','network':'disabled inside inference worker'})
        receipt=json.loads((argos_runtime.home()/'installation.json').read_text(encoding='utf-8'))
        report={'status':'passed','examples':examples,'runtime':{k:receipt[k] for k in ('argos','python','models')},
                'physical_windows11':'not executed by this script'}
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False));return 0
    finally:fixture.tearDown()


if __name__=='__main__':raise SystemExit(main())
