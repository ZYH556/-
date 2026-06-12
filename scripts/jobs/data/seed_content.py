"""演示数据内容生成器：真实结构的教学内容模板（纯函数，无外部依赖）。

22 个概念 × 最多 6 类资源 ≈ 114 条学习资源；20 个学生画像样本；30 条错题。
内容为合成教学内容，结构真实、不冒充真实用户行为（docs/21 §13.5）。
"""

from __future__ import annotations

# 概念库：name/domain/difficulty/points(要点)/example(例子)/pitfall(易错点)/prereq
CONCEPTS: list[dict] = [
    # —— 机器学习（10）——
    {"name": "线性回归", "domain": "机器学习", "difficulty": 0.3,
     "points": ["最小二乘法拟合连续目标", "损失函数为均方误差 MSE", "可解析求解也可梯度下降"],
     "example": "用房屋面积预测房价：y = w·x + b，通过最小化 MSE 求 w 和 b。",
     "pitfall": "特征未标准化导致梯度下降收敛慢，或把分类问题误用线性回归。", "prereq": ""},
    {"name": "逻辑回归", "domain": "机器学习", "difficulty": 0.35,
     "points": ["Sigmoid 把线性输出映射到 (0,1)", "交叉熵损失而非 MSE", "输出是概率，阈值决定类别"],
     "example": "根据复习时长与出勤预测考试是否及格，输出及格概率。",
     "pitfall": "名字带「回归」但解决的是分类问题；类别不平衡时只看准确率会误判。", "prereq": "线性回归"},
    {"name": "梯度下降", "domain": "机器学习", "difficulty": 0.4,
     "points": ["沿负梯度方向迭代更新参数", "学习率控制步长", "批量/随机/小批量三种变体"],
     "example": "w := w - lr * dL/dw，反复迭代直到损失收敛。",
     "pitfall": "学习率过大震荡发散、过小收敛极慢；忘记对特征缩放。", "prereq": "线性回归"},
    {"name": "过拟合与正则化", "domain": "机器学习", "difficulty": 0.5,
     "points": ["训练误差低但泛化差即过拟合", "L1 产生稀疏权重、L2 平滑权重", "交叉验证选择正则强度"],
     "example": "高次多项式完美穿过训练点但在新数据上误差爆炸，加 L2 后曲线平滑。",
     "pitfall": "把验证集当训练集调参导致信息泄漏；正则强度 λ 不做搜索直接拍脑袋。", "prereq": "线性回归"},
    {"name": "决策树", "domain": "机器学习", "difficulty": 0.45,
     "points": ["按信息增益/基尼系数选分裂特征", "可解释性强", "易过拟合需剪枝或限深"],
     "example": "根据「是否刮风、湿度」逐层判断是否适合打球的树状规则。",
     "pitfall": "不限制深度的树会把噪声也学进去；对连续特征要找最优切分点。", "prereq": "过拟合与正则化"},
    {"name": "支持向量机", "domain": "机器学习", "difficulty": 0.6,
     "points": ["最大化分类间隔", "核技巧处理非线性", "软间隔容忍噪声"],
     "example": "二维线性可分数据中，SVM 找到离两类样本都最远的分界线。",
     "pitfall": "未做特征缩放时 RBF 核效果差；大数据集上训练代价高。", "prereq": "逻辑回归"},
    {"name": "K近邻", "domain": "机器学习", "difficulty": 0.3,
     "points": ["按距离找 K 个最近样本投票", "惰性学习无显式训练", "K 与距离度量是关键超参"],
     "example": "新电影按「时长、动作镜头数」找最近 5 部已标注电影投票定类型。",
     "pitfall": "特征量纲不一致时距离失真；K 取 1 对噪声极其敏感。", "prereq": ""},
    {"name": "聚类", "domain": "机器学习", "difficulty": 0.45,
     "points": ["无监督地把相似样本分组", "K-Means 迭代质心收敛", "肘部法/轮廓系数选簇数"],
     "example": "把用户按「消费频次、客单价」自动分成高价值/潜力/流失三群。",
     "pitfall": "K-Means 对初始质心敏感且只适合凸形簇；忘记标准化。", "prereq": "K近邻"},
    {"name": "神经网络基础", "domain": "机器学习", "difficulty": 0.7,
     "points": ["神经元=线性变换+非线性激活", "反向传播链式求导更新权重", "隐藏层带来非线性表达力"],
     "example": "两层网络拟合 XOR：单层线性模型无法分割，加隐藏层即可。",
     "pitfall": "激活函数全用线性等价于单层；梯度消失使深层难训练。", "prereq": "梯度下降"},
    {"name": "卷积神经网络", "domain": "机器学习", "difficulty": 0.75,
     "points": ["卷积核共享权重提取局部特征", "池化降维保留显著信号", "层级堆叠由边缘到语义"],
     "example": "LeNet 识别手写数字：卷积提笔画边缘，池化压缩，全连接分类。",
     "pitfall": "输入尺寸与卷积核/步长不匹配算错输出维度；小数据集直接训练大网络过拟合。", "prereq": "神经网络基础"},
    # —— Python（6）——
    {"name": "变量与类型", "domain": "Python", "difficulty": 0.1,
     "points": ["动态类型，变量是对象的引用", "int/float/str/bool 不可变", "type() 与 isinstance() 检查类型"],
     "example": "a = 3; a = 'three' 合法：名字 a 先后指向不同对象。",
     "pitfall": "可变默认参数 def f(x=[]) 在多次调用间共享同一列表。", "prereq": ""},
    {"name": "函数", "domain": "Python", "difficulty": 0.2,
     "points": ["位置/关键字/默认/可变参数", "函数是一等对象可传递", "作用域 LEGB 规则"],
     "example": "def power(base, exp=2): return base ** exp，power(3) 得 9。",
     "pitfall": "闭包里修改外层变量忘了 nonlocal；*args 与 **kwargs 顺序写反。", "prereq": "变量与类型"},
    {"name": "列表与字典", "domain": "Python", "difficulty": 0.2,
     "points": ["列表有序可变、字典键值映射", "切片与推导式", "dict 平均 O(1) 查找"],
     "example": "{w: len(w) for w in words} 一行构建单词长度映射。",
     "pitfall": "遍历列表时原地删除元素跳项；浅拷贝嵌套结构共享内层引用。", "prereq": "变量与类型"},
    {"name": "面向对象", "domain": "Python", "difficulty": 0.4,
     "points": ["类封装数据与行为", "继承复用、多态重写", "魔术方法定制行为"],
     "example": "class Stack 封装 push/pop，__len__ 让 len(stack) 直接可用。",
     "pitfall": "类属性与实例属性混淆导致跨实例共享状态；忘记调 super().__init__。", "prereq": "函数"},
    {"name": "异常处理", "domain": "Python", "difficulty": 0.3,
     "points": ["try/except/else/finally 流程", "精确捕获优于裸 except", "with 上下文自动清理"],
     "example": "with open(path) as f 即使读取抛错文件也会被关闭。",
     "pitfall": "except Exception 吞掉所有错误掩盖 bug；在 finally 里 return 覆盖异常。", "prereq": "函数"},
    {"name": "迭代器与生成器", "domain": "Python", "difficulty": 0.5,
     "points": ["迭代器协议 __iter__/__next__", "yield 惰性产出节省内存", "生成器表达式与管道组合"],
     "example": "def countdown(n): while n: yield n; n -= 1，按需产出不占整块内存。",
     "pitfall": "生成器只能消费一次，二次遍历得到空；在生成器里捕获 StopIteration。", "prereq": "列表与字典"},
    # —— 数据结构（6）——
    {"name": "数组与链表", "domain": "数据结构", "difficulty": 0.25,
     "points": ["数组随机访问 O(1) 插删 O(n)", "链表插删 O(1) 访问 O(n)", "按读写比例选型"],
     "example": "频繁头部插入用链表；频繁按下标读取用数组。",
     "pitfall": "链表操作丢失 next 引用断链；忘记处理头节点边界。", "prereq": ""},
    {"name": "栈与队列", "domain": "数据结构", "difficulty": 0.25,
     "points": ["栈 LIFO、队列 FIFO", "栈支撑递归/撤销/括号匹配", "双端队列两端皆可操作"],
     "example": "括号匹配：左括号入栈，右括号弹栈比对，结束栈空即合法。",
     "pitfall": "空栈弹出未判空；用 list 当队列头部出队是 O(n)。", "prereq": "数组与链表"},
    {"name": "哈希表", "domain": "数据结构", "difficulty": 0.4,
     "points": ["哈希函数映射键到桶", "冲突用链地址或开放寻址", "负载因子触发扩容"],
     "example": "两数之和：一次遍历用哈希表查 target-x 是否出现过，O(n) 解决。",
     "pitfall": "可变对象作键；忽视最坏情况退化为 O(n)。", "prereq": "数组与链表"},
    {"name": "二叉树", "domain": "数据结构", "difficulty": 0.5,
     "points": ["前/中/后序与层序遍历", "BST 中序遍历有序", "平衡性决定操作复杂度"],
     "example": "BST 查找：目标比节点小走左、大走右，平衡时 O(log n)。",
     "pitfall": "递归遍历忘记空节点终止条件；删除带双子节点的 BST 节点漏换后继。", "prereq": "栈与队列"},
    {"name": "图", "domain": "数据结构", "difficulty": 0.65,
     "points": ["邻接表/矩阵两种存储", "BFS 求无权最短路、DFS 探路径", "拓扑排序处理依赖"],
     "example": "课程先修关系建有向图，拓扑排序给出可行修读顺序。",
     "pitfall": "遍历忘记标记已访问陷入环；稠密图用邻接表反而费空间。", "prereq": "二叉树"},
    {"name": "排序算法", "domain": "数据结构", "difficulty": 0.45,
     "points": ["快排平均 O(n log n) 不稳定", "归并稳定但需辅助空间", "数据规模与稳定性决定选型"],
     "example": "快排：选基准分区，左小右大，递归两侧。",
     "pitfall": "快排基准选首元素遇有序数组退化 O(n²)；混淆稳定性含义。", "prereq": "数组与链表"},
]


