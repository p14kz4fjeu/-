#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策爬虫：每天自动抓取各省科技厅/工信厅最新申报通知
输出：policies.json（前端读取这个文件展示）
"""
import json, os, re, hashlib, time, urllib.request, ssl
from datetime import datetime
from html.parser import HTMLParser

# 忽略SSL验证（部分政府网站证书不全）
ssl._create_default_https_context = ssl._create_unverified_context

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ====== 项目关键词映射（标题含这些词就归类到对应项目） ======
PROJECT_KEYWORDS = {
    'gzrd': ['高新技术企业', '高企认定', '高企申报'],
    'zjtxjr': ['专精特新小巨人', '小巨人企业'],
    'zjtx': ['专精特新', '专精特新中小企业'],
    'cxxzx': ['创新型中小企业', '创新型中小'],
    'kjzzx': ['科技型中小企业', '科技型中小'],
    'sqjszx': ['企业技术中心', '省级企业技术中心'],
    'zgcgx': ['中关村高新', '中关村高新技术'],
    'bjxjsxcp': ['新技术新产品', '北京新技术'],
    'bjwxnf': ['小微企业研发', '小微技术企业研发', '研发补贴'],
    'jshtdj': ['技术合同登记', '技术合同认定'],
    'jjsk': ['加计扣除', '研发费用加计'],
    'rjqy': ['软件企业', '双软'],
    'rjcp': ['软件产品'],
}

# ====== 监控源：各省官网通知列表页 ======
# 每个源定义：名称、省份、URL、列表项CSS选择器（简化版：用关键词定位）
SOURCES = [
    # 国家级
    {'name': '科技部政务服务', 'province': '全国', 'url': 'https://fuwu.most.gov.cn/html/gxjsqyrd/'},
    {'name': '工信部中小企业', 'province': '全国', 'url': 'https://www.miit.gov.cn'},
    # 北京
    {'name': '北京市科委', 'province': '北京', 'url': 'http://kw.beijing.gov.cn/zwgk/zcwj/'},
    # 上海
    {'name': '上海科委', 'province': '上海', 'url': 'https://stcsm.sh.gov.cn/zwgk/tzgs/zhtz/'},
    # 广东
    {'name': '广东科技厅', 'province': '广东', 'url': 'https://gdstc.gd.gov.cn'},
    # 江苏
    {'name': '江苏科技厅', 'province': '江苏', 'url': 'https://kxjst.jiangsu.gov.cn'},
    # 浙江
    {'name': '浙江经信厅', 'province': '浙江', 'url': 'https://jxt.zj.gov.cn'},
    # 山东
    {'name': '山东科技厅', 'province': '山东', 'url': 'http://kjt.shandong.gov.cn'},
    # 河南
    {'name': '河南科技厅', 'province': '河南', 'url': 'https://kjt.henan.gov.cn'},
    # 天津
    {'name': '天津科技局', 'province': '天津', 'url': 'https://kxjs.tj.gov.cn'},
    # 四川
    {'name': '四川科技厅', 'province': '四川', 'url': 'https://kjt.sc.gov.cn'},
    # 河北
    {'name': '河北工信厅', 'province': '河北', 'url': 'https://gxt.hebei.gov.cn'},
    # 湖北
    {'name': '湖北科技厅', 'province': '湖北', 'url': 'https://kjt.hubei.gov.cn'},
    # 湖南
    {'name': '湖南科技厅', 'province': '湖南', 'url': 'https://kjt.hunan.gov.cn'},
    # 福建
    {'name': '福建科技厅', 'province': '福建', 'url': 'https://kjt.fujian.gov.cn'},
    # 安徽
    {'name': '安徽科技厅', 'province': '安徽', 'url': 'https://kjt.ah.gov.cn'},
    # 陕西
    {'name': '陕西科技厅', 'province': '陕西', 'url': 'https://kjt.shaanxi.gov.cn'},
    # 辽宁
    {'name': '辽宁科技厅', 'province': '辽宁', 'url': 'https://kjt.ln.gov.cn'},
    # 重庆
    {'name': '重庆科技局', 'province': '重庆', 'url': 'https://kjj.cq.gov.cn'},
    # 江西
    {'name': '江西科技厅', 'province': '江西', 'url': 'https://kjt.jiangxi.gov.cn'},
    # 广西
    {'name': '广西科技厅', 'province': '广西', 'url': 'https://kjt.gxzf.gov.cn'},
    # 云南
    {'name': '云南科技厅', 'province': '云南', 'url': 'https://kjt.yn.gov.cn'},
    # 山西
    {'name': '山西科技厅', 'province': '山西', 'url': 'https://kjt.shanxi.gov.cn'},
    # 黑龙江
    {'name': '黑龙江科技厅', 'province': '黑龙江', 'url': 'https://kjt.hlj.gov.cn'},
    # 吉林
    {'name': '吉林科技厅', 'province': '吉林', 'url': 'https://kjt.jilin.gov.cn'},
    # 贵州
    {'name': '贵州科技厅', 'province': '贵州', 'url': 'https://kjt.guizhou.gov.cn'},
    # 甘肃
    {'name': '甘肃科技厅', 'province': '甘肃', 'url': 'https://kjt.gansu.gov.cn'},
    # 海南
    {'name': '海南科技厅', 'province': '海南', 'url': 'https://kjt.hainan.gov.cn'},
    # 内蒙古
    {'name': '内蒙古科技厅', 'province': '内蒙古', 'url': 'https://kjt.nmg.gov.cn'},
    # 新疆
    {'name': '新疆科技厅', 'province': '新疆', 'url': 'https://kjt.xinjiang.gov.cn'},
    # 宁夏
    {'name': '宁夏科技厅', 'province': '宁夏', 'url': 'https://kjt.nx.gov.cn'},
    # 青海
    {'name': '青海科技厅', 'province': '青海', 'url': 'https://kjt.qinghai.gov.cn'},
    # 西藏
    {'name': '西藏科技厅', 'province': '西藏', 'url': 'https://kjt.xizang.gov.cn'},
]

def fetch_url(url, timeout=15):
    """抓取网页内容"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            # 尝试检测编码
            charset = resp.headers.get_content_charset() or 'utf-8'
            try:
                return data.decode(charset, errors='ignore')
            except:
                return data.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  [抓取失败] {url}: {e}')
        return ''

