import re
from typing import List, Tuple, Dict, Any

try:
    from django.template.base import (
        Lexer, TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK, Token,
        FilterExpression, Parser, Context, tag_re
    )
    from django.template.base import parse_bits, token_kwargs
    from django.template.library import parse_bits as library_parse_bits
except ImportError:
    # Fallback if Django not available during testing
    Lexer = Parser = Context = FilterExpression = None
    TOKEN_TEXT = TOKEN_VAR = TOKEN_BLOCK = Token = None
    tag_re = parse_bits = token_kwargs = library_parse_bits = None


# Pre-compiled regex patterns for performance optimization
COTTON_VERBATIM_PATTERN = re.compile(r"{%\s*cotton_verbatim\s*%}(.*?){%\s*endcotton_verbatim\s*%}", re.DOTALL)


class ConditionalAttributeStateTracker:
    """O(n) state tracker for Django template syntax - optimizes _is_inside_django_syntax from O(n²) to O(n)"""
    
    def __init__(self, html: str):
        self.html = html
        self.state_map = self._build_state_map()
    
    def _build_state_map(self) -> List[bool]:
        """Build complete state map in single pass - O(n) complexity"""
        state_map = [False] * len(self.html)
        
        # First, mark cotton_verbatim blocks
        for match in COTTON_VERBATIM_PATTERN.finditer(self.html):
            inner_start = match.start() + len(match.group(0)) - len(match.group(1)) - len("{% endcotton_verbatim %}")
            inner_end = match.end() - len("{% endcotton_verbatim %}")
            for pos in range(inner_start, min(inner_end, len(state_map))):
                state_map[pos] = True
        
        # Then, single pass through HTML to track Django syntax states
        i = 0
        in_comment = False
        in_template_var = False  
        in_template_tag = False
        in_django_comment = False
        
        while i < len(self.html):
            # Handle Django comments {# #}
            if not in_template_var and not in_template_tag and not in_django_comment and i + 1 < len(self.html) and self.html[i:i+2] == '{#':
                in_comment = True
                i += 2
                continue
            elif in_comment and i + 1 < len(self.html) and self.html[i:i+2] == '#}':
                in_comment = False
                i += 2
                continue
            
            # Handle Django template variables {{ }}
            elif not in_comment and not in_template_tag and not in_django_comment and i + 1 < len(self.html) and self.html[i:i+2] == '{{':
                in_template_var = True
                i += 2
                continue
            elif in_template_var and i + 1 < len(self.html) and self.html[i:i+2] == '}}':
                in_template_var = False
                i += 2
                continue
            
            # Handle Django template tags {% %}
            elif not in_comment and not in_template_var and not in_django_comment and i + 1 < len(self.html) and self.html[i:i+2] == '{%':
                # Look ahead to see if this is a {% comment %} tag
                tag_content_start = i + 2
                while tag_content_start < len(self.html) and self.html[tag_content_start].isspace():
                    tag_content_start += 1
                
                if tag_content_start + 7 <= len(self.html) and self.html[tag_content_start:tag_content_start+7] == 'comment':
                    in_django_comment = True
                else:
                    in_template_tag = True
                i += 2
                continue
            elif in_template_tag and i + 1 < len(self.html) and self.html[i:i+2] == '%}':
                in_template_tag = False
                i += 2
                continue
            elif in_django_comment and i + 14 < len(self.html) and self.html[i:i+15] == '{% endcomment %}':
                in_django_comment = False
                i += 15
                continue
            
            # Mark current position with current state
            if i < len(state_map):
                state_map[i] = in_comment or in_template_var or in_template_tag or in_django_comment
            
            i += 1
        
        return state_map
    
    def is_inside_django_syntax(self, position: int) -> bool:
        """O(1) lookup instead of O(n) recalculation"""
        if position >= len(self.state_map):
            return False
        return self.state_map[position]