def make_doc(c: dict) -> tuple[str, str]:
    points = "\n".join(f"- {p}" for p in c["points"])
    content = (
        f"# {c['name']} 核心讲解\n\n## 是什么\n{c['example']}\n\n"
        f"## 三个关键点\n{points}\n\n## 易错点\n{c['pitfall']}\n\n"
        f"## 小结\n掌握{c['name']}的判断标准：能向别人解释上面三个关键点，"
        f"并能指出典型易错场景。建议配合练习题巩固。"
    )
    return f"{c['name']} · 讲解文档", content


def make_mindmap(c: dict) -> tuple[str, str]:
    branches = "\n".join(f"  - {p}" for p in c["points"])
    prereq = f"\n- 先修\n  - {c['prereq']}" if c["prereq"] else ""
    content = (
        f"- {c['name']}\n- 核心要点\n{branches}\n- 典型例子\n  - {c['example'][:40]}\n"
        f"- 易错点\n  - {c['pitfall'][:40]}{prereq}"
    )
    return f"{c['name']} · 思维导图", content


def make_quiz(c: dict) -> tuple[str, str]:
    content = (
        f"# {c['name']} 练习题\n\n"
        f"**1.（概念）** 用一句话说明：{c['points'][0]}是什么意思？\n\n"
        f"> 参考：{c['points'][0]}。\n\n"
        f"**2.（判断）** 「{c['pitfall'][:30]}」这种做法是否正确？为什么？\n\n"
        f"> 参考：不正确。{c['pitfall']}\n\n"
        f"**3.（应用）** 结合场景说明：{c['example'][:50]} 中{c['name']}起什么作用？\n\n"
        f"> 参考：{c['example']}\n"
    )
    return f"{c['name']} · 练习题组", content


