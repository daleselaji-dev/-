#!/usr/bin/env python3
import concurrent.futures, datetime, html, json, random, re, time
from curl_cffi import requests

BASE='https://pay.ldxp.cn'
TOKENS='''0error,2425,5W34SF00,282D9KDL,7HVUEC3Y,6TKPIT5E,M67EGQ4V,VCSS5TUW,J3FIDOJO,GTQ,YQUOBIW1,aishop,aistore,grok,O3N30X89,xiaoba,yoyohub,84FRGTKZ,echo_dream,WPXSCE1B,W2WA61DN,oak,8XBEFW66,SubAIP,1CMPMUXM,htl,ai-store,9T40GAS6,YFZZYN8N,ChatShare,YP48FZ43,cohorsAI,EK7VIFEG,ONJ5DYXX,X6H4JRXW,gaccode,ganai,pixelshop,FV0SO242,OG8Y4FKO,I2XZHSEA,GPT9999,xiamai,74BNTMAU,FIFFGN4F,UMK5K588,JFWHT64I,AB7F82VQ,4UOATQTU,iceaix,jieyou92,59FSBGJN,KQ73NYO7,lanyy,Hui-AI666,ainx,Mintapi,7A4829UY,parhom,FNAOIGBK,rexmoo.ai,rick,RSIAY6WR,FPG7WKL2,ZQXOSYAD,superman,haifs,wckj,SQBAF2T3,WOXP888,XRE84N7M,yuaotian,BP7NFXYT,99UV2HM5,WURK0XWX,GT7KX1TN,zhubj,UQE4G5JR,1AESI47M,L0K5A26F,33X1D2BV,22DHYNNV,61KF391I,HIRM9HZZ,5VAWZDGD,YY4KVE2T,GuoWangovo,J5CA6VJZ,Kegan04,47P8PKPP,AY1FXLQX,KHRR17MS,codex8,P5034CNR,1VGV7A8U,V38JA2MD,ED9POSCY,txai,1E5DST9P,J0Q89LSE,SEBYSZ6G,VUOJQOHY,1D0LD6BR,dialogue,HCJW0TDL,AWXK3UJY,MRBUOCI4,doge,wohoo,YE9N6WYK,XWYIE6VL,339,3CCG4B0K,1DM0L7CR,WYDOV9YM,qq987G,7KJU4N9A,IK7OYLXZ,wanghaha,6YHGJOPN,qiudaoyu777,geiliapi,ruozhen,2G4J2E1U,FireSpark,BVK9S0NZ,911,84564786,P9HPIPWA,qingwaAA,HLT0XHF9,1I2Y9GEC,gpticu,shayulajiao,LQHCQF49,V2M14U73'''.split(',')
TAG=re.compile(r'<[^>]+>')
PLUS=re.compile(r'\bplus\b|plus号|plus账|plus帐',re.I)
READY=re.compile(r'成品(?:号|账号|帐号)?|独享(?:号|账号|帐号)|现号|完整账号|完整帐号|直接登录|拿到即用|开箱即用',re.I)
EXCLUDE=re.compile(r'代充|充值|自助开通|升级服务|共享|合租|拼车|team|团队|邀请|席位|卡密|cdk|json|api|中转|镜像|未注册|自行注册|自己注册|需注册|注册教程|未接码|自行接码|自己接码|需接码|接码服务|邮箱单卖|仅邮箱|邮箱批发|试用号|免费号',re.I)
STRONG=re.compile(r'未禁码|不禁码|可接码|还能接码|可再次验证|可重复验证|可多次验证|多次验证|长效手机号|长期手机号|手机号可用',re.I)
WEAK=re.compile(r'已接码|已绑(?:定)?手机号|绑定手机号|带手机号|手机验证完成',re.I)
RISK=re.compile(r'封号不赔|掉号不赔|无售后|无质保|仅质保首登|质保首登|批量号|机刷|自动注册',re.I)

def clean(x):
    return re.sub(r'\s+',' ',TAG.sub(' ',html.unescape(str(x or '')))).strip()

