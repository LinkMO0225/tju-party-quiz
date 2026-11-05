# 入党申请人复习

天津大学入党申请人培训结业考试的复习工具。**单页网页：无后端、无登录、无外部请求**——一个 HTML 文件打开就能刷题。

在线版（**推荐**）：<https://linkmo0225.github.io/tju-party-quiz/>

> 国内直连可用（2026-10-12 实测，手机流量与宽带均通过）。有 Gzip 和缓存，首屏约 87 KB。

备用：<https://tju-party-quiz.app.workbuddy.host/>

> 裸连同样可开；无 Gzip，首屏约 282 KB。

## 功能

| 模块 | 说明 |
| --- | --- |
| 卡片背诵 | 22 张填空题卡片，一张一屏，点开看答案；可标记、可筛范围 |
| 做题测验 | 586 道单选 / 多选，判对错；选项乱序，防止背「位置」而不是背内容 |
| 错题强化 | 答错自动进错题池，按「普通题 + 错题」循环穿插（间隔可调，默认 3 题），答对才出池，直到清空 |
| 关于本网站 | 数据来源、使用须知、鸣谢，以及本站更新日志 |

## 目录结构

```
index.html                    # 成品：完整应用（同时也是 GitHub Pages 的首页）
scripts/
  build_bank6.py              # 数据管道：合并 pdf90 + pdf91 原始题，去重分类，产出 data/
  gen_app.py                  # 生成器：读 data/ 与更新日志，产出 index.html
  test_app.js                 # 测试：在 DOM stub 里真跑页面脚本，共 165 项断言
  test_regressions.js         # 筛选、存储并发、异常恢复和无障碍回归检查
  verify_pages_http.py        # 已部署页面的 Gzip、304 和版本一致性验收
  test_pages_http.py          # HTTP 验收工具的正常与异常场景回归检查
data/                         # 构建产物：合并去重后的最终题库
  bank.json                   #   选择题
  cards.json                  #   填空卡片
pdf90/                        # 第 90 期题库原始数据
  merged_bank.json            #   选择题：第 90 期相关 + 往期真题卷
  fill_cards.json             #   填空卡片
  party_bank.json             #   网上党课第 1–20 讲
pdf91/
  bank91_raw.json             # 第 91 期册子解析出的 92 选择 + 25 填空
output/
  更新日志.md                  # 版本记录（会被嵌进网页的「关于本网站」页）
  04-简答题背诵（纯净版）.md     # 简答 / 辨析 / 论述 / 材料分析 背诵手册
```

两份原始题库（`pdf90/`、`pdf91/`）都只保留了结构化 JSON，**册子原文与 PDF 不入库**。

## 自己跑一遍

需要 Python 3（生成）和 Node.js（只在跑测试时用）。**无第三方依赖，只用标准库。**

```bash
python scripts/build_bank6.py # 合并两个来源、去重、分三类，产出 data/
python scripts/gen_app.py     # 产出 index.html 与 output/入党申请人复习.html（同一份内容）
node scripts/test_app.js      # 165 项断言，直接验证首页，全绿时打印「全部检查通过」
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
| 《复习指导与专题训练》第九十一期版（2026-11） | 57 |
| 往年真题卷（含第 90 期及更早） | 207 |
| 学生党建平台网上党课第 1–20 讲 | 322 |
| **选择题合计** | **586** |

三个分类互斥：每道题只属于一个分类，三个数字相加就是全部。跨分类重复的题干已合并隐藏（5 条，不进队列、不计入统计），题库里仍保留原下标，避免已有进度串位。

另有填空卡片 22 张（只保留第 91 期册子里的）。（`output/04-简答题背诵（纯净版）.md` 是第 90 期版的留存整理，题目未随本版更新。）

所有选择题答案做过**逐题文本交叉校验**（用选项文本反查，不沿用平台下标）；第 91 期新增题按册子原始答案录入。

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
