import hashlib,json,os,pathlib,subprocess
from registry_loader import load_context
PREFERRED=['/generate','/chat','/predict','/respond','/infer','/run']
def run(cmd,timeout=240): return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
def payload_for(spec,prompt):
    p={}; set_prompt=False
    for x in spec.get('parameters',[]):
        n=x.get('name',''); l=n.lower(); req=bool(x.get('required',False)); default=x.get('default'); typ=(x.get('type') or {}).get('type')
        if l in {'message','prompt','text','query','input','instruction','user_message'}: p[n]=prompt; set_prompt=True
        elif l in {'chat_history','history','messages'}: p[n]=[]
        elif l in {'max_new_tokens','max_tokens','maximum_new_tokens'}: p[n]=600
        elif l=='temperature': p[n]=0.1
        elif l=='top_p': p[n]=0.9
        elif l=='top_k': p[n]=40
        elif l in {'system','system_prompt'}: p[n]='CLAIM<=EVIDENCE. UNKNOWN REMAINS UNKNOWN. COMPRESSION!=TRUTH. MEMORY!=UNDERSTANDING.'
        elif req and default is None:
            if typ=='string' and not set_prompt: p[n]=prompt; set_prompt=True
            else: return None
    return p if set_prompt else None
def extract(raw):
    raw=raw.strip()
    try:
        o=json.loads(raw)
        if isinstance(o,dict):
            for k in ('Response','response','text','output','message'):
                if isinstance(o.get(k),str): return o[k].strip()
    except: pass
    return raw
def invoke(space,prompt):
    info=run(['hf-gradio','info',space],120)
    if info.returncode!=0: return False,'',{'error':info.stderr[-4000:]}
    api=json.loads(info.stdout); eps=list(api.items()); eps.sort(key=lambda kv:(PREFERRED.index(kv[0]) if kv[0] in PREFERRED else 99,kv[0])); errors=[]
    for ep,spec in eps:
        payload=payload_for(spec,prompt)
        if payload is None: continue
        pred=run(['hf-gradio','predict',space,ep,json.dumps(payload,ensure_ascii=False)],240)
        if pred.returncode==0 and pred.stdout.strip():
            text=extract(pred.stdout)
            if text: return True,text,{'endpoint':ep,'sha256':hashlib.sha256(text.encode()).hexdigest()}
        errors.append((ep,(pred.stderr or pred.stdout)[-2000:]))
    return False,'',{'errors':errors}
role=os.environ['ROLE']; model=os.environ['MODEL']
registry_context,registry_meta=load_context(['constitution','meta_core','macrograins','disciplines','keys','banks'])
prompt=f'''You are FARM 40 MEMORY COMPRESSION role {role}. Compress knowledge while preserving provenance, uncertainty, contradictions, assumptions, validity domains and reconstruction-critical detail. Identify what can be removed, merged, encoded, indexed, or must be retained verbatim. Distinguish compression loss from uncertainty reduction. CLAIM<=EVIDENCE. UNKNOWN REMAINS UNKNOWN. Return concise sections: critical information; redundancy; dependencies; compression strategy; information-loss risks; provenance requirements; reconstruction test; uncertainty.

CENTRAL C42 GUIDANCE (not self-certifying):
{registry_context}'''
ok,text,meta=invoke(model,prompt)
out={'farm':40,'role':role,'model':model,'inference_success':ok,'status':'UNREVIEWED_EXTERNAL_AGENT_OUTPUT' if ok else 'EXTERNAL_INFERENCE_FAILED','output':text if ok else '', 'meta':meta,'registry_runtime':registry_meta}
pathlib.Path('result').mkdir(exist_ok=True); pathlib.Path(f'result/{role}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