def make_reading(c: dict) -> tuple[str, str]:
    content = (
        f"# {c['name']} 拓展阅读指引\n\n"
        f"## 为什么值得深入\n{c['name']}是{c['domain']}的关键一环，{c['points'][0]}。\n\n"
        f"## 推荐阅读方向\n- 教材对应章节：重点看推导与例题\n"
        f"- 官方/经典文档：对照术语理解定义\n- 实战博客：看真实数据上的踩坑记录\n\n"
        f"## 阅读时自查\n读完应能回答：{c['pitfall'][:40]}该如何避免？"
    )
    return f"{c['name']} · 拓展阅读", content


def make_code(c: dict) -> tuple[str, str]:
    content = (
        f"# {c['name']} 代码实操\n\n```python\n# 任务：用最小例子体会「{c['points'][0]}」\n"
        f"# 1. 阅读并运行下面的骨架\n# 2. 完成 TODO\n# 3. 对照易错点自查：{c['pitfall'][:36]}\n\n"
        f"def demo():\n    \"\"\"{c['example'][:60]}\"\"\"\n"
        f"    # TODO: 按注释补全核心逻辑\n    raise NotImplementedError\n\n"
        f"if __name__ == '__main__':\n    demo()\n```\n\n"
        f"完成后尝试：改一个输入边界，观察行为是否符合预期。"
    )
    return f"{c['name']} · 代码实操", content


