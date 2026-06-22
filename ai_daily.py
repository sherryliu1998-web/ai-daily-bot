import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import feedparser
import requests


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


SERVER_CHAN_API = os.getenv(
    "SERVER_CHAN_API",
    "https://sctapi.ftqq.com/SCT366257TEwaFCrihsXADdz0um1qxPhyF.send",
)

HEADERS = {
    "User-Agent": "AI-Daily-Bot/3.0",
    "Accept": "application/json, application/rss+xml, application/xml, text/xml",
}

AI_KEYWORD_RE = re.compile(
    r"(?i)(\bAI\b|\bLLM(s)?\b|\bagent(s|ic)?\b|\bautomation\b|\bGPT\b)"
)

MAX_NEWS_PER_SOURCE = 5
MAX_HN_TOP_STORIES = 50
MAX_SECTION_ITEMS = 12
TREND_THRESHOLD = 3
STRONG_TREND_THRESHOLD = 5

NEWS_FEEDS = [
    {
        "source": "OpenAI",
        "urls": [
            "https://openai.com/news/rss.xml",
            "https://openai.com/index/rss.xml",
        ],
    },
    {
        "source": "Google DeepMind",
        "urls": [
            "https://deepmind.google/discover/blog/rss.xml",
            "https://deepmind.google/blog/rss.xml",
        ],
    },
    {
        "source": "Anthropic",
        "urls": ["https://www.anthropic.com/news/rss.xml"],
    },
    {
        "source": "Microsoft AI",
        "urls": [
            "https://news.microsoft.com/source/topics/ai/feed/",
            "https://blogs.microsoft.com/ai/feed/",
        ],
    },
    {
        "source": "Hugging Face",
        "urls": [
            "https://huggingface.co/blog/feed.xml",
            "https://huggingface.co/blog/feed",
        ],
    },
]

