# 将本文件的全部内容复制到 AgentArts 工作流的 Python 代码节点。
# 画布连接顺序为“开始 → 代码 → 结束”。
# 代码节点的输入参数 query 引用“开始.query”，输出参数 result 的类型为 String。
# 结束节点引用“代码.result”，指定回复使用 {{result}}。
#
# 在试运行的 query 输入框中填写以下 JSON 文本，即可测试一份配方。
# {"basis":"at%","composition":{"Ti":70,"Nb":20,"Zr":10}}
# basis 指成分单位，at% 是原子百分比，wt% 是质量百分比。
# composition 中的数值采用百分数，例如 70 表示 70%。
#
# 本原型完成输入格式、成分总和和场景元素白名单的检查，并统一输出原子百分比。
# passed 表示通过当前配置的成分预检，材料性能需要交给后续评估工具判断。
# 单个元素的专用上下限、配料精度等规则，需由团队确定参数后继续补充。


def main(args: dict) -> dict:
    # AgentArts 会调用 main，并把画布中的输入参数放进 args 字典。
    # 例如输入参数叫 query，就可以用 args.get("query", "") 读取它的值。
    # -> dict 是返回值的类型提示，下面会返回包含 result 字段的字典。

    # json 是 Python 标准库，用于在 JSON 文本和 Python 字典之间转换。
    import json

    # 字典的键是允许使用的元素符号，值是质量百分比换算时用到的相对原子质量。
    # 这份白名单采用《竞赛》中的生物医用示例，Fe 的使用仍需团队确认。
    # 本原型只接受表中列出的元素，后续可以根据确认后的应用场景调整。
    # 相对原子质量取自 CIAAW 2024 简表。
    # https://www.ciaaw.org/abridged-atomic-weights.htm
    atomic_weights = {
        "Ti": 47.867,
        "Nb": 92.906,
        "Ta": 180.95,
        "Zr": 91.222,
        "Mo": 95.95,
        "Sn": 118.71,
        "O": 15.999,
    }
    # 先创建统一的结果对象。后面无论在哪一步发现问题，都使用这个结构返回。
    # passed 默认是 False，只有全部检查通过后才会设为 True。
    # basis 保存输入单位，total 保存输入配方的百分比总和。
    # composition_at_pct 保存换算并归一化后的原子百分比，通过检查后才会填写。
    # error_code 供下游程序判断问题类别，message 给使用者解释原因。
    # tool 和 tool_version 标明工具名称与版本，方便联调和复查。
    result = {
        "tool": "gate_check",
        "tool_version": "0.1.0",
        "passed": False,
        "basis": None,
        "total": None,
        "composition_at_pct": None,
        "error_code": None,
        "message": "",
    }

    def reply(error_code, message):
        # 把成功或失败的结果整理成画布要求的返回格式，避免每个分支重复写。
        # error_code 为 None 表示没有错误，表达式“is None”的结果就是 True。
        result["error_code"] = error_code
        result["passed"] = error_code is None
        result["message"] = message
        # 内层 result 是 Python 字典，json.dumps 把它转换成 JSON 文本。
        # ensure_ascii=False 让中文以可读的形式输出。
        # 外层仍然返回字典 {"result": ...}，与画布上名为 result 的 String 输出对应。
        return {"result": json.dumps(result, ensure_ascii=False)}

    def unique_keys(pairs):
        # JSON 对象中可能出现重复字段，例如同一份配方写了两次 "Nb"。
        # Python 默认解析会用后面的值覆盖前面的值，因此在读取时逐项检查。
        # pairs 是解析器传来的“字段名、字段值”列表。
        obj = {}
        for key, value in pairs:
            if key in obj:
                # raise 中止本次解析，交给下面的 except 返回明确的错误信息。
                raise ValueError(f"字段 {key} 重复。")
            obj[key] = value
        return obj

    try:
        # query 是用户输入的 JSON 文本，payload 是解析后的 Python 对象。
        # object_pairs_hook 指定每个 JSON 对象都经过上面的重复字段检查。
        payload = json.loads(args.get("query", ""), object_pairs_hook=unique_keys)
    except (TypeError, json.JSONDecodeError):
        # 输入类型不对或 JSON 格式错误时，从这里返回，避免整个节点直接报错退出。
        return reply("INVALID_JSON", "请在 query 中输入有效的 JSON 对象。")
    except ValueError as exc:
        # 接收 unique_keys 发现的重复字段错误，并保留具体字段名。
        return reply("INVALID_JSON", str(exc))

    # 有效 JSON 也可能是列表、字符串或数字，这个工具要求最外层是对象，即字典。
    if not isinstance(payload, dict):
        return reply("INVALID_INPUT", "输入应是包含 basis 和 composition 的对象。")
    basis = payload.get("basis")
    # 要求调用方明确提供单位，避免把质量百分比与原子百分比混用。
    if basis not in ("at%", "wt%"):
        return reply("UNIT_MISMATCH", "basis 必须明确填写 at% 或 wt%。")
    result["basis"] = basis

    composition = payload.get("composition")
    # composition 必须是至少含一个元素的字典，例如 {"Ti": 70, "Nb": 30}。
    if not isinstance(composition, dict) or not composition:
        return reply("INVALID_COMPOSITION", "composition 应是非空的元素与百分比对象。")

    percentages = {}
    for name, value in composition.items():
        # strip 去掉首尾空格，capitalize 统一大小写，例如 " nb " 变成 "Nb"。
        symbol = name.strip().capitalize()
        # 表中同时保存了白名单和换算所需的原子质量，缺少的元素在这里拒绝。
        if symbol not in atomic_weights:
            return reply("ELEMENT_NOT_ALLOWED", f"元素 {symbol} 不在当前场景白名单中。")
        # 两种写法在统一后可能指向同一个元素，例如 "Nb" 和 " nb "。
        if symbol in percentages:
            return reply("DUPLICATE_ELEMENT", f"元素 {symbol} 重复填写。")
        # 含量应是有限的数值且位于 0～100 之间。
        # Python 把 bool 当作 int 的一种，所以要先排除 True、False。
        # 范围比较也会拦截 NaN（非数值）和无穷大。
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            return reply("INVALID_PERCENTAGE", f"元素 {symbol} 的含量必须是 0 到 100 之间的数值。")
        # 统一存成浮点数，方便处理小数配方以及后面的单位换算。
        percentages[symbol] = float(value)

    total = sum(percentages.values())
    # 对显示的总和保留 8 位小数，下面判断时仍使用原始计算结果 total。
    result["total"] = round(total, 8)
    # 这是本原型对“钛合金”的基本输入约定，要求含有大于 0 的 Ti。
    if percentages.get("Ti", 0) <= 0:
        return reply("TI_REQUIRED", "钛含量必须大于 0。")
    # 先检查原始比例，再换算归一化。否则总和只有 95 的错误配方也会被缩放成 100。
    # abs(total - 100) 是总和与 100 的差距，允许偏差为 0.1 个百分点。
    # 例如 99.9、100.1 通过，99.89、100.11 拒绝。
    # 1e-9 是很小的数值容差，用来处理浮点计算在边界处的微小误差。
    if abs(total - 100) > 0.1 + 1e-9:
        return reply("INVALID_TOTAL", "各元素含量之和应为 100%，允许偏差 ±0.1 个百分点。")

    amounts = percentages
    if basis == "wt%":
        # 质量百分比先除以各元素的相对原子质量，得到与原子数量成比例的数。
        # 可把配方理解为总质量约 100 g，各元素质量 ÷ 摩尔质量 = 各元素物质的量。
        amounts = {symbol: value / atomic_weights[symbol] for symbol, value in percentages.items()}
    # at% 输入直接使用原子比例，wt% 输入使用上面得到的物质的量比例。
    # 每个元素的比例 ÷ 所有元素比例之和 × 100，得到统一的原子百分比。
    # 保留 6 位小数用于输出，各项显示值相加可能因舍入出现很小的差异。
    amount_total = sum(amounts.values())
    result["composition_at_pct"] = {
        symbol: round(100 * amount / amount_total, 6) for symbol, amount in amounts.items()
    }
    # 所有检查均已通过，None 使 reply 将 passed 设置为 True。
    return reply(None, "通过本原型的成分预检。")
