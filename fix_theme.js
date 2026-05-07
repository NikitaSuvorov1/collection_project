const fs = require('fs');
const path = require('path');

const srcDir = 'c:/project/collection_app/frontend/src';

// Mapping старых цветов на переменные
const colorMap = {
  '#0d1117': 'var(--bg-body)',
  '#161b22': 'var(--bg-card)',
  '#1c2128': 'var(--bg-surface)',
  '#21262d': 'var(--bg-elevated)',
  '#30363d': 'var(--border)',
  '#e6edf3': 'var(--text-primary)',
  '#8b949e': 'var(--text-secondary)',
  '#484f58': 'var(--text-muted)',
  '#388bfd': 'var(--accent)',
  '#58a6ff': 'var(--accent-hover)',
  '#3fb950': 'var(--success)',
  '#d29922': 'var(--warning)',
  '#f85149': 'var(--danger)',
};

function replaceColors(content) {
  let result = content;
  for (const [oldColor, newColor] of Object.entries(colorMap)) {
    const regex = new RegExp(oldColor.replace(/#/g, '\\#'), 'gi');
    result = result.replace(regex, newColor);
  }
  return result;
}

const files = fs.readdirSync(srcDir).filter(f => f.endsWith('.jsx') || f.endsWith('.js'));

files.forEach(file => {
  const filePath = path.join(srcDir, file);
  let content = fs.readFileSync(filePath, 'utf8');
  const updated = replaceColors(content);

  if (content !== updated) {
    fs.writeFileSync(filePath, updated, 'utf8');
    console.log(`✅ Updated: ${file}`);
  }
});

console.log('Done!');
