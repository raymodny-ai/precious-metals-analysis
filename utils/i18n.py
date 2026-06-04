"""
国际化 (i18n) 支持工具
"""
import json
import os

class I18n:
    """国际化工具类"""
    
    def __init__(self, default_language='zh'):
        self.current_language = default_language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """加载翻译文件"""
        translations_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config',
            'i18n_translations.json'
        )
        
        try:
            with open(translations_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"警告: 翻译文件未找到 {translations_file}")
            self.translations = {}
    
    def set_language(self, language_code):
        """设置当前语言"""
        if language_code in self.translations:
            self.current_language = language_code
        else:
            print(f"警告: 不支持的语言代码 '{language_code}'")
    
    def t(self, key_path, language=None):
        """
        获取翻译文本
        
        Args:
            key_path: 点分隔的键路径，如 'navigation.dashboard'
            language: 可选的语言代码，默认使用当前语言
        
        Returns:
            翻译后的文本，如果找不到则返回键路径本身
        """
        lang = language or self.current_language
        
        if lang not in self.translations:
            return key_path
        
        # 解析点分隔的路径
        keys = key_path.split('.')
        value = self.translations[lang]
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return key_path
    
    def get_available_languages(self):
        """获取所有可用的语言"""
        return list(self.translations.keys())
    
    def get_language_name(self, language_code):
        """获取语言的本地名称"""
        names = {
            'en': 'English',
            'zh': '中文',
            'es': 'Español'
        }
        return names.get(language_code, language_code)

# 创建全局 i18n 实例
i18n = I18n()

# 便捷函数
def t(key_path, language=None):
    """快捷翻译函数"""
    return i18n.t(key_path, language)

def set_language(language_code):
    """设置语言"""
    i18n.set_language(language_code)
