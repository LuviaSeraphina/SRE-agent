"""
语义分块器 — 按 Markdown 标题/段落切分, 保持上下文连贯
"""
import re
from typing import List, Dict


"""
方法: split_by_headers(text, min_chunk_size), 按 Markdown ## / ### 标题切分, 每段保留标题层级

"""
def split_by_headers(text:str, min_chunk_size:int=100)->List[Dict[str,str]]:
    #匹配 ## 或 ### 标题行
    header_re=re.compile(r'^(#{2,4})\s+(.+)$', re.MULTILINE)

    chunks=[]
    parts=header_re.split(text)

    #parts[0] = 标题前的内容, parts[1]=#级别, parts[2]=标题文本, parts[3]=内容...
    current_title=""
    current_content=[]

    i=0
    while i<len(parts):
        if i==0:
            #标题前的内容
            if parts[0].strip():
                current_content.append(parts[0].strip())
            i+=1
            continue

        if i+2<len(parts):
            level=parts[i]     # ## 或 ###
            title=parts[i+1].strip()  # 标题文本
            body=parts[i+2]    # 标题下的内容

            #保存上一个块
            if current_content:
                chunk_text="\n".join(current_content).strip()
                if len(chunk_text)>=min_chunk_size:
                    chunks.append({
                        "title":current_title,
                        "content":chunk_text,
                    })
                current_content=[]

            #更新当前标题 (保留层级)
            full_title=title
            if current_title:
                #如果之前有二级标题, 当前是三级标题, 组合
                full_title=f"{current_title} > {title}"
            current_title=full_title
            current_content.append(body.strip())
            i+=3
        else:
            break

    #最后一个块
    if current_content:
        chunk_text="\n".join(current_content).strip()
        if len(chunk_text)>=min_chunk_size:
            chunks.append({
                "title":current_title,
                "content":chunk_text,
            })

    return chunks


"""
方法: sliding_window_chunks(text, chunk_size, overlap), 滑动窗口分块 — 对大段落做二次切分, 在句号/换行处断开

"""
def sliding_window_chunks(
    text:str,
    chunk_size:int=500,
    overlap:int=80,
)->List[str]:
    if len(text)<=chunk_size:
        return [text]

    chunks=[]
    start=0
    while start<len(text):
        end=start+chunk_size
        chunk=text[start:end]

        #尝试在句号/换行处断开
        if end<len(text):
            #找最近的断点
            for sep in ['\n\n','\n','。','. ','；',';']:
                last=chunk.rfind(sep)
                if last>chunk_size//2:
                    chunk=chunk[:last+len(sep)]
                    end=start+len(chunk)
                    break

        chunks.append(chunk.strip())
        start=end-overlap

    return [c for c in chunks if len(c)>=50]

"""
方法: chunk_markdown_file(filepath, chunk_size, overlap), 对单个 Markdown 文件做完整分块 -- 标题切分 + 滑动窗口二次切分

"""
def chunk_markdown_file(
    filepath:str,
    chunk_size:int=500,
    overlap:int=80,
)->List[Dict[str,str]]:
    with open(filepath, "r", encoding="utf-8") as f:
        text=f.read()

    #提取一级标题作为文件名
    filename=filepath.rsplit("/",1)[-1].replace(".md","")

    sections=split_by_headers(text)
    if not sections:
        #无标题, 直接滑动窗口
        sub=sliding_window_chunks(text, chunk_size, overlap)
        return [{"title":filename, "content":c} for c in sub]

    result=[]
    for sec in sections:
        title=sec["title"] or filename
        content=sec["content"]

        if len(content)<=chunk_size:
            result.append({"title":title, "content":content})
        else:
            #大段二次切分
            sub=sliding_window_chunks(content, chunk_size, overlap)
            for i, c in enumerate(sub):
                suffix=f" (第{i+1}段)" if len(sub)>1 else ""
                result.append({"title":title+suffix, "content":c})

    return result
