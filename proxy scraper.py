#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import threading
import os
import time
import json
import csv
import sqlite3
import hashlib
import sys
import signal
import argparse
import configparser
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import urllib3
import colorama
from colorama import Fore, Back, Style
from tqdm import tqdm
import socket
import random

colorama.init()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RealTimeMonitor:
    def __init__(self):
        self.stats = {
            'total_found': 0,
            'http': 0,
            'https': 0,
            'socks4': 0,
            'socks5': 0,
            'sources_processed': 0,
            'sources_total': 0,
            'start_time': time.time()
        }
        self.lock = Lock()
        self.running = True
        self.live_proxies = defaultdict(set)
        
    def update(self, proxy_type, count, source=None):
        with self.lock:
            self.stats[proxy_type] += count
            self.stats['total_found'] += count
            if source:
                self.stats['sources_processed'] += 1
                
    def display(self):
        while self.running:
            os.system('cls' if os.name == 'nt' else 'clear')
            elapsed = time.time() - self.stats['start_time']
            
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}📡 ПРОКСИ СКРАПЕР - РЕЖИМ РЕАЛЬНОГО ВРЕМЕНИ{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print(f"Время работы: {elapsed:.1f} сек")
            print(f"Источников обработано: {self.stats['sources_processed']}/{self.stats['sources_total']}")
            print(f"{Fore.GREEN}Всего найдено: {self.stats['total_found']}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}📊 Прокси по типам:{Style.RESET_ALL}")
            print(f"  HTTP    : {self.stats['http']}")
            print(f"  HTTPS   : {self.stats['https']}")
            print(f"  SOCKS4  : {self.stats['socks4']}")
            print(f"  SOCKS5  : {self.stats['socks5']}")
            
            if self.live_proxies:
                print(f"\n{Fore.GREEN}🔄 Последние найденные:{Style.RESET_ALL}")
                for ptype, proxies in self.live_proxies.items():
                    if proxies:
                        recent = list(proxies)[-5:]
                        for proxy in recent:
                            print(f"  {ptype}: {proxy}")
            
            print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
            print("Нажмите Ctrl+C для остановки...")
            
            time.sleep(1)
    
    def stop(self):
        self.running = False

class ProxyScraper:
    def __init__(self, config_file=None):
        self.monitor = RealTimeMonitor()
        self.all_proxies = defaultdict(set)
        self.failed_sources = []
        self.successful_sources = []
        self.lock = Lock()
        self.proxy_types = ['http', 'https', 'socks4', 'socks5']
        
        self.sources = self.init_sources()
        self.monitor.stats['sources_total'] = sum(len(s) for s in self.sources.values())
        
    def init_sources(self):
        sources = defaultdict(list)
        
        # ==================== HTTP ИСТОЧНИКИ (200+) ====================
        http_sources = [
            # ProxyScrape API (разные вариации)
            *[f'https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout={t}&country={c}&ssl={s}&anonymity={a}'
              for t in [1000, 2000, 3000, 5000, 10000]
              for c in ['all', 'US', 'RU', 'DE', 'FR', 'GB', 'NL', 'CA', 'AU', 'JP', 'CN', 'BR', 'IN', 'IT', 'ES', 'PL', 'UA', 'SE', 'NO', 'FI', 'DK']
              for s in ['all', 'yes', 'no']
              for a in ['all', 'elite', 'anonymous', 'transparent']],
            
            # Proxy-List.download API
            *[f'https://www.proxy-list.download/api/v1/get?type=http&anon={a}&country={c}'
              for a in ['elite', 'anonymous', 'transparent', 'all']
              for c in ['US', 'RU', 'DE', 'FR', 'GB', 'NL', 'CA', 'AU', 'JP', 'CN', 'BR', 'IN', 'IT', 'ES', 'PL', 'UA']],
            
            # GitHub репозитории
            *[f'https://raw.githubusercontent.com/{repo}/master/{file}'
              for repo in ['TheSpeedX/PROXY-List', 'ShiftyTR/Proxy-List', 'monosans/proxy-list', 
                          'jetkai/proxy-list', 'roosterkid/openproxylist', 'hookzof/socks5_list',
                          'BlackDexa/proxy-list', 'AnonymouX47/Proxy-List', 'elliottophellia/yakumo',
                          'zloi-user/hideip.me', 'casals-ar/proxy-list', 'fate0/proxy-list',
                          'parsex/Proxy-List', 'rdavydov/proxy-list', 'kit4py/proxy-scraper',
                          'saschazesiger/Free-Proxies', 'alpha2phi/proxy-list', 'ErcinDedeoglu/proxies',
                          'a2u/free-proxy-list', 'fahimscopes/Free-Proxy-List', 'prxchk/proxy-list',
                          'mertguvencli/http-proxy-list', 'stamparm/aux', 'clarketm/proxy-list',
                          'sunny9577/proxy-scraper', 'UptimerBot/proxy-list', 'voken100g/AutoSSR',
                          'lingdragon/proxy-pool', 'ihatedeadline/proxy-list', 'baymaxman/Proxy-List',
                          'palmseed/Proxy-List', 'Aircoinoffcial/Proxy-List', 'officialput/Proxy-List',
                          'Jaredy899/proxy-list', 'dragon1018/Proxy-List', 'Volodichev/proxy-list',
                          'm0wl/proxy-list', 'mertguvencli/proxy-list', 'proxylistfun/proxy-list',
                          'proxylist-source/proxy-list', 'proxy4parsing/proxy-list', 'mmpx12/proxy-list',
                          'jimenoz/proxy-list', 'ngneha/proxy-list', 'jamesdedwards/proxy-list',
                          'mertguvencli/proxy-list', 'shreyasminocha/proxy-list', 'secopsmart/proxy-list',
                          'theabbie/proxy-list', 'andrewfox/proxy-list', 'marcelmaatkamp/proxy-list',
                          'sambhav2612/proxy-list', 'abh80/proxy-list', 'develcook/proxy-list',
                          'prasannak77/proxy-list', 'R3H4CK3R/proxy-list', 'Zaeem20/proxy-list']
              for file in ['http.txt', 'proxies.txt', 'list.txt', 'proxy-list.txt', 'proxies/http.txt',
                          'all.txt', 'all-proxies.txt', 'http-proxy.txt', 'proxylist.txt']],
            
            # OpenProxyList
            *[f'https://api.openproxylist.xyz/{type}.txt'
              for type in ['http', 'https', 'socks4', 'socks5', 'all']],
            
            # Бесплатные сайты с прокси
            'https://free-proxy-list.net/',
            'https://free-proxy-list.net/uk-proxy.html',
            'https://free-proxy-list.net/anonymous-proxy.html',
            'https://www.sslproxies.org/',
            'https://www.us-proxy.org/',
            'https://www.socks-proxy.net/',
            'https://www.proxynova.com/proxy-server-list/',
            'https://www.proxynova.com/proxy-server-list/country-us/',
            'https://www.proxynova.com/proxy-server-list/country-ru/',
            'https://www.proxynova.com/proxy-server-list/country-de/',
            'https://www.proxynova.com/proxy-server-list/country-fr/',
            'https://www.proxynova.com/proxy-server-list/country-gb/',
            'https://www.proxynova.com/proxy-server-list/country-cn/',
            'https://www.proxynova.com/proxy-server-list/country-br/',
            'https://www.proxynova.com/proxy-server-list/country-in/',
            'https://www.proxynova.com/proxy-server-list/country-jp/',
            'https://www.proxynova.com/proxy-server-list/country-kr/',
            'https://www.proxynova.com/proxy-server-list/country-au/',
            'https://www.proxynova.com/proxy-server-list/country-ca/',
            'https://www.proxynova.com/proxy-server-list/country-it/',
            'https://www.proxynova.com/proxy-server-list/country-es/',
            'https://www.proxynova.com/proxy-server-list/country-pl/',
            'https://www.proxynova.com/proxy-server-list/country-ua/',
            
            # Proxy-List.org
            'https://proxy-list.org/english/search.php',
            'https://proxy-list.org/english/index.php',
            'https://proxy-list.org/english/search.php?country=US',
            'https://proxy-list.org/english/search.php?country=RU',
            'https://proxy-list.org/english/search.php?country=DE',
            'https://proxy-list.org/english/search.php?country=FR',
            'https://proxy-list.org/english/search.php?country=GB',
            'https://proxy-list.org/english/search.php?country=NL',
            'https://proxy-list.org/english/search.php?country=CA',
            'https://proxy-list.org/english/search.php?country=AU',
            'https://proxy-list.org/english/search.php?country=JP',
            'https://proxy-list.org/english/search.php?country=CN',
            'https://proxy-list.org/english/search.php?country=BR',
            'https://proxy-list.org/english/search.php?country=IN',
            
            # HideMy.name
            'https://hidemy.name/en/proxy-list/',
            'https://hidemy.name/en/proxy-list/?type=h',
            'https://hidemy.name/en/proxy-list/?type=hs',
            'https://hidemy.name/en/proxy-list/?country=US',
            'https://hidemy.name/en/proxy-list/?country=RU',
            'https://hidemy.name/en/proxy-list/?country=DE',
            'https://hidemy.name/en/proxy-list/?country=FR',
            'https://hidemy.name/en/proxy-list/?country=GB',
            'https://hidemy.name/en/proxy-list/?country=NL',
            'https://hidemy.name/en/proxy-list/?country=CA',
            'https://hidemy.name/en/proxy-list/?country=AU',
            'https://hidemy.name/en/proxy-list/?country=JP',
            'https://hidemy.name/en/proxy-list/?country=CN',
            
            # Spys.one
            'https://spys.one/en/free-proxy-list/',
            'https://spys.one/en/http-proxy/',
            'https://spys.one/en/socks-proxy/',
            'https://spys.one/en/anonymous-proxy/',
            'https://spys.one/en/proxy-list/',
            'https://spys.one/en/proxy-list-2/',
            'https://spys.one/en/proxy-list-3/',
            'https://spys.one/en/proxy-list-4/',
            
            # Xseo.in
            'https://xseo.in/freeproxy',
            'https://xseo.in/freeproxy?type=http',
            'https://xseo.in/freeproxy?type=https',
            'https://xseo.in/freeproxy?type=socks4',
            'https://xseo.in/freeproxy?type=socks5',
            'https://xseo.in/freeproxy?page=1',
            'https://xseo.in/freeproxy?page=2',
            'https://xseo.in/freeproxy?page=3',
            'https://xseo.in/freeproxy?page=4',
            'https://xseo.in/freeproxy?page=5',
            
            # Checkerproxy.net
            'https://checkerproxy.net/archive',
            'https://checkerproxy.net/api/archive',
            'https://checkerproxy.net/api/archive/2024-01-01',
            'https://checkerproxy.net/api/archive/2024-01-02',
            'https://checkerproxy.net/api/archive/2024-01-03',
            
            # Geonode API
            'https://proxylist.geonode.com/api/proxy-list?limit=500',
            'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1',
            'https://proxylist.geonode.com/api/proxy-list?limit=500&page=2',
            'https://proxylist.geonode.com/api/proxy-list?limit=500&page=3',
            'https://proxylist.geonode.com/api/proxy-list?protocols=http',
            'https://proxylist.geonode.com/api/proxy-list?protocols=https',
            'https://proxylist.geonode.com/api/proxy-list?protocols=socks4',
            'https://proxylist.geonode.com/api/proxy-list?protocols=socks5',
            'https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite',
            'https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous',
            
            # GetProxyList API
            'https://api.getproxylist.com/proxy',
            'https://api.getproxylist.com/proxy?protocol=http',
            'https://api.getproxylist.com/proxy?protocol=https',
            'https://api.getproxylist.com/proxy?protocol=socks4',
            'https://api.getproxylist.com/proxy?protocol=socks5',
            'https://api.getproxylist.com/proxy?anonymity=elite',
            'https://api.getproxylist.com/proxy?anonymity=anonymous',
            'https://api.getproxylist.com/proxy?country=US',
            'https://api.getproxylist.com/proxy?country=RU',
            'https://api.getproxylist.com/proxy?country=DE',
            
            # ProxyPedia
            'https://proxypedia.org/free-proxy/',
            'https://proxypedia.org/free-proxy/page/1/',
            'https://proxypedia.org/free-proxy/page/2/',
            'https://proxypedia.org/free-proxy/page/3/',
            'https://proxypedia.org/free-proxy/page/4/',
            'https://proxypedia.org/free-proxy/page/5/',
            'https://proxypedia.org/free-proxy/page/6/',
            'https://proxypedia.org/free-proxy/page/7/',
            'https://proxypedia.org/free-proxy/page/8/',
            'https://proxypedia.org/free-proxy/page/9/',
            'https://proxypedia.org/free-proxy/page/10/',
            
            # Proxy-Archive
            'https://proxy-archive.com/',
            'https://proxy-archive.com/http/',
            'https://proxy-archive.com/https/',
            'https://proxy-archive.com/socks4/',
            'https://proxy-archive.com/socks5/',
            'https://proxy-archive.com/page/1/',
            'https://proxy-archive.com/page/2/',
            'https://proxy-archive.com/page/3/',
            
            # ProxyRanker
            'https://proxyranker.com/free-proxy-list/',
            'https://proxyranker.com/free-proxy-list/page/1/',
            'https://proxyranker.com/free-proxy-list/page/2/',
            'https://proxyranker.com/free-proxy-list/page/3/',
            'https://proxyranker.com/free-proxy-list/page/4/',
            'https://proxyranker.com/free-proxy-list/page/5/',
            
            # My-Proxy
            'https://www.my-proxy.com/free-proxy-list/',
            'https://www.my-proxy.com/free-proxy-list-2/',
            'https://www.my-proxy.com/free-proxy-list-3/',
            'https://www.my-proxy.com/free-proxy-list-4/',
            'https://www.my-proxy.com/free-proxy-list-5/',
            'https://www.my-proxy.com/free-socks-4-proxy.html',
            'https://www.my-proxy.com/free-socks-5-proxy.html',
            
            # ProxySite
            'https://www.proxysite.com/free-proxy-list/',
            'https://www.proxysite.com/free-proxy-list-2/',
            'https://www.proxysite.com/free-proxy-list-3/',
            'https://www.proxysite.com/free-socks-proxy/',
            
            # Cool-Proxy
            'https://www.cool-proxy.net/proxies/http_proxy_list/sort:score/direction:desc',
            'https://www.cool-proxy.net/proxies/http_proxy_list/sort:response_time/direction:asc',
            'https://www.cool-proxy.net/proxies/socks4_proxy_list/sort:score/direction:desc',
            'https://www.cool-proxy.net/proxies/socks5_proxy_list/sort:score/direction:desc',
            'https://www.cool-proxy.net/proxies/http_proxy_list/page:1',
            'https://www.cool-proxy.net/proxies/http_proxy_list/page:2',
            'https://www.cool-proxy.net/proxies/http_proxy_list/page:3',
            
            # FineProxy
            'https://fineproxy.org/free-proxy/',
            'https://fineproxy.org/free-proxy-list/',
            'https://fineproxy.org/ru/free-proxy/',
            
            # ProxyDB
            'https://proxydb.net/',
            'https://proxydb.net/?protocol=http',
            'https://proxydb.net/?protocol=https',
            'https://proxydb.net/?protocol=socks4',
            'https://proxydb.net/?protocol=socks5',
            'https://proxydb.net/?country=US',
            'https://proxydb.net/?country=RU',
            'https://proxydb.net/?country=DE',
            
            # ProxyList
            'https://proxy-list.org/english/index.php',
            'https://proxy-list.org/english/search.php?p=1',
            'https://proxy-list.org/english/search.php?p=2',
            'https://proxy-list.org/english/search.php?p=3',
            'https://proxy-list.org/english/search.php?p=4',
            'https://proxy-list.org/english/search.php?p=5',
        ]
        
        # ==================== HTTPS ИСТОЧНИКИ ====================
        https_sources = [
            'https://www.sslproxies.org/',
            'https://free-proxy-list.net/',
            'https://www.us-proxy.org/',
            'https://api.proxyscrape.com/?request=displayproxies&proxytype=http&ssl=yes',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
            'https://api.openproxylist.xyz/https.txt',
            'https://www.proxy-list.download/api/v1/get?type=https',
            'https://proxy-list.org/english/search.php?search=https',
            'https://hidemy.name/en/proxy-list/?type=hs',
            'https://spys.one/en/https-proxy/',
            'https://checkerproxy.net/api/archive?protocol=https',
        ]
        
        # ==================== SOCKS4 ИСТОЧНИКИ ====================
        socks4_sources = [
            *[f'https://api.proxyscrape.com/?request=displayproxies&proxytype=socks4&timeout={t}&country={c}'
              for t in [1000, 2000, 3000, 5000, 10000]
              for c in ['all', 'US', 'RU', 'DE', 'FR', 'GB', 'NL', 'CA', 'AU', 'JP', 'CN']],
            
            *[f'https://raw.githubusercontent.com/{repo}/master/{file}'
              for repo in ['TheSpeedX/PROXY-List', 'monosans/proxy-list', 'jetkai/proxy-list',
                          'ShiftyTR/Proxy-List', 'roosterkid/openproxylist', 'hookzof/socks5_list',
                          'BlackDexa/proxy-list', 'AnonymouX47/Proxy-List', 'elliottophellia/yakumo',
                          'zloi-user/hideip.me', 'casals-ar/proxy-list', 'fate0/proxy-list',
                          'parsex/Proxy-List', 'rdavydov/proxy-list', 'kit4py/proxy-scraper']
              for file in ['socks4.txt', 'proxies/socks4.txt', 'socks4-proxy.txt']],
            
            'https://www.proxy-list.download/api/v1/get?type=socks4',
            'https://www.socks-proxy.net/',
            'https://spys.one/en/socks-proxy/',
            'https://www.my-proxy.com/free-socks-4-proxy.html',
            'https://www.cool-proxy.net/proxies/socks4_proxy_list/sort:score/direction:desc',
            'https://api.openproxylist.xyz/socks4.txt',
            'https://proxy-list.org/english/search.php?search=socks4',
            'https://hidemy.name/en/proxy-list/?type=4',
            'https://checkerproxy.net/api/archive?protocol=socks4',
        ]
        
        # ==================== SOCKS5 ИСТОЧНИКИ ====================
        socks5_sources = [
            *[f'https://api.proxyscrape.com/?request=displayproxies&proxytype=socks5&timeout={t}&country={c}'
              for t in [1000, 2000, 3000, 5000, 10000]
              for c in ['all', 'US', 'RU', 'DE', 'FR', 'GB', 'NL', 'CA', 'AU', 'JP', 'CN']],
            
            *[f'https://raw.githubusercontent.com/{repo}/master/{file}'
              for repo in ['TheSpeedX/PROXY-List', 'monosans/proxy-list', 'jetkai/proxy-list',
                          'ShiftyTR/Proxy-List', 'roosterkid/openproxylist', 'hookzof/socks5_list',
                          'BlackDexa/proxy-list', 'AnonymouX47/Proxy-List', 'elliottophellia/yakumo',
                          'zloi-user/hideip.me', 'casals-ar/proxy-list', 'fate0/proxy-list',
                          'parsex/Proxy-List', 'rdavydov/proxy-list', 'kit4py/proxy-scraper',
                          'saschazesiger/Free-Proxies']
              for file in ['socks5.txt', 'proxies/socks5.txt', 'socks5-proxy.txt']],
            
            'https://www.proxy-list.download/api/v1/get?type=socks5',
            'https://www.socks-proxy.net/',
            'https://spys.one/en/socks-proxy/',
            'https://www.my-proxy.com/free-socks-5-proxy.html',
            'https://www.cool-proxy.net/proxies/socks5_proxy_list/sort:score/direction:desc',
            'https://api.openproxylist.xyz/socks5.txt',
            'https://proxy-list.org/english/search.php?search=socks5',
            'https://hidemy.name/en/proxy-list/?type=5',
            'https://checkerproxy.net/api/archive?protocol=socks5',
            'https://raw.githubusercontent.com/hookzof/socks5_list/master/socks5.txt',
            'https://raw.githubusercontent.com/blackhatethicalhacking/proxy-list/main/socks5.txt',
        ]
        
        sources['http'] = http_sources
        sources['https'] = https_sources + http_sources
        sources['socks4'] = socks4_sources
        sources['socks5'] = socks5_sources
        
        return sources
    
    def extract_proxies(self, text):
        patterns = [
            r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b',
            r'(?:http|https|socks4|socks5)://(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}'
        ]
        
        proxies = set()
        for pattern in patterns:
            found = re.findall(pattern, text)
            for proxy in found:
                cleaned = re.sub(r'^.*://', '', proxy.strip())
                if self.is_valid_proxy(cleaned):
                    proxies.add(cleaned)
        return proxies
    
    def is_valid_proxy(self, proxy):
        try:
            ip, port = proxy.split(':')
            port = int(port)
            if not (1 <= port <= 65535):
                return False
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except:
            return False
    
    def fetch_from_url(self, url, proxy_type):
        proxies = set()
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                extracted = self.extract_proxies(response.text)
                proxies.update(extracted)
                
                with self.lock:
                    self.monitor.update(proxy_type, len(extracted), url)
                    self.monitor.live_proxies[proxy_type] = list(extracted)[-10:]
                    self.successful_sources.append(url)
                    
        except Exception:
            with self.lock:
                self.failed_sources.append(url)
        
        return proxies
    
    def scrape_proxy_type(self, proxy_type, sources):
        all_proxies = set()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for url in sources:
                future = executor.submit(self.fetch_from_url, url, proxy_type)
                futures.append(future)
                time.sleep(0.05)
            
            for future in as_completed(futures):
                proxies = future.result()
                all_proxies.update(proxies)
        
        self.all_proxies[proxy_type] = all_proxies
        return all_proxies
    
    def scrape_all(self):
        monitor_thread = threading.Thread(target=self.monitor.display)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for proxy_type, sources in self.sources.items():
                if sources:
                    future = executor.submit(self.scrape_proxy_type, proxy_type, sources)
                    futures.append(future)
                    time.sleep(0.1)
            
            for future in futures:
                future.result()
        
        self.monitor.stop()
    
    def save_results(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = f"proxies_{timestamp}"
        os.makedirs(base_dir, exist_ok=True)
        
        for proxy_type, proxies in self.all_proxies.items():
            if proxies:
                filename = os.path.join(base_dir, f"{proxy_type}.txt")
                with open(filename, 'w') as f:
                    f.write('\n'.join(sorted(proxies)))
        
        all_proxies = set()
        for proxies in self.all_proxies.values():
            all_proxies.update(proxies)
        
        if all_proxies:
            filename = os.path.join(base_dir, "all_proxies.txt")
            with open(filename, 'w') as f:
                f.write('\n'.join(sorted(all_proxies)))
        
        stats_file = os.path.join(base_dir, "stats.txt")
        with open(stats_file, 'w') as f:
            f.write(f"Дата сбора: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Время работы: {time.time() - self.monitor.stats['start_time']:.2f} сек\n")
            f.write(f"Всего источников: {self.monitor.stats['sources_total']}\n")
            f.write(f"Успешных источников: {len(self.successful_sources)}\n")
            f.write(f"Неудачных источников: {len(self.failed_sources)}\n\n")
            
            for proxy_type, proxies in self.all_proxies.items():
                if proxies:
                    f.write(f"{proxy_type.upper()}: {len(proxies)}\n")
            
            f.write(f"\nВСЕГО УНИКАЛЬНЫХ: {len(all_proxies)}\n")
        
        return base_dir

def main():
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🚀 ПРОКСИ СКРАПЕР - МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"Всего источников: ~500+")
    print(f"Типы прокси: HTTP, HTTPS, SOCKS4, SOCKS5")
    print(f"{Fore.YELLOW}Запуск мониторинга...{Style.RESET_ALL}")
    print(f"{'='*60}\n")
    
    scraper = ProxyScraper()
    
    try:
        scraper.scrape_all()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Остановка по требованию пользователя{Style.RESET_ALL}")
        scraper.monitor.stop()
    
    print(f"\n{Fore.GREEN}Сбор завершен! Сохраняем результаты...{Style.RESET_ALL}")
    base_dir = scraper.save_results()
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ РЕЗУЛЬТАТЫ:{Style.RESET_ALL}")
    print(f"HTTP    : {len(scraper.all_proxies['http'])}")
    print(f"HTTPS   : {len(scraper.all_proxies['https'])}")
    print(f"SOCKS4  : {len(scraper.all_proxies['socks4'])}")
    print(f"SOCKS5  : {len(scraper.all_proxies['socks5'])}")
    print(f"\nФайлы сохранены в: {Fore.YELLOW}{base_dir}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()