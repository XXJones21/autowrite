"""Public job-board clients and normalizers. Every posting becomes one flat dict."""
import datetime
import html
import json
import re
import urllib.request

from filters import location_ok, parse_pay, title_ok

UA = 'autowrite-job-search/0.1'


class Http:
    def __init__(self, timeout=30):
        self.timeout = timeout

    def _open(self, req):
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode('utf-8'))

    def get_json(self, url):
        return self._open(urllib.request.Request(
            url, headers={'User-Agent': UA, 'Accept': 'application/json'}))

    def post_json(self, url, body):
        return self._open(urllib.request.Request(
            url, data=json.dumps(body).encode('utf-8'), method='POST',
            headers={'User-Agent': UA, 'Accept': 'application/json',
                     'Content-Type': 'application/json'}))


def html_to_text(s):
    s = html.unescape(html.unescape(s or ''))
    s = re.sub(r'<(br|/p|/li|/h\d|/div)[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '\n- ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'[ \t\xa0]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n\n', s).strip()


def _posting(**kw):
    base = {'id': '', 'board': '', 'company': '', 'title': '', 'team': '', 'locations': [],
            'remote': False, 'pay_min': None, 'pay_max': None, 'pay_text': '',
            'posted_date': None, 'url': '', 'description_text': ''}
    base.update(kw)
    return base


def _pay_from_text(text):
    pay = parse_pay(text)
    if not pay:
        return None, None, ''
    return pay[0], pay[1], '$%s - $%s' % (format(pay[0], ','), format(pay[1], ','))


def normalize_ashby(data, company, org):
    out = []
    for j in data.get('jobs', []):
        if j.get('isListed') is False:
            continue
        locs = [j.get('location') or '']
        locs += [s.get('location') or '' for s in (j.get('secondaryLocations') or [])]
        addr = (j.get('address') or {}).get('postalAddress') or {}
        joined = ', '.join(x for x in (addr.get('addressLocality'), addr.get('addressRegion'),
                                       addr.get('addressCountry')) if x)
        if joined:
            locs.append(joined)
        desc = j.get('descriptionPlain') or html_to_text(j.get('descriptionHtml'))
        comp = j.get('compensation') or {}
        salary = [c for c in comp.get('summaryComponents') or []
                  if c.get('compensationType') == 'Salary'
                  and c.get('interval') in (None, '1 YEAR')
                  and c.get('currencyCode') in (None, 'USD') and c.get('maxValue')]
        if salary:
            lo, hi = salary[0].get('minValue'), salary[0]['maxValue']
            pay_min, pay_max = (int(lo) if lo else None), int(hi)
            pay_text = (comp.get('scrapeableCompensationSalarySummary')
                        or comp.get('compensationTierSummary') or '')
        else:
            pay_min, pay_max, pay_text = _pay_from_text(desc)
        out.append(_posting(
            id='ashby:%s:%s' % (org, j['id']), board='ashby', company=company,
            title=j.get('title', ''), team=j.get('team') or j.get('department') or '',
            locations=[x for x in locs if x],
            remote=bool(j.get('isRemote')) or j.get('workplaceType') == 'Remote',
            pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
            posted_date=(j.get('publishedAt') or '')[:10] or None,
            url=j.get('jobUrl', ''), description_text=desc))
    return out


def normalize_greenhouse(data, company, token):
    out = []
    for j in data.get('jobs', []):
        desc = html_to_text(j.get('content'))
        locs = [(j.get('location') or {}).get('name') or '']
        locs += [o.get('location') or o.get('name') or '' for o in (j.get('offices') or [])]
        depts = j.get('departments') or []
        pay_min, pay_max, pay_text = _pay_from_text(desc)
        out.append(_posting(
            id='greenhouse:%s:%s' % (token, j['id']), board='greenhouse', company=company,
            title=j.get('title', ''), team=depts[0].get('name', '') if depts else '',
            locations=[x for x in locs if x],
            remote='remote' in ' '.join(locs).lower(),
            pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
            posted_date=(j.get('first_published') or j.get('updated_at') or '')[:10] or None,
            url=j.get('absolute_url', ''), description_text=desc))
    return out


