"""
为 Markdown 专题报告添加交叉引用锚点，使正文中的 [N] 可点击跳转到文末参考文献。
- 正文: [N] -> [[N]](#ref-N)
- 参考文献: [N] Title... -> <a id="ref-N"></a>[N] Title...
"""
import re, pathlib, sys

FILES = [
    "专题报告一：SDL闭环系统架构与多智能体协同.md",
    "专题报告二：AI实验设计优化算法——LLM+BO与RL前沿框架.md",
    "专题报告三：LLM领域适配微调与自驱动实验室容错自愈.md",
    "专题报告四：电化学数据深度学习编码与AI驱动HER性能提升.md",
]

BASE = pathlib.Path(__file__).parent

# Patterns to skip (not real citations)
SKIP_PATTERNS = {'image1', 'image2', 'image3', 'image4', 'image5',
                 'image6', 'image7', 'image8', 'image9', 'image10'}

def find_ref_section_start(lines):
    """Find the line index where the reference section begins."""
    ref_headers = ['## 参考文献', '## 引用的著作', '#### 引用的著作',
                   '#### **引用的著作**', '### 电化学深度学习编码方法核心文献']
    for i, line in enumerate(lines):
        stripped = line.strip()
        for hdr in ref_headers:
            if stripped.startswith(hdr) or stripped == hdr:
                return i
    return len(lines)  # no ref section found

def process_file(filepath):
    text = filepath.read_text(encoding='utf-8')
    lines = text.split('\n')
    
    ref_start = find_ref_section_start(lines)
    
    # Collect all citation numbers used in references
    ref_nums = set()
    for line in lines[ref_start:]:
        m = re.match(r'^\s*\[(\d+)\]', line)
        if m:
            ref_nums.add(m.group(1))
    
    # --- Process reference section: add anchors ---
    new_ref_lines = []
    for line in lines[ref_start:]:
        m = re.match(r'^(\s*)\[(\d+)\]', line)
        if m and m.group(2) not in SKIP_PATTERNS:
            num = m.group(2)
            prefix = m.group(1)
            anchor = f'<a id="ref-{num}"></a>'
            if anchor not in line:
                line = f'{prefix}{anchor}[{num}]' + line[m.end():]
        new_ref_lines.append(line)
    
    # --- Process body: make citations clickable ---
    # Pattern: [N] where N is a number, but NOT already inside a markdown link [[N]](#ref-N)
    # and NOT at start of line (which would be a reference entry)
    def replace_citation(match):
        full = match.group(0)
        num = match.group(1)
        if num in SKIP_PATTERNS:
            return full
        # Check if already converted (preceded by '[')
        start = match.start()
        if start > 0 and text_body[start-1] == '[':
            return full
        # Check if it's preceded by '#ref-' (already a link target)
        if start > 5 and '#ref-' in text_body[max(0,start-10):start]:
            return full
        return f'[[{num}]](#ref-{num})'
    
    body_lines = lines[:ref_start]
    text_body = '\n'.join(body_lines)
    
    # Don't replace [N] at start of line (reference entries that might be in body)
    # Replace [N] in running text
    # Pattern: match [N] where N is 1-3 digits, not preceded by [ or (
    new_body = re.sub(
        r'(?<!\[)(?<!\(#ref-)\[(\d{1,3})\](?!\(#)',
        replace_citation,
        text_body
    )
    
    # Reconstruct
    result = new_body + '\n' + '\n'.join(new_ref_lines)
    
    filepath.write_text(result, encoding='utf-8')
    
    # Stats
    anchor_count = sum(1 for l in new_ref_lines if '<a id="ref-' in l)
    link_count = len(re.findall(r'\[\[\d+\]\]\(#ref-', new_body))
    print(f"  {filepath.name}: {anchor_count} anchors, {link_count} body links")

def main():
    print("Processing cross-references...")
    for fname in FILES:
        fp = BASE / fname
        if fp.exists():
            process_file(fp)
        else:
            print(f"  WARNING: {fname} not found!")
    print("Done!")

if __name__ == '__main__':
    main()
