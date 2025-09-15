"""
增强JSON解析器 - 专门处理复杂的API返回数据
支持字符串对象表示、嵌套JSON字符串、混合数据格式等
"""

import json
import re
import ast
from typing import Dict, Any, List, Optional, Union
from datetime import datetime


class EnhancedJSONParser:
    """增强的JSON解析器，支持多种数据格式"""

    def __init__(self):
        self.parse_stats = {
            'total_items': 0,
            'successful_parses': 0,
            'string_object_parses': 0,
            'json_string_parses': 0,
            'fallback_parses': 0,
            'failed_parses': 0
        }

    def parse_api_response(self, data: Union[str, Dict, Any]) -> Dict[str, Any]:
        """
        解析API响应数据，支持多种输入格式

        Args:
            data: API响应数据（可能是字符串、字典或其他格式）

        Returns:
            Dict[str, Any]: 标准化的JSON数据
        """
        try:
            # 重置统计信息
            self.parse_stats = {k: 0 for k in self.parse_stats}

            print("🔍 开始解析API响应数据...")

            # 1. 如果是字符串，尝试解析为JSON
            if isinstance(data, str):
                parsed_data = self._parse_string_data(data)
            # 2. 如果已经是字典，直接使用
            elif isinstance(data, dict):
                parsed_data = data
            # 3. 如果是列表，包装为标准格式
            elif isinstance(data, list):
                parsed_data = {'items': data}
            # 4. 其他类型，尝试转换
            else:
                parsed_data = self._parse_unknown_type(data)

            # 验证和标准化数据结构
            if isinstance(parsed_data, dict) and 'items' in parsed_data:
                parsed_data['items'] = self._parse_items_array(parsed_data['items'])

            # 输出解析统计
            self._print_parse_stats()

            return parsed_data

        except Exception as e:
            print(f"❌ API响应解析失败: {e}")
            return {'items': [], 'error': str(e)}

    def _parse_string_data(self, data: str) -> Dict[str, Any]:
        """解析字符串数据"""
        data = data.strip()

        # 尝试直接JSON解析
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            pass

        # 检查是否是对象表示字符串
        if self._is_object_representation(data):
            return self._parse_object_string(data)

        # 尝试修复常见的JSON格式问题
        fixed_data = self._fix_json_format(data)
        try:
            return json.loads(fixed_data)
        except json.JSONDecodeError:
            pass

        # 最后尝试提取JSON片段
        return self._extract_json_fragments(data)

    def _parse_items_array(self, items: List[Any]) -> List[Dict[str, Any]]:
        """解析items数组，处理各种格式的item"""
        if not isinstance(items, list):
            print(f"⚠️ items不是列表格式: {type(items)}")
            return []

        parsed_items = []
        self.parse_stats['total_items'] = len(items)

        for i, item in enumerate(items):
            try:
                parsed_item = self._parse_single_item(item, i)
                if parsed_item:
                    parsed_items.append(parsed_item)
                    self.parse_stats['successful_parses'] += 1
                else:
                    self.parse_stats['failed_parses'] += 1
            except Exception as e:
                print(f"❌ 解析第{i+1}项失败: {e}")
                self.parse_stats['failed_parses'] += 1

        return parsed_items

    def _parse_single_item(self, item: Any, index: int) -> Optional[Dict[str, Any]]:
        """解析单个数据项"""
        # 1. 字典格式 - 标准情况
        if isinstance(item, dict):
            return self._normalize_dict_item(item)

        # 2. 字符串格式 - 可能是JSON字符串或对象表示
        elif isinstance(item, str):
            return self._parse_string_item(item, index)

        # 3. 对象格式 - 有__dict__属性的对象
        elif hasattr(item, '__dict__'):
            return self._parse_object_item(item)

        # 4. 列表格式 - 嵌套列表
        elif isinstance(item, list):
            return self._parse_list_item(item, index)

        # 5. 其他格式
        else:
            return self._parse_other_item(item, index)

    def _parse_string_item(self, item: str, index: int) -> Optional[Dict[str, Any]]:
        """解析字符串格式的item"""
        item = item.strip()

        # 检查是否是对象表示
        if self._is_object_representation(item):
            self.parse_stats['string_object_parses'] += 1
            return self._parse_object_string(item)

        # 尝试JSON解析
        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict):
                self.parse_stats['json_string_parses'] += 1
                return self._normalize_dict_item(parsed)
        except json.JSONDecodeError:
            pass

        # 尝试修复JSON格式
        fixed_item = self._fix_json_format(item)
        try:
            parsed = json.loads(fixed_item)
            if isinstance(parsed, dict):
                self.parse_stats['json_string_parses'] += 1
                return self._normalize_dict_item(parsed)
        except json.JSONDecodeError:
            pass

        # 尝试从字符串中提取信息
        return self._extract_from_string(item, index)

    def _is_object_representation(self, text: str) -> bool:
        """检查字符串是否是对象表示"""
        patterns = [
            r'<.*?object\s+at\s+0x[0-9a-f]+>',  # <Video object at 0x...>
            r'<.*?\s+object\s+at\s+0x[0-9a-f]+>',  # <SomeClass object at 0x...>
            r'Video\([^)]*\)',  # Video(id=123, title="...")
            r'\w+\([^)]*\)',  # ClassName(field=value, ...)
        ]

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _parse_object_string(self, obj_str: str) -> Dict[str, Any]:
        """解析对象表示字符串"""
        result = {'_source': 'object_string', '_raw': obj_str}

        # 尝试提取类名
        class_match = re.search(r'<(\w+)\s+object', obj_str, re.IGNORECASE)
        if class_match:
            result['_class'] = class_match.group(1)

        # 尝试提取括号内的参数
        param_match = re.search(r'\(([^)]+)\)', obj_str)
        if param_match:
            params_str = param_match.group(1)
            result.update(self._parse_object_parameters(params_str))

        # 尝试提取常见字段
        self._extract_common_fields(obj_str, result)

        return result

    def _parse_object_parameters(self, params_str: str) -> Dict[str, Any]:
        """解析对象参数字符串"""
        params = {}

        # 分割参数（考虑嵌套引号）
        param_items = self._split_parameters(params_str)

        for item in param_items:
            if '=' in item:
                key, value = item.split('=', 1)
                key = key.strip()
                value = value.strip()

                # 尝试解析值
                params[key] = self._parse_parameter_value(value)

        return params

    def _split_parameters(self, params_str: str) -> List[str]:
        """智能分割参数字符串"""
        items = []
        current = ""
        in_quotes = False
        quote_char = None
        paren_level = 0

        for char in params_str:
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            elif char == '(' and not in_quotes:
                paren_level += 1
            elif char == ')' and not in_quotes:
                paren_level -= 1
            elif char == ',' and not in_quotes and paren_level == 0:
                items.append(current.strip())
                current = ""
                continue

            current += char

        if current.strip():
            items.append(current.strip())

        return items

    def _parse_parameter_value(self, value: str) -> Any:
        """解析参数值"""
        value = value.strip()

        # 移除外层引号
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # 尝试解析为数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # 尝试解析为布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # 尝试解析为None
        if value.lower() in ('none', 'null'):
            return None

        # 尝试解析为列表或字典
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            pass

        # 返回原始字符串
        return value

    def _extract_common_fields(self, text: str, result: Dict[str, Any]):
        """从文本中提取常见字段"""
        # 提取常见的字段模式
        patterns = {
            'id': r'id[\'"]?\s*[:=]\s*[\'"]?([^,\'")\s]+)',
            'title': r'title[\'"]?\s*[:=]\s*[\'"]([^\'"]+)',
            'description': r'description[\'"]?\s*[:=]\s*[\'"]([^\'"]]*)',
            'url': r'url[\'"]?\s*[:=]\s*[\'"]([^\'"\s]+)',
            'cover': r'cover[\'"]?\s*[:=]\s*[\'"]([^\'"\s]+)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[field] = match.group(1)

    def _normalize_dict_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """标准化字典格式的item"""
        # 处理嵌套的JSON字符串
        normalized = {}
        for key, value in item.items():
            if isinstance(value, str) and self._looks_like_json(value):
                try:
                    normalized[key] = json.loads(value)
                except json.JSONDecodeError:
                    normalized[key] = value
            else:
                normalized[key] = value

        return normalized

    def _looks_like_json(self, text: str) -> bool:
        """检查字符串是否像JSON格式"""
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))

    def _fix_json_format(self, text: str) -> str:
        """修复常见的JSON格式问题"""
        # 移除BOM
        if text.startswith('\ufeff'):
            text = text[1:]

        # 修复单引号为双引号
        text = re.sub(r"'([^']*)':", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)

        # 修复尾随逗号
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)

        # 修复未引用的键
        text = re.sub(r'(\w+):', r'"\1":', text)

        return text

    def _extract_json_fragments(self, text: str) -> Dict[str, Any]:
        """从文本中提取JSON片段"""
        result = {'items': [], '_source': 'text_extraction'}

        # 查找JSON对象
        json_objects = re.findall(r'\{[^{}]*\}', text)
        for obj_str in json_objects:
            try:
                obj = json.loads(obj_str)
                if isinstance(obj, dict):
                    result['items'].append(obj)
            except json.JSONDecodeError:
                continue

        # 查找JSON数组
        json_arrays = re.findall(r'\[[^\[\]]*\]', text)
        for arr_str in json_arrays:
            try:
                arr = json.loads(arr_str)
                if isinstance(arr, list):
                    result['items'].extend(arr)
            except json.JSONDecodeError:
                continue

        return result

    def _extract_from_string(self, text: str, index: int) -> Optional[Dict[str, Any]]:
        """从普通字符串中提取信息"""
        self.parse_stats['fallback_parses'] += 1

        result = {
            '_source': 'string_extraction',
            '_index': index,
            'raw_text': text[:200] + ('...' if len(text) > 200 else '')
        }

        # 尝试提取URL
        url_pattern = r'https?://[^\s<>"\']+[^\s<>"\'.,;]'
        urls = re.findall(url_pattern, text)
        if urls:
            result['url'] = urls[0]

        # 尝试提取ID
        id_pattern = r'\b[A-Za-z0-9]{10,}\b'
        ids = re.findall(id_pattern, text)
        if ids:
            result['id'] = ids[0]

        # 使用文本作为描述
        if len(text) > 10:
            result['description'] = text

        return result if len(result) > 3 else None

    def _parse_object_item(self, obj: Any) -> Dict[str, Any]:
        """解析对象格式的item"""
        result = {'_source': 'object'}

        # 尝试获取对象属性
        if hasattr(obj, '__dict__'):
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):  # 忽略私有属性
                    result[key] = value

        # 尝试常见属性
        common_attrs = ['id', 'title', 'description', 'url', 'cover']
        for attr in common_attrs:
            if hasattr(obj, attr):
                result[attr] = getattr(obj, attr)

        return result

    def _parse_list_item(self, item: List[Any], index: int) -> Optional[Dict[str, Any]]:
        """解析列表格式的item"""
        if not item:
            return None

        # 如果列表只有一个元素，递归解析
        if len(item) == 1:
            return self._parse_single_item(item[0], index)

        # 多个元素的情况，尝试组合
        result = {'_source': 'list', '_index': index}

        for i, sub_item in enumerate(item):
            if isinstance(sub_item, dict):
                result.update(sub_item)
            elif isinstance(sub_item, str) and len(sub_item) > 5:
                result[f'text_{i}'] = sub_item

        return result if len(result) > 2 else None

    def _parse_other_item(self, item: Any, index: int) -> Optional[Dict[str, Any]]:
        """解析其他格式的item"""
        result = {
            '_source': 'other',
            '_type': type(item).__name__,
            '_index': index
        }

        # 尝试转换为字符串
        try:
            str_repr = str(item)
            if len(str_repr) > 10:
                result['string_representation'] = str_repr

                # 从字符串表示中提取信息
                self._extract_common_fields(str_repr, result)
        except Exception as e:
            result['_error'] = str(e)

        return result if len(result) > 3 else None

    def _parse_unknown_type(self, data: Any) -> Dict[str, Any]:
        """解析未知类型的数据"""
        # 尝试转换为字符串并解析
        try:
            str_data = str(data)
            return self._parse_string_data(str_data)
        except Exception:
            return {
                'items': [],
                '_source': 'unknown_type',
                '_type': type(data).__name__,
                '_error': 'Unable to parse unknown data type'
            }

    def _print_parse_stats(self):
        """输出解析统计信息"""
        stats = self.parse_stats
        total = stats['total_items']

        if total > 0:
            print(f"\n📊 解析统计:")
            print(f"   总项目数: {total}")
            print(f"   成功解析: {stats['successful_parses']} ({stats['successful_parses']/total*100:.1f}%)")
            print(f"   字符串对象: {stats['string_object_parses']}")
            print(f"   JSON字符串: {stats['json_string_parses']}")
            print(f"   降级解析: {stats['fallback_parses']}")
            print(f"   解析失败: {stats['failed_parses']} ({stats['failed_parses']/total*100:.1f}%)")

    def get_parse_stats(self) -> Dict[str, int]:
        """获取解析统计信息"""
        return self.parse_stats.copy()
