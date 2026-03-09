#!/usr/bin/env python3
"""
Strip browser-in-browser chrome from all content pages.

HTML section: Remove all browser chrome (title bar, menu bar, toolbar, address bar,
              era tabs, status bar, wrapper tables). Keep only HTML content with
              simple navigation links. No CSS, no JavaScript.

CSS section:  Remove browser chrome HTML elements. Keep <style> blocks but remove
              browser chrome CSS rules. Keep era-appropriate content styling.
              No JavaScript.

JavaScript section: Remove browser chrome HTML elements. Keep <style> blocks
                    (minus chrome CSS) and <script> blocks. Keep all three technologies.
"""

import re
import os

BASE = '/workspaces/HistoryOfWebDesign'


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# ============================================================
# HTML SECTION - strip everything, keep pure HTML
# ============================================================

def process_html_file(filepath):
    """Strip browser chrome from HTML section files. Keep only HTML content."""
    content = read_file(filepath)
    lines = content.split('\n')
    
    # Find the content area - it's between the era tabs closing and the status bar
    # Pattern: after "<!-- Content area -->" table opening, before status bar
    
    # Strategy: find the actual content between the chrome tables
    # The HTML files use nested tables for chrome. Content is inside the innermost table.
    
    # Find title from <title> tag
    title_match = re.search(r'<title>(.*?)</title>', content)
    title = title_match.group(1) if title_match else 'History of Web Design'
    
    # Find content start marker
    content_start = None
    content_end = None
    
    # Look for the content area table or the first <h1> tag
    for i, line in enumerate(lines):
        if '<!-- Content area -->' in line or ('<!-- ORIGINAL PAGE CONTENT' in line.upper()):
            content_start = i + 1
            break
        if content_start is None and '<h1>' in line.lower() or '<h1 ' in line.lower():
            # Backtrack to find the content table
            content_start = i
            break
        if content_start is None and ('<header>' in line.lower()):
            content_start = i
            break
    
    if content_start is None:
        # Try to find after era tabs - look for the pattern after era tabs table
        for i, line in enumerate(lines):
            if 'bgcolor="#c0c0c0" width="100%">&nbsp;' in line:
                # This is the end of era tabs, skip closing tags
                for j in range(i+1, min(i+10, len(lines))):
                    if '<h1' in lines[j].lower() or '<header' in lines[j].lower() or '<center' in lines[j].lower():
                        content_start = j
                        break
                    if '<!-- Content area -->' in lines[j]:
                        content_start = j + 1
                        break
                if content_start:
                    break

    if content_start is None:
        print(f"  WARNING: Could not find content start in {filepath}")
        return
    
    # Skip table wrapper lines right before content
    while content_start < len(lines):
        stripped = lines[content_start].strip()
        if stripped.startswith('<!-- Content area -->'):
            content_start += 1
            continue
        if stripped.startswith('<table') and ('cellpadding="8"' in stripped or 'cellpadding="0"' in stripped):
            content_start += 1
            continue
        if stripped == '<tr><td>' or stripped == '<tr><td bgcolor=':
            content_start += 1
            continue
        break
    
    # Find content end - look for status bar or closing wrapper tables at the end
    for i in range(len(lines) - 1, content_start, -1):
        line = lines[i].strip()
        if '<!-- Status bar -->' in line or 'statusbar' in line.lower():
            content_end = i
            break
        if ('Document:' in line and 'Done' in line) or 'historyofwd.netlify.app' in line:
            # Found status bar content, go back to find its start
            for j in range(i, max(i-5, content_start), -1):
                if '<!-- Status' in lines[j] or '<table' in lines[j]:
                    content_end = j
                    break
            if content_end:
                break
    
    if content_end is None:
        content_end = len(lines)
    
    # Now go backwards from content_end to skip closing wrapper table tags
    while content_end > content_start:
        stripped = lines[content_end - 1].strip()
        if stripped in ('</td></tr>', '</table>', '</td>', '</tr>', '', '</div>'):
            content_end -= 1
        elif stripped.startswith('</table>'):
            content_end -= 1
        else:
            break
    
    # Extract the actual content lines
    content_lines = lines[content_start:content_end]
    
    # Build the navigation links based on filename
    basename = os.path.basename(filepath)
    
    nav_links = '''<p>
<a href="/index.html">Hub</a> |
<a href="htmlhome.html">Home</a> |
<a href="era1-1990-1994.html">1990-1994</a> |
<a href="era2-1994-1997.html">1994-1997</a> |
<a href="era3-1997-2003.html">1997-2003</a> |
<a href="era4-2004-2013.html">2004-2013</a> |
<a href="era5-2014-now.html">2014-Now</a> |
<a href="glossary.html">Glossary</a> |
<a href="bibliography.html">Bibliography</a> |
<a href="contributors.html">Contributors</a> |
<a href="discussion.html">Discussion</a>
</p>
<hr>'''
    
    # Clean up content - remove any embedded nav links that duplicate what we're adding
    cleaned_content = '\n'.join(content_lines)
    
    # Remove old nav blocks (links at top of content area)
    # Pattern: <p>\n<a href="/index.html">Hub</a><br>... </p>
    cleaned_content = re.sub(
        r'<p>\s*\n\s*<a href="/index\.html">Hub</a><br>.*?</p>',
        '', cleaned_content, flags=re.DOTALL
    )
    
    # Build the new file - pure HTML, no CSS, no JS
    new_content = f'''<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>
</head>
<body bgcolor="#c0c0c0">

{nav_links}

{cleaned_content.strip()}

<hr>
{nav_links}

</body>
</html>
'''
    
    write_file(filepath, new_content)
    print(f"  Processed HTML: {filepath}")


