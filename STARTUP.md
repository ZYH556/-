# ReflexLearn 解压即用启动说明

本包已经包含运行依赖：

- 后端 Python 虚拟环境：`.venv/`
- Web 前端依赖：`frontend/node_modules/`
- UniApp 端依赖：`uniapp/node_modules/`

因此正常情况下不需要重新执行 `pip install` 或 `npm install`。

## 一键启动

在项目根目录双击：

```text
一键启动.bat
```

或在命令行执行：

```bat
一键启动.bat
```

脚本会打开 3 个命令行窗口：

- 后端 API：`http://127.0.0.1:8000`
- Web 前端：`http://127.0.0.1:3000`
- UniApp H5：以 UniApp 窗口输出的地址为准，通常是 `http://localhost:5173`

默认演示账号：

```text
用户名：admin
密码：reflexlearn-admin
```

## 推荐录屏入口

Web 端：

```text
http://127.0.0.1:3000
```

UniApp H5 端：

```text
查看 “ReflexLearn UniApp H5” 命令行窗口输出的 Local 地址
```

推荐录屏路径：

```text
今日学习 -> AI 导师 -> 智能辅导 -> 精品课程 -> 课程详情 -> 个人知识库 -> 错题本 -> 学习空间 -> 成长档案
```

UniApp 端推荐路径：

```text
今日 -> 知识库 -> 辅导 -> 课程 -> 画像
```

## 手动启动

如果不想使用一键脚本，可以分别运行：

```bat
set PYTHONPATH=%cd%\src
.venv\Scripts\uvicorn.exe reflexlearn.main:app --host 127.0.0.1 --port 8000
```

```bat
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

```bat
cd uniapp
npm run dev:h5
```

## 如果依赖缺失

通常不会发生。如果复制过程中漏掉了依赖目录，可重新安装：

```bat
.venv\Scripts\python.exe -m pip install -e .
```

```bat
cd frontend
npm install
```

```bat
cd uniapp
npm install
```

## 注意

- 本演示包不包含本机私密 `.env` / `frontend/.env.local`。
- 首次运行时，`一键启动.bat` 会自动从 `.env.example` 和 `frontend/.env.example` 复制演示配置。
- 大模型和虚拟人密钥不是启动必需项；未配置时页面仍可用假数据完成录屏展示。
- 关闭项目时，直接关闭一键启动打开的 3 个命令行窗口即可。
