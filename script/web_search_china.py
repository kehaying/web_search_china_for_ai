import requests
import json
import re
from bs4 import BeautifulSoup
import sys
import argparse

class WebSearchChina:
    def __init__(self):
        self.engines = {
            "baidu": self._search_baidu,
            "bing": self._search_bing,
            "360": self._search_360
        }
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        })
    
    def search(self, query, engine="baidu", count=5):
        """
        执行中国国内搜索
        
        Args:
            query: 搜索关键词
            engine: 搜索引擎（baidu、bing、360）
            count: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        if engine not in self.engines:
            engine = "baidu"
        
        try:
            results = self.engines[engine](query, count)
            return self._format_results(results, count)
        except Exception as e:
            return [{"title": "错误", "url": "", "snippet": f"搜索失败: {str(e)}"}]
    
    def _search_baidu(self, query, count):
        """百度搜索"""
        # 先访问首页获取cookies
        self.session.get("https://www.baidu.com", timeout=10)
        url = f"https://www.baidu.com/s?wd={query}&rn={count}"
        response = self.session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        # 尝试不同的选择器
        selectors = [".result", ".c-container", ".result-op", ".result-content", ".t", ".s_tab", ".s_result"]
        
        for selector in selectors:
            for item in soup.select(selector):
                # 尝试不同的标题选择器
                title_elems = item.select("a")
                for title_elem in title_elems:
                    if title_elem:
                        title = title_elem.text.strip()
                        url = title_elem.get("href")
                        # 跳过没有标题或URL的结果
                        if not title or not url:
                            continue
                        # 跳过百度内部链接
                        if "baidu.com" in url and not url.startswith("http"):
                            continue
                        # 尝试不同的摘要选择器
                        snippet = item.select_one(".c-abstract, .c-summary, .content-right, .abstract, .result-op .c-abstract, .result-content .c-abstract")
                        # 如果没有找到摘要，尝试从其他地方提取
                        if not snippet:
                            # 尝试从文本内容中提取
                            text_content = item.get_text(separator=" ", strip=True)
                            if text_content:
                                snippet = text_content[:150] + "..." if len(text_content) > 150 else text_content
                            else:
                                snippet = ""
                        else:
                            snippet = snippet.text.strip() if snippet else ""
                        # 过滤掉无关结果
                        if "备" in title or "许可证" in title or "ICP" in title or "公安" in title:
                            continue
                        # 过滤掉太短的标题
                        if len(title) < 5:
                            continue
                        # 过滤掉重复结果
                        is_duplicate = False
                        for result in results:
                            if result["title"] == title:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            results.append({"title": title, "url": url, "snippet": snippet})
                            if len(results) >= count:
                                return results
        
        # 如果没有结果，尝试直接从HTML中提取
        if not results:
            # 简单的正则表达式提取
            matches = re.findall(r'<a[^>]+href="(https?://[^"&]+)"[^>]*>([^<]+)</a>', response.text)
            for href, title in matches[:count * 5]:  # 多提取一些结果以便过滤
                if href and title:
                    # 过滤掉备案信息等无关结果
                    if "备" in title or "许可证" in title or "ICP" in title or "公安" in title:
                        continue
                    # 过滤掉太短的标题
                    if len(title) < 5:
                        continue
                    # 过滤掉重复结果
                    is_duplicate = False
                    for result in results:
                        if result["title"] == title:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        results.append({"title": title, "url": href, "snippet": ""})
                        if len(results) >= count:
                            break
        
        return results
    
    def _search_bing(self, query, count):
        """必应搜索"""
        try:
            # 先访问首页获取cookies
            self.session.get("https://cn.bing.com", timeout=10)
            url = f"https://cn.bing.com/search?q={query}&count={count}"
            response = self.session.get(url, timeout=15)
            
            # 尝试不同的选择器来找到搜索结果
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # 尝试不同的选择器
            for item in soup.select(".b_algo, .sa_cc, .b_result"):
                title_elem = item.select_one("h2 a, .b_title a")
                if title_elem:
                    title = title_elem.text
                    url = title_elem.get("href")
                    snippet_elem = item.select_one(".b_caption p, .b_snippet")
                    snippet = snippet_elem.text if snippet_elem else ""
                    
                    # 过滤掉无关结果
                    if ("备" in title or "许可证" in title or "ICP" in title or "公安" in title or 
                        "隐私" in title or "法律声明" in title or "广告" in title or 
                        "Cookie" in title or "go.microsoft.com" in url or 
                        "bing.com" in url or "microsoft.com" in url):
                        continue
                    
                    # 确保URL是完整的
                    if url and not url.startswith("http"):
                        if url.startswith("//"):
                            url = "https:" + url
                        else:
                            continue
                    
                    results.append({"title": title, "url": url, "snippet": snippet})
                    if len(results) >= count:
                        break
            
            # 如果没有结果，尝试直接从HTML中提取
            if not results:
                matches = re.findall(r'<a[^>]+href="(https?://[^"&]+)"[^>]*>([^<]+)</a>', response.text)
                
                for href, title in matches[:count * 3]:
                    # 过滤掉无关结果
                    if ("备" in title or "许可证" in title or "ICP" in title or "公安" in title or 
                        "隐私" in title or "法律声明" in title or "广告" in title or 
                        "Cookie" in title or "go.microsoft.com" in href or 
                        "bing.com" in href or "microsoft.com" in href):
                        continue
                    # 过滤掉太短的标题
                    if len(title) < 5:
                        continue
                    results.append({"title": title, "url": href, "snippet": ""})
                    if len(results) >= count:
                        break
            
            # 如果仍然没有结果，返回默认信息
            if not results:
                results.append({"title": "必应搜索暂时不可用", "url": "", "snippet": "请尝试使用百度或360搜索"})
        except Exception as e:
            results = [{"title": "必应搜索失败", "url": "", "snippet": f"错误: {str(e)}"}]
        
        return results
    
    def _search_360(self, query, count):
        """360搜索"""
        # 先访问首页获取cookies
        self.session.get("https://www.so.com", timeout=10)
        url = f"https://www.so.com/s?q={query}&num={count}"
        response = self.session.get(url, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        for item in soup.select(".res-list .res-item, .result"):
            title_elem = item.select_one(".res-title a, .t a")
            if title_elem:
                title = title_elem.text
                url = title_elem.get("href")
                snippet = item.select_one(".res-desc, .c-abstract")
                snippet = snippet.text if snippet else ""
                results.append({"title": title, "url": url, "snippet": snippet})
                if len(results) >= count:
                    break
        
        # 如果没有结果，尝试直接从HTML中提取
        if not results:
            matches = re.findall(r'<a[^>]+href="(https?://[^"&]+)"[^>]*>([^<]+)</a>', response.text)
            for href, title in matches[:count * 2]:  # 多提取一些结果以便过滤
                if href and title:
                    # 过滤掉备案信息等无关结果
                    if "备" in title or "许可证" in title or "ICP" in title or "公安" in title:
                        continue
                    # 过滤掉太短的标题
                    if len(title) < 5:
                        continue
                    results.append({"title": title, "url": href, "snippet": ""})
                    if len(results) >= count:
                        break
        
        return results
    
    def _format_results(self, results, count):
        """格式化搜索结果"""
        formatted_results = []
        for i, result in enumerate(results[:count]):
            formatted_results.append({
                "rank": i + 1,
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", "")
            })
        return formatted_results

# 命令行参数处理
if __name__ == "__main__":
    # 处理命令行参数
    parser = argparse.ArgumentParser(description="中国国内搜索引擎")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--engine", default="baidu", choices=["baidu", "bing", "360"], help="搜索引擎")
    parser.add_argument("--count", type=int, default=5, help="返回结果数量")
    
    args = parser.parse_args()
    
    searcher = WebSearchChina()
    results = searcher.search(args.query, engine=args.engine, count=args.count)
    print(json.dumps(results, ensure_ascii=False))
    