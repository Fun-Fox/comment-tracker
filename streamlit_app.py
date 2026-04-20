"""
小红书评论监控管理系统 - Streamlit 前端
"""
import os
import json
import streamlit as st
import requests
import time

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="小红书监控", page_icon="📱")

st.title("📱 小红书评论监控")

# Cookie 管理
st.subheader("🍪 Cookie 设置")

col1, col2 = st.columns([4, 1])
with col1:
    cookie_input = st.text_area("Cookie (JSON格式)", height=80, label_visibility="collapsed")

with col2:
    if st.button("保存", use_container_width=True):
        try:
            cookies = json.loads(cookie_input) if cookie_input else []
            res = requests.post(f"{API_BASE}/api/v1/cookies", json={"cookies": json.dumps(cookies)})
            if res.ok:
                st.success("保存成功")
            else:
                st.error("保存失败")
        except:
            st.error("JSON格式错误")
    
    if st.button("清除", use_container_width=True):
        requests.delete(f"{API_BASE}/api/v1/cookies")
        st.success("已清除")

st.divider()

# 提交任务
st.subheader("🚀 开始监控")

url = st.text_input("帖子URL", placeholder="https://www.xiaohongshu.com/explore/xxx")

if st.button("提交监控", type="primary"):
    if url:
        res = requests.post(f"{API_BASE}/api/v1/posts/monitor", json={"url": url})
        if res.ok:
            st.success("已提交")
        else:
            st.error(res.json().get("detail", "提交失败"))
    else:
        st.warning("请输入URL")

st.divider()

# 任务列表
st.subheader("📋 任务列表")

if st.button("刷新列表"):
    st.rerun()

try:
    jobs = requests.get(f"{API_BASE}/api/v1/jobs").json()
    
    if jobs:
        for job in jobs:
            status_icon = {"running": "🟢", "completed": "⚪", "failed": "🔴", "pending": "🟡"}.get(job["status"], "⚪")
            
            with st.expander(f"{status_icon} {job['job_id'][:8]}... - {job['status']} ({job['poll_count']}/{job['max_polls']})", expanded=(job["status"] == "running")):
                st.text(f"URL: {job['url'][:60]}...")
                st.text(f"创建时间: {job['created_at']}")
                
                if job["status"] == "running":
                    if st.button("取消", key=f"cancel_{job['job_id']}"):
                        requests.delete(f"{API_BASE}/api/v1/jobs/{job['job_id']}")
                        st.rerun()
    else:
        st.info("暂无任务")
except:
    st.error("连接API失败，请检查后端是否启动")

# 自动刷新
if st.checkbox("自动刷新 (30秒)"):
    time.sleep(30)
    st.rerun()
