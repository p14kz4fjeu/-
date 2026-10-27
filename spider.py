#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高新企业政策定向爬虫
- 目标：43个科技/工信主管部门官网
- 策略：首页智能发现栏目 → 列表页关键词过滤 → 自动翻页
- 输出：policies.json
"""
import json, os, re, time, random, ssl
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# ============ 配置 ============
KEYWORDS = ['高新技术企业', '高新认定', '高企认定', '高新技术企业认定', '高新企业', '高企申报', '高新技术企业申报', '高企复审']
SKIP_WORDS = ['党建', '人事', '预决算', '财务', '采购', '招标', '邮箱', '登录', '注册']
COLUMN_KEYWORDS = ['通知', '公告', '政策', '文件', '高新', '公示', '政务公开', '信息公开', '申报']
MAX_PAGES_PER_SITE = 5
UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]
ssl._create_default_https_context = ssl._create_unverified_context

# ============ 监测站点（来自xlsx） ============
SITES = [
    {'province':'深圳','dept':'深圳市科创局','url':'http://stic.sz.gov.cn'},
    {'province':'青岛','dept':'青岛市科技局','url':'http://qdstc.qingdao.gov.cn'},
    {'province':'宁波','dept':'宁波市科技局','url':'http://kjj.ningbo.gov.cn'},
    {'province':'厦门','dept':'厦门市科技局','url':'http://kjj.xm.gov.cn'},
    {'province':'大连','dept':'大连市科技局','url':'http://www.kjj.dl.gov.cn'},
    {'province':'北京','dept':'北京市科委','url':'https://kw.beijing.gov.cn'},
    {'province':'天津','dept':'天津市科技局','url':'https://kxjs.tj.gov.cn'},
    {'province':'河北','dept':'河北省科技厅','url':'https://kjt.hebei.gov.cn'},
    {'province':'山西','dept':'山西省科技厅','url':'http://kjt.shanxi.gov.cn'},
    {'province':'内蒙古','dept':'内蒙古科技厅','url':'https://kjt.nmg.gov.cn'},
    {'province':'辽宁','dept':'辽宁省科技厅','url':'https://kjt.ln.gov.cn'},
    {'province':'吉林','dept':'吉林省科技厅','url':'http://kjt.jl.gov.cn'},
    {'province':'黑龙江','dept':'黑龙江科技厅','url':'http://kjt.hlj.gov.cn'},
    {'province':'上海','dept':'上海科委','url':'https://stcsm.sh.gov.cn'},
    {'province':'江苏','dept':'江苏省科技厅','url':'https://kjt.jiangsu.gov.cn'},
    {'province':'浙江','dept':'浙江省科技厅','url':'https://kjt.zj.gov.cn'},
    {'province':'安徽','dept':'安徽省科技厅','url':'https://kjt.ah.gov.cn'},
    {'province':'福建','dept':'福建省科技厅','url':'http://kjt.fj.gov.cn'},
    {'province':'江西','dept':'江西省科技厅','url':'https://kjt.jiangxi.gov.cn'},
    {'province':'山东','dept':'山东省科技厅','url':'http://kjt.shandong.gov.cn'},
    {'province':'河南','dept':'河南省科技厅','url':'https://kjt.henan.gov.cn'},
    {'province':'湖北','dept':'湖北省科技厅','url':'https://kjt.hubei.gov.cn'},
    {'province':'湖南','dept':'湖南省科技厅','url':'https://kjt.hunan.gov.cn'},
    {'province':'广东','dept':'广东省科技厅','url':'http://gdstc.gd.gov.cn'},
    {'province':'广西','dept':'广西科技厅','url':'http://kjt.gxzf.gov.cn'},
    {'province':'海南','dept':'海南省科技厅','url':'https://dost.hainan.gov.cn'},
    {'province':'重庆','dept':'重庆市科技局','url':'http://kjj.cq.gov.cn'},
    {'province':'四川','dept':'四川省科技厅','url':'https://kjt.sc.gov.cn'},
    {'province':'贵州','dept':'贵州省科技厅','url':'https://kjt.guizhou.gov.cn'},
    {'province':'云南','dept':'云南省科技厅','url':'https://kjt.yn.gov.cn'},
    {'province':'西藏','dept':'西藏科技厅','url':'http://sti.xizang.gov.cn'},
    {'province':'陕西','dept':'陕西省科技厅','url':'http://kjt.shaanxi.gov.cn'},
    {'province':'甘肃','dept':'甘肃省科技厅','url':'https://kjt.gansu.gov.cn'},
    {'province':'青海','dept':'青海省科技厅','url':'https://kjt.qinghai.gov.cn'},
    {'province':'宁夏','dept':'宁夏科技厅','url':'https://kjt.nx.gov.cn'},
    {'province':'新疆','dept':'新疆科技厅','url':'https://kjt.xinjiang.gov.cn'},
    {'province':'全国','dept':'高新认定工作网','url':'http://www.innocom.gov.cn'},
    {'province':'全国','dept':'科技部火炬中心','url':'http://www.chinatorch.gov.cn'},
]

# ============ 工具函数 ============
def get_session():
    s = requests.Session()
    s.headers.update({'User-Agent': random.choice(UA_POOL)})
    s.verify = False
    return s

def fetch(sess, url, timeout=15, retry=2):
    for i in range(retry + 1):
        try:
            time.sleep(random.uniform(1, 3))
            r = sess.get(url, timeout=timeout, allow_redirects=True)
            if not r.encoding or r.encoding.lower() == 'iso-8859-1':
                r.encoding = r.apparent_encoding or 'utf-8'
            return r.text
        except Exception as e:
            print(f'    重试{i+1}: {url} -> {e}')
            time.sleep(2)
    return ''

def match_keyword(title):
    return any(kw in title for kw in KEYWORDS)

def should_skip(text):
    return any(w in text for w in SKIP_WORDS)

def extract_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if not text or len(text) < 6:
            continue
        if href.startswith('javascript') or href.startswith('#') or href.startswith('mailto'):
            continue
        full_url = urljoin(base_url, href)
        results.append({'title': text, 'url': full_url})
    return results

def find_columns(home_html, base_url):
    links = extract_links(home_html, base_url)
    columns = []
    seen = set()
    for link in links:
        text = link['title']
        if should_skip(text):
            continue
        if any(kw in text for kw in COLUMN_KEYWORDS):
            key = link['url']
            if key not in seen:
                seen.add(key)
                columns.append(link)
    return columns[:8]

def find_next_page(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if text in ['下一页', '下页', '>', 'Next', 'next', '»']:
            return urljoin(base_url, a['href'])
    return None

def extract_date(text):
    m = re.search(r'(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})', text)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    return ''

# ============ 主流程 ============
def crawl_site(sess, site, seen_urls):
    province = site['province']
    base = site['url']
    print(f'\n[{province}] {site["dept"]} {base}')
    found = []

    home = fetch(sess, base)
    if not home:
        print('  首页访问失败')
        return found

    columns = find_columns(home, base)
    print(f'  发现 {len(columns)} 个相关栏目')

    visited_pages = set()
    for col in columns[:5]:
        col_url = col['url']
        page = 1
        current_url = col_url
        while current_url and page <= MAX_PAGES_PER_SITE:
            if current_url in visited_pages:
                break
            visited_pages.add(current_url)

            html = fetch(sess, current_url)
            if not html:
                break

            links = extract_links(html, current_url)
            for link in links:
                title = link['title']
                url = link['url']
                if not match_keyword(title):
                    continue
                if url in seen_urls:
                    continue
                if should_skip(title):
                    continue
                date = extract_date(title)
                found.append({
                    'project': 'gzrd',
                    'province': province,
                    'title': title,
                    'url': url,
                    'date': date,
                    'source': site['dept'],
                    'found_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                })
                seen_urls.add(url)
                print(f'  ✓ {title[:50]}')

            next_url = find_next_page(html, current_url)
            if not next_url or next_url == current_url:
                break
            current_url = next_url
            page += 1

    return found

def main():
    print(f'=== 开始爬取 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    existing_path = 'policies.json'
    if os.path.exists(existing_path):
        with open(existing_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    else:
        existing = {'last_updated': '', 'policies': []}

    seen_urls = {p['url'] for p in existing['policies']}
    sess = get_session()

    all_new = []
    for site in SITES:
        try:
            results = crawl_site(sess, site, seen_urls)
            all_new.extend(results)
        except Exception as e:
            print(f'  [错误] {site["dept"]}: {e}')
            continue

    existing['policies'] = all_new + existing['policies']
    existing['policies'] = existing['policies'][:2000]
    existing['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    with open(existing_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f'\n=== 完成: 新增 {len(all_new)} 条, 总计 {len(existing["policies"])} 条 ===')

if __name__ == '__main__':
    main()
#（注：内容由AI生成）