TREND_KEYWORDS = [
    {
        "name": "AI Agent",
        "category": "technology",
        "patterns": [r"\bAI agent(s)?\b", r"\bagent(s|ic)?\b", r"\bmulti-agent\b"],
        "description": "agent / multi-agent / agentic 等词在数据中高频出现。",
        "why": "Agent 高频出现，说明今天的数据里有较多内容围绕 AI 执行任务、调用工具或完成流程展开。",
        "changed": "AI 能力叙事从回答问题扩展到执行任务和协作系统。",
        "opportunity": "AI Agent 正在从概念变成真实工具：普通人能怎么用？",
    },
    {
        "name": "automation",
        "category": "behavior",
        "patterns": [r"\bautomation\b", r"\bautomate(s|d)?\b", r"\bautomating\b", r"\bautonomous\b"],
        "description": "automation / autonomous 等词在数据中高频出现。",
        "why": "自动化词汇高频出现，说明用户关注点正在从单次生成转向连续流程处理。",
        "changed": "用户行为从手动操作转向让 AI 接管重复步骤。",
        "opportunity": "AI 自动化正在替代哪些手动流程？",
    },
    {
        "name": "coding assistant",
        "category": "product",
        "patterns": [r"\bcoding\b", r"\bcode\b", r"\bdeveloper(s)?\b", r"\bprogramming\b", r"\bIDE\b"],
        "description": "coding / developer / IDE 等词在数据中高频出现。",
        "why": "编程相关词汇高频出现，说明开发者工具仍是 AI 产品落地最活跃的区域之一。",
        "changed": "AI 编程工具从补全代码扩展到项目级协作和开发流程。",
        "opportunity": "AI coding 工具爆发：哪些工具值得普通创作者了解？",
    },
    {
        "name": "LLM",
        "category": "technology",
        "patterns": [r"\bLLM(s)?\b", r"\blarge language model(s)?\b", r"\bGPT\b", r"\bClaude\b", r"\bGemini\b"],
        "description": "LLM / GPT / Claude / Gemini 等模型词在数据中高频出现。",
        "why": "模型词高频出现，说明底层模型能力和模型生态仍是当天 AI 信息的核心来源。",
        "changed": "模型竞争继续体现在能力、速度、开放程度和具体场景适配上。",
        "opportunity": "今天这些模型更新，普通人到底该关心什么？",
    },
    {
        "name": "multimodal",
        "category": "technology",
        "patterns": [r"\bmultimodal\b", r"\bmulti-modal\b", r"\bimage(s)?\b", r"\baudio\b", r"\bvideo\b", r"\bvoice\b"],
        "description": "multimodal / image / audio / video / voice 等词在数据中高频出现。",
        "why": "多模态词汇高频出现，说明 AI 能力正在跨文本、图像、音频、视频等输入输出形态扩展。",
        "changed": "AI 的交互边界从文本扩展到更丰富的媒体形式。",
        "opportunity": "AI 多模态工具怎么改变内容生产？",
    },
    {
        "name": "open-source model",
        "category": "technology",
        "patterns": [r"\bopen source\b", r"\bopen-source\b", r"\bopen weights?\b", r"\bopen model(s)?\b"],
        "description": "open-source / open weights / open model 等词在数据中高频出现。",
        "why": "开放模型词汇高频出现，说明开发者社区正在持续关注可本地部署、可复用的模型能力。",
        "changed": "模型使用方式从只依赖闭源 API 扩展到开放权重和本地部署。",
        "opportunity": "开源大模型追上来了吗？用普通话讲清楚。",
    },
    {
        "name": "workflow",
        "category": "behavior",
        "patterns": [r"\bworkflow(s)?\b", r"\bwork flow(s)?\b", r"\bpipeline(s)?\b", r"\bprocess(es)?\b"],
        "description": "workflow / pipeline / process 等词在数据中高频出现。",
        "why": "流程词汇高频出现，说明 AI 正被放进实际工作链路，而不只是作为单点工具使用。",
        "changed": "用户开始把 AI 嵌入日常工作流，而不是只用它生成一次性内容。",
        "opportunity": "一条真实 AI workflow 是怎么跑起来的？",
    },
    {
        "name": "AI search",
        "category": "product",
        "patterns": [r"\bAI search\b", r"\bsearch\b", r"\bretrieval\b", r"\bRAG\b"],
        "description": "search / retrieval / RAG 等词在数据中高频出现。",
        "why": "搜索和检索词汇高频出现，说明 AI 产品越来越依赖外部信息获取和知识连接。",
        "changed": "AI 产品从封闭生成转向连接资料、检索信息和回答具体问题。",
        "opportunity": "AI search 和传统搜索到底有什么不同？",
    },
    {
        "name": "video generation",
        "category": "product",
        "patterns": [r"\bvideo generation\b", r"\bvideo\b", r"\bVeo\b", r"\bgenerate video\b"],
        "description": "video / video generation / Veo 等词在数据中高频出现。",
        "why": "视频生成词汇高频出现，说明生成式 AI 的产品形态继续向视频内容生产延伸。",
        "changed": "内容创作从图文生成进一步扩展到视频生成和视频编辑。",
        "opportunity": "AI 视频生成现在适合做哪些内容？",
    },
]

CATEGORY_TITLES = {
    "technology": "🟢 技术趋势",
    "product": "🔵 产品趋势",
    "behavior": "🟣 行为趋势",
}