def make_video_script(c: dict) -> tuple[str, str]:
    content = (
        f"# {c['name']} 教学短视频分镜\n\n"
        f"| 镜头 | 画面 | 旁白 |\n| --- | --- | --- |\n"
        f"| 1 开场 | 标题卡：{c['name']} | 30 秒带你抓住{c['name']}的核心 |\n"
        f"| 2 直觉 | 动画演示 | {c['example'][:50]} |\n"
        f"| 3 要点 | 逐条弹出 | {'；'.join(p[:18] for p in c['points'])} |\n"
        f"| 4 避坑 | 错误示范打叉 | {c['pitfall'][:40]} |\n"
        f"| 5 收尾 | 总结卡 | 动手做一道练习巩固它 |\n"
    )
    return f"{c['name']} · 教学视频脚本", content


# 资源类型 → (生成器, 适用领域过滤)
_MAKERS = [
    ("doc", make_doc, None),
    ("mindmap", make_mindmap, None),
    ("quiz", make_quiz, None),
    ("reading", make_reading, {"机器学习", "数据结构"}),
    ("code", make_code, None),
    ("video", make_video_script, {"机器学习"}),
]


def build_all_resources() -> list[dict]:
    """全部演示资源：type/title/content/concept/domain/difficulty。"""
    out: list[dict] = []
    for c in CONCEPTS:
        for rtype, maker, domains in _MAKERS:
            if domains is not None and c["domain"] not in domains:
                continue
            title, content = maker(c)
            out.append(
                {
                    "type": rtype,
                    "title": title,
                    "content": content,
                    "concept": c["name"],
                    "domain": c["domain"],
                    "difficulty": c["difficulty"],
                }
            )
    return out


_MAJORS = ["计算机科学", "人工智能", "软件工程", "数据科学", "自动化", "电子信息", "应用数学", "信息管理"]
_STAGES = ["大一", "大二", "大三", "研一"]
_GOALS = [
    ("课程补弱", "把挂科风险的核心课补到中上水平"),
    ("期末备考", "两周内系统复习应对期末考试"),
    ("竞赛准备", "为算法/建模竞赛打基础"),
    ("项目实践", "完成一个可写进简历的课程项目"),
    ("求职准备", "刷面试高频考点并能讲清原理"),
    ("科研入门", "读懂论文方法部分所需的基础"),
]
_STYLES = ["visual", "verbal", "active", "reflective"]
_PREFS = [
    {"language": "zh", "prefer_code_examples": True},
    {"language": "zh", "prefer_video": True},
    {"language": "zh", "prefer_quiz_drill": True},
    {"language": "zh", "prefer_mindmap": True},
]


def build_student_profiles() -> list[dict]:
    """20 个画像样本：专业 × 学历 × 目标 × 风格 组合覆盖。"""
    profiles: list[dict] = []
    kb_pool = [c["name"] for c in CONCEPTS]
    for i in range(20):
        goal_kind, goal_text = _GOALS[i % len(_GOALS)]
        base = 0.2 + (i % 5) * 0.15
        knowledge = {
            kb_pool[(i * 3 + j) % len(kb_pool)]: round(min(0.9, base + j * 0.1), 2)
            for j in range(4)
        }
        weak = [kb_pool[(i * 3 + 7) % len(kb_pool)], kb_pool[(i * 5 + 11) % len(kb_pool)]]
        profiles.append(
            {
                "user_id": f"seed-stu-{i + 1:02d}",
                "major": _MAJORS[i % len(_MAJORS)],
                "stage": _STAGES[i % len(_STAGES)],
                "goal_kind": goal_kind,
                "dimensions": {
                    "goal": goal_text,
                    "major": _MAJORS[i % len(_MAJORS)],
                    "stage": _STAGES[i % len(_STAGES)],
                    "knowledge_base": knowledge,
                    "weak_points": weak,
                    "cognitive_style": _STYLES[i % len(_STYLES)],
                    "preferences": _PREFS[i % len(_PREFS)],
                    "progress": round((i % 7) / 10, 2),
                },
            }
        )
    return profiles


def build_mistakes(user_id: str) -> list[dict]:
    """30 条错题样本，错因取自概念易错点。"""
    out: list[dict] = []
    for i in range(30):
        c = CONCEPTS[i % len(CONCEPTS)]
        out.append(
            {
                "mistake_id": f"seed-m-{i + 1:03d}",
                "user_id": user_id,
                "question": f"关于{c['name']}：{c['points'][i % len(c['points'])]}，请举例说明。",
                "answer": f"（学生作答）只复述了定义，未结合例子，混淆了{c['pitfall'][:20]}的情形。",
                "expected": c["example"],
                "concept": c["name"],
                "status": "open" if i % 3 else "reviewed",
            }
        )
    return out