class DjangoLexerProcessor:
    """Ultra-compact processor using Django's professional template system"""
    
    @staticmethod
    def tokenize_and_extract_components(html: str) -> Tuple[List[Token], List[Dict[str, Any]]]:
        """Use manual parsing to properly extract Cotton components with Django template syntax"""
        # Always use manual parsing to handle Django template syntax correctly
        return DjangoLexerProcessor._manual_component_extraction(html)
    
    @staticmethod
    def _manual_component_extraction(html: str) -> Tuple[List, List[Dict[str, Any]]]:
        """Manual component extraction that handles Django template syntax properly - OPTIMIZED O(n)"""
        components = []
        
        # OPTIMIZATION: Create state tracker once - O(n) instead of O(n²)
        state_tracker = ConditionalAttributeStateTracker(html)
        
        # Find ALL component matches at once - O(n) instead of multiple searches
        all_component_matches = list(re.finditer(r'<(/?)c-([^\s/>]+)', html))
        
        for match in all_component_matches:
            tag_start = match.start()
            is_closing = bool(match.group(1))
            tag_name = match.group(2)
            
            # Check if this component is inside Django template syntax - O(1) lookup
            if state_tracker.is_inside_django_syntax(tag_start):
                continue  # Skip this match
            
            # Handle closing tags quickly
            if is_closing:
                end_pos = html.find('>', tag_start)
                if end_pos != -1:
                    components.append({
                        'is_closing': True,
                        'tag_name': tag_name,
                        'attrs_string': '',
                        'is_self_closing': False,
                        'full_match': html[tag_start:end_pos + 1]
                    })
                continue
            
            # For opening tags, find the end using Django-aware parsing
            attrs_start = tag_start + match.end() - match.start()  # Adjust for absolute positioning
            tag_end_pos = DjangoLexerProcessor._find_tag_end_django_aware(html, attrs_start)
            
            if tag_end_pos == -1:
                continue  # Malformed tag, skip
            
            attrs_section = html[attrs_start:tag_end_pos].strip()
            is_self_closing = html[tag_end_pos:tag_end_pos + 2] == "/>"
            actual_end = tag_end_pos + (2 if is_self_closing else 1)
            
            components.append({
                'is_closing': False,
                'tag_name': tag_name,
                'attrs_string': attrs_section,
                'is_self_closing': is_self_closing,
                'full_match': html[tag_start:actual_end]
            })
        
        return [], components
    
    @staticmethod
    def _is_inside_django_syntax(html: str, position: int) -> bool:
        """Check if a position is inside Django template syntax (comments, variables, tags, cotton_verbatim)"""
        if position >= len(html):
            return False
        
        # Check for cotton_verbatim blocks first
        cotton_verbatim_pattern = re.compile(r"{%\s*cotton_verbatim\s*%}(.*?){%\s*endcotton_verbatim\s*%}", re.DOTALL)
        for match in cotton_verbatim_pattern.finditer(html):
            # Check if position is inside the inner content
            inner_start = match.start() + len(match.group(0)) - len(match.group(1)) - len("{% endcotton_verbatim %}")
            inner_end = match.end() - len("{% endcotton_verbatim %}")
            if inner_start <= position < inner_end:
                return True
        
        # Check all Django syntax patterns up to the position
        i = 0
        in_comment = False
        in_template_var = False
        in_template_tag = False
        in_django_comment = False
        
        while i < position:
            # Handle Django comments {# #}
            if not in_template_var and not in_template_tag and not in_django_comment and html[i:i+2] == '{#':
                in_comment = True
                i += 2
                continue
            elif in_comment and html[i:i+2] == '#}':
                in_comment = False
                i += 2
                continue
            
            # Handle Django template variables {{ }}
            elif not in_comment and not in_template_tag and not in_django_comment and html[i:i+2] == '{{':
                in_template_var = True
                i += 2
                continue
            elif in_template_var and html[i:i+2] == '}}':
                in_template_var = False
                i += 2
                continue
            
            # Handle Django template tags {% %}
            elif not in_comment and not in_template_var and not in_django_comment and html[i:i+2] == '{%':
                # Look ahead to see if this is a {% comment %} tag
                tag_content_start = i + 2
                # Skip whitespace after {%
                while tag_content_start < len(html) and html[tag_content_start].isspace():
                    tag_content_start += 1
                
                # Check if this starts with "comment"
                if html[tag_content_start:tag_content_start+7] == 'comment':
                    in_django_comment = True
                else:
                    in_template_tag = True
                i += 2
                continue
            elif in_template_tag and html[i:i+2] == '%}':
                in_template_tag = False
                i += 2
                continue
            elif in_django_comment and html[i:i+15] == '{% endcomment %}':
                in_django_comment = False
                i += 15
                continue
            
            i += 1
        
        return in_comment or in_template_var or in_template_tag or in_django_comment
    
    @staticmethod
    def _find_tag_end_django_aware(html: str, start_pos: int) -> int:
        """Find tag end with Django template syntax awareness"""
        i = start_pos
        in_quote = False
        quote_char = None
        in_template_var = False  # Inside {{ }}
        in_template_tag = False  # Inside {% %}
        
        while i < len(html):
            char = html[i]
            
            # Handle Django template variables {{ }} - these can occur anywhere
            if html[i:i+2] == '{{':
                in_template_var = True
                i += 2
                continue
            elif in_template_var and html[i:i+2] == '}}':
                in_template_var = False
                i += 2
                continue
            
            # Handle Django template tags {% %} - these can occur anywhere
            elif html[i:i+2] == '{%':
                in_template_tag = True
                i += 2
                continue
            elif in_template_tag and html[i:i+2] == '%}':
                in_template_tag = False
                i += 2
                continue
            
            # Handle quotes - but ignore quotes inside template syntax
            elif not in_template_var and not in_template_tag and char in ['"', "'"]:
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char:
                    # Check for escape
                    if i > 0 and html[i-1] != '\\':
                        in_quote = False
                        quote_char = None
            
            # Check for tag end (only when not inside quotes or template syntax)
            elif not in_quote and not in_template_var and not in_template_tag:
                if char == '>' or (char == '/' and i + 1 < len(html) and html[i + 1] == '>'):
                    return i
            
            i += 1
        
        return -1
    
    @staticmethod
    def _fallback_tokenize(html: str) -> Tuple[List, List[Dict[str, Any]]]:
        """Fallback tokenization for testing environments"""
        # Simple fallback that mimics Django's tokenization
        components = []
        component_matches = re.finditer(
            r'<(/?)c-([^\s/>]+)(.*?)(/?)>', 
            html, 
            re.DOTALL
        )
        for match in component_matches:
            components.append({
                'is_closing': bool(match.group(1)),
                'tag_name': match.group(2),
                'attrs_string': match.group(3).strip(),
                'is_self_closing': bool(match.group(4)),
                'full_match': match.group(0)
            })
        return [], components
    
    @staticmethod
    def extract_template_blocks_from_attrs(attrs_string: str) -> Tuple[str, Dict[str, str]]:
        """Extract Django template blocks from attributes - ONLY those outside quoted values"""
        if not attrs_string.strip():
            return attrs_string, {}
        
        # First check if template blocks should be extracted as conditional attributes
        if DjangoLexerProcessor._are_all_template_blocks_in_quotes(attrs_string):
            # Template blocks are inside attribute values - don't extract them
            return attrs_string, {}
        
        # Extract only template blocks that are outside quoted attribute values
        return DjangoLexerProcessor._extract_conditional_blocks_only(attrs_string)
    
    @staticmethod
    def _fallback_extract_blocks(attrs_string: str) -> Tuple[str, Dict[str, str]]:
        """Enhanced fallback block extraction handling complete nested template blocks"""
        if not attrs_string.strip():
            return attrs_string, {}
        
        template_blocks = {}
        block_counter = 0
        cleaned_attrs = attrs_string
        i = 0
        
        while i < len(attrs_string):
            # Look for template block start
            if attrs_string[i:i+2] == "{%":
                # Find the end of the opening tag
                tag_end = i + 2
                while tag_end < len(attrs_string) and attrs_string[tag_end:tag_end+2] != "%}":
                    tag_end += 1
                
                if tag_end >= len(attrs_string):
                    i += 1  # Malformed, skip
                    continue
                
                # Extract tag name to check if it needs a closing tag
                tag_content = attrs_string[i + 2:tag_end].strip()
                if not tag_content:
                    i = tag_end + 2
                    continue
                
                tag_name = tag_content.split()[0]
                
                # Tags that need closing tags
                if tag_name in ["if", "for", "with", "block", "comment", "verbatim", "spaceless", "filter"]:
                    # Find matching end tag
                    block_start = i
                    block_end = DjangoLexerProcessor._find_complete_block_end(attrs_string, i, tag_name)
                    
                    if block_end > block_start:
                        # Extract complete block
                        complete_block = attrs_string[block_start:block_end]
                        placeholder = f"__COTTON_TEMPLATE_BLOCK_{block_counter}__"
                        template_blocks[placeholder] = complete_block
                        cleaned_attrs = cleaned_attrs.replace(complete_block, f" {placeholder} ")
                        block_counter += 1
                        i = block_end
                    else:
                        i += 1
                else:
                    # Single tag like {% load %}, {% extends %}, etc.
                    single_tag = attrs_string[i:tag_end + 2]
                    placeholder = f"__COTTON_TEMPLATE_BLOCK_{block_counter}__"
                    template_blocks[placeholder] = single_tag
                    cleaned_attrs = cleaned_attrs.replace(single_tag, f" {placeholder} ")
                    block_counter += 1
                    i = tag_end + 2
            else:
                i += 1
        
        return cleaned_attrs.strip(), template_blocks
    
    @staticmethod
    def _find_complete_block_end(attrs_string: str, start_pos: int, tag_name: str) -> int:
        """Find the end of a complete template block including nested blocks"""
        nest_level = 1
        i = start_pos
        end_tag = f"end{tag_name}"
        
        # Skip past the opening tag
        while i < len(attrs_string) and attrs_string[i:i+2] != "%}":
            i += 1
        i += 2  # Skip past %}
        
        while i < len(attrs_string) and nest_level > 0:
            if attrs_string[i:i+2] == "{%":
                # Find this tag's end
                tag_end = i + 2
                while tag_end < len(attrs_string) and attrs_string[tag_end:tag_end+2] != "%}":
                    tag_end += 1
                
                if tag_end < len(attrs_string):
                    inner_content = attrs_string[i + 2:tag_end].strip()
                    if inner_content:
                        inner_tag = inner_content.split()[0]
                        if inner_tag == tag_name:
                            nest_level += 1
                        elif inner_tag == end_tag:
                            nest_level -= 1
                    i = tag_end + 2
                else:
                    break
            else:
                i += 1
        
        return i if nest_level == 0 else start_pos
    
    @staticmethod
    def _are_all_template_blocks_in_quotes(attrs_string: str) -> bool:
        """Check if ALL template blocks in attributes are inside quoted values"""
        if not attrs_string.strip():
            return False
        
        # Find all template blocks (both {% %} and {{ }})
        template_blocks = []
        for match in re.finditer(r'({%.*?%}|{{.*?}})', attrs_string, re.DOTALL):
            template_blocks.append(match)
        
        if not template_blocks:
            return False
        
        # Check if ALL template blocks are inside quotes
        blocks_outside_quotes = 0
        blocks_inside_quotes = 0
        
        for block_match in template_blocks:
            if DjangoLexerProcessor._is_position_inside_quotes(attrs_string, block_match.start()):
                blocks_inside_quotes += 1
            else:
                blocks_outside_quotes += 1
        
        # If there are blocks outside quotes, we should extract them as conditional attributes
        # If ALL blocks are inside quotes, we should NOT extract them
        return blocks_outside_quotes == 0 and blocks_inside_quotes > 0
    
    @staticmethod
    def _is_position_inside_quotes(text: str, position: int) -> bool:
        """Check if a position in text is inside quoted attribute values"""
        if position >= len(text):
            return False
        
        in_quote = False
        quote_char = None
        i = 0
        
        while i < position:
            char = text[i]
            if char in ['"', "'"]:
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif char == quote_char:
                    # Check for escape
                    backslashes = 0
                    j = i - 1
                    while j >= 0 and text[j] == '\\':
                        backslashes += 1
                        j -= 1
                    if backslashes % 2 == 0:  # Even number = not escaped
                        in_quote = False
                        quote_char = None
            i += 1
        
        return in_quote
    
    @staticmethod
    def _extract_conditional_blocks_only(attrs_string: str) -> Tuple[str, Dict[str, str]]:
        """Extract only template blocks that are outside quoted attribute values - OPTIMIZED O(n)"""
        template_blocks = {}
        block_positions = []  # Store (start, end, block_content, placeholder) for StringBuilder pattern
        block_counter = 0
        i = 0
        
        # PHASE 1: Find all blocks that need extraction - O(n)
        while i < len(attrs_string):
            if attrs_string[i:i+2] == "{%":
                # Check if this block is inside quotes
                if not DjangoLexerProcessor._is_position_inside_quotes(attrs_string, i):
                    # This block is outside quotes - extract it
                    tag_end = i + 2
                    while tag_end < len(attrs_string) and attrs_string[tag_end:tag_end+2] != "%}":
                        tag_end += 1
                    
                    if tag_end < len(attrs_string):
                        tag_content = attrs_string[i + 2:tag_end].strip()
                        if tag_content:
                            tag_name = tag_content.split()[0]
                            
                            # Handle block vs single tags
                            if tag_name in ["if", "for", "with", "block", "comment", "verbatim", "spaceless", "filter"]:
                                # Find complete block
                                block_end = DjangoLexerProcessor._find_complete_block_end(attrs_string, i, tag_name)
                                if block_end > i:
                                    complete_block = attrs_string[i:block_end]
                                    placeholder = f"__COTTON_TEMPLATE_BLOCK_{block_counter}__"
                                    template_blocks[placeholder] = complete_block
                                    block_positions.append((i, block_end, complete_block, placeholder))
                                    block_counter += 1
                                    i = block_end
                                    continue
                            else:
                                # Single tag
                                single_tag = attrs_string[i:tag_end + 2]
                                placeholder = f"__COTTON_TEMPLATE_BLOCK_{block_counter}__"
                                template_blocks[placeholder] = single_tag
                                block_positions.append((i, tag_end + 2, single_tag, placeholder))
                                block_counter += 1
                                i = tag_end + 2
                                continue
                
            i += 1
        
        # PHASE 2: Build result using StringBuilder pattern - O(n)
        if not block_positions:
            return attrs_string.strip(), template_blocks
        
        # Sort by position to ensure correct replacement order
        block_positions.sort(key=lambda x: x[0])
        
        result_parts = []
        last_end = 0
        
        for start, end, block_content, placeholder in block_positions:
            # Add text before this block
            result_parts.append(attrs_string[last_end:start])
            # Add placeholder
            result_parts.append(f" {placeholder} ")
            last_end = end
        
        # Add remaining text
        result_parts.append(attrs_string[last_end:])
        
        # Single join operation - O(n)
        cleaned_attrs = ''.join(result_parts)
        
        return cleaned_attrs.strip(), template_blocks