def normalize_lever(data, company, handle):
    out = []
    for j in data or []:
        cats = j.get('categories') or {}
        locs = cats.get('allLocations') or [cats.get('location') or '']
        lists = '\n'.join('%s\n%s' % (x.get('text', ''), html_to_text(x.get('content')))
                          for x in j.get('lists') or [])
        desc = '\n\n'.join(x for x in (j.get('descriptionPlain') or '', lists,
                                       j.get('additionalPlain') or '') if x)
        sal = j.get('salaryRange') or {}
        if (sal.get('max') and sal.get('interval') in (None, 'per-year-salary')
                and sal.get('currency') in (None, 'USD')):
            pay_min, pay_max = (int(sal['min']) if sal.get('min') else None), int(sal['max'])
            pay_text = '$%s - $%s' % (format(pay_min or 0, ','), format(pay_max, ','))
        else:
            pay_min, pay_max, pay_text = _pay_from_text(desc)
        created = j.get('createdAt')
        posted = (datetime.datetime.fromtimestamp(int(created) / 1000, datetime.timezone.utc)
                  .strftime('%Y-%m-%d') if created else None)
        out.append(_posting(
            id='lever:%s:%s' % (handle, j['id']), board='lever', company=company,
            title=j.get('text', ''), team=cats.get('team') or '',
            locations=[x for x in locs if x], remote=(j.get('workplaceType') == 'remote'),
            pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
            posted_date=posted, url=j.get('hostedUrl', ''), description_text=desc))
    return out


def normalize_workday(detail, company, tenant, external_path):
    info = detail.get('jobPostingInfo') or {}
    desc = html_to_text(info.get('jobDescription'))
    locs = [info.get('location') or ''] + list(info.get('additionalLocations') or [])
    pay_min, pay_max, pay_text = _pay_from_text(desc)
    return _posting(
        id='workday:%s:%s' % (tenant, external_path), board='workday', company=company,
        title=info.get('title', ''), locations=[x for x in locs if x],
        remote='remote' in ((info.get('remoteType') or '') + ' ' + ' '.join(locs)).lower(),
        pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
        posted_date=info.get('startDate'), url=info.get('externalUrl', ''),
        description_text=desc)


def board_prefix(entry):
    if entry['board'] == 'workday':
        return 'workday:%s:' % entry['tenant']
    return '%s:%s:' % (entry['board'], entry['board_id'])


def workday_base(entry):
    return 'https://%s/wday/cxs/%s/%s' % (entry['host'], entry['tenant'], entry['site'])


def _fetch_workday(entry, http, seen_ids, config):
    base = workday_base(entry)
    titles = config.get('titles') or {}
    terms = entry.get('search_terms') or titles.get('include') or ['']
    keep = (config.get('locations') or {}).get('keep') or []
    cap = (config.get('workday') or {}).get('detail_cap', 40)
    items = {}
    for term in terms:
        offset = 0
        while offset < 100:
            page = http.post_json(base + '/jobs', {'appliedFacets': {}, 'limit': 20,
                                                   'offset': offset, 'searchText': term})
            rows = page.get('jobPostings') or []
            for r in rows:
                if r.get('externalPath'):
                    items.setdefault(r['externalPath'], r)
            if len(rows) < 20:
                break
            offset += 20
    tenant = entry['tenant']
    live = {'workday:%s:%s' % (tenant, path) for path in items}
    posts = []
    for path, r in items.items():
        pid = 'workday:%s:%s' % (tenant, path)
        if pid in seen_ids or len(posts) >= cap:
            continue
        if not title_ok(r.get('title'), titles.get('include'), titles.get('exclude'),
                        titles.get('qualify')):
            continue
        loc_text = r.get('locationsText') or ''
        if (loc_text and not re.match(r'^\d+ Locations$', loc_text)
                and not location_ok([loc_text], False, keep)):
            continue
        posts.append(normalize_workday(http.get_json(base + path), entry['name'], tenant, path))
    return live, posts


def fetch_board(entry, http, seen_ids, config):
    """Return (live_ids, postings). live_ids covers every listed posting, before filters."""
    board, name = entry.get('board'), entry.get('name')
    if board == 'ashby':
        data = http.get_json('https://api.ashbyhq.com/posting-api/job-board/%s'
                             '?includeCompensation=true' % entry['board_id'])
        posts = normalize_ashby(data, name, entry['board_id'])
    elif board == 'greenhouse':
        data = http.get_json('https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true'
                             % entry['board_id'])
        posts = normalize_greenhouse(data, name, entry['board_id'])
    elif board == 'lever':
        data = http.get_json('https://api.lever.co/v0/postings/%s?mode=json' % entry['board_id'])
        posts = normalize_lever(data, name, entry['board_id'])
    elif board == 'workday':
        return _fetch_workday(entry, http, seen_ids, config)
    else:
        raise ValueError('unsupported board: %s' % board)
    return {p['id'] for p in posts}, posts
