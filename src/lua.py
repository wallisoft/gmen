#!/usr/bin/env python3
"""
lua.py - Pure Python Lua interpreter for GMen
Simplified Lua interpreter for scripting support
"""

import re
import math
import random
import subprocess
import time

class LuaState:
    """Simple Lua interpreter state"""
    
    def __init__(self):
        self.globals = {}
        self.functions = {
            'print': self._print,
            'type': self._type,
            'tonumber': self._tonumber,
            'tostring': self._tostring,
            'pairs': self._pairs,
            'ipairs': self._ipairs,
            'next': self._next,
            'select': self._select,
            'unpack': self._unpack,
            'table': {
                'concat': self._table_concat,
                'insert': self._table_insert,
                'remove': self._table_remove,
                'sort': self._table_sort,
            },
            'string': {
                'format': self._string_format,
                'sub': self._string_sub,
                'find': self._string_find,
                'gsub': self._string_gsub,
                'match': self._string_match,
                'len': len,
                'lower': lambda s: s.lower(),
                'upper': lambda s: s.upper(),
            },
            'math': {
                'floor': math.floor,
                'ceil': math.ceil,
                'abs': abs,
                'max': max,
                'min': min,
                'random': self._math_random,
                'pi': math.pi,
                'sin': math.sin,
                'cos': math.cos,
                'sqrt': math.sqrt,
            },
            'os': {
                'time': time.time,
                'date': self._os_date,
                'difftime': lambda t2, t1: t2 - t1,
            }
        }
        
        # GMen-specific API
        self.gmen_api = {
            'launch': self._gmen_launch,
            'notify': self._gmen_notify,
            'sleep': self._gmen_sleep,
            'run_script': self._gmen_run_script,
            'set_window': self._gmen_set_window,
            'get_window_state': self._gmen_get_window_state,
        }
        
        self.open_libs()
    
    def open_libs(self):
        """Open standard libraries"""
        for name, func in self.functions.items():
            if isinstance(func, dict):
                self.globals[name] = func
            else:
                self.globals[name] = func
        
        # Add GMen API
        self.globals['gmen'] = self.gmen_api
    
    def eval(self, code):
        """Evaluate Lua code"""
        try:
            # Remove comments and extra whitespace
            lines = code.split('\n')
            cleaned_lines = []
            for line in lines:
                # Remove Lua comments
                line = re.sub(r'--.*$', '', line)
                if line.strip():
                    cleaned_lines.append(line)
            
            cleaned_code = '\n'.join(cleaned_lines)
            
            # Check for main function pattern
            if 'function main()' in cleaned_code:
                # Extract main function
                main_match = re.search(r'function main\s*\((.*?)\)\s*(.*?)\s*end', cleaned_code, re.DOTALL)
                if main_match:
                    # Define main function
                    self.globals['main'] = lambda *args: self._execute_lua_block(main_match.group(2))
                    # Call main function
                    return self.globals['main']()
                else:
                    # Execute as block
                    return self._execute_lua_block(cleaned_code)
            elif cleaned_code.strip().startswith('return'):
                # Single return statement
                expr = cleaned_code.replace('return', '', 1).strip()
                return self._eval_expression(expr)
            else:
                # Execute as block
                return self._execute_lua_block(cleaned_code)
        except Exception as e:
            print(f"Lua error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _execute_lua_block(self, block):
        """Execute a block of Lua code"""
        lines = block.split(';')
        last_result = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Handle function definitions
            if line.startswith('function'):
                self._parse_function(line)
                continue
            
            # Handle local variable declarations
            if line.startswith('local'):
                line = line[5:].strip()
                if '=' in line:
                    var_name, expr = line.split('=', 1)
                    var_name = var_name.strip()
                    value = self._eval_expression(expr.strip())
                    self.globals[var_name] = value
                continue
            
            # Handle assignments
            if '=' in line and not line.startswith('if') and not line.startswith('for') and not line.startswith('while'):
                var_name, expr = line.split('=', 1)
                var_name = var_name.strip()
                value = self._eval_expression(expr.strip())
                self.globals[var_name] = value
                last_result = value
                continue
            
            # Handle if statements (simplified)
            if line.startswith('if'):
                # Very simple if statement handling
                condition = line[2:].split('then')[0].strip()
                if self._eval_expression(condition):
                    # Execute then block (simplified)
                    pass
                continue
            
            # Handle for loops (simplified)
            if line.startswith('for'):
                # Very simple for loop handling
                parts = line[3:].split('in')
                if len(parts) == 2:
                    # pairs/ipairs loop
                    pass
                continue
            
            # Handle expressions
            last_result = self._eval_expression(line)
        
        return last_result
    
    def _parse_function(self, line):
        """Parse a function definition"""
        match = re.match(r'function\s+(\w+)\s*\((.*?)\)', line)
        if match:
            func_name = match.group(1)
            params = [p.strip() for p in match.group(2).split(',')] if match.group(2) else []
            self.globals[func_name] = lambda *args: None  # Placeholder
    
    def _eval_expression(self, expr):
        """Evaluate a Lua expression"""
        expr = expr.strip()
        
        # Handle nil
        if expr == 'nil':
            return None
        
        # Handle booleans
        if expr == 'true':
            return True
        if expr == 'false':
            return False
        
        # Handle numbers
        if re.match(r'^-?\d+(\.\d+)?$', expr):
            try:
                return float(expr) if '.' in expr else int(expr)
            except:
                return None
        
        # Handle strings
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        
        # Handle concatenation
        if '..' in expr:
            parts = expr.split('..')
            result = ''
            for part in parts:
                part = part.strip()
                result += str(self._eval_expression(part))
            return result
        
        # Handle arithmetic
        if '+' in expr and not expr.startswith('+'):
            parts = expr.split('+')
            result = 0
            for part in parts:
                part = part.strip()
                val = self._eval_expression(part)
                if isinstance(val, (int, float)):
                    result += val
            return result
        
        if '-' in expr and not expr.startswith('-') and not re.match(r'^-?\d', expr):
            parts = expr.split('-')
            result = self._eval_expression(parts[0].strip())
            for part in parts[1:]:
                part = part.strip()
                val = self._eval_expression(part)
                if isinstance(val, (int, float)):
                    result -= val
            return result
        
        # Handle function calls
        if '(' in expr and expr.endswith(')'):
            func_name = expr.split('(', 1)[0].strip()
            args_str = expr.split('(', 1)[1][:-1]
            args = self._parse_args(args_str)
            return self._call_function(func_name, args)
        
        # Handle table constructors
        if expr.startswith('{') and expr.endswith('}'):
            return self._parse_table(expr[1:-1])
        
        # Handle variable reference
        if expr in self.globals:
            return self.globals[expr]
        
        # Handle table access
        if '.' in expr:
            parts = expr.split('.')
            current = self.globals.get(parts[0])
            for part in parts[1:]:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            return current
        
        return expr
    
    def _parse_table(self, table_str):
        """Parse Lua table"""
        table = {}
        index = 1
        
        # Remove outer braces if present
        table_str = table_str.strip()
        if table_str.startswith('{'):
            table_str = table_str[1:]
        if table_str.endswith('}'):
            table_str = table_str[:-1]
        
        # Simple parser for key-value pairs
        items = []
        current_item = ''
        brace_count = 0
        
        for char in table_str:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == ',' and brace_count == 0:
                items.append(current_item.strip())
                current_item = ''
                continue
            current_item += char
        
        if current_item.strip():
            items.append(current_item.strip())
        
        for item in items:
            if not item:
                continue
                
            if '=' in item:
                key, value = item.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes from string keys
                if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
                    key = key[1:-1]
                
                table[key] = self._eval_expression(value)
            else:
                table[index] = self._eval_expression(item)
                index += 1
        
        return table
    
    def _parse_args(self, args_str):
        """Parse function arguments"""
        args = []
        if args_str.strip():
            current_arg = ''
            brace_count = 0
            
            for char in args_str:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == ',' and brace_count == 0:
                    args.append(self._eval_expression(current_arg.strip()))
                    current_arg = ''
                    continue
                current_arg += char
            
            if current_arg.strip():
                args.append(self._eval_expression(current_arg.strip()))
        
        return args
    
    def _call_function(self, func_name, args):
        """Call a Lua function"""
        # Check if it's a table access
        if '.' in func_name:
            parts = func_name.split('.')
            current = self.globals.get(parts[0])
            
            for part in parts[1:-1]:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            
            func = current.get(parts[-1]) if isinstance(current, dict) else None
        else:
            func = self.globals.get(func_name)
        
        if callable(func):
            try:
                return func(*args)
            except Exception as e:
                print(f"Function call error: {e}")
                return None
        elif isinstance(func, dict) and 'main' in func:
            return func['main'](*args)
        
        return None
    
    # ===== BUILT-IN FUNCTIONS =====
    
    def _print(self, *args):
        """Lua print function"""
        output = '\t'.join(str(arg) for arg in args)
        print(output)
        return None
    
    def _type(self, obj):
        """Lua type function"""
        if obj is None:
            return 'nil'
        elif isinstance(obj, bool):
            return 'boolean'
        elif isinstance(obj, (int, float)):
            return 'number'
        elif isinstance(obj, str):
            return 'string'
        elif isinstance(obj, (list, dict)):
            return 'table'
        elif callable(obj):
            return 'function'
        else:
            return 'userdata'
    
    def _tonumber(self, val):
        """Convert to number"""
        try:
            return float(val)
        except:
            return None
    
    def _tostring(self, val):
        """Convert to string"""
        return str(val)
    
    def _pairs(self, table):
        """Lua pairs iterator"""
        if isinstance(table, dict):
            return iter(table.items())
        return iter([])
    
    def _ipairs(self, table):
        """Lua ipairs iterator"""
        if isinstance(table, dict):
            numeric_keys = [k for k in table.keys() if isinstance(k, (int, float))]
            numeric_keys.sort()
            return ((i, table[i]) for i in numeric_keys)
        return iter([])
    
    def _next(self, table, key=None):
        """Lua next function"""
        if not isinstance(table, dict):
            return None
        
        keys = list(table.keys())
        if key is None:
            if keys:
                return keys[0], table[keys[0]]
        else:
            try:
                idx = keys.index(key)
                if idx + 1 < len(keys):
                    next_key = keys[idx + 1]
                    return next_key, table[next_key]
            except:
                pass
        
        return None
    
    def _select(self, index, *args):
        """Lua select function"""
        if index == '#':
            return len(args)
        elif index > 0:
            return args[index-1:]
        else:
            return args[index:]
    
    def _unpack(self, table):
        """Lua unpack function"""
        if isinstance(table, dict):
            numeric_keys = [k for k in table.keys() if isinstance(k, (int, float))]
            numeric_keys.sort()
            return [table[k] for k in numeric_keys]
        return []
    
    def _table_concat(self, table, sep="", i=1, j=None):
        """Lua table.concat"""
        if not isinstance(table, dict):
            return ""
        
        if j is None:
            numeric_keys = [k for k in table.keys() if isinstance(k, (int, float))]
            j = max(numeric_keys) if numeric_keys else 0
        
        parts = []
        for k in range(i, j+1):
            if k in table:
                parts.append(str(table[k]))
        
        return sep.join(parts)
    
    def _table_insert(self, table, pos, value=None):
        """Lua table.insert"""
        if not isinstance(table, dict):
            return
        
        if value is None:
            value = pos
            numeric_keys = [k for k in table.keys() if isinstance(k, (int, float))]
            pos = max(numeric_keys, default=0) + 1
        
        keys_to_shift = [k for k in table.keys() if isinstance(k, (int, float)) and k >= pos]
        keys_to_shift.sort(reverse=True)
        for k in keys_to_shift:
            table[k+1] = table[k]
        
        table[pos] = value
    
    def _table_remove(self, table, pos=None):
        """Lua table.remove"""
        if not isinstance(table, dict):
            return None
        
        if pos is None:
            numeric_keys = [k for k in table.keys() if isinstance(k, (int, float))]
            if not numeric_keys:
                return None
            pos = max(numeric_keys)
        
        if pos in table:
            value = table.pop(pos)
            keys_to_shift = [k for k in table.keys() if isinstance(k, (int, float)) and k > pos]
            keys_to_shift.sort()
            for k in keys_to_shift:
                table[k-1] = table.pop(k)
            return value
        
        return None
    
    def _table_sort(self, table):
        """Lua table.sort (simplified)"""
        if not isinstance(table, dict):
            return
        
        items = [(k, table[k]) for k in table.keys() if isinstance(k, (int, float))]
        items.sort(key=lambda x: x[1])  # Sort by value
        
        for idx, (old_key, value) in enumerate(items, 1):
            table[idx] = value
            if old_key != idx:
                table.pop(old_key, None)
    
    def _string_format(self, fmt, *args):
        """Lua string.format (simplified)"""
        try:
            return fmt % args
        except:
            return fmt
    
    def _string_sub(self, s, i, j=None):
        """Lua string.sub"""
        if j is None:
            j = len(s)
        if i < 0:
            i = len(s) + i + 1
        if j < 0:
            j = len(s) + j + 1
        return s[i-1:j]
    
    def _string_find(self, s, pattern, init=1):
        """Lua string.find (simplified)"""
        if init < 0:
            init = len(s) + init + 1
        
        idx = s.find(pattern, init-1)
        if idx != -1:
            return idx + 1
        return None
    
    def _string_gsub(self, s, pattern, repl, n=None):
        """Lua string.gsub (simplified)"""
        if n is None:
            n = 0
        
        result = s
        count = 0
        
        if n == 0:
            result, count = re.subn(pattern, repl, s)
        else:
            for _ in range(n):
                result, replaced = re.subn(pattern, repl, result, count=1)
                if replaced:
                    count += 1
                else:
                    break
        
        return result, count
    
    def _string_match(self, s, pattern):
        """Lua string.match"""
        match = re.search(pattern, s)
        if match:
            if match.groups():
                return match.groups()[0]
            else:
                return match.group(0)
        return None
    
    def _math_random(self, m=None, n=None):
        """Lua math.random"""
        if m is None and n is None:
            return random.random()
        elif n is None:
            return random.randint(1, int(m))
        else:
            return random.randint(int(m), int(n))
    
    def _os_date(self, format_str=None, time_val=None):
        """Lua os.date (simplified)"""
        import time as t
        if time_val is None:
            time_val = t.time()
        
        if format_str is None:
            return t.ctime(time_val)
        elif format_str == '*t':
            tm = t.localtime(time_val)
            return {
                'year': tm.tm_year,
                'month': tm.tm_mon,
                'day': tm.tm_mday,
                'hour': tm.tm_hour,
                'min': tm.tm_min,
                'sec': tm.tm_sec,
                'wday': tm.tm_wday + 1,
                'yday': tm.tm_yday,
                'isdst': tm.tm_isdst
            }
        else:
            return t.strftime(format_str, t.localtime(time_val))
    
    # ===== GMEN API FUNCTIONS =====
    
    def _gmen_launch(self, command):
        """GMen launch function"""
        try:
            process = subprocess.Popen(command, shell=True)
            return process.pid
        except Exception as e:
            print(f"Launch error: {e}")
            return -1
    
    def _gmen_notify(self, message):
        """GMen notify function"""
        print(f"📢 GMen Notification: {message}")
        return True
    
    def _gmen_sleep(self, seconds):
        """GMen sleep function"""
        time.sleep(seconds)
        return True
    
    def _gmen_run_script(self, script_name):
        """GMen run_script function"""
        print(f"📜 Running script: {script_name}")
        return True
    
    def _gmen_set_window(self, pid, x, y, width, height):
        """GMen set_window function"""
        print(f"🪟 Setting window {pid} to {x},{y} {width}x{height}")
        return True
    
    def _gmen_get_window_state(self, app_name):
        """GMen get_window_state function"""
        print(f"🪟 Getting window state for {app_name}")
        return {'x': 100, 'y': 100, 'width': 800, 'height': 600, 'monitor': 0}


# Simple test
if __name__ == "__main__":
    lua = LuaState()
    
    print("Testing Lua interpreter...")
    
    # Test basic Lua
    print("1 + 1 =", lua.eval("return 1 + 1"))
    print('String: "Hello" .. " World" =', lua.eval('return "Hello" .. " World"'))
    
    # Test table
    print("Table: {1, 2, 3} =", lua.eval("return {1, 2, 3}"))
    
    # Test GMen API
    print("\nTesting GMen API...")
    lua.eval('gmen.notify("Hello from Lua!")')
    lua.eval('gmen.sleep(0.5)')
    
    # Test function
    test_code = """
function add(a, b)
    return a + b
end

return add(10, 20)
"""
    print("Function test:", lua.eval(test_code))
    
    print("\n✅ Lua interpreter ready!")
