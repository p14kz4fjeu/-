#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全国项目申报政策爬虫（全项目版）
- 目标：43个科技/工信主管部门官网
- 策略：首页智能发现栏目 → 列表页关键词初筛 → 翻页（最多50页）
- 输出：policies.json
"""
import json, os, re, time, random, ssl
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# ============ 项目关键词映射 ============
PROJECT_KEYWORDS = {
    'gzrd':     ['高新技术企业', '高新认定', '高企认定', '高新技术企业认定', '高新企业', '高企申报', '高新技术企业申报', '高企复审'],
    'zdxjrd':   ['重点小巨人', '重点“小巨人”', '重点"小巨人"', '重点小巨人申报', '重点小巨人支持', '重点小巨人复核', '专精特新重点小巨人'],
    'zjtxjr':   ['专精特新“小巨人”', '专精特新"小巨人"', '专精特新小巨人', '专精特新小巨人申报', '专精特新小巨人复核', '优质中小企业梯度培育'],
    'zjtx':     ['专精特新中小企业', '专精特新企业申报', '专精特新培育', '专精特新中小企业评价'],
    'cxxzx':    ['创新型中小企业', '创新型中小企业评价', '创新型中小企业申报', '创新型中小企业评价办法'],
    'kjzzx':    ['科技型中小企业', '科技型中小企业评价', '科技型中小企业入库', '科技型中小企业评价办法', '国科发政〔2017〕115号'],
    'zgcgx':    ['中关村高新技术企业', '中关村高企备案', '中关村示范区高新技术'],
    'sqjszx':   ['省级企业技术中心', '企业技术中心申报', '省级企业技术中心管理', '企业技术中心评价'],
    'bjxjsxcp': ['北京市新技术新产品', '新技术新产品新服务认定', '北京新技术新产品申报'],
    'rjcp':     ['软件产品评估', '软件产品认定', '软件产品登记', '软件产品检测', '首版次软件'],
    'rjqy':     ['国家鼓励的软件企业', '软件企业认定', '软件企业评估', '软件企业清单', '软件产业协会'],
    'jshtdj':   ['技术合同认定登记', '技术合同登记备案', '技术合同认定登记管理', '技术交易减免税'],
    'jjsk':     ['研发费用加计扣除', '研发支出辅助账', '研发加计扣除备查', '加计扣除留存备查'],
}

SKIP_WORDS = ['党建', '人事', '预决算', '财务', '采购公告', '招标公告', '邮箱', '登录', '注册', '招聘', '意见征集', '访谈', '直播', '视频', '图解']
# 扩大栏目识别：所有可能包含政策通知的栏目都抓
COLUMN_KEYWORDS = ['通知', '公告', '政策', '文件', '高新', '公示', '政务公开', '信息公开', '申报', '认定', '政策动态', '信息公告', '信息公示', '解读', '要闻动态', '政务服务', '通知公告', '政策文件', '政策解读', '政府信息公开', '业务', '办事', '公告公示', '通知公示', '最新', '新闻', '动态', '资讯']
MAX_PAGES_PER_COLUMN = 50
UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]
ssl._create_default_https_context = ssl._create_unverified_context

# ============ 监测站点 ============
SITES = [
    # 计划单列市 - 科技局
    {'province':'深圳','dept':'深圳市科创局','url':'http://stic.sz.gov.cn'},
    {'province':'青岛','dept':'青岛市科技局','url':'http://qdstc.qingdao.gov.cn'},
    {'province':'宁波','dept':'宁波市科技局','url':'http://kjj.ningbo.gov.cn'},
    {'province':'厦门','dept':'厦门市科技局','url':'http://kjj.xm.gov.cn'},
    {'province':'大连','dept':'大连市科技局','url':'http://www.kjj.dl.gov.cn'},
    # 计划单列市 - 工信局
    {'province':'深圳','dept':'深圳市工信局','url':'http://gxj.sz.gov.cn'},
    {'province':'青岛','dept':'青岛市工信局','url':'http://gxj.qingdao.gov.cn'},
    {'province':'宁波','dept':'宁波市经信局','url':'http://jxj.ningbo.gov.cn'},
    {'province':'厦门','dept':'厦门市工信局','url':'http://gxj.xm.gov.cn'},
    {'province':'大连','dept':'大连市工信局','url':'http://gxj.dl.gov.cn'},
    # 各省 - 科技厅
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
    {'province':'新疆兵团','dept':'新疆兵团科技局','url':'http://kjj.xjbt.gov.cn'},
    # 各省 - 工信厅
    {'province':'北京','dept':'北京市经信局','url':'https://jxj.beijing.gov.cn'},
    {'province':'天津','dept':'天津市工信局','url':'https://gyxxh.tj.gov.cn'},
    {'province':'河北','dept':'河北省工信厅','url':'https://gxt.hebei.gov.cn'},
    {'province':'山西','dept':'山西省工信厅','url':'http://gxt.shanxi.gov.cn'},
    {'province':'内蒙古','dept':'内蒙古工信厅','url':'http://gxt.nmg.gov.cn'},
    {'province':'辽宁','dept':'辽宁省工信厅','url':'https://gxt.ln.gov.cn'},
    {'province':'吉林','dept':'吉林省工信厅','url':'http://gxt.jl.gov.cn'},
    {'province':'黑龙江','dept':'黑龙江工信厅','url':'http://gxt.hlj.gov.cn'},
    {'province':'上海','dept':'上海市经信委','url':'https://www.sheitc.sh.gov.cn'},
    {'province':'江苏','dept':'江苏省工信厅','url':'http://gxt.jiangsu.gov.cn'},
    {'province':'浙江','dept':'浙江省经信厅','url':'https://jxt.zj.gov.cn'},
    {'province':'安徽','dept':'安徽省经信厅','url':'https://jx.ah.gov.cn'},
    {'province':'福建','dept':'福建省工信厅','url':'http://gxt.fujian.gov.cn'},
    {'province':'江西','dept':'江西省工信厅','url':'http://gxt.jiangxi.gov.cn'},
    {'province':'山东','dept':'山东省工信厅','url':'http://gxt.shandong.gov.cn'},
    {'province':'河南','dept':'河南省工信厅','url':'https://gxt.henan.gov.cn'},
    {'province':'湖北','dept':'湖北省经信厅','url':'https://jxt.hubei.gov.cn'},
    {'province':'湖南','dept':'湖南省工信厅','url':'https://gxt.hunan.gov.cn'},
    {'province':'广东','dept':'广东省工信厅','url':'https://gdii.gd.gov.cn'},
    {'province':'广西','dept':'广西工信厅','url':'http://gxt.gxzf.gov.cn'},
    {'province':'海南','dept':'海南省工信厅','url':'https://iitb.hainan.gov.cn'},
    {'province':'重庆','dept':'重庆市经信委','url':'https://jjxxw.cq.gov.cn'},
    {'province':'四川','dept':'四川省经信厅','url':'https://jxt.sc.gov.cn'},
    {'province':'贵州','dept':'贵州省工信厅','url':'http://gxt.guizhou.gov.cn'},
    {'province':'云南','dept':'云南省工信厅','url':'http://gxt.yn.gov.cn'},
    {'province':'西藏','dept':'西藏工信厅','url':'http://jxt.xizang.gov.cn'},
    {'province':'陕西','dept':'陕西省工信厅','url':'https://gxt.shaanxi.gov.cn'},
    {'province':'甘肃','dept':'甘肃省工信厅','url':'http://gxt.gansu.gov.cn'},
    {'province':'青海','dept':'青海省工信厅','url':'http://gxt.qinghai.gov.cn'},
    {'province':'宁夏','dept':'宁夏工信厅','url':'http://gxt.nx.gov.cn'},
    {'province':'新疆','dept':'新疆工信厅','url':'http://gxt.xinjiang.gov.cn'},
    {'province':'新疆兵团','dept':'新疆兵团工信局','url':'http://gxj.xjbt.gov.cn'},
    # 区级
    {'province':'北京','dept':'昌平区科创平台','url':'https://www.cpkjcg.cn/nindex/index/index'},
    # 国家级平台
    {'province':'全国','dept':'高新认定工作网','url':'http://www.innocom.gov.cn'},
    {'province':'全国','dept':'优质中小企业平台','url':'https://zjtx.miit.gov.cn'},
    {'province':'全国','dept':'科技部火炬中心','url':'http://www.chinatorch.gov.cn'},
    {'province':'全国','dept':'工信部中小企业局','url':'https://www.miit.gov.cn/jgsj/qyj/index.html'},
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
            time.sleep(random.uniform(1, 2))
            r = sess.get(url, timeout=timeout, allow_redirects=True)
            if not r.encoding or r.encoding.lower() == 'iso-8859-1':
                r.encoding = r.apparent_encoding or 'utf-8'
            return r.text
        except Exception as e:
            print(f'    重试{i+1}: {url[:60]} -> {e}')
            time.sleep(2)
    return ''

def match_projects(title):
    """返回命中的所有项目ID列表"""
    matched = []
    for pid, keywords in PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                matched.append(pid)
                break
    return matched

def should_skip(text):
    return any(w in text for w in SKIP_WORDS)

def extract_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if not text or len(text) < 2:
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
    # 判断URL是否像栏目页（目录/list/index结尾），优先抓
    def is_column_url(url):
        path = url.lower()
        return any(k in path for k in ['/list', '/index', '/tzgg', '/zcwj', '/zcfg', '/zwgk', '/zfxxgk', '/gfxwj', '/lzyj', '/jdhy', '/govxxx', '/channel', '/column'])
    scored = []
    for link in links:
        text = link['title']
        if should_skip(text):
            continue
        if not any(kw in text for kw in COLUMN_KEYWORDS):
            continue
        # 栏目页URL高分，具体文章页低分
        score = 10 if is_column_url(link['url']) else 1
        # 短文本（栏目名）再加2分
        if len(text) <= 8:
            score += 2
        scored.append((score, link))
    scored.sort(key=lambda x: -x[0])
    for score, link in scored[:20]:  # 最多抓20个栏目
        key = link['url']
        if key not in seen:
            seen.add(key)
            columns.append(link)
    return columns

def find_next_page(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if text in ['下一页', '下页', '>', 'Next', 'next', '»', '下一页>']:
            return urljoin(base_url, a['href'])
    return None

def detect_js_pages(html, base_url):
    """识别JS分页模式，如 createPageHTML('page_div', 50, 1, 'list', 'shtml', 1000)
    返回从当前页之后的所有页URL列表"""
    m = re.search(r"createPageHTML\(['\"][^'\"]+['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", html)
    if not m:
        return []
    total = int(m.group(1))
    current = int(m.group(2))
    prefix = m.group(3)
    ext = m.group(4)
    # base_url 形如 .../list.shtml，要替换成 .../list_N.shtml
    # 当前页可能是 list.shtml 或 list_1.shtml
    base_dir = base_url.rsplit('/', 1)[0] + '/'
    pages = []
    for p in range(current + 1, total + 1):
        pages.append(f'{base_dir}{prefix}_{p}.{ext}')
    return pages[:MAX_PAGES_PER_COLUMN]

def extract_date(text):
    m = re.search(r'(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})', text)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    return ''

# ============ 主流程 ============
def crawl_site(sess, site, seen_urls):
    province = site['province']
    base = site['url']
    dept = site['dept']
    result = {'dept': dept, 'province': province, 'url': base, 'status': 'ok', 'columns_found': 0, 'pages_crawled': 0, 'items_found': 0}
    found = []

    print(f'\n[{province}] {dept}')
    home = fetch(sess, base)
    if not home:
        print('  ❌ 首页访问失败')
        result['status'] = 'failed_home'
        return found, result

    columns = find_columns(home, base)
    result['columns_found'] = len(columns)
    print(f'  发现 {len(columns)} 个相关栏目')

    visited_pages = set()
    total_pages = 0
    for col in columns[:20]:
        # 先访问第1页
        page_urls = [col['url']]
        first_html = fetch(sess, col['url'])
        if not first_html:
            continue
        # 检查是否有JS分页，如果有，构造后续所有页URL
        js_pages = detect_js_pages(first_html, col['url'])
        if js_pages:
            page_urls.extend(js_pages)
            print(f'  检测到JS分页，共{len(js_pages)+1}页')

        for idx, current_url in enumerate(page_urls):
            if current_url in visited_pages:
                continue
            visited_pages.add(current_url)
            total_pages += 1

            html = first_html if idx == 0 else fetch(sess, current_url)
            if not html:
                continue

            links = extract_links(html, current_url)
            for link in links:
                title = link['title']
                url = link['url']
                if should_skip(title):
                    continue
                pids = match_projects(title)
                if not pids:
                    continue
                if url in seen_urls:
                    continue
                date = extract_date(title)
                for pid in pids:
                    found.append({
                        'project': pid,
                        'province': province,
                        'title': title,
                        'url': url,
                        'date': date,
                        'source': dept,
                        'found_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    })
                    seen_urls.add(url)
                print(f'  ✓ [{",".join(pids)}] {title[:45]}')

            # 如果没有JS分页，用传统"下一页"逻辑
            if idx == 0 and not js_pages:
                next_url = find_next_page(html, current_url)
                page_num = 2
                while next_url and page_num <= MAX_PAGES_PER_COLUMN:
                    if next_url in visited_pages:
                        break
                    visited_pages.add(next_url)
                    total_pages += 1
                    nhtml = fetch(sess, next_url)
                    if not nhtml:
                        break
                    nlinks = extract_links(nhtml, next_url)
                    for link in nlinks:
                        title = link['title']
                        url = link['url']
                        if should_skip(title):
                            continue
                        pids = match_projects(title)
                        if not pids:
                            continue
                        if url in seen_urls:
                            continue
                        date = extract_date(title)
                        for pid in pids:
                            found.append({
                                'project': pid,
                                'province': province,
                                'title': title,
                                'url': url,
                                'date': date,
                                'source': dept,
                                'found_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            })
                            seen_urls.add(url)
                        print(f'  ✓ [{",".join(pids)}] {title[:45]}')
                    next_url = find_next_page(nhtml, next_url)
                    page_num += 1

    result['pages_crawled'] = total_pages
    result['items_found'] = len(found)
    print(f'  ✅ 完成: 翻了{total_pages}页, 抓到{len(found)}条')
    return found, result

def main():
    start_time = datetime.now()
    print(f'=== 开始爬取 {start_time.strftime("%Y-%m-%d %H:%M")} ===')
    print(f'=== 共 {len(SITES)} 个监测站点 ===')
    existing_path = 'policies.json'
    if os.path.exists(existing_path):
        with open(existing_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    else:
        existing = {'last_updated': '', 'policies': []}

    seen_urls = {p['url'] for p in existing['policies']}
    sess = get_session()

    all_new = []
    crawl_log = []
    for i, site in enumerate(SITES, 1):
        print(f'\n----- [{i}/{len(SITES)}] -----')
        try:
            results, log = crawl_site(sess, site, seen_urls)
            all_new.extend(results)
            crawl_log.append(log)
        except Exception as e:
            print(f'  ❌ [异常] {site["dept"]}: {e}')
            crawl_log.append({'dept': site['dept'], 'province': site['province'], 'status': 'error', 'error': str(e)})
            continue

    existing['policies'] = all_new + existing['policies']
    existing['policies'] = existing['policies'][:5000]
    existing['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    with open(existing_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    # ====== 输出完整汇总表 ======
    elapsed = (datetime.now() - start_time).seconds
    print('\n' + '='*70)
    print(f'  爬取完成! 用时 {elapsed//60}分{elapsed%60}秒')
    print(f'  总站点: {len(SITES)} | 成功: {sum(1 for x in crawl_log if x["status"]=="ok")} | 失败: {sum(1 for x in crawl_log if x["status"]!="ok")}')
    print(f'  新增政策: {len(all_new)} 条 | 累计: {len(existing["policies"])} 条')
    print('='*70)
    print(f'\n{"省份":<8}{"部门":<20}{"状态":<12}{"栏目":<6}{"页数":<6}{"抓到":<6}')
    print('-'*70)
    for log in crawl_log:
        status_mark = '✅' if log['status']=='ok' else '❌'
        print(f'{log["province"]:<8}{log["dept"][:18]:<20}{status_mark+log["status"]:<12}{log.get("columns_found",0):<6}{log.get("pages_crawled",0):<6}{log.get("items_found",0):<6}')
    failed = [x for x in crawl_log if x['status']!='ok']
    if failed:
        print(f'\n⚠️  失败站点({len(failed)}个):')
        for f in failed:
            print(f'  - {f["province"]} {f["dept"]}: {f.get("error", f["status"])}')
    print('\n' + '='*70)

if __name__ == '__main__':
    main()
#（注：内容由AI生成）
