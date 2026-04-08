"""
MiroFish - Hugging Face Spaces 启动入口
同时提供 API 和静态前端文件
"""

import os
import sys

if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for err in errors:
            print(f"  - {err}")
        print("\n请在 HF Space Settings 中配置环境变量")
        sys.exit(1)

    app = create_app()

    # 服务前端静态文件（Vue build 产物）
    frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    if os.path.exists(frontend_dist):
        from flask import send_from_directory

        @app.route('/')
        def serve_index():
            return send_from_directory(frontend_dist, 'index.html')

        @app.route('/assets/<path:filename>')
        def serve_assets(filename):
            return send_from_directory(os.path.join(frontend_dist, 'assets'), filename)

        # SPA fallback: 所有非 API 路由都返回 index.html
        @app.errorhandler(404)
        def spa_fallback(e):
            request_path = e.description if hasattr(e, 'description') else ''
            from flask import request
            if not request.path.startswith('/api/'):
                return send_from_directory(frontend_dist, 'index.html')
            return {"success": False, "error": "Not found"}, 404

        print(f"前端静态文件: {frontend_dist}")
    else:
        print(f"警告: 前端 dist 目录不存在: {frontend_dist}")

    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 7860))

    print(f"Starting MiroFish on {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
