## 项目结构

以下是项目的主要目录和文件：

```
video_downloader/
│
├── video_downloader/        # 包含主要代码
│   ├── __init__.py
│   ├── main.py              # 主程序文件
│   ├── downloader.py         # 下载器模块
│   └── database/
│       ├── __init__.py
│       └── models.py         # 数据模型
│
├── tests/                   # 单元测试
│   ├── __init__.py
│   └── test_downloader.py    # 下载器模块的测试
│
├── requirements.txt         # Python 包依赖
├── config.yaml              # 配置文件
└── README.md                # 项目说明文件
```

`downloads/` 目录是默认的视频下载位置。`data/` 目录用于存放数据库和配置文件等数据文件。

## 数据模型 (`VideoRecord`)

项目的核心数据结构由 `video_downloader/database/models.py` 文件中的 `VideoRecord` 数据类 (dataclass) 定义。这个类代表了单个视频的所有相关信息。

**主要字段**:

*   `title` (str): 视频标题。通常是从原始描述信息中提取出来的。
*   `video_date` (str): 视频的日期，通常是从标题中提取的四位数字。
*   `cover` (str): 视频封面的 URL。
*   `url` (Optional[str]): m3u8 视频流的链接。如果此字段为空，则视频可能为付费内容。
*   `description` (str): API 返回的原始描述文本。
*   `uid` (Optional[str]): 视频的唯一标识符。如果存在，`url` 会根据它动态生成。
*   `download` (bool): 下载状态。`True` 表示视频文件已成功下载到本地。
*   `is_primer` (bool): 是否为付费内容的标记。通常在 `url` 为空时为 `True`。
*   `created_at` / `updated_at` (datetime): 记录的创建和更新时间。

## 工具模块 (`utils`)

`utils` 目录包含一系列用于数据处理和解析的辅助模块，它们是保证应用能够处理各种脏数据和复杂格式的关键。

### `data_processor.py` - 数据处理器

`DataProcessor` 类是一个高级处理器，它封装了读取和清理数据的逻辑。

*   **主要功能**:
    *   `read_json_file_enhanced()`: 这是它的核心方法之一。它不仅能读取标准的 JSON 文件，当遇到格式错误的 JSON 时，它会调用 `EnhancedJSONParser` 来尝试进行修复和解析。这大大增强了应用的健壮性。
    *   `clean_title()`: 提供一个标准化的方法来清理视频标题，例如移除换行符、多余的空格和 `#` 标签。

### `enhanced_json_parser.py` - 增强型 JSON 解析器

`EnhancedJSONParser` 是本项目的一个亮点。由于从 API 或其他非标准来源获取的数据可能不是严格的 JSON 格式，这个解析器被设计用来处理各种棘手的情况。

*   **解决的问题**:
    *   **字符串化的对象**: 解析形如 `<Video object at 0x...>` 或 `Video(id=123, ...)` 的字符串。
    *   **嵌套的 JSON 字符串**: 解析一个 JSON 字段的值本身又是一个 JSON 字符串的情况。
    *   **格式不规范的 JSON**: 尝试修复例如结尾多余逗号等常见的 JSON 语法错误。
*   **工作流程**:
    1.  它会首先尝试使用标准的 `json.loads` 进行解析。
    2.  如果失败，它会检查输入是否像一个 Python 对象或类的字符串表示，并尝试从中提取键值对。
    3.  它还会尝试修复一些常见的 JSON 格式问题，然后再次尝试解析。
    4.  这个解析器内部维护了解析的统计信息，可以知道有多少数据项是通过标准方式解析的，有多少是通过各种“黑魔法”修复后解析的。

这个模块的存在，使得整个应用在面对不完美的数据源时，依然能够最大程度地提取出有效信息。
