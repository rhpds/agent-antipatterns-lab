-- Let Pandoc parse Markdown; adapt only Antora's document title, diagrams and reveals.
function Header(header)
  if header.level == 1 then
    return pandoc.RawBlock('asciidoc', '= ' .. pandoc.utils.stringify(header.content) .. '\n\n')
  end
  header.level = header.level - 1
  return header
end

function CodeBlock(block)
  if block.classes:includes('mermaid') then
    return pandoc.RawBlock('asciidoc', '[mermaid]\n....\n' .. block.text .. '\n....\n\n')
  end
end

function Blocks(blocks)
  local result = pandoc.List()
  local i = 1
  while i <= #blocks do
    local block = blocks[i]
    if block.t == 'RawBlock' and block.format == 'html' then
      -- Pandoc parses details/summary into separate blocks, with a parsed summary between them.
      if block.text == '<details>' and blocks[i + 1] and blocks[i + 3] and
         blocks[i + 1].text == '<summary>' and blocks[i + 3].text == '</summary>' then
        result:insert(pandoc.RawBlock('asciidoc', '.' .. pandoc.utils.stringify(blocks[i + 2]) ..
          '\n[%collapsible]\n====\n\n'))
        i = i + 3
      elseif block.text == '</details>' then
        result:insert(pandoc.RawBlock('asciidoc', '\n====\n\n'))
      else
        error('Unsupported raw HTML in notebook: ' .. block.text)
      end
    else
      result:insert(block)
    end
    i = i + 1
  end
  return result
end

function Link(link)
  local target = link.target
  if target:match('^%a[%w+.-]*:') or target:match('^#') or target:match('^//') then return end
  if target:match('^module%-%d[^/]*%.ipynb$') then
    return pandoc.RawInline('asciidoc', 'xref:' .. target:gsub('%.ipynb$', '.adoc') ..
      '[' .. pandoc.utils.stringify(link.content) .. ']')
  end
  -- Notebook-relative repository links must remain useful without a running workbench.
  local parts = {'notebooks'}
  for part in target:gmatch('[^/]+') do
    if part == '..' then
      if #parts == 0 then error('Link escapes repository: ' .. target) end
      table.remove(parts)
    elseif part ~= '.' then
      table.insert(parts, part)
    end
  end
  link.target = '{lab-source-url}/' .. table.concat(parts, '/')
  return link
end
