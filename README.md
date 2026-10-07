# ldap-filter

解析并求值 LDAP 过滤表达式：等值、存在、子串、与或非，以及多值属性与转义。只用 Python 标准库。

```
python3 -m unittest discover -s tests
python3 -m ldapfilter --sample=substr
python3 -m ldapfilter --sample=esc
python3 -m ldapfilter --sample=not
python3 -m ldapfilter --sample=multi
python3 -m ldapfilter --sample=work
```

## 口径

- **存在**：`(attr=*)` 只看属性在不在。
- **子串**：值里未转义的 `*` 分段，初始段、若干中间段、末尾段都要按顺序出现。
- **转义**：`\xx` 还原成对应字节，`\2a` 就是字面的 `*`。
- **非**：`(!(f))` 取内部结果的反。
- **多值**：属性的值可能是列表，任一值命中即算命中。
- **查找**：按属性建索引，等值查询直接取候选，不逐条比较。

## 不变量

- 转义过的 `*` 不参与子串分段。
- 结果索引按升序返回。
- `scanned` 不随条目数乘查询次数放大：八百个条目查八百次的 `scanned` 不超过 6000。

## 输出契约

`parse` 返回语法树，`match` 对单个条目求值，`search` 对一批条目返回命中下标。
场景打印一行 JSON。`--sample=work` 打印 `{"entries": N, "scanned": N}`。