# ============================================================
# CSS SECTION - keep HTML + CSS, remove browser chrome, no JS
# ============================================================

def process_css_file(filepath):
    """Strip browser chrome from CSS section files. Keep HTML + CSS only."""
    content = read_file(filepath)
    lines = content.split('\n')
    
    title_match = re.search(r'<title>(.*?)</title>', content)
    title = title_match.group(1) if title_match else 'CSS History'
    
    basename = os.path.basename(filepath)
    
    # Extract the <style> block content
    style_match = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    style_content = style_match.group(1) if style_match else ''
    
    # Remove browser chrome CSS rules from the style content
    # Remove rules for: .browser-shell, .titlebar, .menubar, .toolbar, .tbtn,
    # .addrbar, .addr-label, .addr-field, .era-tabs, .etab, .etab-active,
    # .content-area, .statusbar, .status-right, .clear, .titlebar-right
    chrome_selectors = [
        r'\.browser-shell\s*\{[^}]*\}',
        r'\.titlebar[^{]*\{[^}]*\}',
        r'\.titlebar-right[^{]*\{[^}]*\}',
        r'\.menubar[^{]*\{[^}]*\}',
        r'\.menubar\s+span[^{]*\{[^}]*\}',
        r'\.toolbar[^{]*\{[^}]*\}',
        r'\.tbtn[^{]*\{[^}]*\}',
        r'\.addrbar[^{]*\{[^}]*\}',
        r'\.addr-label[^{]*\{[^}]*\}',
        r'\.addr-field[^{]*\{[^}]*\}',
        r'\.era-tabs[^{]*\{[^}]*\}',
        r'\.etab(?:-active)?[^{]*\{[^}]*\}',
        r'\.content-area[^{]*\{[^}]*\}',
        r'\.statusbar[^{]*\{[^}]*\}',
        r'\.status-right[^{]*\{[^}]*\}',
        r'\.clear[^{]*\{[^}]*\}',
        r'/\*\s*[-]+\s*Browser chrome[^*]*\*/',
    ]
    
    for pattern in chrome_selectors:
        style_content = re.sub(pattern, '', style_content, flags=re.DOTALL)
    
    # Clean up multiple blank lines
    style_content = re.sub(r'\n{3,}', '\n\n', style_content).strip()
    
    # Find the real content - after browser chrome, before status bar
    # For div-based: content is after era-tabs div, inside content-area or after it
    content_start = None
    content_end = None
    
    # Look for content markers
    for i, line in enumerate(lines):
        stripped = line.strip()
        if '<!-- ORIGINAL PAGE CONTENT' in line.upper() or '<!-- Original page content' in line:
            content_start = i + 1
            break
        if content_start is None and ('class="content-area"' in line or 'class="page"' in line or 'class="page-body"' in line):
            content_start = i + 1
            break
    
    if content_start is None:
        # Look for first <h1> or <header> after the era-tabs
        era_tabs_end = None
        for i, line in enumerate(lines):
            if 'era-tabs' in line or 'class="etab' in line:
                era_tabs_end = i
        if era_tabs_end:
            for i in range(era_tabs_end, len(lines)):
                stripped = lines[i].strip()
                if stripped.startswith('<h1') or stripped.startswith('<header') or stripped.startswith('<div class="page') or stripped.startswith('<div id="container') or stripped.startswith('<div id="wrap') or stripped.startswith('<div id="header'):
                    content_start = i
                    break
    
    if content_start is None:
        # Just look for the first h1
        for i, line in enumerate(lines):
            if '<h1' in line.lower():
                content_start = i
                break
    
    if content_start is None:
        print(f"  WARNING: Could not find content start in {filepath}")
        return
    
    # Find content end - look for status bar or closing browser-shell div
    for i in range(len(lines) - 1, content_start, -1):
        stripped = lines[i].strip()
        if '<!-- Status' in stripped or 'class="statusbar"' in stripped:
            content_end = i
            break
    
    if content_end is None:
        # Look for closing </div> of browser-shell
        for i in range(len(lines) - 1, content_start, -1):
            stripped = lines[i].strip()
            if '</body>' in stripped:
                content_end = i
                break
    
    if content_end is None:
        content_end = len(lines)
    
    # Go backwards to skip closing wrapper divs
    while content_end > content_start:
        stripped = lines[content_end - 1].strip()
        if stripped in ('</div>', '', '</div><!-- /browser-shell -->', '</div> <!-- browser-shell -->'):
            content_end -= 1
        elif stripped.startswith('</div>'):
            content_end -= 1
        else:
            break
    
    content_lines = lines[content_start:content_end]
    cleaned_content = '\n'.join(content_lines)
    
    # Remove any remaining browser chrome divs from content
    cleaned_content = re.sub(r'<div class="content-area">\s*', '', cleaned_content)
    
    # Remove any script blocks (CSS section should have no JS)
    cleaned_content = re.sub(r'<script[^>]*>.*?</script>', '', cleaned_content, flags=re.DOTALL)
    
    # Build navigation - styled with CSS
    nav_css = '''
    /* Navigation */
    .site-nav { padding: 8px; margin-bottom: 10px; }
    .site-nav a { margin-right: 8px; }'''
    
    nav_html = '''<nav class="site-nav">
  <a href="/index.html">Hub</a> |
  <a href="csshome.html">Home</a> |
  <a href="era-1-1994-1996.html">1994-1996</a> |
  <a href="era-2-1996-1998.html">1996-1998</a> |
  <a href="era-3-1998-2004.html">1998-2004</a> |
  <a href="era-4-2004-2011.html">2004-2011</a> |
  <a href="era-5-2011-2017.html">2011-2017</a> |
  <a href="era-6-2017-2026.html">2017-2026</a> |
  <a href="glossary.html">Glossary</a> |
  <a href="bibliography.html">Bibliography</a> |
  <a href="contributors.html">Contributors</a> |
  <a href="discussion.html">Discussion</a>
</nav>'''
    
    # Build new file
    new_content = f'''<!doctype html>
<html>
<head>
  <title>{title}</title>
  <meta charset="utf-8">
  <style type="text/css">
{style_content}
{nav_css}
  </style>
</head>
<body>

{nav_html}

{cleaned_content.strip()}

{nav_html}

</body>
</html>
'''
    
    write_file(filepath, new_content)
    print(f"  Processed CSS: {filepath}")