def extract_links(html, base_url):
    """从HTML中提取<a>标签的链接和文本"""
    links = []
    # 匹配 <a href="xxx">标题</a>
    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
    for match in re.finditer(pattern, html, re.DOTALL):
        href = match.group(1)
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
        if not text or len(text) < 6:
            continue
        # 补全相对URL
        if href.startswith('/'):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            href = f'{parsed.scheme}://{parsed.netloc}{href}'
        elif not href.startswith('http'):
            href = base_url.rstrip('/') + '/' + href
        links.append({'title': text, 'url': href})
    return links

def match_project(title):
    """根据标题匹配项目"""
    matched = []
    for pid, keywords in PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                matched.append(pid)
                break
    return matched

def load_existing():
    """加载已有的政策数据"""
    if os.path.exists('policies.json'):
        with open('policies.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'last_updated': '', 'policies': []}

def save(data):
    with open('policies.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print(f'=== 开始抓取 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    existing = load_existing()
    seen_urls = {p['url'] for p in existing['policies']}
    new_count = 0

    for source in SOURCES:
        print(f'抓取: {source["name"]} ({source["province"]})')
        html = fetch_url(source['url'])
        if not html:
            continue
        links = extract_links(html, source['url'])
        for link in links:
            # 只保留和项目相关的
            projects = match_project(link['title'])
            if not projects:
                continue
            if link['url'] in seen_urls:
                continue
            # 新政策
            for pid in projects:
                existing['policies'].append({
                    'project': pid,
                    'province': source['province'],
                    'title': link['title'],
                    'url': link['url'],
                    'found_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'source': source['name'],
                })
                seen_urls.add(link['url'])
                new_count += 1
        time.sleep(1)  # 礼貌延时

    existing['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    save(existing)
    print(f'=== 完成: 新增 {new_count} 条政策, 总计 {len(existing["policies"])} 条 ===')

if __name__ == '__main__':
    main()
#（注：内容由AI生成）
