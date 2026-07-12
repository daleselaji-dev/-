#!/usr/bin/env python3
import datetime, html, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE='https://pay.ldxp.cn'
TOKENS='''0error,2425,5W34SF00,282D9KDL,7HVUEC3Y,6TKPIT5E,M67EGQ4V,VCSS5TUW,J3FIDOJO,GTQ,YQUOBIW1,aishop,aistore,grok,O3N30X89,xiaoba,yoyohub,84FRGTKZ,echo_dream,WPXSCE1B,W2WA61DN,oak,8XBEFW66,SubAIP,1CMPMUXM,htl,ai-store,9T40GAS6,YFZZYN8N,ChatShare,YP48FZ43,cohorsAI,EK7VIFEG,ONJ5DYXX,X6H4JRXW,gaccode,ganai,pixelshop,FV0SO242,OG8Y4FKO,I2XZHSEA,GPT9999,xiamai,74BNTMAU,FIFFGN4F,UMK5K588,JFWHT64I,AB7F82VQ,4UOATQTU,iceaix,jieyou92,59FSBGJN,KQ73NYO7,lanyy,Hui-AI666,ainx,Mintapi,7A4829UY,parhom,FNAOIGBK,rexmoo.ai,rick,RSIAY6WR,FPG7WKL2,ZQXOSYAD,superman,haifs,wckj,SQBAF2T3,WOXP888,XRE84N7M,yuaotian,BP7NFXYT,99UV2HM5,WURK0XWX,GT7KX1TN,zhubj,UQE4G5JR,1AESI47M,L0K5A26F,33X1D2BV,22DHYNNV,61KF391I,HIRM9HZZ,5VAWZDGD,YY4KVE2T,GuoWangovo,J5CA6VJZ,Kegan04,47P8PKPP,AY1FXLQX,KHRR17MS,codex8,P5034CNR,1VGV7A8U,V38JA2MD,ED9POSCY,txai,1E5DST9P,J0Q89LSE,SEBYSZ6G,VUOJQOHY,1D0LD6BR,dialogue,HCJW0TDL,AWXK3UJY,MRBUOCI4,doge,wohoo,YE9N6WYK,XWYIE6VL,339,3CCG4B0K,1DM0L7CR,WYDOV9YM,qq987G,7KJU4N9A,IK7OYLXZ,wanghaha,6YHGJOPN,qiudaoyu777,geiliapi,ruozhen,2G4J2E1U,FireSpark,BVK9S0NZ,911,84564786,P9HPIPWA,qingwaAA,HLT0XHF9,1I2Y9GEC,gpticu,shayulajiao,LQHCQF49,V2M14U73'''.split(',')
TAG=re.compile(r'<[^>]+>')
GPT=re.compile(r'chat\s*gpt|\bgpt\b',re.I)
PLUS=re.compile(r'\bplus\b|plus号|plus账|plus帐',re.I)
READY=re.compile(r'成品(?:号|账号|帐号)?|独享(?:号|账号|帐号)|现号|完整账号|完整帐号|直接登录|拿到即用|开箱即用|满月号|手搓号|手搓',re.I)
EXCLUDE_PATTERNS=[
 ('topup',r'代充|充值|自助开通|升级服务'),('shared',r'共享|合租|拼车'),
 ('team',r'\bteam\b|团队|邀请|席位'),('key',r'卡密|cdk|json'),
 ('api',r'\bapi\b|中转|镜像'),('self_register',r'未注册|自行注册|自己注册|需注册|注册教程'),
 ('self_sms',r'自行接码|自己接码|需接码|接码服务'),('email_only',r'邮箱单卖|仅邮箱|邮箱批发'),
 ('trial_free',r'试用号|免费号')]
STRONG=re.compile(r'未禁码|不禁码|可接码|还能接码|可再次验证|可重复验证|可多次验证|多次验证|长效手机号|长期手机号|手机号可用',re.I)
WEAK=re.compile(r'已接码|已绑(?:定)?手机号|绑定手机号|带手机号|手机验证完成',re.I)


def clean(x):return re.sub(r'\s+',' ',TAG.sub(' ',html.unescape(str(x or '')))).strip()
def num(v,default=-1):
    try:return float(str(v).replace(',','').strip())
    except:return default
def is_listed(v):return str(v).lower() in ('1','true','on','normal','available','selling','上架')