# ============================================================
# JAVASCRIPT SECTION - keep HTML + CSS + JS, remove browser chrome
# ============================================================

def process_js_file(filepath):
    """Strip browser chrome from JavaScript section files. Keep HTML + CSS + JS."""
    content = read_file(filepath)
    lines = content.split('\n')
    
    title_match = re.search(r'<title>(.*?)</title>', content)
    title = title_match.group(1) if title_match else 'JavaScript History'
    
    basename = os.path.basename(filepath)
    
    # Extract the <style> block content
    style_match = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    style_content = style_match.group(1) if style_match else ''
    
    # Remove browser chrome CSS rules
    chrome_selectors = [
        r'\.browser-shell\s*\{[^}]*\}',
        r'\.titlebar[^{]*\{[^}]*\}',
        r'\.titlebar-right[^{]*\{[^}]*\}',
        r'\.menubar[^{]*\{[^}]*\}',
        r'\.menubar\s+span[^{]*\{[^}]*\}',
        r'\.toolbar[^{]*\{[^}]*\}',
        r'\.tbtn[^{]*\{[^}]*\}',
        r'\.addrbar[^{]*\{[^}]*\}',
        r'\.addr-label[^{]*\{[^}]*\}',
        r'\.addr-field[^{]*\{[^}]*\}',
        r'\.era-tabs[^{]*\{[^}]*\}',
        r'\.etab(?:-active)?[^{]*\{[^}]*\}',
        r'\.content-area[^{]*\{[^}]*\}',
        r'\.statusbar[^{]*\{[^}]*\}',
        r'\.status-right[^{]*\{[^}]*\}',
        r'\.status-left[^{]*\{[^}]*\}',
        r'\.clear[^{]*\{[^}]*\}',
        r'/\*\s*[-]+\s*Browser chrome[^*]*\*/',
    ]
    
    for pattern in chrome_selectors:
        style_content = re.sub(pattern, '', style_content, flags=re.DOTALL)
    
    style_content = re.sub(r'\n{3,}', '\n\n', style_content).strip()
    
    # Extract ALL <script> blocks
    script_blocks = re.findall(r'<script[^>]*>.*?</script>', content, re.DOTALL)
    
    # Filter out chrome-only scripts (initChrome, etc.)
    filtered_scripts = []
    for script in script_blocks:
        # Keep scripts that have actual demo/content functionality
        # Remove scripts that only have initChrome or chrome state management
        if 'initChrome' in script and len(script) < 500:
            # Small chrome-only script, skip
            continue
        # Remove initChrome function from larger scripts
        cleaned_script = re.sub(r'function\s+initChrome\s*\(\)\s*\{[^}]*\}', '', script)
        if cleaned_script.strip() != '<script></script>' and cleaned_script.strip() != '<script>\n</script>':
            filtered_scripts.append(cleaned_script)
    
    # Find real content 
    content_start = None
    content_end = None
    
    # For the 1995.html table-based file
    if '1995.html' in filepath:
        for i, line in enumerate(lines):
            if '<!-- ORIGINAL PAGE CONTENT' in line.upper():
                content_start = i + 1
                break
            if '<center>' in line and i > 60:
                content_start = i
                break
        
        if content_start:
            # Find end - look for script blocks or closing tables
            for i in range(len(lines) - 1, content_start, -1):
                stripped = lines[i].strip()
                if '<!-- Status' in stripped or ('Document:' in stripped and 'Done' in stripped):
                    content_end = i
                    break
            
            if content_end is None:
                for i in range(len(lines) - 1, content_start, -1):
                    if '</body>' in lines[i]:
                        content_end = i
                        break
            
            # Strip closing wrapper tables
            while content_end > content_start:
                stripped = lines[content_end - 1].strip()
                if stripped in ('</td></tr>', '</table>', '</td>', '</tr>', '', '</td></tr></table>', '</div>'):
                    content_end -= 1
                elif stripped.startswith('</table>') or stripped.startswith('</td>'):
                    content_end -= 1
                else:
                    break
    else:
        # Div-based structure
        for i, line in enumerate(lines):
            stripped = line.strip()
            if '<!-- ORIGINAL PAGE CONTENT' in line.upper() or '<!-- Original page' in line:
                content_start = i + 1
                break
            if content_start is None and ('class="page-body"' in line or 'class="page"' in line):
                content_start = i + 1
                break
        
        if content_start is None:
            era_tabs_end = None
            for i, line in enumerate(lines):
                if 'era-tabs' in line or 'class="etab' in line:
                    era_tabs_end = i
            if era_tabs_end:
                for i in range(era_tabs_end, len(lines)):
                    stripped = lines[i].strip()
                    if (stripped.startswith('<h1') or stripped.startswith('<header') or 
                        stripped.startswith('<nav') or stripped.startswith('<site-header') or
                        stripped.startswith('<div class="page') or stripped.startswith('<div id="') or
                        stripped.startswith('<!-- Content')):
                        content_start = i
                        break
        
        if content_start is None:
            for i, line in enumerate(lines):
                if '<h1' in line.lower() and i > 30:
                    content_start = i
                    break
        
        if content_start is None:
            print(f"  WARNING: Could not find content start in {filepath}")
            return
        
        # Find content end
        for i in range(len(lines) - 1, content_start, -1):
            stripped = lines[i].strip()
            if '<!-- Status' in stripped or 'class="statusbar"' in stripped:
                content_end = i
                break
        
        if content_end is None:
            for i in range(len(lines) - 1, content_start, -1):
                if '</body>' in lines[i]:
                    content_end = i
                    break
        
        if content_end is None:
            content_end = len(lines)
        
        # Skip closing wrappers
        while content_end > content_start:
            stripped = lines[content_end - 1].strip()
            if stripped in ('</div>', '', '</div><!-- /browser-shell -->', '</div> <!-- browser-shell -->'):
                content_end -= 1
            elif stripped.startswith('</div>') and 'browser' in stripped.lower():
                content_end -= 1
            elif stripped == '</div>' or stripped == '':
                content_end -= 1
            else:
                break
    
    content_lines = lines[content_start:content_end]
    cleaned_content = '\n'.join(content_lines)
    
    # Remove content-area wrapper divs
    cleaned_content = re.sub(r'<div class="content-area">\s*', '', cleaned_content)
    
    # Build navigation
    nav_html = '''<nav class="site-nav">
  <a href="/index.html">Hub</a> |
  <a href="jsindex.html">Home</a> |
  <a href="1995.html">1995</a> |
  <a href="1999.html">1999</a> |
  <a href="2009.html">2009</a> |
  <a href="2015.html">2015</a> |
  <a href="2025.html">2025</a> |
  <a href="glossary.html">Glossary</a> |
  <a href="bibliography.html">Bibliography</a> |
  <a href="contributors.html">Contributors</a> |
  <a href="discussion.html">Discussion</a>
</nav>'''
    
    nav_css = '''
    /* Navigation */
    .site-nav { padding: 8px; margin-bottom: 10px; }
    .site-nav a { margin-right: 8px; }'''
    
    # For 1995.html - no CSS at all, use table-based nav and basic HTML
    if '1995.html' in filepath:
        nav_1995 = '''<table width="600" border="0" cellpadding="4" cellspacing="0" align="center">
<tr><td>
<font face="Arial, Helvetica" size="2">
<a href="/index.html">Hub</a> |
<a href="jsindex.html">Home</a> |
<a href="1995.html">1995</a> |
<a href="1999.html">1999</a> |
<a href="2009.html">2009</a> |
<a href="2015.html">2015</a> |
<a href="2025.html">2025</a> |
<a href="glossary.html">Glossary</a> |
<a href="bibliography.html">Bibliography</a> |
<a href="contributors.html">Contributors</a> |
<a href="discussion.html">Discussion</a>
</font>
</td></tr>
</table>
<hr>'''
        
        scripts_text = '\n'.join(filtered_scripts)
        new_content = f'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<title>{title}</title>
