import gspread
import re
import collections
from html import escape
import os

def get_sheet_data(service_account_path, sheet_id, gid):
    try:
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(
            service_account_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.get_worksheet_by_id(gid)
        return worksheet.get_all_values()
    except Exception as e:
        print(f"Error reading Google Sheet: {e}")
        return None

def parse_data(raw_data):
    if not raw_data:
        return []
    events = []
    current_category = "미분류"
    current_owner = ""
    for row in raw_data[1:]:
        while len(row) < 12:
            row.append('')
        if row[0] and row[0].strip():
            current_owner = row[0].strip()
        if row[1] and row[1].strip():
            current_category = row[1].strip()
        if not row[2] or not row[2].strip():
            continue
        event_names = [n.strip() for n in row[2].strip().split('\n') if n.strip()]
        descriptions = [d.strip() for d in row[3].strip().split('\n') if d.strip()]
        properties_text = row[5].strip()
        comments = []
        comment_authors = ["자현", "예진", "나연", "인준"]
        for j, author in enumerate(comment_authors):
            col = 6 + j
            if row[col] and row[col].strip():
                comments.append({"author": author, "text": row[col].strip()})
        for i, name_line in enumerate(event_names):
            match = re.match(r'\[(\w+)\]\s*(.*)', name_line)
            if match:
                event_type = match.group(1).upper()
                event_name = match.group(2).strip()
            else:
                event_type = "EVENT"
                event_name = name_line
            desc = descriptions[i] if i < len(descriptions) else ""
            events.append({
                "category": current_category,
                "owner": current_owner,
                "type": event_type,
                "name": event_name,
                "description": desc,
                "properties": properties_text if i == 0 else "",
                "comments": comments if i == 0 else [],
            })
    return events

def generate_html(events):
    events_by_category = collections.OrderedDict()
    for event in events:
        cat = event['category']
        if cat not in events_by_category:
            events_by_category[cat] = []
        events_by_category[cat].append(event)

    type_colors = {
        'ROUTE': '#3b82f6', 'CLICK': '#22c55e', 'MODAL': '#f97316',
        'EVENT': '#a855f7', 'VIEW': '#ec4899',
    }

    owner_colors = {'클라이언트': '#0ea5e9', '서버': '#f59e0b'}

    sidebar_items = f'<li class="cat-item active" data-cat="all"><span class="cat-name">전체보기</span><span class="cat-count">{len(events)}</span></li>'
    for cat, evs in events_by_category.items():
        cid = re.sub(r'[^\w]', '_', cat)
        sidebar_items += f'<li class="cat-item" data-cat="{cid}"><span class="cat-name">{escape(cat)}</span><span class="cat-count">{len(evs)}</span></li>'

    sections_html = ''
    for cat, evs in events_by_category.items():
        cid = re.sub(r'[^\w]', '_', cat)
        cards_html = ''
        for ev in evs:
            color = type_colors.get(ev['type'], '#6b7280')
            oc = owner_colors.get(ev['owner'], '#6b7280')
            prop_html = ''
            if ev['properties']:
                prop_html = f'<div class="prop-block"><div class="prop-label">Properties</div><pre>{escape(ev["properties"])}</pre></div>'
            cmt_html = ''
            if ev['comments']:
                items = ''.join(f'<div class="cmt-item"><span class="cmt-author">{escape(c["author"])}</span>{escape(c["text"])}</div>' for c in ev['comments'])
                cmt_html = f'<details class="cmt-wrap"><summary>코멘트 {len(ev["comments"])}개</summary><div class="cmt-list">{items}</div></details>'
            search = escape(f"{ev['name']} {ev['description']} {ev['type']} {cat} {ev['owner']}".lower())
            owner_val = escape(ev['owner'].lower()) if ev['owner'] else ''
            cards_html += f'''<div class="card" data-search="{search}" data-cat="{cid}" data-owner="{owner_val}">
  <div class="card-top">
    <span class="owner-badge" style="background:{oc}">{escape(ev["owner"])}</span>
    <span class="type-badge" style="background:{color}">{escape(ev["type"])}</span>
    <span class="ev-name">{escape(ev["name"])}</span>
  </div>
  {f'<div class="ev-desc">{escape(ev["description"])}</div>' if ev["description"] else ''}
  {prop_html}{cmt_html}
</div>'''
        sections_html += f'<section id="sec_{cid}" class="cat-section" data-cat="{cid}"><h2 class="sec-title">{escape(cat)}</h2>{cards_html}</section>'

    # 퍼널 뷰 생성
    funnel_html = '<div class="funnel-container">'
    for idx, (cat, evs) in enumerate(events_by_category.items()):
        cid = re.sub(r'[^\w]', '_', cat)
        event_count = len(evs)
        route_count = sum(1 for e in evs if e['type'] == 'ROUTE')
        click_count = sum(1 for e in evs if e['type'] == 'CLICK')
        modal_count = sum(1 for e in evs if e['type'] == 'MODAL')
        event_type_count = sum(1 for e in evs if e['type'] == 'EVENT')
        view_count = sum(1 for e in evs if e['type'] == 'VIEW')

        type_pills = ''
        if route_count: type_pills += f'<span class="fpill" style="background:#3b82f6">ROUTE {route_count}</span>'
        if click_count: type_pills += f'<span class="fpill" style="background:#22c55e">CLICK {click_count}</span>'
        if modal_count: type_pills += f'<span class="fpill" style="background:#f97316">MODAL {modal_count}</span>'
        if event_type_count: type_pills += f'<span class="fpill" style="background:#a855f7">EVENT {event_type_count}</span>'
        if view_count: type_pills += f'<span class="fpill" style="background:#ec4899">VIEW {view_count}</span>'

        ev_names = ''.join(f'<div class="fev">{escape(e["name"])}</div>' for e in evs[:8])
        more = f'<div class="fev fev-more">+{event_count - 8}개 더</div>' if event_count > 8 else ''

        arrow = '<div class="funnel-arrow">→</div>' if idx < len(events_by_category) - 1 else ''

        funnel_html += f'''<div class="funnel-step" data-cat="{cid}">
  <div class="fstep-header">
    <div class="fstep-title">{escape(cat)}</div>
    <div class="fstep-count">{event_count}개</div>
  </div>
  <div class="fstep-types">{type_pills}</div>
  <div class="fstep-events">{ev_names}{more}</div>
</div>{arrow}'''
    funnel_html += '</div>'

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>이벤트 딕셔너리</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f0f13;color:#d4d4d8;display:flex;height:100vh;overflow:hidden}}
.sidebar{{width:260px;flex-shrink:0;background:#141418;border-right:1px solid #2a2a2f;display:flex;flex-direction:column;overflow:hidden}}
.sidebar-header{{padding:16px;border-bottom:1px solid #2a2a2f}}
.sidebar-header h1{{font-size:15px;font-weight:700;color:#fff;margin-bottom:10px}}
#search{{width:100%;padding:8px 10px;background:#0f0f13;border:1px solid #333;border-radius:6px;color:#d4d4d8;font-size:13px;outline:none}}
#search:focus{{border-color:#3b82f6}}
.cat-list{{flex:1;overflow-y:auto;padding:8px}}
.cat-item{{display:flex;align-items:center;padding:7px 10px;border-radius:6px;cursor:pointer;transition:background .15s;margin-bottom:2px}}
.cat-item:hover{{background:#1f1f24}}
.cat-item.active{{background:#1e3a5f}}
.cat-item.active .cat-name{{color:#93c5fd;font-weight:600}}
.cat-name{{flex:1;font-size:13px;color:#9ca3af}}
.cat-count{{font-size:11px;background:#2a2a2f;color:#6b7280;padding:1px 6px;border-radius:10px;min-width:22px;text-align:center}}
.cat-item.active .cat-count{{background:#2563eb;color:#fff}}
.main{{flex:1;overflow-y:auto;padding:24px}}
.cat-section{{margin-bottom:36px}}
.sec-title{{font-size:18px;font-weight:700;color:#fff;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #2a2a2f}}
.card{{background:#1a1a1f;border:1px solid #2a2a2f;border-radius:8px;padding:16px;margin-bottom:10px;transition:border-color .15s}}
.card:hover{{border-color:#3a3a4f}}
.card-top{{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}}
.type-badge{{font-size:11px;font-weight:700;color:#fff;padding:2px 8px;border-radius:4px;letter-spacing:.5px;flex-shrink:0}}
.owner-badge{{font-size:10px;font-weight:600;color:#fff;padding:2px 6px;border-radius:3px;flex-shrink:0}}
.ev-name{{font-size:15px;font-weight:600;color:#e4e4e7;font-family:"SFMono-Regular",Consolas,monospace;word-break:break-all}}
.ev-desc{{font-size:13px;color:#9ca3af;margin-bottom:10px;line-height:1.5}}
.prop-block{{margin-bottom:10px}}
.prop-label{{font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}
.prop-block pre{{background:#0f0f13;border:1px solid #2a2a2f;border-radius:5px;padding:10px;font-size:12px;color:#a3e635;white-space:pre-wrap;word-break:break-all;font-family:"SFMono-Regular",Consolas,monospace;line-height:1.5}}
.cmt-wrap summary{{font-size:12px;color:#6366f1;cursor:pointer;padding:2px 0}}
.cmt-list{{margin-top:8px;padding-left:12px;border-left:2px solid #2a2a2f}}
.cmt-item{{font-size:12px;color:#9ca3af;padding:4px 0;line-height:1.5}}
.cmt-author{{color:#a78bfa;font-weight:600;margin-right:6px}}
.filter-row{{display:flex;gap:4px;margin-top:10px}}
.filter-btn{{background:transparent;border:1px solid #333;color:#9ca3af;padding:3px 8px;border-radius:4px;font-size:11px;cursor:pointer}}
.filter-btn.active{{color:#fff;background:#2a2a2f}}
.view-toggle{{display:flex;gap:4px;margin-top:6px}}
.view-btn{{background:transparent;border:1px solid #333;color:#9ca3af;padding:3px 8px;border-radius:4px;font-size:11px;cursor:pointer;flex:1;text-align:center}}
.view-btn.active{{color:#fff;background:#2563eb;border-color:#2563eb}}
.funnel-container{{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;padding:8px}}
.funnel-step{{background:#1a1a1f;border:1px solid #2a2a2f;border-radius:8px;padding:14px;min-width:200px;max-width:260px;flex-shrink:0}}
.funnel-step:hover{{border-color:#3a3a4f}}
.fstep-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.fstep-title{{font-size:14px;font-weight:700;color:#fff}}
.fstep-count{{font-size:11px;background:#2a2a2f;color:#6b7280;padding:1px 6px;border-radius:10px}}
.fstep-types{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px}}
.fpill{{font-size:10px;font-weight:600;color:#fff;padding:1px 6px;border-radius:3px}}
.fstep-events{{display:flex;flex-direction:column;gap:2px}}
.fev{{font-size:11px;color:#9ca3af;font-family:"SFMono-Regular",Consolas,monospace;padding:2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.fev-more{{color:#6366f1;font-style:italic}}
.funnel-arrow{{color:#4b5563;font-size:24px;display:flex;align-items:center;padding:0 2px;flex-shrink:0}}
.hidden{{display:none!important}}
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:#0f0f13}}
::-webkit-scrollbar-thumb{{background:#333;border-radius:3px}}
</style>
</head>
<body>
<nav class="sidebar">
  <div class="sidebar-header">
    <h1>이벤트 딕셔너리</h1>
    <input id="search" type="text" placeholder="이벤트명/설명 검색...">
    <div class="filter-row">
      <button class="filter-btn active" data-owner="all">전체</button>
      <button class="filter-btn" data-owner="클라이언트" style="border-color:#0ea5e9">클라이언트</button>
      <button class="filter-btn" data-owner="서버" style="border-color:#f59e0b">서버</button>
    </div>
    <div class="view-toggle">
      <button class="view-btn active" data-view="list">목록</button>
      <button class="view-btn" data-view="funnel">퍼널</button>
    </div>
  </div>
  <ul class="cat-list">{sidebar_items}</ul>
</nav>
<main class="main" id="main">
  <div id="list-view">{sections_html}</div>
  <div id="funnel-view" class="hidden">{funnel_html}</div>
</main>
<script>
const cards=document.querySelectorAll('.card');
const sections=document.querySelectorAll('.cat-section');
const catItems=document.querySelectorAll('.cat-item');
let activeCat='all';

function show(cat){{
  activeCat=cat;
  catItems.forEach(i=>i.classList.toggle('active',i.dataset.cat===cat));
  const q=document.getElementById('search').value.toLowerCase();
  sections.forEach(s=>{{
    if(cat!=='all'&&s.dataset.cat!==cat){{s.classList.add('hidden');return;}}
    s.classList.remove('hidden');
    let any=false;
    s.querySelectorAll('.card').forEach(c=>{{
      const ownerOk=activeOwner==='all'||c.dataset.owner===activeOwner.toLowerCase();
      const ok=ownerOk&&(!q||c.dataset.search.includes(q));
      c.classList.toggle('hidden',!ok);
      if(ok)any=true;
    }});
    s.classList.toggle('hidden',!any);
  }});
}}

catItems.forEach(i=>i.addEventListener('click',()=>{{
  show(i.dataset.cat);
  document.getElementById('main').scrollTop=0;
  if(i.dataset.cat!=='all'){{
    const sec=document.getElementById('sec_'+i.dataset.cat);
    if(sec)setTimeout(()=>sec.scrollIntoView({{behavior:'smooth',block:'start'}}),50);
  }}
}}));

document.getElementById('search').addEventListener('input',()=>show(activeCat));

// Owner filter
let activeOwner='all';
document.querySelectorAll('.filter-btn').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('.filter-btn').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  activeOwner=b.dataset.owner;
  show(activeCat);
}}));

// View toggle
document.querySelectorAll('.view-btn').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('.view-btn').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  const v=b.dataset.view;
  document.getElementById('list-view').classList.toggle('hidden',v!=='list');
  document.getElementById('funnel-view').classList.toggle('hidden',v!=='funnel');
}}));

// Funnel step click → switch to list view for that category
document.querySelectorAll('.funnel-step').forEach(s=>s.addEventListener('click',()=>{{
  const cat=s.dataset.cat;
  document.querySelectorAll('.view-btn').forEach(x=>x.classList.remove('active'));
  document.querySelector('.view-btn[data-view="list"]').classList.add('active');
  document.getElementById('list-view').classList.remove('hidden');
  document.getElementById('funnel-view').classList.add('hidden');
  show(cat);
  const sec=document.getElementById('sec_'+cat);
  if(sec)setTimeout(()=>sec.scrollIntoView({{behavior:'smooth',block:'start'}}),50);
}}));
</script>
</body>
</html>'''

if __name__ == "__main__":
    print("시트 데이터 읽는 중...")
    data = get_sheet_data(
        os.path.expanduser('~/.config/gcloud/sheets-service-account.json'),
        '1-v4gyRD9yzzNDqy5NwjDj02uJQZItM-R8EGE88-1diQ',
        1531837284
    )
    if data:
        print("파싱 중...")
        events = parse_data(data)
        print(f"이벤트 {len(events)}개 파싱 완료")
        html = generate_html(events)
        with open('/tmp/event-dictionary.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("완료: /tmp/event-dictionary.html")
    else:
        print("데이터 읽기 실패")