def settle(page,token):
    for _ in range(6):
        page.goto(f'{BASE}/shop/{token}',wait_until='domcontentloaded',timeout=60000)
        page.wait_for_timeout(1600)
        body=page.content()
        if 'var arg1=' not in body and 'a0j' not in body:return
    raise RuntimeError('challenge did not settle')

def post(page,path,payload,token):
    result=None
    for _ in range(3):
        result=page.evaluate('''async ({url,payload})=>{const r=await fetch(url,{method:'POST',credentials:'include',headers:{'accept':'application/json, text/plain, */*','content-type':'application/json'},body:JSON.stringify(payload)});return {status:r.status,ctype:r.headers.get('content-type')||'',text:await r.text()}}''',{'url':BASE+path,'payload':payload})
        text=(result.get('text') or '').strip()
        if text.startswith('{'):
            out=json.loads(text)
            if str(out.get('code'))!='1':raise RuntimeError(out.get('msg') or text[:200])
            return out.get('data') or {}
        settle(page,token)
    raise RuntimeError(f"non-json {result}")

def rejection_hits(text):
    hits=[]
    for label,pattern in EXCLUDE_PATTERNS:
        m=re.search(pattern,text,re.I)
        if m:hits.append(f'{label}:{m.group(0)}')
    return hits

def main():
    started=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    all_plus=[];errors=[];seen=set();shop_summaries=[]
    with sync_playwright() as p:
        try:browser=p.chromium.launch(channel='chrome',headless=False,args=['--no-sandbox','--disable-dev-shm-usage'])
        except Exception:browser=p.chromium.launch(headless=False,args=['--no-sandbox','--disable-dev-shm-usage'])
        ctx=browser.new_context(locale='zh-CN',timezone_id='Asia/Singapore',viewport={'width':1280,'height':800})
        page=ctx.new_page();settle(page,TOKENS[0])
        for token in TOKENS:
            try:
                data=post(page,'/shopApi/Shop/goodsList',{'token':token,'keywords':'','category_id':0,'goods_type':'card','current':1,'pageSize':300},token)
                rows=data.get('list') or []; plus_count=0
                for row in rows:
                    list_text=clean(f"{row.get('name','')} {row.get('description','')} {(row.get('category') or {}).get('name','')}")
                    if not PLUS.search(list_text):continue
                    key=str(row.get('goods_key') or '').strip()
                    if not key or key in seen:continue
                    seen.add(key);plus_count+=1
                    try:info=post(page,'/shopApi/Shop/goodsInfo',{'goods_key':key,'trade_no':''},token)
                    except Exception as e:
                        errors.append({'token':token,'goods_key':key,'error':str(e)});continue
                    merged=dict(row);merged.update(info)
                    category=merged.get('category') or {};user=merged.get('user') or {};ext=merged.get('extend') or {}
                    text=clean(f"{merged.get('name','')} {merged.get('description','')} {category.get('name','')}")
                    price=num(merged.get('real_price'))
                    if price<0:price=num(merged.get('price'))
                    stock=num(ext.get('stock_count'))
                    strong=STRONG.search(text);weak=WEAK.search(text)
                    link=clean(merged.get('link')) or f'{BASE}/item/{key}'
                    if link.startswith('/'):link=BASE+link
                    all_plus.append({
                      'price':price,'stock':stock,'status':merged.get('status'),'listed':is_listed(merged.get('status')),
                      'ready_signal':READY.search(text).group(0) if READY.search(text) else '',
                      'verification_grade':'A' if strong else ('B' if weak else 'C'),
                      'verification_evidence':strong.group(0) if strong else (weak.group(0) if weak else ''),
                      'exclusion_hits':rejection_hits(text),'shop':clean(user.get('nickname')) or token,'token':token,
                      'title':clean(merged.get('name')),'category':clean(category.get('name')),'goods_key':key,'url':link,
                      'description':clean(merged.get('description'))[:1200]})
                shop_summaries.append({'token':token,'goods_count':len(rows),'plus_count':plus_count})
            except Exception as e:errors.append({'token':token,'error':str(e)})
        browser.close()
    all_plus.sort(key=lambda x:(x['price'] if x['price']>=0 else 10**9,-x['stock']))
    result={'captured_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),'shop_count':len(TOKENS),'all_plus_count':len(all_plus),'all_plus':all_plus,'shop_summaries':shop_summaries,'errors':errors}
    Path('results').mkdir(exist_ok=True)
    Path('results/latest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'all_plus_count':len(all_plus),'errors':len(errors),'top':all_plus[:20]},ensure_ascii=False))
if __name__=='__main__':main()
