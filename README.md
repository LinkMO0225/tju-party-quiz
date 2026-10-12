# 入党申请人复习

天津大学入党申请人培训结业考试的复习工具。**单页网页：无后端、无登录、无外部请求**——一个 HTML 文件打开就能刷题。

在线版（**推荐给同学用**）：<https://tju-party-quiz.app.workbuddy.host/>

> 这是分享给考生时应该发的那个地址。国内直连可打开，不需要任何工具。
> 平台不提供自定义响应头，所以这版不走 Gzip、缓存也弱一些，但打开就能用。

GitHub Pages：<https://linkmo0225.github.io/tju-party-quiz/>

> 有 Gzip 和 `Cache-Control`/`ETag`，传输量约为上面那版的 1/3。
> 但 `github.io` 在国内 DNS 被污染，**不加工具打不开**——所以它适合开发者预览，不适合发给考生。

## 功能

| 模块 | 说明 |
| --- | --- |
| 卡片背诵 | 87 张填空题卡片，一张一屏，点开看答案；可标记、可筛范围 |
| 做题测验 | 579 道单选 / 多选，判对错；选项乱序，防止背「位置」而不是背内容 |
| 错题强化 | 答错自动进错题池，按「3 道普通题 + 1 道错题」循环穿插，答对才出池，直到清空 |
| 关于本网站 | 数据来源、使用须知、鸣谢，以及本站更新日志 |

## 目录结构

```
index.html                    # 成品：完整应用（同时也是 GitHub Pages 的首页）
scripts/
  gen_app.py                  # 生成器：读题库数据 + 更新日志，产出 index.html
  test_app.js                 # 测试：在 DOM stub 里真跑页面脚本，共 163 项断言
  test_regressions.js         # 筛选、存储并发、异常恢复和无障碍回归检查
  verify_pages_http.py        # 已部署页面的 Gzip、304 和版本一致性验收
  test_pages_http.py          # HTTP 验收工具的正常与异常场景回归检查
pdf90/                        # 题库数据（生成器的输入）
  merged_bank.json            #   选择题：第 90 期相关 + 往期真题卷
  fill_cards.json             #   填空卡片
  party_bank.json             #   网上党课第 1–20 讲
output/
  更新日志.md                  # 版本记录（会被嵌进网页的「关于本网站」页）
  04-简答题背诵（纯净版）.md     # 简答 / 辨析 / 论述 / 材料分析 背诵手册
```

## 自己跑一遍

需要 Python 3（生成）和 Node.js（只在跑测试时用）。**无第三方依赖，只用标准库。**

```bash
python scripts/gen_app.py     # 产出 index.html 与 output/入党申请人复习.html（同一份内容）
node scripts/test_app.js      # 163 项断言，直接验证首页，全绿时打印「全部检查通过」
node scripts/test_regressions.js # 功能和稳定性问题的回归检查
```

两个脚本都用相对路径定位文件，clone 到任何目录都能跑。

## GitHub Pages 压缩与缓存

使用 Pages 原生 Gzip、ETag / Last-Modified 和平台缓存；仓库不添加无效的自定义响应头文件。具体配置、限制和发布流程见 [GitHub Pages 压缩与缓存方案](docs/GitHub-Pages压缩与缓存.md)。

```bash
python scripts/test_pages_http.py
python scripts/verify_pages_http.py https://linkmo0225.github.io/tju-party-quiz/ --output pages-http-report.json
```

发布后增加 `--expected-file index.html` 可以核对线上内容与当前发布版本是否一致。Pages 部署成功后，新增的 Actions 工作流会自动执行该验收，也支持手动指定网址运行。

## 数据

| 来源 | 题量 |
| --- | --- |
| 《复习指导与专题训练》第九十期版（2026-09） | 71 |
| 25261 学期版真题卷 | 171 |
| 学生党建平台网上党课第 1–20 讲 | 337 |
| **选择题合计** | **579** |

另有填空卡片 87 张；背诵手册收录 144 道（填空 87 + 简答 39 + 辨析 6 + 论述 5 + 材料分析 7）。

所有选择题答案做过**逐题文本交叉校验**（用选项文本反查，不沿用平台下标）。

## 说明

- 内容整理自公开复习资料，**不是官方答案**；如与官方题库有出入，以官方为准。
- 进度存在浏览器 `localStorage`，不上传任何数据，也没有后端。
- 同一站点的多个标签页按题目同步进度，已有进度兼容读取；本地保存失败会提示并提供重试。
- 平台对不同账号会随机化题目顺序与选项顺序，因此**建议按选项内容记忆，不要按 A/B/C/D 的位置记**。

## 更新日志

见 [`output/更新日志.md`](output/更新日志.md)，或在网页里：首页 → 关于本网站 → 版本号。

## License

[MIT](LICENSE) © 2026 Link_MO

代码可自由使用、修改、分发。题目内容整理自公开复习资料，非官方答案。

---

鸣谢：**Wilson**（AI 助手 · DeepSeek V4.1 Flash）参与整理与开发；以及 26 天大 JiaYuan 群参与测试的群友。