def post(path,payload,referer,retries=3):
    headers={
        'accept':'application/json, text/plain, */*',
        'accept-language':'zh-CN,zh;q=0.9,en;q=0.8',
        'content-type':'application/json',
        'origin':BASE,
        'referer':referer,
        'sec-fetch-dest':'empty',
        'sec-fetch-mode':'cors',
        'sec-fetch-site':'same-origin',
        'visitorid':'live-scan-browser'
    }
    last=None
    for n in range(retries):
        try:
            r=requests.post(BASE+path,json=payload,headers=headers,impersonate='chrome',timeout=30)
            r.raise_for_status()
            ctype=(r.headers.get('content-type') or '').lower()
            if 'json' not in ctype and not r.text.lstrip().startswith('{'):
                raise RuntimeError(f'non-json status={r.status_code} content-type={ctype} body={r.text[:160]!r}')
            out=r.json()
            if str(out.get('code'))!='1': raise RuntimeError(out.get('msg') or str(out)[:200])
            return out.get('data') or {}
        except Exception as e:
            last=e; time.sleep((n+1)*1.2+random.random())
    raise last

def listed(v): return str(v).lower() in ('1','true','on','normal','available','selling','上架')
def num(v,default=0):
    try:return float(str(v).replace(',','').strip())
    except:return default

def scan_shop(token):
    rows=post('/shopApi/Shop/goodsList',{'token':token,'keywords':'','category_id':0,'goods_type':'card','current':1,'pageSize':200},f'{BASE}/shop/{token}').get('list') or []
    found=[]
    for row in rows:
        text=clean(f"{row.get('name','')} {row.get('description','')} {(row.get('category') or {}).get('name','')}")
        if not (PLUS.search(text) and READY.search(text)) or EXCLUDE.search(text): continue
        key=str(row.get('goods_key') or '').strip()
        if not key: continue
        try: info=post('/shopApi/Shop/goodsInfo',{'goods_key':key,'trade_no':''},f'{BASE}/item/{key}')
        except Exception: continue
        merged=dict(row); merged.update(info)
        text=clean(f"{merged.get('name','')} {merged.get('description','')} {((merged.get('category') or {}).get('name',''))}")
        if not (PLUS.search(text) and READY.search(text)) or EXCLUDE.search(text) or not listed(merged.get('status')): continue
        ext=merged.get('extend') or {}; stock=int(num(ext.get('stock_count'),0))
        if stock<=0: continue
        price=num(merged.get('real_price'),-1)
        if price<0: price=num(merged.get('price'),-1)
        if price<0: continue
        strong=STRONG.search(text); weak=WEAK.search(text)
        grade='A' if strong else ('B' if weak else 'C')
        user=merged.get('user') or {}; shop=clean(user.get('nickname')) or token
        risks='、'.join(sorted(set(m.group(0) for m in RISK.finditer(text))))
        found.append({'grade':grade,'evidence':strong.group(0) if strong else (weak.group(0) if weak else ''),'price':round(price,2),'stock':stock,'shop':shop,'token':token,'title':clean(merged.get('name')),'risks':risks,'url':clean(merged.get('link')) or f'{BASE}/item/{key}','goods_key':key,'description':clean(merged.get('description'))[:500]})
    return found

def main():
    started=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    products=[]; errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(scan_shop,t):t for t in TOKENS}
        for fut in concurrent.futures.as_completed(futs):
            t=futs[fut]
            try: products.extend(fut.result())
            except Exception as e: errors.append({'token':t,'error':str(e)})
    uniq={p['goods_key']:p for p in products}
    products=sorted(uniq.values(),key=lambda p:({'A':0,'B':1,'C':2}[p['grade']],p['price'],-p['stock']))
    result={'captured_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),'shop_count':len(TOKENS),'criteria':'上架status=1、库存>0、Plus成品号、排除代充/卡密/共享/需自行注册或接码','note':'A=卖家明确写未禁码/可再次验证；B=只写已接码；C=未说明接码状态','products':products,'errors':errors}
    import pathlib
    pathlib.Path('results').mkdir(exist_ok=True)
    pathlib.Path('results/latest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# LDXP Plus 实时扫描结果','',f"抓取开始：{started}",f"扫描店铺：{len(TOKENS)}；有效商品：{len(products)}；失败店铺：{len(errors)}",'', '|等级|价格|库存|店铺|商品|接码证据|风险|网址|','|---|---:|---:|---|---|---|---|---|']
    for p in products[:50]:
        vals=[p['grade'],f"¥{p['price']:.2f}",str(p['stock']),p['shop'],p['title'],p['evidence'],p['risks'],p['url']]
        lines.append('|'+ '|'.join(str(v).replace('|','/') for v in vals)+'|')
    pathlib.Path('results/latest.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__': main()
