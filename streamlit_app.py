"""
小红书/TikTok 评论监控管理系统 - Streamlit 前端
"""
import os
import json
import streamlit as st
import requests
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# API 地址配置（支持环境变量）
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="社媒监控", page_icon="📱")

st.title("📱 社媒评论监控")
st.caption("支持小红书和 TikTok 评论实时监控")

# Cookie 管理
st.subheader("🍪 Cookie 设置")

platform_tab = st.tabs(["小红书", "TikTok"])

with platform_tab[0]:
    st.write("📕 小红书 Cookie")
    xhs_cookie_input = st.text_area("小红书 Cookie (JSON格式)", 
                                     placeholder='[{"name": "cookie_name", "value": "cookie_value", "domain": ".xiaohongshu.com", "path": "/"}]',
                                     height=100,
                                     label_visibility="collapsed")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 保存小红书 Cookie", use_container_width=True, key="save_xhs"):
            try:
                cookies = json.loads(xhs_cookie_input) if xhs_cookie_input else []
                res = requests.post(f"{API_BASE}/api/v1/cookies", json={"cookies": json.dumps(cookies)})
                if res.ok:
                    data = res.json()
                    st.success(data.get('message', '保存成功'))
                else:
                    st.error(res.json().get("detail", "保存失败"))
            except:
                st.error("JSON格式错误")
    with col2:
        if st.button("🗑️ 清除小红书 Cookie", use_container_width=True, key="clear_xhs"):
            requests.delete(f"{API_BASE}/api/v1/cookies", params={"platform": "xiaohongshu"})
            st.success("已清除小红书 Cookie")

with platform_tab[1]:
    st.write("🎵 TikTok Cookie")
    tiktok_cookie_input = st.text_area("TikTok Cookie (JSON格式)", 
                                        placeholder='[{"name": "cookie_name", "value": "cookie_value", "domain": ".tiktok.com", "path": "/"}]',
                                        height=100,
                                        label_visibility="collapsed")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 保存 TikTok Cookie", use_container_width=True, key="save_tiktok"):
            try:
                cookies = json.loads(tiktok_cookie_input) if tiktok_cookie_input else []
                res = requests.post(f"{API_BASE}/api/v1/cookies", json={"cookies": json.dumps(cookies)})
                if res.ok:
                    data = res.json()
                    st.success(data.get('message', '保存成功'))
                else:
                    st.error(res.json().get("detail", "保存失败"))
            except:
                st.error("JSON格式错误")
    with col2:
        if st.button("🗑️ 清除 TikTok Cookie", use_container_width=True, key="clear_tiktok"):
            requests.delete(f"{API_BASE}/api/v1/cookies", params={"platform": "tiktok"})
            st.success("已清除 TikTok Cookie")

st.divider()

# 提交任务
st.subheader("🚀 开始监控")

platform = st.radio("选择平台", ["📕 小红书", "🎵 TikTok"], horizontal=True)

url_placeholder = {
    "📕 小红书": "https://www.xiaohongshu.com/explore/xxx",
    "🎵 TikTok": "https://www.tiktok.com/@username/video/xxx"
}

url = st.text_input("帖子URL", placeholder=url_placeholder[platform])

if st.button(" 提交监控", type="primary"):
    if url:
        res = requests.post(f"{API_BASE}/api/v1/posts/monitor", json={"url": url})
        if res.ok:
            data = res.json()
            st.success(data.get('message', '已提交'))
            st.info(f"任务ID: {data.get('job_id', '')}")
        else:
            st.error(res.json().get("detail", "提交失败"))
    else:
        st.warning("请输入URL")

st.divider()

# 任务列表
st.subheader("📋 任务列表")

if st.button("🔄 刷新列表"):
    st.rerun()

try:
    jobs = requests.get(f"{API_BASE}/api/v1/jobs").json()
    
    if jobs:
        for job in jobs:
            # 判断平台
            is_tiktok = job.get('platform') == 'tiktok' or 'tiktok.com' in job.get('url', '').lower()
            platform_icon = "🎵" if is_tiktok else "📕"
            platform_name = "TikTok" if is_tiktok else "小红书"
            
            status_icon = {"running": "🟢", "completed": "⚪", "failed": "🔴", "pending": "🟡"}.get(job["status"], "⚪")
            
            with st.expander(f"{platform_icon} {status_icon} {job['job_id'][:8]}... - {job['status']} ({job['poll_count']}/{job['max_polls']})", expanded=(job["status"] == "running")):
                st.text(f"平台: {platform_name}")
                st.text(f"URL: {job['url'][:60]}...")
                st.text(f"创建时间: {job['created_at']}")
                
                if job["status"] == "running":
                    if st.button("❌ 取消", key=f"cancel_{job['job_id']}"):
                        requests.delete(f"{API_BASE}/api/v1/jobs/{job['job_id']}")
                        st.rerun()
    else:
        st.info("暂无任务")
except Exception as e:
    st.error(f"连接API失败，请检查后端是否启动: {e}")

# 自动刷新
auto_refresh = st.checkbox("⏱️ 自动刷新 (30秒)")
if auto_refresh:
    time.sleep(30)
    st.rerun()
