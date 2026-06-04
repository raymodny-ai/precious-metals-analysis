import os

class KeywordMatcher:
    def __init__(self, keywords_file=None):
        if not keywords_file:
            # Assuming relative path from where script is run or absolute path
            # This assumes the script is in DataCollector/ and config is in ../config/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            keywords_file = os.path.join(base_dir, 'config', 'precious_metals_keywords.txt')
        
        self.keywords_file = keywords_file
        self.must_words = []
        self.filter_words = []
        self.general_words = []
        self.load_keywords()

    def load_keywords(self):
        if not os.path.exists(self.keywords_file):
            print(f"Keywords file not found: {self.keywords_file}")
            return

        with open(self.keywords_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if line.startswith('+'):
                    self.must_words.append(line[1:].lower())
                elif line.startswith('!'):
                    self.filter_words.append(line[1:].lower())
                else:
                    self.general_words.append(line.lower())

    def match(self, text):
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check filter words (exclusion)
        for word in self.filter_words:
            if word in text_lower:
                return False
        
        # Check general words (at least one must be present)
        has_general = False
        for word in self.general_words:
            if word in text_lower:
                has_general = True
                break
        
        if not has_general:
            return False

        # Check must words (if any defined, at least one must be present)
        # Note: This logic assumes that if there are ANY must words defined in the file,
        # the text MUST contain at least one of them.
        if self.must_words:
            has_must = False
            for word in self.must_words:
                if word in text_lower:
                    has_must = True
                    break
            if not has_must:
                return False
        
        return True