</head>
<body bgcolor="#c0c0c0">

{nav_1995}

{cleaned_content.strip()}

<hr>
{nav_1995}

{scripts_text}

</body>
</html>
'''
    else:
        scripts_text = '\n'.join(filtered_scripts)
        
        # Check if there's an onload handler we need to preserve
        onload_match = re.search(r'onload="([^"]*)"', content)
        onload_attr = ''
        if onload_match:
            handler = onload_match.group(1)
            if 'initChrome' not in handler:
                onload_attr = f' onload="{handler}"'
        
        new_content = f'''<!doctype html>
<html>
<head>
  <title>{title}</title>
  <meta charset="utf-8">
  <style type="text/css">
{style_content}
{nav_css}
  </style>
</head>
<body{onload_attr}>

{nav_html}

{cleaned_content.strip()}

{nav_html}

{scripts_text}

</body>
</html>
'''
    
    write_file(filepath, new_content)
    print(f"  Processed JS: {filepath}")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("=== Processing HTML section files ===")
    html_files = [
        'html/era1-1990-1994.html',
        'html/era2-1994-1997.html',
        'html/era3-1997-2003.html',
        'html/era4-2004-2013.html',
        'html/era5-2014-now.html',
        'html/htmlhome.html',
        'html/glossary.html',
        'html/bibliography.html',
        'html/contributors.html',
        'html/discussion.html',
    ]
    for f in html_files:
        process_html_file(os.path.join(BASE, f))
    
    print("\n=== Processing CSS section files ===")
    css_files = [
        'css/era-1-1994-1996.html',
        'css/era-2-1996-1998.html',
        'css/era-3-1998-2004.html',
        'css/era-4-2004-2011.html',
        'css/era-5-2011-2017.html',
        'css/era-6-2017-2026.html',
        'css/csshome.html',
        'css/glossary.html',
        'css/bibliography.html',
        'css/contributors.html',
        'css/discussion.html',
    ]
    for f in css_files:
        process_css_file(os.path.join(BASE, f))
    
    print("\n=== Processing JavaScript section files ===")
    js_files = [
        'javascript/1995.html',
        'javascript/1999.html',
        'javascript/2009.html',
        'javascript/2015.html',
        'javascript/2025.html',
        'javascript/jsindex.html',
        'javascript/glossary.html',
        'javascript/bibliography.html',
        'javascript/contributors.html',
        'javascript/discussion.html',
    ]
    for f in js_files:
        process_js_file(os.path.join(BASE, f))
    
    print("\nDone!")