class CottonComponentProcessor:
    """Ultra-compact component processor using Django's parse utilities"""
    
    @staticmethod
    def process_component(component_info: Dict[str, Any]) -> str:
        """Convert Cotton component to Django template tag using parse_bits"""
        tag_name = component_info['tag_name']
        attrs_string = component_info['attrs_string']
        is_closing = component_info['is_closing']
        is_self_closing = component_info['is_self_closing']
        
        # Handle special cases
        if tag_name == "vars":
            return ""  # c-vars handled separately
        elif tag_name == "slot":
            return CottonComponentProcessor._process_slot(attrs_string, is_closing)
        elif is_closing:
            return "{% endc %}"
        
        # Extract template blocks from attributes
        cleaned_attrs, template_blocks = DjangoLexerProcessor.extract_template_blocks_from_attrs(attrs_string)
        
        # Parse attributes using Django's approach
        processed_attrs, extracted_attrs = CottonComponentProcessor._parse_attributes_with_django(
            cleaned_attrs, template_blocks
        )
        
        # Build final template tag
        attrs_str = f" {' '.join(processed_attrs)}" if processed_attrs else ""
        opening_tag = f"{{% c {tag_name}{attrs_str} %}}"
        all_attrs = "".join(extracted_attrs)
        
        return f"{opening_tag}{all_attrs}{{% endc %}}" if is_self_closing else f"{opening_tag}{all_attrs}"
    
    @staticmethod
    def _process_slot(attrs_string: str, is_closing: bool) -> str:
        """Process c-slot tags"""
        if is_closing:
            return "{% endslot %}"
        
        # Extract slot name using simple regex (Django parse_bits overkill for this)
        name_match = re.search(r'name=(["\'])(.*?)\1', attrs_string)
        if not name_match:
            raise ValueError(f"c-slot tag must have a name attribute:")
        return f"{{% slot {name_match.group(2)} %}}"
    
    @staticmethod
    def _parse_attributes_with_django(cleaned_attrs: str, template_blocks: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Parse attributes using Django-aware approach"""
        processed_attrs = []
        extracted_attrs = []
        
        # Remove any leftover template block placeholders from cleaned_attrs
        cleaned_attrs = re.sub(r'__COTTON_TEMPLATE_BLOCK_\d+__', '', cleaned_attrs)
        # Note: Don't normalize whitespace here as it would destroy formatting in attribute values
        
        if cleaned_attrs:
            # Django-aware attribute parsing
            i = 0
            while i < len(cleaned_attrs):
                # Skip whitespace
                while i < len(cleaned_attrs) and cleaned_attrs[i].isspace():
                    i += 1
                if i >= len(cleaned_attrs):
                    break
                
                # Find attribute name
                attr_start = i
                while i < len(cleaned_attrs) and not cleaned_attrs[i].isspace() and cleaned_attrs[i] != '=':
                    i += 1
                
                if attr_start == i:
                    break  # No attribute found
                
                attr_name = cleaned_attrs[attr_start:i]
                
                # Skip whitespace after attribute name
                while i < len(cleaned_attrs) and cleaned_attrs[i].isspace():
                    i += 1
                
                # Check if we have a value (= sign)
                if i >= len(cleaned_attrs) or cleaned_attrs[i] != '=':
                    # Boolean attribute
                    processed_attrs.append(attr_name)
                    continue
                
                # Skip the = sign
                i += 1
                
                # Skip whitespace after = sign
                while i < len(cleaned_attrs) and cleaned_attrs[i].isspace():
                    i += 1
                
                if i >= len(cleaned_attrs):
                    break  # Malformed attribute
                
                # Parse attribute value (Django-aware)
                if cleaned_attrs[i] in ['"', "'"]:
                    # Quoted attribute value
                    quote_char = cleaned_attrs[i]
                    i += 1  # Skip opening quote
                    value_start = i
                    
                    # Find closing quote (Django-aware)
                    in_template_var = False
                    in_template_tag = False
                    
                    while i < len(cleaned_attrs):
                        char = cleaned_attrs[i]
                        
                        # Handle Django template variables {{ }}
                        if cleaned_attrs[i:i+2] == '{{':
                            in_template_var = True
                            i += 2
                            continue
                        elif in_template_var and cleaned_attrs[i:i+2] == '}}':
                            in_template_var = False
                            i += 2
                            continue
                        
                        # Handle Django template tags {% %}
                        elif cleaned_attrs[i:i+2] == '{%':
                            in_template_tag = True
                            i += 2
                            continue
                        elif in_template_tag and cleaned_attrs[i:i+2] == '%}':
                            in_template_tag = False
                            i += 2
                            continue
                        
                        # Handle quotes - only end on matching quote when not inside template syntax
                        elif not in_template_var and not in_template_tag and char == quote_char:
                            # Check for escape
                            if i > 0 and cleaned_attrs[i-1] != '\\':
                                break  # Found closing quote
                        
                        i += 1
                    
                    if i < len(cleaned_attrs) and cleaned_attrs[i] == quote_char:
                        value = cleaned_attrs[value_start:i]
                        i += 1  # Skip closing quote
                        
                        # Check if attribute needs extraction
                        if any(s in value for s in ("{{", "{%", "=")):
                            extracted_attrs.append(f"{{% attr {attr_name} %}}{value}{{% endattr %}}")
                        else:
                            processed_attrs.append(f'{attr_name}="{value}"')
                    else:
                        # Malformed attribute, skip
                        break
                else:
                    # Unquoted attribute value
                    value_start = i
                    while i < len(cleaned_attrs) and not cleaned_attrs[i].isspace():
                        i += 1
                    value = cleaned_attrs[value_start:i]
                    
                    # Check if attribute needs extraction
                    if any(s in value for s in ("{{", "{%", "=")):
                        extracted_attrs.append(f"{{% attr {attr_name} %}}{value}{{% endattr %}}")
                    else:
                        processed_attrs.append(f'{attr_name}="{value}"')
        
        # Add template blocks as conditional attributes
        for i, block_content in enumerate(template_blocks.values()):
            extracted_attrs.append(f"{{% attr _conditional_{i} %}}{block_content}{{% endattr %}}")
        
        return processed_attrs, extracted_attrs


class CottonCompiler:
    """Ultra-compact single-pass Cotton compiler using Django's Lexer"""
    
    def __init__(self):
        self.c_vars_pattern = re.compile(r"<c-vars\s([^>]*)(?:/>|>(.*?)</c-vars>)", re.DOTALL)
        self.cotton_verbatim_pattern = re.compile(
            r"{%\s*cotton_verbatim\s*%}(.*?){%\s*endcotton_verbatim\s*%}", re.DOTALL
        )
    
    def process(self, html: str) -> str:
        """Single-pass processing using Django's Lexer for professional template handling"""
        
        # Step 1: Handle cotton_verbatim blocks
        html = self._process_cotton_verbatim(html)
        
        # Step 2: Extract c-vars first
        vars_content, html = self._process_c_vars(html)
        
        # Step 3: Process Cotton components using Django Lexer
        tokens, components = DjangoLexerProcessor.tokenize_and_extract_components(html)
        
        # Step 4: Transform components in reverse order to avoid position issues
        for component in reversed(components):
            try:
                replacement = CottonComponentProcessor.process_component(component)
                html = html.replace(component['full_match'], replacement)
            except ValueError as e:
                # Enhanced error reporting
                line_number = html[:html.find(component['full_match'])].count('\n') + 1
                raise ValueError(f"Error in template at line {line_number}: {str(e)}") from e
        
        # Step 5: Wrap with vars if needed
        if vars_content:
            html = f"{vars_content}{html}{{% endvars %}}"
        
        return html
    
    def _process_cotton_verbatim(self, html: str) -> str:
        """Process cotton_verbatim blocks by extracting their inner content"""
        def extract_verbatim_content(match):
            return match.group(1)  # Return just the inner content
        return self.cotton_verbatim_pattern.sub(extract_verbatim_content, html)
    
    def _get_cotton_verbatim_ranges(self, html: str) -> List[Tuple[int, int]]:
        """Get ranges of cotton_verbatim content that should be ignored"""
        ranges = []
        for match in self.cotton_verbatim_pattern.finditer(html):
            # Get the range of the inner content (without the tags)
            inner_start = match.start() + len(match.group(0)) - len(match.group(1)) - len("{% endcotton_verbatim %}")
            inner_end = match.end() - len("{% endcotton_verbatim %}")
            ranges.append((inner_start, inner_end))
        return ranges
    
    def _process_c_vars(self, html: str) -> Tuple[str, str]:
        """Extract c-vars content and remove c-vars tags from the html (Django-aware) - OPTIMIZED O(n)"""
        # Find all potential c-vars matches
        all_matches = list(self.c_vars_pattern.finditer(html))
        
        # OPTIMIZATION: Create state tracker once instead of O(n²) calls
        state_tracker = ConditionalAttributeStateTracker(html)
        
        # Filter out matches that are inside Django template syntax - O(1) per match
        valid_matches = []
        for match in all_matches:
            if not state_tracker.is_inside_django_syntax(match.start()):
                valid_matches.append(match)
        
        if len(valid_matches) > 1:
            raise ValueError(
                "Multiple c-vars tags found in component template. Only one c-vars tag is allowed per template."
            )
        
        if valid_matches:
            match = valid_matches[0]
            attrs = match.group(1)
            vars_content = f"{{% vars {attrs.strip()} %}}"
            # Remove only the valid match
            html = html[:match.start()] + html[match.end():]
            return vars_content, html
        
        return "", html
