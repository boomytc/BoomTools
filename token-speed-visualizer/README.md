# Token 生成速度可视化工具

一个无 Node 构建依赖的静态 Web 工具，用于直观展示不同 token 生成速度的体感差异。

## 技术栈

- HTML
- Tailwind CSS browser build
- Alpine.js
- Vanilla JS
- 本地 CSS

Tailwind 使用官方 browser build，以避免 `npm install` 和构建步骤。官方不建议将 browser build 作为生产构建方案；如果后续要做正式发布，可以将 Tailwind 预编译 CSS 和 Alpine.js vendor 到本仓库。

## 运行

直接打开：

```bash
open index.html
```

或启动一个静态服务器：

```bash
python3 -m http.server 8000
```

然后访问 `http://127.0.0.1:8000`。

## 文件结构

```text
token-speed-visualizer/
├── index.html
├── static/
│   ├── app.js
│   └── styles.css
└── README.md
```
