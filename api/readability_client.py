from typing import Dict
from readability import Document
from lxml import html as lxml_html
import re


class ReadabilityError(Exception):
    pass


def extract_readability(html_content: bytes | str) -> Dict[str, str]:
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='ignore')
    
    doc = Document(html_content)
    title = doc.title() or "Untitled"
    content = doc.summary()
    
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='ignore')
    
    content = _clean_structural_elements(content)
    content = _ensure_title(content, title)
    
    text_content = _html_to_text(content)
    
    if not text_content or len(text_content) < 100:
        text_content = _extract_fallback_content(html_content)
        content = _extract_fallback_html(html_content)
    
    return {
        "title": title,
        "content": content,
        "text_content": text_content
    }


def _clean_structural_elements(html_content: str) -> str:
    try:
        tree = lxml_html.fromstring(html_content)
        for tag in ['nav', 'header', 'footer', 'aside', 'script', 'style']:
            for elem in tree.iter(tag):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
        for elem in tree.xpath('.//p[contains(@class, "shortdescription")]'):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
        return lxml_html.tostring(tree, encoding='unicode')
    except Exception:
        for tag in ['nav', 'header', 'footer', 'aside', 'script', 'style']:
            html_content = re.sub(
                rf'<{tag}[^>]*>.*?</{tag}>',
                '',
                html_content,
                flags=re.DOTALL | re.IGNORECASE
            )
        html_content = re.sub(
            r'<p[^>]*class="[^"]*shortdescription[^"]*"[^>]*>.*?</p>',
            '',
            html_content,
            flags=re.DOTALL | re.IGNORECASE
        )
        return html_content


def _ensure_title(html_content: str, title: str) -> str:
    try:
        tree = lxml_html.fromstring(html_content)
        has_h1 = any(elem.tag == 'h1' for elem in tree.iter())
        if not has_h1:
            heading = lxml_html.fromstring(f'<h1>{title}</h1>')
            body = tree.find('.//body')
            if body is not None:
                body.insert(0, heading)
            else:
                tree.insert(0, heading)
            return lxml_html.tostring(tree, encoding='unicode')
    except Exception:
        if not re.search(r'<h1[^>]*>', html_content, re.IGNORECASE):
            html_content = f'<h1>{title}</h1>\n' + html_content
    return html_content


def _extract_fallback_content(html_content: str) -> str:
    from xml.etree import ElementTree as ET
    
    try:
        root = ET.fromstring(f"<html>{html_content}</html>", ET.HTMLParser())
        
        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside']:
            for elem in root.iter(tag):
                elem.text = ''
                elem.tail = ''
        
        text_parts = []
        for elem in root.iter('*'):
            if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'li', 'td', 'th']:
                if elem.text:
                    text = elem.text.strip()
                    if text and len(text) > 10:
                        text_parts.append(text)
        
        return ' '.join(text_parts[:50])
    
    except Exception:
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()[:5000]


def _extract_fallback_html(html_content: str) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
    return text[:10000]


def _html_to_text(html_content: str | bytes) -> str:
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='ignore')
    text = re.sub(r'<[^>]+>', '', html_content)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