def request_json(url: str, *, headers: Optional[Dict[str, str]] = None, timeout: int = 20):
    response = requests.get(url, headers=headers or HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def contains_ai_keyword(text: str) -> bool:
    return bool(AI_KEYWORD_RE.search(text or ""))


def normalize_time(entry) -> str:
    return str(entry.get("published") or entry.get("updated") or "").strip()


def fetch_news() -> List[Dict[str, str]]:
    news: List[Dict[str, str]] = []
    seen_urls = set()

    for feed in NEWS_FEEDS:
        source_items: List[Dict[str, str]] = []
        for feed_url in feed["urls"]:
            try:
                parsed = feedparser.parse(feed_url, request_headers=HEADERS)
            except Exception:
                continue

            if parsed.bozo and not parsed.entries:
                continue

            for entry in parsed.entries[:MAX_NEWS_PER_SOURCE]:
                title = clean_text(entry.get("title", ""))
                url = entry.get("link", "")
                published = normalize_time(entry)
                if not title or not url:
                    continue
                source_items.append(
                    {
                        "title": title,
                        "source": feed["source"],
                        "url": url,
                        "time": published,
                    }
                )

            if source_items:
                break

        for item in source_items[:MAX_NEWS_PER_SOURCE]:
            key = item["url"].rstrip("/")
            if key in seen_urls:
                continue
            seen_urls.add(key)
            news.append(item)

    return news[:MAX_SECTION_ITEMS]


def fetch_hackernews_trends() -> List[Dict[str, str]]:
    try:
        top_story_ids = request_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    except Exception:
        return []

    trends: List[Dict[str, str]] = []
    for story_id in top_story_ids[:MAX_HN_TOP_STORIES]:
        try:
            item = request_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
        except Exception:
            continue

        if not item or item.get("type") != "story":
            continue

        title = clean_text(item.get("title", ""))
        url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        hn_url = f"https://news.ycombinator.com/item?id={story_id}"

        if not contains_ai_keyword(f"{title} {url}"):
            continue

        trends.append(
            {
                "title": title,
                "source": "HackerNews",
                "url": url,
                "time": str(item.get("time", "")),
                "hn_url": hn_url,
                "score": str(item.get("score", "")),
            }
        )

        if len(trends) >= MAX_SECTION_ITEMS:
            break

    return trends


def fetch_github_tools() -> List[Dict[str, str]]:
    params = {
        "q": "AI OR LLM OR agent in:name,description,readme",
        "sort": "stars",
        "order": "desc",
        "per_page": str(MAX_SECTION_ITEMS),
    }
    headers = {
        **HEADERS,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        response = requests.get(
            "https://api.github.com/search/repositories",
            headers=headers,
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    tools: List[Dict[str, str]] = []
    for repo in payload.get("items", []):
        tools.append(
            {
                "title": repo.get("full_name", ""),
                "source": "GitHub",
                "url": repo.get("html_url", ""),
                "time": repo.get("updated_at", ""),
                "description": repo.get("description") or "",
                "stars": str(repo.get("stargazers_count", "")),
            }
        )

    return tools


def fetch_product_hunt_tools() -> List[Dict[str, str]]:
    token = os.getenv("PRODUCT_HUNT_TOKEN")
    if not token:
        return []

    query = """
    query {
      posts(first: 10, topic: "artificial-intelligence") {
        edges {
          node {
            name
            tagline
            url
            createdAt
          }
        }
      }
    }
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "AI-Daily-Bot/3.0",
    }

    try:
        response = requests.post(
            "https://api.producthunt.com/v2/api/graphql",
            headers=headers,
            json={"query": query},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    tools: List[Dict[str, str]] = []
    edges = payload.get("data", {}).get("posts", {}).get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        tools.append(
            {
                "title": node.get("name", ""),
                "source": "Product Hunt",
                "url": node.get("url", ""),
                "time": node.get("createdAt", ""),
                "description": node.get("tagline", ""),
            }
        )

    return tools


def fetch_tools() -> List[Dict[str, str]]:
    tools = []
    tools.extend(fetch_github_tools())
    tools.extend(fetch_product_hunt_tools())
    return tools[:MAX_SECTION_ITEMS]


def fetch_real_ai_data() -> Dict[str, List[Dict[str, str]]]:
    return {
        "news": fetch_news(),
        "trends": fetch_hackernews_trends(),
        "tools": fetch_tools(),
    }


def build_analysis_corpus(data: Dict[str, List[Dict[str, str]]]) -> str:
    parts: List[str] = []
    for section in ("news", "trends", "tools"):
        for item in data.get(section, []):
            parts.extend(
                [
                    item.get("title", ""),
                    item.get("source", ""),
                    item.get("description", ""),
                    item.get("url", ""),
                ]
            )
    return "\n".join(parts)


def count_keyword_occurrences(text: str, patterns: List[str]) -> int:
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)


def analyze_trends(data: Dict[str, List[Dict[str, str]]]) -> Dict[str, List[Dict[str, object]]]:
    corpus = build_analysis_corpus(data)
    analysis = {"technology": [], "product": [], "behavior": []}

    for keyword in TREND_KEYWORDS:
        count = count_keyword_occurrences(corpus, keyword["patterns"])
        if count < TREND_THRESHOLD:
            continue
        analysis[keyword["category"]].append(
            {
                "name": keyword["name"],
                "count": count,
                "strength": "强趋势" if count >= STRONG_TREND_THRESHOLD else "趋势",
                "description": keyword["description"],
                "why": keyword["why"],
                "changed": keyword["changed"],
                "opportunity": keyword["opportunity"],
            }
        )

    for category in analysis:
        analysis[category].sort(key=lambda item: item["count"], reverse=True)

    return analysis


def flatten_detected_trends(trend_analysis: Dict[str, List[Dict[str, object]]]) -> List[Dict[str, object]]:
    trends = []
    for items in trend_analysis.values():
        trends.extend(items)
    return sorted(trends, key=lambda item: item["count"], reverse=True)


def generate_insights(trend_analysis: Dict[str, List[Dict[str, object]]]) -> Dict[str, List[str]]:
    detected = flatten_detected_trends(trend_analysis)
    top_trends = detected[:3]
    return {
        "why_it_matters": [str(item["why"]) for item in top_trends],
        "what_changed": [str(item["changed"]) for item in top_trends],
        "content_opportunities": [str(item["opportunity"]) for item in detected[:5]],
    }


def generate_report(data: Dict[str, List[Dict[str, str]]]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trend_analysis = analyze_trends(data)
    insights = generate_insights(trend_analysis)

    report = f"""# 📊 AI情报日报 v3

生成时间：{generated_at}

---

## AI News

"""
    if data["news"]:
        for item in data["news"]:
            report += f"""- 标题：{item["title"]}
- 来源：{item["source"]}
- 时间：{item["time"]}
- 链接：{item["url"]}

"""
    else:
        report += "- 未获取到 RSS 新闻数据。\n\n"

    report += """---

## Trends

"""
    if data["trends"]:
        for item in data["trends"]:
            report += f"""- 标题：{item["title"]}
- 来源：{item["source"]}
- 分数：{item.get("score", "")}
- 链接：{item["url"]}
- HN链接：{item.get("hn_url", "")}

"""
    else:
        report += "- 未获取到符合关键词的 HackerNews Top 50 条目。\n\n"

    report += """---

## Tools

"""
    if data["tools"]:
        for item in data["tools"]:
            report += f"""- 名称：{item["title"]}
- 来源：{item["source"]}
- 描述：{item.get("description", "")}
- 时间：{item["time"]}
- 链接：{item["url"]}

"""
    else:
        report += "- 未获取到工具数据。Product Hunt 需要配置 PRODUCT_HUNT_TOKEN；GitHub API 失败时返回空数组。\n\n"

    report += """---

# 📈 Trend Analysis（趋势分析）

"""
    for category, title in CATEGORY_TITLES.items():
        report += f"## {title}\n\n"
        items = trend_analysis[category]
        if not items:
            report += f"- 未发现出现次数 ≥ {TREND_THRESHOLD} 的趋势关键词。\n\n"
            continue
        for item in items:
            report += f"""- 趋势名称：{item["name"]}（{item["strength"]}）
- 出现次数：{item["count"]}
- 说明：{item["description"]}

"""

    report += """---

# 🧠 Insight（核心洞察）

## 💡 Why it matters

"""
    if insights["why_it_matters"]:
        for item in insights["why_it_matters"]:
            report += f"- {item}\n"
    else:
        report += "- 今日数据中没有达到频次阈值的趋势，暂不生成洞察。\n"

    report += "\n## 🔄 What changed\n\n"
    if insights["what_changed"]:
        for item in insights["what_changed"]:
            report += f"- {item}\n"
    else:
        report += "- 今日数据中没有达到频次阈值的趋势，暂不生成变化说明。\n"

    report += "\n## 🎯 Content opportunities（内容机会）\n\n"
    if insights["content_opportunities"]:
        for item in insights["content_opportunities"]:
            report += f"- {item}\n"
    else:
        report += "- 今日数据中没有达到频次阈值的趋势，暂不生成内容机会。\n"

    report += """\n---

## Summary

- 本日报仅使用 RSS 或官方 API 数据源。
- 趋势分析只基于 news / trends / tools 的关键词频次统计。
- 出现次数 ≥ 3 记为趋势，出现次数 ≥ 5 记为强趋势。
- Insight 与内容机会只从达到阈值的趋势关键词生成。
"""
    return report


def send_to_wechat(report: str) -> Dict[str, object]:
    response = requests.post(
        SERVER_CHAN_API,
        data={
            "title": "📊 AI情报日报",
            "desp": report,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    data = fetch_real_ai_data()
    report = generate_report(data)
    print(report)
    print("正在推送到 Server酱...")
    result = send_to_wechat(report)
    print("Server酱返回：", result)


if __name__ == "__main__":
    main()
