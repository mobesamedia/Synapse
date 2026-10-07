"""Portable, read-only Anki references. No collection edits or card scheduling."""
import re
from html import unescape
from html.parser import HTMLParser

MAX_LINKS = 12

class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.hidden+=1
        if tag in ('br','div','p'): self.parts.append('\n')
        if tag=='img': self.parts.append('[image]')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def plain(value, limit=500):
    parser=_Text();parser.feed(str(value)[:100000])
    return re.sub(r'[ \t]+',' ',unescape(''.join(parser.parts))).strip()[:limit]

def clean_link(value):
    if not isinstance(value,dict) or value.get('version')!=1 or value.get('kind') not in ('note','card'):
        raise ValueError('Invalid Anki link')
    guid=value.get('noteGuid')
    if not isinstance(guid,str) or not 1<=len(guid)<=100 or any(ord(c)<32 for c in guid):
        raise ValueError('Invalid note identifier')
    result={'version':1,'kind':value['kind'],'noteGuid':guid,'label':str(value.get('label',''))[:180]}
    for key in ('noteId','cardId'):
        number=str(value.get(key,''))
        if key=='cardId' and result['kind']=='note': continue
        if not re.fullmatch(r'[1-9][0-9]{0,18}',number): raise ValueError('Invalid Anki identifier')
        result[key]=number
    if result['kind']=='card':
        ordinal=value.get('cardOrd')
        if isinstance(ordinal,bool) or not isinstance(ordinal,int) or not 0<=ordinal<=65535: raise ValueError('Invalid card ordinal')
        result['cardOrd']=ordinal
        result['template']=str(value.get('template',''))[:200]
    return result

def key(link):
    return (link['noteGuid'],link['kind'],link.get('cardOrd'))

def clean_links(values):
    if not isinstance(values,list) or len(values)>MAX_LINKS: raise ValueError('Too many Anki links')
    result=[];seen=set()
    for value in values:
        link=clean_link(value)
        if key(link) not in seen: result.append(link);seen.add(key(link))
    return result

def resolve(col, value):
    link=clean_link(value)
    # A numeric ID alone is never sufficient across profiles/imports.
    rows=col.db.all('select id from notes where guid = ? limit 2',link['noteGuid'])
    if len(rows)!=1: return None
    nid=int(rows[0][0])
    if link['kind']=='note': return {'nid':nid,'search':'nid:'+str(nid)}
    rows=col.db.all('select id, ord from cards where nid = ?',nid)
    for cid,ordinal in rows:
        if str(cid)==link['cardId'] and int(ordinal)==link['cardOrd']:
            return {'nid':nid,'cid':int(cid),'search':'cid:'+str(cid)}
    for cid,ordinal in rows:
        if int(ordinal)==link['cardOrd']:
            card=col.get_card(cid)
            if link.get('template') and card.template().get('name')!=link['template']: return None
            return {'nid':nid,'cid':int(cid),'search':'cid:'+str(cid)}
    return None

def describe(col,nid):
    note=col.get_note(nid)
    fields=[];remaining=16000
    for name,value in note.items():
        if remaining<=0:break
        text=plain(value,min(5000,remaining));fields.append((name,text));remaining-=len(text)+len(name)+2
    title=next((value.replace('\n',' ') for _,value in fields if value.strip()),'…')[:160]
    base={'version':1,'kind':'note','noteGuid':note.guid,'noteId':str(note.id),'label':title}
    cards=[]
    for card in note.cards():
        template=card.template().get('name','')
        label=template+(' · c'+str(card.ord+1) if note.note_type().get('type')==1 else '')
        cards.append({'name':label,'link':dict(base,kind='card',cardId=str(card.id),cardOrd=card.ord,template=template), 'deck':col.decks.name(card.odid or card.did)})
    return {'nid':int(note.id),'title':title,'fields':fields,'note':base,'cards':cards,'tags':list(note.tags),'type':note.note_type().get('name','')}

def search(col,text,deck='',tag='',ids=None):
    if ids is None:
        from anki.collection import SearchNode
        terms=[text or '']
        if deck: terms.append(SearchNode(deck=deck))
        if tag: terms.append(SearchNode(tag=tag))
        ids=col.find_notes(col.build_search_string(*terms))
    result=[]
    # Bound both preview work and the data returned to the GUI.
    for nid in ids[:60]:
        if col.db.scalar('select 1 from notes where id = ?',int(nid)):
            result.append(describe(col,nid))
    return {'items':result,'more':len(ids)>60}
