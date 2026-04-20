"""
小红书评论轮询服务API测试脚本。
演示如何使用API端点。
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"


def test_health_check():
    """测试健康检查端点。"""
    print("=" * 60)
    print("1. 测试健康检查")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_submit_post(url):
    """测试提交帖子进行监控。"""
    print("=" * 60)
    print("2. 提交帖子进行监控")
    print("=" * 60)

    payload = {"url": url}
    response = requests.post(
        f"{BASE_URL}/api/v1/posts/monitor",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

    job_id = result.get("job_id")
    print(f"\n任务ID: {job_id}")
    return job_id


def test_get_job_status(job_id):
    """测试获取任务状态。"""
    print("\n" + "=" * 60)
    print("3. 检查任务状态")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_list_jobs():
    """测试列出所有任务。"""
    print("=" * 60)
    print("4. 列出所有任务")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/v1/jobs")
    print(f"状态码: {response.status_code}")
    print(f"任务总数: {len(response.json())}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_cancel_job(job_id):
    """测试取消任务。"""
    print("=" * 60)
    print("5. 取消任务")
    print("=" * 60)

    response = requests.delete(f"{BASE_URL}/api/v1/jobs/{job_id}")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def main():
    """运行所有测试。"""
    print("\n" + "=" * 60)
    print("小红书评论轮询服务 - API测试套件")
    print("=" * 60 + "\n")

    # 测试1: 健康检查
    test_health_check()

    # 测试2: 提交帖子（使用真实的小红书URL进行实际测试）
    test_url = "https://www.xiaohongshu.com/explore/69e3f650000000001a027857?xsec_token=ABo_qhQZNEF9mrrrziLRqQz1feBJwO88Dfc7-YibOxBqM=&xsec_source=pc_feed"
    job_id = test_submit_post(test_url)

    # 等待任务启动
    time.sleep(2)

    # 测试3: 检查任务状态
    test_get_job_status(job_id)

    # 测试4: 列出所有任务
    test_list_jobs()

    # 测试5: 取消任务（可选 - 如果想让它运行则注释掉）
    # test_cancel_job(job_id)

    # 测试6: 无效URL
    # test_invalid_url()

    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务器。")
        print("请确保服务正在运行: python main.py")
    except Exception as e:
        print(f"错误: {e}")
